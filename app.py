"""
app.py — TripSketch AI: AI-powered travel itinerary generator.

Run with:  streamlit run app.py

Screens:
  1. Hero / landing with CTA
  2. Sidebar trip setup form
  3. Staged loading spinner
  4. Trip overview (summary + metrics)
  5. Day-by-day itinerary tabs
  6. Map view with pydeck
  7. Export / actions
"""

from __future__ import annotations

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # Streamlit Cloud injects secrets into os.environ directly

import time
import json
import base64
import zlib
import streamlit as st

from services.itinerary_service import create_itinerary
from services.cost_service import get_budget_label
from utils.formatters import itinerary_to_json, itinerary_to_text, itinerary_to_summary
from utils.validators import validate_all, ValidationError

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="TripSketch AI",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS — outputs BOTH light and dark palettes.
# Light is default. Dark is scoped under .theme-dark class.
# A JS snippet detects the actual rendered background and toggles the class.
# This works regardless of OS preference, Streamlit toggle, or Cloud deploy.
# ---------------------------------------------------------------------------

def _rules(c, prefix=""):
    """Generate CSS rules, optionally prefixed for scoping."""
    p = f"{prefix} " if prefix else ""
    return f"""
    {p}.hero .hero-title {{ font-family: 'DM Sans', sans-serif; font-size: 2.8rem; font-weight: 700; color: {c['tp']}; margin: 0 0 0.25rem 0; letter-spacing: -0.02em; }}
    {p}.hero .tagline {{ font-size: 1.12rem; color: {c['ts']}; margin: 0 0 0.5rem 0; }}
    {p}.hero .description {{ font-size: 0.92rem; color: {c['tm']}; max-width: 540px; margin: 0 auto; line-height: 1.6; }}
    {p}.divider {{ border: none; border-top: 1px solid {c['bc']}; margin: 1.5rem 0; }}
    {p}.trip-title {{ font-family: 'DM Sans', sans-serif; font-size: 2rem; font-weight: 700; color: {c['tp']}; margin: 0 0 0.15rem 0; }}
    {p}.trip-summary {{ color: {c['ts']}; font-size: 1rem; line-height: 1.65; max-width: 780px; margin-bottom: 1.2rem; }}
    {p}.metric-card {{ background: {c['mb']}; border: 1px solid {c['bc']}; border-radius: 12px; padding: 1.1rem 0.9rem; text-align: center; }}
    {p}.metric-card .label {{ font-size: 0.68rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; color: {c['ml']}; margin-bottom: 0.25rem; }}
    {p}.metric-card .value {{ font-family: 'DM Sans', sans-serif; font-size: 1.45rem; font-weight: 700; color: {c['mt']}; line-height: 1.2; }}
    {p}.day-header .day-theme {{ font-family: 'DM Sans', sans-serif; font-size: 1.3rem; font-weight: 700; color: {c['tp']}; margin: 0 0 0.1rem 0; }}
    {p}.day-meta {{ font-size: 0.85rem; color: {c['tm']}; margin-bottom: 0.75rem; }}
    {p}.time-block-label {{ font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: {c['tm']}; margin: 1rem 0 0.4rem 0; padding-bottom: 0.2rem; border-bottom: 1px solid {c['bc']}; }}
    {p}.item-card {{ background: {c['ib']}; border: 1px solid {c['bl']}; border-left: 4px solid {c['bc']}; border-radius: 8px; padding: 0.85rem 1.1rem; margin-bottom: 0.5rem; }}
    {p}.item-card.type-activity {{ border-left-color: {c['ag']}; }}
    {p}.item-card.type-meal {{ border-left-color: {c['ao']}; }}
    {p}.item-title {{ font-weight: 600; font-size: 1rem; color: {c['tp']}; margin-bottom: 0.15rem; }}
    {p}.item-desc {{ color: {c['ts']}; font-size: 0.88rem; line-height: 1.55; }}
    {p}.item-footer {{ display: flex; gap: 1rem; margin-top: 0.4rem; font-size: 0.76rem; color: {c['tm']}; }}
    {p}.item-footer a {{ color: {c['lk']}; text-decoration: none; }}
    {p}.type-badge {{ display: inline-block; padding: 0.08rem 0.5rem; border-radius: 20px; font-size: 0.66rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; margin-left: 0.5rem; }}
    {p}.type-badge.activity {{ background: {c['bab']}; color: {c['bat']}; }}
    {p}.type-badge.meal {{ background: {c['bmb']}; color: {c['bmt']}; }}
    {p}.tip-box {{ background: {c['bs']}; border: 1px solid {c['bc']}; border-radius: 8px; padding: 0.7rem 0.9rem; margin-top: 0.6rem; font-size: 0.86rem; color: {c['ts']}; line-height: 1.5; }}
    {p}.empty-state {{ text-align: center; padding: 4rem 2rem; color: {c['tm']}; }}
    {p}.empty-state .icon {{ font-size: 3rem; margin-bottom: 0.6rem; }}
    {p}.empty-state p {{ font-size: 1.02rem; max-width: 420px; margin: 0 auto; line-height: 1.6; }}
    {p}.map-section-title {{ font-family: 'DM Sans', sans-serif; font-size: 1.2rem; font-weight: 700; color: {c['tp']}; margin: 0.5rem 0 0.5rem 0; }}
    """

