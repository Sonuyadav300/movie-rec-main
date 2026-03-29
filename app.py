import requests
import streamlit as st
import random

# =============================
# CONFIG
# =============================
API_BASE = "https://movie-rec-466x.onrender.com"  # Change to your API URL
TMDB_IMG = "https://image.tmdb.org/t/p/w500"

st.set_page_config(page_title="MoodFlix - Movie Recommender", page_icon="🎬", layout="wide")

# =============================
# MOOD CONFIGURATION WITH TMDB GENRE IDs
# =============================
MOOD_CONFIG = {
    "Happy": {
        "emoji": "😊",
        "name": "Happy",
        "description": "Feel-good comedies and uplifting stories",
        "color": "#FFD700",
        "genre_ids": [35, 10751],
        "exclude_genres": [18, 27],
    },
    "Sad": {
        "emoji": "😢",
        "name": "Sad",
        "description": "Emotional dramas and tearjerkers",
        "color": "#6495ED",
        "genre_ids": [18],
        "exclude_genres": [35, 10751],
    },
    "Scared": {
        "emoji": "😱",
        "name": "Scared",
        "description": "Horror and spine-chilling thrillers",
        "color": "#8B0000",
        "genre_ids": [27],
        "exclude_genres": [35, 10749],
    },
    "Excited": {
        "emoji": "🤩",
        "name": "Excited",
        "description": "Action-packed adventures",
        "color": "#FF4500",
        "genre_ids": [28],
        "exclude_genres": [18, 10749],
    },
    "Romantic": {
        "emoji": "💕",
        "name": "Romantic",
        "description": "Love stories and romantic comedies",
        "color": "#FF69B4",
        "genre_ids": [10749],
        "exclude_genres": [27, 53],
    },
    "Thoughtful": {
        "emoji": "🤔",
        "name": "Thoughtful",
        "description": "Mind-bending mysteries and thrillers",
        "color": "#9370DB",
        "genre_ids": [9648],
        "exclude_genres": [35, 10751],
    },
    "Relaxed": {
        "emoji": "😌",
        "name": "Relaxed",
        "description": "Light-hearted and easy watching",
        "color": "#98FB98",
        "genre_ids": [16, 10751],
        "exclude_genres": [27, 53],
    },
    "Adventurous": {
        "emoji": "🚀",
        "name": "Adventurous",
        "description": "Epic journeys and fantasy worlds",
        "color": "#00CED1",
        "genre_ids": [12, 14],
        "exclude_genres": [18],
    },
    "Funny": {
        "emoji": "😂",
        "name": "Funny",
        "description": "Laugh-out-loud comedies",
        "color": "#FFA500",
        "genre_ids": [35],
        "exclude_genres": [18, 27],
    },
    "Motivated": {
        "emoji": "💪",
        "name": "Motivated",
        "description": "Inspiring true stories and sports dramas",
        "color": "#32CD32",
        "genre_ids": [36, 18],
        "exclude_genres": [27, 35],
    },
    "Family": {
        "emoji": "👨‍👩‍👧‍👦",
        "name": "Family",
        "description": "Fun for the whole family",
        "color": "#87CEEB",
        "genre_ids": [10751, 16],
        "exclude_genres": [27, 53],
    },
    "Mysterious": {
        "emoji": "🔮",
        "name": "Mysterious",
        "description": "Crime and detective stories",
        "color": "#4B0082",
        "genre_ids": [80, 9648],
        "exclude_genres": [35, 10751],
    },
}

# =============================
# STYLES
# =============================
st.markdown(
    """
<style>
/* General Layout */
.block-container { 
    padding-top: 1rem; 
    padding-bottom: 2rem; 
    max-width: 1400px; 
}

/* Text Styles */
.small-muted { 
    color: #6b7280; 
    font-size: 0.92rem; 
}

.movie-title { 
    font-size: 0.9rem; 
    line-height: 1.15rem; 
    height: 2.3rem; 
    overflow: hidden; 
    text-align: center; 
    font-weight: 500; 
}

/* Card Styles */
.card { 
    border: 1px solid rgba(0,0,0,0.08); 
    border-radius: 16px; 
    padding: 14px; 
    background: rgba(255,255,255,0.7); 
}

/* Mood Section Header */
.mood-section-header { 
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
    padding: 30px; 
    border-radius: 20px; 
    margin: 20px 0; 
    text-align: center; 
}

/* Image Hover Effect */
.stImage > img {
    border-radius: 12px;
    transition: transform 0.3s ease;
}

.stImage > img:hover {
    transform: scale(1.02);
}

/* Button Styles */
.stButton > button {
    border-radius: 8px;
    font-weight: 500;
    transition: all 0.2s ease;
}

.stButton > button:hover {
    transform: translateY(-1px);
}

/* Hide Streamlit Branding */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>
""",
    unsafe_allow_html=True,
)

