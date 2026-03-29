import os
import pickle
import random
from typing import Optional, List, Dict, Any, Tuple

import numpy as np
import pandas as pd
import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# =========================
# ENVIRONMENT VARIABLES
# =========================
load_dotenv()
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMG_500 = "https://image.tmdb.org/t/p/w500"

if not TMDB_API_KEY:
    raise RuntimeError("TMDB_API_KEY missing. Add it to .env file as TMDB_API_KEY=your_key_here")


# =========================
# FASTAPI APP INITIALIZATION
# =========================
app = FastAPI(
    title="MoodFlix API",
    description="Movie recommendation API with mood-based suggestions",
    version="3.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# MOOD CONFIGURATION
# =========================
MOOD_TO_GENRES = {
    "Happy": [35, 10751],
    "Sad": [18],
    "Scared": [27],
    "Excited": [28, 12],
    "Romantic": [10749],
    "Thoughtful": [9648, 99],
    "Relaxed": [10751, 16],
    "Adventurous": [12, 14],
    "Funny": [35],
    "Motivated": [99, 36],
    "Family": [10751],
    "Mysterious": [9648, 80],
}

MOOD_SETTINGS = {
    "Happy": {"sort": "vote_average.desc", "min_rating": 7.0, "exclude": [18, 27]},
    "Sad": {"sort": "vote_average.desc", "min_rating": 7.5, "exclude": [35, 10751]},
    "Scared": {"sort": "popularity.desc", "min_rating": 6.0, "exclude": [35, 10749]},
    "Excited": {"sort": "popularity.desc", "min_rating": 7.0, "exclude": [18]},
    "Romantic": {"sort": "vote_average.desc", "min_rating": 7.0, "exclude": [27, 53]},
    "Thoughtful": {"sort": "vote_average.desc", "min_rating": 7.5, "exclude": [35]},
    "Relaxed": {"sort": "vote_average.desc", "min_rating": 6.5, "exclude": [27, 53]},
    "Adventurous": {"sort": "popularity.desc", "min_rating": 7.0, "exclude": [18]},
    "Funny": {"sort": "vote_average.desc", "min_rating": 7.0, "exclude": [18, 27]},
    "Motivated": {"sort": "vote_average.desc", "min_rating": 7.5, "exclude": [27]},
    "Family": {"sort": "vote_average.desc", "min_rating": 6.5, "exclude": [27, 53]},
    "Mysterious": {"sort": "vote_average.desc", "min_rating": 7.0, "exclude": [35]},
}


# =========================
# PICKLE FILE PATHS
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DF_PATH = os.path.join(BASE_DIR, "df.pkl")
INDICES_PATH = os.path.join(BASE_DIR, "indices.pkl")
TFIDF_MATRIX_PATH = os.path.join(BASE_DIR, "tfidf_matrix.pkl")
TFIDF_PATH = os.path.join(BASE_DIR, "tfidf.pkl")

# Global variables for TF-IDF
df: Optional[pd.DataFrame] = None
indices_obj: Any = None
tfidf_matrix: Any = None
tfidf_obj: Any = None
TITLE_TO_IDX: Optional[Dict[str, int]] = None


# =========================
# PYDANTIC MODELS
# =========================
class TMDBMovieCard(BaseModel):
    tmdb_id: int
    title: str
    poster_url: Optional[str] = None
    release_date: Optional[str] = None
    vote_average: Optional[float] = None


class TMDBMovieDetails(BaseModel):
    tmdb_id: int
    title: str
    overview: Optional[str] = None
    release_date: Optional[str] = None
    poster_url: Optional[str] = None
    backdrop_url: Optional[str] = None
    genres: List[dict] = []


class TFIDFRecItem(BaseModel):
    title: str
    score: float
    tmdb: Optional[TMDBMovieCard] = None


class SearchBundleResponse(BaseModel):
    query: str
    movie_details: TMDBMovieDetails
    tfidf_recommendations: List[TFIDFRecItem]
    genre_recommendations: List[TMDBMovieCard]


class MoodInfo(BaseModel):
    name: str
    emoji: str
    description: str


class HealthResponse(BaseModel):
    status: str
    tfidf_loaded: bool
    movie_count: int


# =========================
# UTILITY FUNCTIONS
# =========================
def _norm_title(t: str) -> str:
    """Normalize title for comparison"""
    return str(t).strip().lower()


def make_img_url(path: Optional[str]) -> Optional[str]:
    """Create full TMDB image URL"""
    if not path:
        return None
    return f"{TMDB_IMG_500}{path}"


async def tmdb_get(path: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Make GET request to TMDB API"""
    q = dict(params)
    q["api_key"] = TMDB_API_KEY

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(f"{TMDB_BASE}{path}", params=q)
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=502,
            detail=f"TMDB request error: {type(e).__name__}"
        )

    if r.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"TMDB error {r.status_code}: {r.text[:200]}"
        )

    return r.json()


async def tmdb_cards_from_results(
    results: List[dict],
    limit: int = 20
) -> List[TMDBMovieCard]:
    """Convert TMDB results to movie cards"""
    out: List[TMDBMovieCard] = []
    for m in (results or [])[:limit]:
        out.append(
            TMDBMovieCard(
                tmdb_id=int(m["id"]),
                title=m.get("title") or m.get("name") or "",
                poster_url=make_img_url(m.get("poster_path")),
                release_date=m.get("release_date"),
                vote_average=m.get("vote_average"),
            )
        )
    return out


async def tmdb_movie_details(movie_id: int) -> TMDBMovieDetails:
    """Get detailed movie info from TMDB"""
    data = await tmdb_get(f"/movie/{movie_id}", {"language": "en-US"})
    return TMDBMovieDetails(
        tmdb_id=int(data["id"]),
        title=data.get("title") or "",
        overview=data.get("overview"),
        release_date=data.get("release_date"),
        poster_url=make_img_url(data.get("poster_path")),
        backdrop_url=make_img_url(data.get("backdrop_path")),
        genres=data.get("genres", []) or [],
    )


async def tmdb_search_movies(query: str, page: int = 1) -> Dict[str, Any]:
    """Search movies on TMDB"""
    return await tmdb_get(
        "/search/movie",
        {
            "query": query,
            "include_adult": "false",
            "language": "en-US",
            "page": page,
        },
    )


async def tmdb_search_first(query: str) -> Optional[dict]:
    """Get first movie from TMDB search"""
    data = await tmdb_search_movies(query=query, page=1)
    results = data.get("results", [])
    return results[0] if results else None


# =========================
# TF-IDF HELPER FUNCTIONS
# =========================
def build_title_to_idx_map(indices: Any) -> Dict[str, int]:
    """Build title to index mapping"""
    title_to_idx: Dict[str, int] = {}
    
    if isinstance(indices, dict):
        for k, v in indices.items():
            title_to_idx[_norm_title(k)] = int(v)
        return title_to_idx
    
    try:
        for k, v in indices.items():
            title_to_idx[_norm_title(k)] = int(v)
        return title_to_idx
    except Exception:
        raise RuntimeError("indices.pkl must be dict or pandas Series-like")


def get_local_idx_by_title(title: str) -> int:
    """Get local index for a movie title"""
    global TITLE_TO_IDX
    if TITLE_TO_IDX is None:
        raise HTTPException(status_code=500, detail="TF-IDF not initialized")
    key = _norm_title(title)
    if key in TITLE_TO_IDX:
        return int(TITLE_TO_IDX[key])
    raise HTTPException(status_code=404, detail=f"Title not found: '{title}'")


def tfidf_recommend_titles(query_title: str, top_n: int = 10) -> List[Tuple[str, float]]:
    """Get TF-IDF based recommendations"""
    global df, tfidf_matrix
    if df is None or tfidf_matrix is None:
        raise HTTPException(status_code=500, detail="TF-IDF not loaded")

    idx = get_local_idx_by_title(query_title)
    qv = tfidf_matrix[idx]
    scores = (tfidf_matrix @ qv.T).toarray().ravel()
    order = np.argsort(-scores)

    out: List[Tuple[str, float]] = []
    for i in order:
        if int(i) == int(idx):
            continue
        try:
            title_i = str(df.iloc[int(i)]["title"])
        except Exception:
            continue
        out.append((title_i, float(scores[int(i)])))
        if len(out) >= top_n:
            break
    return out


async def attach_tmdb_card_by_title(title: str) -> Optional[TMDBMovieCard]:
    """Attach TMDB card to a title"""
    try:
        m = await tmdb_search_first(title)
        if not m:
            return None
        return TMDBMovieCard(
            tmdb_id=int(m["id"]),
            title=m.get("title") or title,
            poster_url=make_img_url(m.get("poster_path")),
            release_date=m.get("release_date"),
            vote_average=m.get("vote_average"),
        )
    except Exception:
        return None


# =========================
# STARTUP EVENT
# =========================
@app.on_event("startup")
def load_pickles():
    """Load pickle files on startup"""
    global df, indices_obj, tfidf_matrix, tfidf_obj, TITLE_TO_IDX

    try:
        with open(DF_PATH, "rb") as f:
            df = pickle.load(f)
        with open(INDICES_PATH, "rb") as f:
            indices_obj = pickle.load(f)
        with open(TFIDF_MATRIX_PATH, "rb") as f:
            tfidf_matrix = pickle.load(f)
        with open(TFIDF_PATH, "rb") as f:
            tfidf_obj = pickle.load(f)
        
        TITLE_TO_IDX = build_title_to_idx_map(indices_obj)
        print(f"✅ Loaded {len(df)} movies from pickle files")
        
    except FileNotFoundError as e:
        print(f"⚠️ Pickle file not found: {e}. TF-IDF features disabled.")
    except Exception as e:
        print(f"⚠️ Error loading pickles: {e}. TF-IDF features disabled.")


# =========================
# API ROUTES
# =========================

@app.get("/")
def root():
    """Root endpoint - API info"""
    return {
        "message": "🎬 MoodFlix API is running!",
        "version": "3.0",
        "docs": "/docs",
        "endpoints": {
            "health": "/health",
            "home": "/home",
            "search": "/tmdb/search",
            "discover": "/tmdb/discover",
            "movie_details": "/movie/id/{tmdb_id}",
            "mood_recommendations": "/recommend/mood",
            "genre_recommendations": "/recommend/genre",
            "moods_list": "/moods",
        }
    }


@app.get("/health", response_model=HealthResponse)
def health():
    """Health check endpoint"""
    return HealthResponse(
        status="ok",
        tfidf_loaded=df is not None,
        movie_count=len(df) if df is not None else 0
    )


@app.get("/moods")
def get_available_moods():
    """Get list of available moods"""
    return {
        "moods": [
            {"name": "Happy", "emoji": "😊", "description": "Feel-good comedies"},
            {"name": "Sad", "emoji": "😢", "description": "Emotional dramas"},
            {"name": "Scared", "emoji": "😱", "description": "Horror thrillers"},
            {"name": "Excited", "emoji": "🤩", "description": "Action adventures"},
            {"name": "Romantic", "emoji": "💕", "description": "Love stories"},
            {"name": "Thoughtful", "emoji": "🤔", "description": "Mind-bending films"},
            {"name": "Relaxed", "emoji": "😌", "description": "Easy watching"},
            {"name": "Adventurous", "emoji": "🚀", "description": "Epic journeys"},
            {"name": "Funny", "emoji": "😂", "description": "Comedies"},
            {"name": "Motivated", "emoji": "💪", "description": "Inspiring stories"},
            {"name": "Family", "emoji": "👨‍👩‍👧‍👦", "description": "All ages"},
            {"name": "Mysterious", "emoji": "🔮", "description": "Crime mysteries"},
        ]
    }


@app.get("/home", response_model=List[TMDBMovieCard])
async def home(
    category: str = Query("popular", description="Category: trending, popular, top_rated, now_playing, upcoming"),
    limit: int = Query(24, ge=1, le=50),
):
    """Get home feed movies by category"""
    try:
        if category == "trending":
            data = await tmdb_get("/trending/movie/day", {"language": "en-US"})
            return await tmdb_cards_from_results(data.get("results", []), limit=limit)

        if category not in {"popular", "top_rated", "upcoming", "now_playing"}:
            raise HTTPException(status_code=400, detail=f"Invalid category: {category}")

        data = await tmdb_get(f"/movie/{category}", {"language": "en-US", "page": 1})
        return await tmdb_cards_from_results(data.get("results", []), limit=limit)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch movies: {e}")


@app.get("/tmdb/search")
async def tmdb_search(
    query: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1, le=10),
):
    """Search movies on TMDB"""
    return await tmdb_search_movies(query=query, page=page)


@app.get("/tmdb/discover")
async def tmdb_discover(
    with_genres: Optional[str] = Query(None, description="Genre IDs (comma-separated)"),
    without_genres: Optional[str] = Query(None, description="Exclude genre IDs"),
    sort_by: str = Query("popularity.desc"),
    page: int = Query(1, ge=1, le=10),
    language: str = Query("en-US"),
):
    """
    TMDB Discover endpoint - for mood-based recommendations
    """
    params = {
        "language": language,
        "sort_by": sort_by,
        "page": page,
        "vote_count.gte": 50,
    }
    
    if with_genres:
        params["with_genres"] = with_genres
    if without_genres:
        params["without_genres"] = without_genres
    
    return await tmdb_get("/discover/movie", params)


@app.get("/movie/id/{tmdb_id}", response_model=TMDBMovieDetails)
async def movie_details_route(tmdb_id: int):
    """Get movie details by TMDB ID"""
    return await tmdb_movie_details(tmdb_id)


@app.get("/recommend/mood", response_model=List[TMDBMovieCard])
async def recommend_by_mood(
    mood: str = Query(..., description="User's current mood"),
    limit: int = Query(24, ge=1, le=50),
    page: int = Query(1, ge=1, le=10),
):
    """
    Get movie recommendations based on mood.
    
    Supported moods: Happy, Sad, Scared, Excited, Romantic, Thoughtful,
    Relaxed, Adventurous, Funny, Motivated, Family, Mysterious
    """
    mood_normalized = mood.strip().title()
    genre_ids = MOOD_TO_GENRES.get(mood_normalized)
    
    if not genre_ids:
        # Fallback to popular
        data = await tmdb_get("/movie/popular", {"language": "en-US", "page": page})
        return await tmdb_cards_from_results(data.get("results", []), limit=limit)
    
    settings = MOOD_SETTINGS.get(mood_normalized, {
        "sort": "popularity.desc",
        "min_rating": 6.0,
        "exclude": []
    })
    
    # Use primary genre
    primary_genre = genre_ids[0]
    exclude_genres = settings.get("exclude", [])
    
    discover_params = {
        "with_genres": str(primary_genre),
        "language": "en-US",
        "sort_by": settings["sort"],
        "page": page,
        "vote_count.gte": 50,
        "vote_average.gte": settings["min_rating"],
    }
    
    if exclude_genres:
        discover_params["without_genres"] = ",".join(str(g) for g in exclude_genres)
    
    try:
        data = await tmdb_get("/discover/movie", discover_params)
        cards = await tmdb_cards_from_results(data.get("results", []), limit=limit)
        
        # Shuffle for variety
        cards_list = list(cards)
        random.shuffle(cards_list)
        
        # If not enough, try with relaxed filters
        if len(cards_list) < limit // 2:
            discover_params["vote_count.gte"] = 20
            discover_params["vote_average.gte"] = 5.5
            data = await tmdb_get("/discover/movie", discover_params)
            cards = await tmdb_cards_from_results(data.get("results", []), limit=limit)
            cards_list = list(cards)
            random.shuffle(cards_list)
        
        return cards_list[:limit]
        
    except Exception as e:
        print(f"Mood recommendation error: {e}")
        data = await tmdb_get("/movie/popular", {"language": "en-US", "page": 1})
        return await tmdb_cards_from_results(data.get("results", []), limit=limit)


@app.get("/recommend/genre", response_model=List[TMDBMovieCard])
async def recommend_genre(
    tmdb_id: int = Query(..., description="TMDB movie ID"),
    limit: int = Query(18, ge=1, le=50),
):
    """Get recommendations based on movie's genre"""
    details = await tmdb_movie_details(tmdb_id)
    if not details.genres:
        return []

    genre_id = details.genres[0]["id"]
    discover = await tmdb_get(
        "/discover/movie",
        {
            "with_genres": genre_id,
            "language": "en-US",
            "sort_by": "popularity.desc",
            "page": 1,
        },
    )
    cards = await tmdb_cards_from_results(discover.get("results", []), limit=limit)
    return [c for c in cards if c.tmdb_id != tmdb_id]


@app.get("/recommend/tfidf")
async def recommend_tfidf(
    title: str = Query(..., min_length=1, description="Movie title"),
    top_n: int = Query(10, ge=1, le=50),
):
    """Get TF-IDF based recommendations"""
    if df is None:
        raise HTTPException(status_code=503, detail="TF-IDF model not loaded")
    
    recs = tfidf_recommend_titles(title, top_n=top_n)
    return [{"title": t, "score": s} for t, s in recs]


@app.get("/movie/search", response_model=SearchBundleResponse)
async def search_bundle(
    query: str = Query(..., min_length=1, description="Search query"),
    tfidf_top_n: int = Query(12, ge=1, le=30),
    genre_limit: int = Query(12, ge=1, le=30),
):
    """Search movie and get bundled recommendations"""
    best = await tmdb_search_first(query)
    if not best:
        raise HTTPException(status_code=404, detail=f"No movie found for: {query}")

    tmdb_id = int(best["id"])
    details = await tmdb_movie_details(tmdb_id)

    # TF-IDF recommendations
    tfidf_items: List[TFIDFRecItem] = []
    
    if df is not None:
        try:
            recs = tfidf_recommend_titles(details.title, top_n=tfidf_top_n)
        except Exception:
            try:
                recs = tfidf_recommend_titles(query, top_n=tfidf_top_n)
            except Exception:
                recs = []

        for title, score in recs:
            card = await attach_tmdb_card_by_title(title)
            tfidf_items.append(TFIDFRecItem(title=title, score=score, tmdb=card))

    # Genre recommendations
    genre_recs: List[TMDBMovieCard] = []
    if details.genres:
        genre_id = details.genres[0]["id"]
        discover = await tmdb_get(
            "/discover/movie",
            {
                "with_genres": genre_id,
                "language": "en-US",
                "sort_by": "popularity.desc",
                "page": 1,
            },
        )
        cards = await tmdb_cards_from_results(
            discover.get("results", []), limit=genre_limit
        )
        genre_recs = [c for c in cards if c.tmdb_id != details.tmdb_id]

    return SearchBundleResponse(
        query=query,
        movie_details=details,
        tfidf_recommendations=tfidf_items,
        genre_recommendations=genre_recs,
    )


# =========================
# RUN SERVER (for local dev)
# =========================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)