_LIGHT = {
    "tp": "#1a1a1a", "ts": "#555555", "tm": "#777777",
    "bc": "#e0ddd5", "bl": "#ece7dc", "bs": "#f8f7f4",
    "ag": "#3a7a3a", "ao": "#b8860b",
    "bab": "#e8f0e8", "bat": "#3a6a3a", "bmb": "#fdf2e0", "bmt": "#8a6020",
    "lk": "#6a8a6a",
    "mb": "#f8f7f4", "mt": "#1a1a1a", "ml": "#777777",
    "ib": "#f8f7f4",
}
_DARK = {
    "tp": "#e6e6e6", "ts": "#b0b0b0", "tm": "#909090",
    "bc": "#333840", "bl": "#2a2e35", "bs": "#1a1d24",
    "ag": "#6abf6a", "ao": "#daa520",
    "bab": "#1e3a1e", "bat": "#7acf7a", "bmb": "#3a2e10", "bmt": "#e0b050",
    "lk": "#8abf8a",
    "mb": "#2c2f36", "mt": "#ffffff", "ml": "#a0a4ac",
    "ib": "#1e2128",
}

st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700&display=swap');
    .block-container {{ padding-top: 1rem; max-width: 1100px; }}
    .hero {{ text-align: center; padding: 3rem 1rem 1.5rem 1rem; }}
    .metric-row {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.75rem; margin-bottom: 1.5rem; }}
    .metric-card {{ transition: transform 0.15s ease, box-shadow 0.15s ease; }}
    .metric-card:hover {{ transform: translateY(-2px); box-shadow: 0 4px 14px rgba(0,0,0,0.1); }}
    .item-card {{ transition: border-left-color 0.2s, box-shadow 0.2s; }}
    .item-card:hover {{ box-shadow: 0 2px 10px rgba(0,0,0,0.08); }}
    .item-footer a:hover {{ color: #3a7a3a; }}
    [data-testid="stSidebar"] h2 {{ font-family: 'DM Sans', sans-serif; }}

    /* Hide Streamlit's built-in character counter (we show our own below the input) */
    .stTextInput [data-testid="InputInstructions"],
    .stTextArea [data-testid="InputInstructions"],
    .stTextInput .st-emotion-cache-1gulkj5,
    .stTextArea .st-emotion-cache-1gulkj5 {{ display: none !important; }}

    /* ---- LIGHT (default — no prefix, applies everywhere) ---- */
    {_rules(_LIGHT)}

    /* ---- DARK (only applies when .theme-dark is on stApp) ---- */
    {_rules(_DARK, ".theme-dark")}
    </style>
    """,
    unsafe_allow_html=True,
)

# JS: detect actual background brightness and add .theme-dark if needed.
# Runs in an iframe but accesses parent document where Streamlit lives.
# Re-checks every 500ms to catch theme toggles.
import streamlit.components.v1 as _components
_components.html(
    """
    <script>
    function detectTheme() {
        const app = window.parent.document.querySelector('.stApp');
        if (!app) return;
        const bg = getComputedStyle(app).backgroundColor;
        const m = bg.match(/\\d+/g);
        if (m) {
            const brightness = (parseInt(m[0]) * 299 + parseInt(m[1]) * 587 + parseInt(m[2]) * 114) / 1000;
            if (brightness < 128) {
                app.classList.add('theme-dark');
            } else {
                app.classList.remove('theme-dark');
            }
        }
    }
    detectTheme();
    // Re-check periodically to catch theme toggles
    setInterval(detectTheme, 500);
    </script>
    """,
    height=0,
)

# ---------------------------------------------------------------------------
# Screen 1: Hero
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="hero">
        <div class="hero-title">✈️ TripSketch AI</div>
        <p class="tagline">Generate a personalized, budget-aware travel plan in minutes.</p>
        <p class="description">
            Enter your destination and preferences — TripSketch AI builds a
            structured day-by-day itinerary with restaurants, activities,
            cost estimates, and a map. Powered by Claude.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Screen 2: Sidebar trip setup form
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("🗺️ Plan Your Trip")
    st.caption("Fill in the details and hit **Generate**.")

    destination = st.text_input(
        "Destination",
        value="Kyoto, Japan",
        placeholder="e.g. Lisbon, Portugal",
    )

    trip_length_days = st.slider(
        "Trip length (days)", min_value=1, max_value=14, value=4,
    )

    budget_level = st.select_slider(
        "Budget level",
        options=["Budget", "Moderate", "Premium", "Luxury"],
        value="Moderate",
    )

    travel_style = st.multiselect(
        "Travel style (how you travel)",
        options=[
            "Culture", "Culinary", "Adventure", "Relaxation",
            "Romance", "Family", "Solo Explorer", "Social",
        ],
        default=["Culinary", "Culture"],
        max_selections=3,
    )

    interests = st.multiselect(
        "Interests (what you want to see)",
        options=[
            "Temples", "Museums", "Street Food", "Fine Dining",
            "Markets", "Hiking", "Architecture", "Art",
            "Beaches", "Gardens", "Photography", "History",
            "Shopping", "Live Music", "Nightlife & Bars",
            "Craft Beer & Wine", "Local Neighborhoods", "Amusement Parks",
        ],
        default=["Temples", "Markets", "Street Food"],
        max_selections=5,
    )

    pace = st.radio(
        "Trip pace",
        options=["Relaxed", "Balanced", "Packed"],
        index=1,
        horizontal=True,
    )

    season = st.selectbox(
        "Trip season",
        options=[
            "Not sure yet", "Spring (Mar–May)", "Summer (Jun–Aug)",
            "Fall (Sep–Nov)", "Winter (Dec–Feb)",
        ],
        index=0,
    )

    first_visit = st.radio(
        "Been before?",
        options=["First visit", "Returning visitor"],
        index=0,
        horizontal=True,
    )

    must_see = st.text_input(
        "Must-see places (comma-separated)",
        placeholder="e.g. Fushimi Inari, Nishiki Market",
        max_chars=200,
    )
    if must_see:
        _ms_len = len(must_see)
        if _ms_len >= 200:
            st.markdown(
                f'<p style="font-size:0.78rem; color:#e74c3c; margin-top:-0.5rem;">⚠️ Maximum 200 characters reached ({_ms_len}/200)</p>',
                unsafe_allow_html=True,
            )
        elif _ms_len > 160:
            st.markdown(
                f'<p style="font-size:0.78rem; color:#e74c3c; margin-top:-0.5rem;">{_ms_len}/200 characters</p>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<p style="font-size:0.78rem; color:#909090; margin-top:-0.5rem;">{_ms_len}/200 characters</p>',
                unsafe_allow_html=True,
            )

    rainy_day = st.toggle(
        "🌧️ Rainy day mode",
        value=False,
        help="Prefer indoor activities — museums, cafés, covered markets, workshops.",
    )

    notes = st.text_area(
        "Optional notes",
        placeholder="e.g. We arrive late on day 1, vegetarian meals preferred...",
        height=80,
        max_chars=500,
    )
    if notes:
        _n_len = len(notes)
        if _n_len >= 500:
            st.markdown(
                f'<p style="font-size:0.78rem; color:#e74c3c; margin-top:-0.5rem;">⚠️ Maximum 500 characters reached ({_n_len}/500)</p>',
                unsafe_allow_html=True,
            )
        elif _n_len > 400:
            st.markdown(
                f'<p style="font-size:0.78rem; color:#e74c3c; margin-top:-0.5rem;">{_n_len}/500 characters</p>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<p style="font-size:0.78rem; color:#909090; margin-top:-0.5rem;">{_n_len}/500 characters</p>',
                unsafe_allow_html=True,
            )

    st.divider()

    mode = st.radio(
        "Generation mode",
        options=["mock", "claude"],
        index=0,
        horizontal=True,
        help="**Mock**: instant demo data. **Claude**: real AI generation (needs API key).",
    )

    generate_btn = st.button(
        "🚀 Generate Itinerary",
        use_container_width=True,
        type="primary",
    )


# ---------------------------------------------------------------------------
# Helper: build Google Maps link
# ---------------------------------------------------------------------------
def _maps_link(title: str, location_name: str, lat: float, lng: float) -> str:
    """Build a Google Maps search link using the place name so it
    opens the actual listing with reviews, photos, etc."""
    # Prefer location_name (e.g. "Fushimi Inari Taisha"), fall back to title
    name = location_name or title
    query = name.replace(" ", "+")
    return f"https://www.google.com/maps/search/?api=1&query={query}"


# ---------------------------------------------------------------------------
# Helper: render items grouped by time block
# ---------------------------------------------------------------------------
TIME_BLOCK_ORDER = ["Morning", "Lunch", "Afternoon", "Dinner", "Evening"]


def render_day_items(items: list, day_idx: int, day: dict, itin: dict, mode: str) -> None:
    """Render a day's items grouped by time block with styled cards and swap buttons."""
    # Group items by time block, preserving original index
    grouped = {}
    for idx, item in enumerate(items):
        block = item.get("time_block", "Morning")
        if block not in grouped:
            grouped[block] = []
        grouped[block].append((idx, item))

    # Render in the canonical order
    for block in TIME_BLOCK_ORDER:
        if block not in grouped:
            continue

        st.markdown(
            f'<div class="time-block-label">{block}</div>',
            unsafe_allow_html=True,
        )

        for item_idx, item in grouped[block]:
            item_type = item.get("type", "activity")
            type_class = "type-meal" if item_type == "meal" else "type-activity"
            badge_class = "meal" if item_type == "meal" else "activity"
            badge_label = "Meal" if item_type == "meal" else "Activity"

            cost = item.get("estimated_cost", 0)
            cost_str = "Free" if cost == 0 else f"${cost:,.0f}"

            lat = item.get("latitude", 0)
            lng = item.get("longitude", 0)
            maps_url = _maps_link(
                item.get("title", ""),
                item.get("location_name", ""),
                lat, lng,
            )

            rating_str = ""
            place_info = item.get("place_info", {})
            if place_info and place_info.get("rating"):
                rating_str = f" · ⭐ {place_info['rating']}"

            st.markdown(
                f'<div class="item-card {type_class}">'
                f'<span class="item-title">{item.get("title", "")}</span>'
                f'<span class="type-badge {badge_class}">{badge_label}</span>'
                f'<div class="item-desc">{item.get("description", "")}</div>'
                f'<div class="item-footer">'
                f'💰 {cost_str}{rating_str}'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # Map link + swap button row
            col_map, col_swap = st.columns([4, 1])
            with col_map:
                st.markdown(
                    f'<div style="margin: -0.2rem 0 0.4rem 0; font-size: 0.76rem;">'
                    f'&nbsp;&nbsp;📍 <a href="{maps_url}" target="_blank" '
                    f'style="color: #8a9a7a; text-decoration: none;">View on Google Maps</a>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col_swap:
                swap_key = f"swap_{day_idx}_{item_idx}"
                if st.button("🔄 Swap", key=swap_key, use_container_width=True):
                    from services.llm_service import swap_item
                    try:
                        # Build neighbor items string (other items on this day)
                        neighbor_lines = []
                        for other in day.get("items", []):
                            if other.get("title") != item.get("title"):
                                lat = other.get("latitude", 0)
                                lon = other.get("longitude", 0)
                                coord = f" ({lat}, {lon})" if lat and lon else ""
                                neighbor_lines.append(
                                    f"  - {other.get('time_block', '?')}: "
                                    f"{other.get('title', '?')}{coord}"
                                )
                        neighbor_str = "\n".join(neighbor_lines) if neighbor_lines else ""

                        # Collect ALL existing titles across entire itinerary
                        all_titles = []
                        for d in itin.get("days", []):
                            for it in d.get("items", []):
                                title = it.get("title", "").strip()
                                if title:
                                    all_titles.append(title)
                        existing_str = ", ".join(all_titles)

                        new_item = swap_item(
                            destination=itin.get("destination", ""),
                            budget_level=itin.get("budget_level", "Moderate"),
                            travel_style=itin.get("travel_style", []),
                            day_number=day.get("day_number", 1),
                            day_theme=day.get("theme", ""),
                            time_block=item.get("time_block", "Morning"),
                            current_title=item.get("title", ""),
                            current_description=item.get("description", ""),
                            item_type=item_type,
                            notes=st.session_state.get("generation_notes", ""),
                            interests=st.session_state.get("generation_interests", []),
                            pace=st.session_state.get("generation_pace", "Balanced"),
                            season=st.session_state.get("generation_season", "Not sure yet"),
                            neighbor_items=neighbor_str,
                            existing_titles=existing_str,
                            mode=mode,
                        )
                        # Replace the item in session state
                        st.session_state["itinerary"]["days"][day_idx]["items"][item_idx] = new_item
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Swap failed: {exc}")


# ---------------------------------------------------------------------------
# Helper: build Google Maps-style map from itinerary
# ---------------------------------------------------------------------------
def render_map(itinerary: dict) -> None:
    """Render a Leaflet map with Google Maps tiles, markers, and tooltips."""
    import streamlit.components.v1 as components

    points = []
    for day in itinerary.get("days", []):
        for item in day.get("items", []):
            lat = item.get("latitude", 0)
            lng = item.get("longitude", 0)
            if lat == 0 and lng == 0:
                continue
            points.append({
                "title": item.get("title", ""),
                "type": item.get("type", "activity"),
                "lat": lat,
                "lng": lng,
                "day": day.get("day_number", 0),
            })

    if not points:
        st.info("No location data available for map.")
        return

    # Calculate center
    avg_lat = sum(p["lat"] for p in points) / len(points)
    avg_lng = sum(p["lng"] for p in points) / len(points)

    # Build marker JS
    markers_js = ""
    for p in points:
        color = "#c4923a" if p["type"] == "meal" else "#3a7a3a"
        icon_char = "🍽" if p["type"] == "meal" else "📍"
        tooltip = f"Day {p['day']}: {p['title']} ({p['type'].title()})"
        markers_js += f"""
        L.circleMarker([{p['lat']}, {p['lng']}], {{
            radius: 8,
            fillColor: '{color}',
            color: '#fff',
            weight: 2,
            opacity: 1,
            fillOpacity: 0.85
        }}).addTo(map).bindTooltip("{tooltip}", {{
            direction: 'top',
            offset: [0, -8],
            className: 'custom-tooltip'
        }});
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <style>
            #map {{ width: 100%; height: 450px; border-radius: 10px; }}
            .custom-tooltip {{
                background: #1b2e1b;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 10px;
                font-family: 'Source Sans 3', sans-serif;
                font-size: 13px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            }}
            .custom-tooltip::before {{
                border-top-color: #1b2e1b;
            }}
            .legend {{
                position: absolute;
                bottom: 14px;
                right: 14px;
                background: white;
                padding: 8px 12px;
                border-radius: 6px;
                font-size: 12px;
                font-family: sans-serif;
                box-shadow: 0 1px 5px rgba(0,0,0,0.15);
                z-index: 1000;
                line-height: 1.8;
            }}
            .legend-dot {{
                display: inline-block;
                width: 10px;
                height: 10px;
                border-radius: 50%;
                margin-right: 5px;
                vertical-align: middle;
            }}
        </style>
    </head>
    <body>
        <div id="map"></div>
        <div class="legend">
            <span class="legend-dot" style="background:#3a7a3a;"></span> Activity<br>
            <span class="legend-dot" style="background:#c4923a;"></span> Meal
        </div>
        <script>
            var map = L.map('map').setView([{avg_lat}, {avg_lng}], 13);
            L.tileLayer('https://mt1.google.com/vt/lyrs=m&x={{x}}&y={{y}}&z={{z}}', {{
                maxZoom: 20,
                attribution: '© Google Maps'
            }}).addTo(map);
            {markers_js}
        </script>
    </body>
    </html>
    """

    components.html(html, height=480)


# ---------------------------------------------------------------------------
# Load shared trip from URL if present
# ---------------------------------------------------------------------------
_query_params = st.query_params

# Gist-based sharing (short URLs)
if "gist" in _query_params and "itinerary" not in st.session_state:
    try:
        from services.share_service import load_gist
        _gist_data = load_gist(_query_params["gist"])
        if _gist_data:
            st.session_state["itinerary"] = _gist_data
            st.session_state["generation_mode"] = "shared"
            st.info("📩 Viewing a shared trip! Generate your own using the sidebar.")
        else:
            st.warning("Could not load the shared trip. The link may have expired.")
    except Exception:
        st.warning("Could not load the shared trip link.")

# Legacy compressed URL sharing
if "trip" in _query_params and "itinerary" not in st.session_state:
    try:
        from utils.url_compress import decompress_itinerary
        st.session_state["itinerary"] = decompress_itinerary(_query_params["trip"])
        st.session_state["generation_mode"] = "shared"
        st.info("📩 Viewing a shared trip! Generate your own using the sidebar.")
    except Exception:
        try:
            compressed = base64.urlsafe_b64decode(_query_params["trip"])
            raw_json = zlib.decompress(compressed).decode("utf-8")
            st.session_state["itinerary"] = json.loads(raw_json)
            st.session_state["generation_mode"] = "shared"
            st.info("📩 Viewing a shared trip! Generate your own using the sidebar.")
        except Exception:
            st.warning("Could not load the shared trip link.")


# ---------------------------------------------------------------------------
# Screen 3: Generate (with staged loading)
# ---------------------------------------------------------------------------
_should_generate = generate_btn or st.session_state.pop("regenerate", False)
if _should_generate:
    # Validate inputs
    try:
        validate_all(destination, trip_length_days, budget_level, pace, interests)
        from utils.validators import validate_notes, validate_must_see
        validate_notes(notes)
        validate_must_see(must_see)
    except ValidationError as exc:
        st.error(str(exc))
        st.stop()

    # Staged loading messages
    progress_bar = st.progress(0)
    status_text = st.empty()

    stages = [
        (0.15, "🔍 Researching destination..."),
        (0.35, "🏗️ Building itinerary..."),
        (0.60, "💰 Estimating costs..."),
        (0.80, "📍 Looking up places..."),
        (0.95, "✨ Polishing your trip..."),
    ]

    for pct, msg in stages:
        status_text.text(msg)
        progress_bar.progress(pct)
        time.sleep(0.35)

    try:
        # Append rainy day instruction to notes if toggled
        effective_notes = notes
        if rainy_day:
            rain_note = "IMPORTANT: It will be rainy. Strongly prefer indoor activities — museums, covered markets, indoor workshops, cafés, galleries, aquariums, cooking classes. Avoid outdoor hiking, parks, and open-air sightseeing."
            effective_notes = f"{notes}\n{rain_note}" if notes else rain_note

        itinerary = create_itinerary(
            destination=destination.strip(),
            trip_length_days=trip_length_days,
            budget_level=budget_level,
            travel_style=travel_style,
            interests=interests,
            pace=pace,
            season=season,
            first_visit=first_visit,
            must_see=must_see,
            notes=effective_notes,
            mode=mode,
        )
        st.session_state["itinerary"] = itinerary
        st.session_state["generation_mode"] = mode
        st.session_state["generation_notes"] = effective_notes
        st.session_state["generation_interests"] = interests
        st.session_state["generation_pace"] = pace
        st.session_state["generation_season"] = season

        # Run post-generation quality checks
        from utils.itinerary_checker import validate_itinerary
        preference_warnings = validate_itinerary(
            itinerary,
            requested_destination=destination.strip(),
            requested_days=trip_length_days,
            notes=effective_notes,
        )
        st.session_state["preference_warnings"] = preference_warnings

    except Exception as exc:
        progress_bar.empty()
        status_text.empty()
        st.error(f"Generation failed: {exc}")
        st.stop()

    progress_bar.progress(1.0)
    status_text.text("✅ Your trip is ready!")
    time.sleep(0.4)
    progress_bar.empty()
    status_text.empty()


# ---------------------------------------------------------------------------
# Screens 4-7: Display results
# ---------------------------------------------------------------------------
if "itinerary" in st.session_state:
    itin = st.session_state["itinerary"]
    _active_mode = st.session_state.get("generation_mode", mode)

    # ---- Screen 4: Trip overview ----
    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown(
        f'<div class="trip-title">🌍 {itin["destination"]}</div>',
        unsafe_allow_html=True,
    )

    summary = itin.get("summary", "")
    if summary:
        st.markdown(
            f'<div class="trip-summary">{summary}</div>',
            unsafe_allow_html=True,
        )

    # Metric cards
    n_days = len(itin.get("days", []))
    total_cost = itin.get("estimated_total_cost", 0)
    avg_cost = itin.get("daily_cost_average", 0)
    budget_label = get_budget_label(itin.get("budget_level", "Moderate"))

    st.markdown(
        f"""
        <div class="metric-row">
            <div class="metric-card">
                <div class="label">Duration</div>
                <div class="value">{n_days} Day{"s" if n_days != 1 else ""}</div>
            </div>
            <div class="metric-card">
                <div class="label">Budget Tier</div>
                <div class="value">{budget_label}</div>
            </div>
            <div class="metric-card">
                <div class="label">Est. Total</div>
                <div class="value">${total_cost:,.0f}</div>
            </div>
            <div class="metric-card">
                <div class="label">Avg / Day</div>
                <div class="value">${avg_cost:,.0f}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---- Preference warnings ----
    pref_warnings = st.session_state.get("preference_warnings", [])
    if pref_warnings:
        with st.expander(f"⚠️ {len(pref_warnings)} preference warning{'s' if len(pref_warnings) != 1 else ''} — click to review", expanded=False):
            for w in pref_warnings:
                st.warning(w)
            st.caption("These are automated checks. Use the 🔄 Swap buttons to replace items that don't fit your preferences.")

    # ---- Screen 5: Day-by-day tabs ----
    days = itin.get("days", [])
    if days:
        tab_labels = [f"Day {d['day_number']}" for d in days]
        tabs = st.tabs(tab_labels)

        for day_idx, (tab, day) in enumerate(zip(tabs, days)):
            with tab:
                day_num = day.get("day_number", "?")
                theme = day.get("theme", "")
                day_cost = day.get("estimated_day_cost", 0)

                st.markdown(
                    f"""
                    <div class="day-header">
                        <div class="day-theme">{theme}</div>
                        <div class="day-meta">
                            Day {day_num} · Est. ${day_cost:,.0f}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                render_day_items(day.get("items", []), day_idx, day, itin, _active_mode)

    # ---- Screen 6: Map view ----
    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown(
        '<div class="map-section-title">📍 Trip Map</div>',
        unsafe_allow_html=True,
    )
    render_map(itin)

    # ---- Screen 7: Export / Actions ----
    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown("**📥 Export Your Itinerary**")

    # Copyable summary
    with st.expander("📋 Quick Summary (copy-friendly)"):
        _summary = itinerary_to_summary(itin)
        st.text_area("", value=_summary, height=200, label_visibility="collapsed")

    # Download buttons
    safe_name = (
        itin["destination"]
        .replace(" ", "_")
        .replace(",", "")
        .replace(".", "")
        .lower()
    )

    col_pdf, col_json, col_txt = st.columns(3)
    with col_pdf:
        from utils.pdf_export import itinerary_to_pdf
        st.download_button(
            label="⬇ Download PDF",
            data=itinerary_to_pdf(itin),
            file_name=f"tripsketch_{safe_name}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    with col_json:
        st.download_button(
            label="⬇ Download JSON",
            data=itinerary_to_json(itin),
            file_name=f"tripsketch_{safe_name}.json",
            mime="application/json",
            use_container_width=True,
        )
    with col_txt:
        st.download_button(
            label="⬇ Download Plain Text",
            data=itinerary_to_text(itin),
            file_name=f"tripsketch_{safe_name}.txt",
            mime="text/plain",
            use_container_width=True,
        )

    # Share link
    st.markdown("**🔗 Share This Trip**")
    _share_created = False

    # Try gist-based sharing first (short URL)
    try:
        from services.share_service import create_gist, _get_github_token
        if _get_github_token():
            if st.button("📤 Create shareable link", use_container_width=True):
                with st.spinner("Creating share link..."):
                    gist_id = create_gist(itin)
                if gist_id:
                    share_url = f"?gist={gist_id}"
                    st.markdown(
                        f'<a href="{share_url}" target="_blank" '
                        f'style="color: #e74c3c; font-weight: 600; '
                        f'font-size: 1rem; text-decoration: none;">'
                        f'Click here to open shareable link</a>',
                        unsafe_allow_html=True,
                    )
                    st.caption(
                        "Right-click the link and choose 'Copy link address' to share. "
                        "Works in iMessage, DMs, anywhere."
                    )
                    _share_created = True
                else:
                    st.error("Failed to create share link. Try again or use the download options.")
        else:
            _share_created = False  # No token — fall through to compressed URL
    except Exception:
        pass

    # Fallback: compressed URL (long but works without token)
    if not _share_created:
        try:
            from utils.url_compress import compress_itinerary
            encoded = compress_itinerary(itin)
            if len(encoded) < 8000:
                st.markdown(
                    f'<a href="?trip={encoded}" target="_blank" '
                    f'style="color: #e74c3c; font-weight: 600; '
                    f'font-size: 1rem; text-decoration: none;">'
                    f'Click here to open shareable link</a>',
                    unsafe_allow_html=True,
                )
                st.caption(
                    "Right-click the link and choose 'Copy link address' to share. "
                    "Note: this link is long — for shorter links, add a GITHUB_GIST_TOKEN to your secrets."
                )
            else:
                st.caption("Trip is too large to share via link. Use the JSON download instead.")
        except Exception:
            pass

    # Regenerate button
    if st.button("🔄 Regenerate Trip", use_container_width=True):
        if "itinerary" in st.session_state:
            del st.session_state["itinerary"]
        if "preference_warnings" in st.session_state:
            del st.session_state["preference_warnings"]
        st.session_state["regenerate"] = True
        st.rerun()

    st.markdown("</div><!-- end results -->", unsafe_allow_html=True)


else:
    # ---- Empty state ----
    st.markdown(
        """
        <div class="empty-state">
            <div class="icon">🗺️</div>
            <p>
                Fill in your trip details in the sidebar and hit
                <strong>Generate</strong> to sketch your perfect itinerary.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