# =============================
# SESSION STATE INITIALIZATION
# =============================
if "current_page" not in st.session_state:
    st.session_state.current_page = "home"
if "selected_tmdb_id" not in st.session_state:
    st.session_state.selected_tmdb_id = None
if "selected_mood" not in st.session_state:
    st.session_state.selected_mood = None
if "search_query" not in st.session_state:
    st.session_state.search_query = ""

# =============================
# URL QUERY PARAMS HANDLING
# =============================
qp_page = st.query_params.get("page")
qp_id = st.query_params.get("id")
qp_mood = st.query_params.get("mood")

if qp_page in ("home", "moods", "mood_results", "details"):
    st.session_state.current_page = qp_page
if qp_id:
    try:
        st.session_state.selected_tmdb_id = int(qp_id)
        st.session_state.current_page = "details"
    except:
        pass
if qp_mood:
    st.session_state.selected_mood = qp_mood
    st.session_state.current_page = "mood_results"


# =============================
# NAVIGATION FUNCTIONS
# =============================
def goto_home():
    st.session_state.current_page = "home"
    st.session_state.selected_mood = None
    st.session_state.search_query = ""
    st.query_params.clear()
    st.query_params["page"] = "home"
    st.rerun()


def goto_moods_page():
    st.session_state.current_page = "moods"
    st.query_params.clear()
    st.query_params["page"] = "moods"
    st.rerun()


def goto_mood_results(mood: str):
    st.session_state.current_page = "mood_results"
    st.session_state.selected_mood = mood
    st.query_params.clear()
    st.query_params["page"] = "mood_results"
    st.query_params["mood"] = mood
    st.rerun()


def goto_details(tmdb_id: int):
    st.session_state.current_page = "details"
    st.session_state.selected_tmdb_id = int(tmdb_id)
    st.query_params.clear()
    st.query_params["page"] = "details"
    st.query_params["id"] = str(int(tmdb_id))
    st.rerun()


# =============================
# API HELPER FUNCTIONS
# =============================
@st.cache_data(ttl=60)
def api_get_json(path: str, params: dict | None = None):
    """Make GET request to backend API with caching"""
    try:
        r = requests.get(f"{API_BASE}{path}", params=params, timeout=30)
        if r.status_code >= 400:
            return None, f"HTTP {r.status_code}: {r.text[:300]}"
        return r.json(), None
    except requests.exceptions.Timeout:
        return None, "Request timed out. Please try again."
    except requests.exceptions.ConnectionError:
        return None, "Connection error. Please check your internet."
    except Exception as e:
        return None, f"Request failed: {e}"


# =============================
# UI COMPONENTS
# =============================
def poster_grid(cards, cols=5, key_prefix="grid"):
    """Display movies in a responsive poster grid"""
    if not cards:
        st.info("No movies to show.")
        return

    rows = (len(cards) + cols - 1) // cols
    idx = 0
    
    for r in range(rows):
        colset = st.columns(cols)
        for c in range(cols):
            if idx >= len(cards):
                break
            m = cards[idx]
            idx += 1

            tmdb_id = m.get("tmdb_id")
            title = m.get("title", "Untitled")
            poster = m.get("poster_url")
            year = (m.get("release_date") or "")[:4]

            with colset[c]:
                # Poster Image
                if poster:
                    st.image(poster, use_column_width=True)
                else:
                    st.markdown(
                        """
                        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                    height: 280px; display: flex; align-items: center; 
                                    justify-content: center; border-radius: 12px;">
                            <span style="font-size: 3rem;">🎬</span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                # View Button
                if st.button("▶ View", key=f"{key_prefix}_{r}_{c}_{idx}_{tmdb_id}", use_container_width=True):
                    if tmdb_id:
                        goto_details(tmdb_id)

                # Movie Title
                st.markdown(f"<div class='movie-title'>{title}</div>", unsafe_allow_html=True)
                
                # Year
                if year:
                    st.markdown(
                        f"<div style='text-align:center; color:#888; font-size:0.75rem;'>{year}</div>",
                        unsafe_allow_html=True
                    )


def render_mood_grid(key_suffix=""):
    """Render mood selection buttons in a grid layout"""
    mood_list = list(MOOD_CONFIG.values())
    cols_per_row = 4
    
    for i in range(0, len(mood_list), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, col in enumerate(cols):
            if i + j < len(mood_list):
                mood = mood_list[i + j]
                with col:
                    btn_label = f"{mood['emoji']} {mood['name']}"
                    if st.button(
                        btn_label,
                        key=f"mood_{mood['name']}_{key_suffix}_{i}_{j}",
                        use_container_width=True,
                        help=mood['description']
                    ):
                        goto_mood_results(mood['name'])


def to_cards_from_tfidf_items(tfidf_items):
    """Convert TF-IDF recommendation items to card format"""
    cards = []
    for x in tfidf_items or []:
        tmdb = x.get("tmdb") or {}
        if tmdb.get("tmdb_id"):
            cards.append({
                "tmdb_id": tmdb["tmdb_id"],
                "title": tmdb.get("title") or x.get("title") or "Untitled",
                "poster_url": tmdb.get("poster_url"),
                "release_date": tmdb.get("release_date"),
            })
    return cards


def parse_tmdb_search_to_cards(data, keyword: str, limit: int = 24):
    """Parse TMDB search response to cards and suggestions"""
    keyword_l = keyword.strip().lower()

    # Handle dict with 'results' key (raw TMDB response)
    if isinstance(data, dict) and "results" in data:
        raw = data.get("results") or []
        raw_items = []
        for m in raw:
            title = (m.get("title") or "").strip()
            tmdb_id = m.get("id")
            poster_path = m.get("poster_path")
            if not title or not tmdb_id:
                continue
            raw_items.append({
                "tmdb_id": int(tmdb_id),
                "title": title,
                "poster_url": f"{TMDB_IMG}{poster_path}" if poster_path else None,
                "release_date": m.get("release_date", ""),
            })
    # Handle list format
    elif isinstance(data, list):
        raw_items = []
        for m in data:
            tmdb_id = m.get("tmdb_id") or m.get("id")
            title = (m.get("title") or "").strip()
            poster_url = m.get("poster_url")
            if not title or not tmdb_id:
                continue
            raw_items.append({
                "tmdb_id": int(tmdb_id),
                "title": title,
                "poster_url": poster_url,
                "release_date": m.get("release_date", ""),
            })
    else:
        return [], []

    # Filter by keyword
    matched = [x for x in raw_items if keyword_l in x["title"].lower()]
    final_list = matched if matched else raw_items

    # Build suggestions
    suggestions = []
    for x in final_list[:10]:
        year = (x.get("release_date") or "")[:4]
        label = f"{x['title']} ({year})" if year else x["title"]
        suggestions.append((label, x["tmdb_id"]))

    # Build cards
    cards = [
        {
            "tmdb_id": x["tmdb_id"],
            "title": x["title"],
            "poster_url": x["poster_url"],
            "release_date": x.get("release_date")
        }
        for x in final_list[:limit]
    ]
    
    return suggestions, cards


# =============================
# SIDEBAR
# =============================
with st.sidebar:
    # Logo/Title
    st.markdown("## 🎬 MoodFlix")
    st.markdown("---")
    
    # Main Navigation
    if st.button("🏠 Home", use_container_width=True):
        goto_home()
    
    if st.button("🎭 Mood Picks", use_container_width=True):
        goto_moods_page()
    
    st.markdown("---")
    
   
    st.markdown("---")
    
    # Category Selection
    st.markdown("### 📂 Browse Categories")
    home_category = st.selectbox(
        "Category",
        ["trending", "popular", "top_rated", "now_playing", "upcoming"],
        index=0,
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    
    # Settings
    st.markdown("### ⚙️ Display Settings")
    grid_cols = st.slider("Grid columns", 3, 8, 5)
    
    st.markdown("---")
    
 

# =============================
# MAIN HEADER
# =============================
st.markdown(
    """
    <div style="text-align: center; padding: 20px 0;">
        <h1 style="font-size: 2.8rem; margin-bottom: 5px; 
                   background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                   -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
            🎬 MoodFlix
        </h1>
        <p style="color: #666; font-size: 1.1rem;">
            AI Based Movie Recommendations System
        </p>
    </div>
    """,
    unsafe_allow_html=True
)
st.divider()


# ==========================================================
# PAGE: HOME
# ==========================================================
if st.session_state.current_page == "home":
    
    # Search Section
    st.markdown("### 🔍 Search Movies")
    
    col1, col2 = st.columns([5, 1])
    with col1:
        typed = st.text_input(
            "Search",
            value=st.session_state.search_query,
            placeholder="Type movie name: Avengers, Batman, Inception, Hulk...",
            label_visibility="collapsed"
        )
        st.session_state.search_query = typed
    
    with col2:
        search_btn = st.button("🔍", use_container_width=True)

    # Handle Search
    if typed.strip():
        if len(typed.strip()) < 2:
            st.caption("⚠️ Type at least 2 characters to search.")
        else:
            with st.spinner("🔍 Searching..."):
                data, err = api_get_json("/tmdb/search", params={"query": typed.strip()})

            if err or data is None:
                st.error(f"❌ Search failed: {err}")
            else:
                suggestions, cards = parse_tmdb_search_to_cards(data, typed.strip(), limit=24)

                # Quick Select Dropdown
                if suggestions:
                    st.markdown("#### 💡 Quick Select")
                    labels = ["-- Select a movie --"] + [s[0] for s in suggestions]
                    selected = st.selectbox(
                        "Suggestions",
                        labels,
                        index=0,
                        label_visibility="collapsed"
                    )

                    if selected != "-- Select a movie --":
                        label_to_id = {s[0]: s[1] for s in suggestions}
                        goto_details(label_to_id[selected])
                
                # Search Results Grid
                if cards:
                    st.markdown(f"### 🎯 Search Results ({len(cards)} movies found)")
                    poster_grid(cards, cols=grid_cols, key_prefix="search_results")
                else:
                    st.info("No movies found. Try a different search term.")

            st.stop()

    st.divider()

    # Category Movies
    category_display = home_category.replace('_', ' ').title()
    st.markdown(f"### 🏠 {category_display} Movies")

    with st.spinner(f"Loading {category_display.lower()} movies..."):
        home_cards, err = api_get_json(
            "/home", params={"category": home_category, "limit": 24}
        )
    
    if err or not home_cards:
        st.error(f"❌ Failed to load movies: {err or 'Unknown error'}")
        st.info("Please check your internet connection or try again later.")
        st.stop()

    poster_grid(home_cards, cols=grid_cols, key_prefix="home_feed")


# ==========================================================
# PAGE: MOOD SELECTION
# ==========================================================
elif st.session_state.current_page == "moods":
    
    # Back Button
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("← Home", use_container_width=True):
            goto_home()
    
    # Mood Header
    st.markdown(
        """
        <div class="mood-section-header">
            <h2 style="color: white; margin-bottom: 10px; font-size: 2rem;">
                🎭 Choose Your Mood
            </h2>
            <p style="color: rgba(255,255,255,0.9); font-size: 1.1rem;">
                How are you feeling? Select a mood to get personalized movie recommendations!
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    st.markdown("#### Select a mood below:")
    st.markdown("")
    
    render_mood_grid(key_suffix="moods_page")
    
    st.markdown("")
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; color: #666; padding: 20px;">
            <p>💡 <strong>Tip:</strong> Each mood is mapped to specific movie genres to give you the best recommendations!</p>
        </div>
        """,
        unsafe_allow_html=True
    )


# ==========================================================
# PAGE: MOOD RESULTS
# ==========================================================
elif st.session_state.current_page == "mood_results":
    mood = st.session_state.selected_mood
    
    if not mood:
        st.warning("No mood selected.")
        if st.button("← Back to Home"):
            goto_home()
        st.stop()

    # Get mood info
    mood_info = MOOD_CONFIG.get(mood, {
        "emoji": "🎬",
        "name": mood,
        "description": "Movie recommendations",
        "color": "#667eea",
        "genre_ids": [28],
        "exclude_genres": [],
    })

    # Navigation Buttons
    col1, col2, col3 = st.columns([1, 3, 1])
    with col1:
        if st.button("← Home", key="mood_back_home", use_container_width=True):
            goto_home()
    with col3:
        if st.button("🎭 Change Mood", key="mood_change", use_container_width=True):
            goto_moods_page()

    # Mood Header with Gradient
    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, {mood_info['color']}99 0%, {mood_info['color']} 100%); 
                    padding: 50px 30px; border-radius: 20px; margin: 20px 0; text-align: center;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.15);">
            <div style="font-size: 5rem; margin-bottom: 15px;">{mood_info['emoji']}</div>
            <h2 style="color: white; margin-bottom: 10px; font-size: 2rem;">
                Feeling {mood_info['name']}?
            </h2>
            <p style="color: rgba(255,255,255,0.95); font-size: 1.2rem;">
                {mood_info['description']}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # =============================
    # FETCH MOOD-BASED MOVIES
    # =============================
    mood_cards = []
    
    with st.spinner(f"🎬 Finding perfect {mood_info['name'].lower()} movies for you..."):
        
        # Get genre settings
        primary_genre = mood_info.get("genre_ids", [28])[0]
        exclude_genres = mood_info.get("exclude_genres", [])
        
        # Random page for variety
        random_page = random.randint(1, 5)
        
        # Build discover params
        discover_params = {
            "with_genres": str(primary_genre),
            "sort_by": "popularity.desc",
            "vote_count.gte": "50",
            "page": str(random_page),
            "language": "en-US",
        }
        
        if exclude_genres:
            discover_params["without_genres"] = ",".join(str(g) for g in exclude_genres)
        
        # Method 1: Try /tmdb/discover endpoint
        data, err = api_get_json("/tmdb/discover", params=discover_params)
        
        if not err and data and isinstance(data, dict) and "results" in data:
            results = data.get("results", [])
            for m in results[:24]:
                poster_path = m.get("poster_path")
                mood_cards.append({
                    "tmdb_id": int(m["id"]),
                    "title": m.get("title") or "Untitled",
                    "poster_url": f"{TMDB_IMG}{poster_path}" if poster_path else None,
                    "release_date": m.get("release_date"),
                })
            random.shuffle(mood_cards)
        
        # Method 2: Fallback to /recommend/mood
        if not mood_cards:
            data2, err2 = api_get_json("/recommend/mood", params={"mood": mood, "limit": 24})
            if not err2 and data2 and isinstance(data2, list):
                mood_cards = data2
                random.shuffle(mood_cards)
        
        # Method 3: Fallback to home categories
        if not mood_cards:
            mood_to_category = {
                "Happy": "popular",
                "Sad": "top_rated",
                "Scared": "popular",
                "Excited": "trending",
                "Romantic": "top_rated",
                "Thoughtful": "top_rated",
                "Relaxed": "popular",
                "Adventurous": "trending",
                "Funny": "popular",
                "Motivated": "top_rated",
                "Family": "popular",
                "Mysterious": "top_rated",
            }
            fallback_category = mood_to_category.get(mood, "popular")
            data3, err3 = api_get_json("/home", params={"category": fallback_category, "limit": 24})
            if not err3 and data3:
                mood_cards = data3

    # Display Results
    if mood_cards and len(mood_cards) > 0:
        st.markdown(f"### 🎬 Movies for Your {mood_info['name']} Mood")
        st.markdown(f"*Found {len(mood_cards)} movies perfect for you!*")
        poster_grid(mood_cards, cols=grid_cols, key_prefix="mood_results")
    else:
        st.warning("😕 Couldn't find movies for this mood right now.")
        
        st.markdown("### 🔥 Here are some popular movies instead:")
        fallback_cards, _ = api_get_json("/home", params={"category": "popular", "limit": 12})
        if fallback_cards:
            poster_grid(fallback_cards, cols=grid_cols, key_prefix="fallback_movies")

    st.divider()
    
    # Try Another Mood Section
    st.markdown("### 🔄 Try Another Mood")
    render_mood_grid(key_suffix="mood_results_page")


# ==========================================================
# PAGE: MOVIE DETAILS
# ==========================================================
elif st.session_state.current_page == "details":
    tmdb_id = st.session_state.selected_tmdb_id
    
    if not tmdb_id:
        st.warning("No movie selected.")
        if st.button("← Back to Home"):
            goto_home()
        st.stop()

    # Back Button
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("← Back", use_container_width=True):
            goto_home()

    # Fetch Movie Details
    with st.spinner("Loading movie details..."):
        data, err = api_get_json(f"/movie/id/{tmdb_id}")
    
    if err or not data:
        st.error(f"❌ Could not load movie details: {err}")
        if st.button("🏠 Go to Home"):
            goto_home()
        st.stop()

    st.markdown("---")
    
    # Movie Details Layout
    left, right = st.columns([1, 2.5], gap="large")

    with left:
        # Poster
        if data.get("poster_url"):
            st.image(data["poster_url"], use_column_width=True)
        else:
            st.markdown(
                """
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                            height: 450px; display: flex; align-items: center; 
                            justify-content: center; border-radius: 12px;">
                    <span style="font-size: 5rem;">🎬</span>
                </div>
                """,
                unsafe_allow_html=True
            )

    with right:
        # Title
        st.markdown(f"# {data.get('title', 'Unknown Title')}")
        
        # Metadata
        release = data.get("release_date") or "Unknown"
        genres = ", ".join([g["name"] for g in data.get("genres", [])]) or "Unknown"
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f"**📅 Release Date:** {release}")
        with col_b:
            st.markdown(f"**🎭 Genres:** {genres}")
        
        st.markdown("---")
        
        # Overview
        st.markdown("### 📖 Overview")
        overview = data.get("overview") or "No overview available."
        st.write(overview)
        
        # Quick Actions
        st.markdown("---")
        action_cols = st.columns(3)
        with action_cols[0]:
            if data.get("genres"):
                genre_name = data["genres"][0]["name"]
                st.button(f"🎭 More {genre_name}", disabled=True, use_container_width=True)

    # Backdrop Image
    if data.get("backdrop_url"):
        st.markdown("### 🖼️ Backdrop")
        st.image(data["backdrop_url"], use_column_width=True)

    st.divider()
    
    # =============================
    # RECOMMENDATIONS SECTION
    # =============================
    st.markdown("### ✨ You Might Also Like")

    title = (data.get("title") or "").strip()
    
    if title:
        with st.spinner("Finding similar movies..."):
            bundle, err2 = api_get_json(
                "/movie/search",
                params={"query": title, "tfidf_top_n": 12, "genre_limit": 12},
            )

        if not err2 and bundle:
            # TF-IDF Based Recommendations
            tfidf_cards = to_cards_from_tfidf_items(bundle.get("tfidf_recommendations"))
            if tfidf_cards:
                st.markdown("#### 🔎 Similar by Content (TF-IDF)")
                poster_grid(tfidf_cards, cols=grid_cols, key_prefix="details_tfidf")

            # Genre Based Recommendations
            genre_cards = bundle.get("genre_recommendations", [])
            if genre_cards:
                st.markdown("#### 🎭 Same Genre")
                poster_grid(genre_cards, cols=grid_cols, key_prefix="details_genre")
        else:
            # Fallback: Genre-only recommendations
            with st.spinner("Loading recommendations..."):
                genre_only, err3 = api_get_json(
                    "/recommend/genre", params={"tmdb_id": tmdb_id, "limit": 18}
                )
            if not err3 and genre_only:
                st.markdown("#### 🎭 Similar Movies")
                poster_grid(genre_only, cols=grid_cols, key_prefix="details_genre_fallback")
            else:
                st.info("No recommendations available for this movie.")
    else:
        st.info("Cannot generate recommendations without movie title.")
    
    st.divider()
    
    # Mood Quick Access
    st.markdown("### 🎭 Explore by Mood")
    render_mood_grid(key_suffix="details_page_mood")