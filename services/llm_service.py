"""
llm_service.py — LLM integration for itinerary generation.

Primary provider: Anthropic Claude (via the official Python SDK).
Fallback: mock mode returns bundled sample data with no API key.

The module reads ANTHROPIC_API_KEY from environment variables.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from utils.prompts import build_itinerary_prompt
from utils.parser import parse_itinerary, ItineraryParseError

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MOCK_DATA_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "sample_trip.json"
)


def _load_mock_data() -> dict:
    """Load the bundled sample itinerary for demo / offline mode."""
    with open(MOCK_DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Anthropic Claude API
# ---------------------------------------------------------------------------
def _call_claude(system_prompt: str, user_prompt: str) -> str:
    """
    Call the Anthropic Messages API and return the raw response text.

    Requires ANTHROPIC_API_KEY in the environment. Uses claude-sonnet
    by default (configurable via ANTHROPIC_MODEL env var).
    """
    try:
        import anthropic  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "The 'anthropic' package is required. "
            "Install it with: pip install anthropic"
        ) from exc

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets.get("ANTHROPIC_API_KEY")
        except Exception:
            pass
    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY not found. "
            "Add it to your .env file or Streamlit secrets."
        )

    model = os.getenv("ANTHROPIC_MODEL", "")
    if not model:
        try:
            import streamlit as st
            model = st.secrets.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
        except Exception:
            model = "claude-sonnet-4-20250514"

    client = anthropic.Anthropic(api_key=api_key)

    response = client.messages.create(
        model=model,
        max_tokens=8192,
        system=system_prompt,
        messages=[
            {"role": "user", "content": user_prompt},
        ],
    )

    text = response.content[0].text

    # If the response was truncated (hit max_tokens), the JSON is incomplete
    if response.stop_reason == "max_tokens":
        raise ValueError(
            "Response was truncated — the itinerary is too long. "
            "Try reducing trip length or setting pace to Balanced/Relaxed."
        )

    return text


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def generate_itinerary(
    destination: str,
    trip_length_days: int,
    budget_level: str,
    travel_style: list,
    interests: list,
    pace: str,
    season: str = "Not sure yet",
    first_visit: str = "First visit",
    must_see: str = "",
    notes: str = "",
    mode: str = "mock",
) -> dict:
    """
    Generate a structured itinerary dict.

    Parameters
    ----------
    mode : str
        "mock" — returns bundled sample data (no API key needed).
        "claude" — calls the Anthropic Claude API.

    Returns
    -------
    dict — parsed and validated itinerary matching the app data model.

    Raises
    ------
    ValueError — if the LLM output cannot be parsed.
    ImportError — if the anthropic package isn't installed.
    """
    # -- Mock mode --
    if mode == "mock":
        import copy
        import random

        data = copy.deepcopy(_load_mock_data())
        # Patch in the user's inputs so the UI reflects what they typed
        data["destination"] = destination
        data["trip_length_days"] = trip_length_days
        data["budget_level"] = budget_level
        data["travel_style"] = travel_style
        data["interests"] = interests
        data["pace"] = pace
        # Trim days to match requested length
        data["days"] = data["days"][:trip_length_days]

        # Randomize: shuffle item order within each day and randomly
        # swap ~30% of items with alternatives so Regenerate feels fresh
        for day in data["days"]:
            items = day.get("items", [])
            random.shuffle(items)
            for i, item in enumerate(items):
                if random.random() < 0.3:
                    pool_key = item.get("type", "activity")
                    pool = _MOCK_ALTERNATIVES.get(pool_key, [])
                    if pool:
                        alt = random.choice(pool)
                        items[i] = {
                            **item,
                            "title": alt["title"],
                            "description": alt["description"],
                            "estimated_cost": alt["estimated_cost"],
                            "location_name": alt["location_name"],
                        }
            day["items"] = items
        return data

    # -- Claude API mode --
    if mode == "claude":
        system_prompt, user_prompt = build_itinerary_prompt(
            destination=destination,
            trip_length_days=trip_length_days,
            budget_level=budget_level,
            travel_style=travel_style,
            interests=interests,
            pace=pace,
            season=season,
            first_visit=first_visit,
            must_see=must_see,
            notes=notes,
        )
        raw = _call_claude(system_prompt, user_prompt)
        try:
            return parse_itinerary(raw)
        except ItineraryParseError:
            # Retry once — LLMs occasionally produce slightly malformed JSON
            raw = _call_claude(system_prompt, user_prompt)
            return parse_itinerary(raw)

    raise ValueError(
        f"Unknown generation mode: '{mode}'. Use 'mock' or 'claude'."
    )


# ---------------------------------------------------------------------------
# Single-item swap
# ---------------------------------------------------------------------------
# Small pool of mock alternatives for demo mode
_MOCK_ALTERNATIVES = {
    "activity": [
        {"title": "Local Walking Tour", "description": "Join a small-group walking tour through historic neighborhoods with a knowledgeable local guide.", "estimated_cost": 15, "location_name": "City Center"},
        {"title": "Traditional Craft Workshop", "description": "Learn a traditional local craft from an artisan in a hands-on workshop lasting about 90 minutes.", "estimated_cost": 25, "location_name": "Artisan Quarter"},
        {"title": "Botanical Garden Visit", "description": "Wander through beautifully landscaped gardens featuring native and exotic plants with peaceful walking paths.", "estimated_cost": 8, "location_name": "Botanical Gardens"},
        {"title": "Vintage Market Browsing", "description": "Explore a curated vintage and antique market with unique finds, local art, and handmade goods.", "estimated_cost": 0, "location_name": "Flea Market"},
        {"title": "Sunrise Viewpoint Hike", "description": "A short morning hike to a scenic overlook with panoramic views of the city and surrounding landscape.", "estimated_cost": 0, "location_name": "Scenic Viewpoint"},
    ],
    "meal": [
        {"title": "Hidden Izakaya Dinner", "description": "A tucked-away local pub serving shareable small plates, cold beer, and seasonal specials in a lively atmosphere.", "estimated_cost": 25, "location_name": "Local Izakaya"},
        {"title": "Farm-to-Table Café Lunch", "description": "A bright café sourcing ingredients from nearby farms. Try the seasonal set lunch with soup, salad, and a main.", "estimated_cost": 18, "location_name": "Farm Café"},
        {"title": "Street Food Stall Crawl", "description": "Hit three or four street stalls in one area — grilled skewers, dumplings, and something sweet to finish.", "estimated_cost": 12, "location_name": "Street Food Alley"},
        {"title": "Riverside Brunch Spot", "description": "Enjoy brunch with a view — fresh pastries, eggs, and excellent coffee by the water.", "estimated_cost": 20, "location_name": "Riverside Café"},
        {"title": "Neighborhood Noodle Shop", "description": "A no-frills counter-seat noodle joint beloved by locals. Fast, cheap, and deeply satisfying.", "estimated_cost": 8, "location_name": "Noodle Shop"},
    ],
}


def swap_item(
    destination: str,
    budget_level: str,
    travel_style: list,
    day_number: int,
    day_theme: str,
    time_block: str,
    current_title: str,
    current_description: str,
    item_type: str,
    notes: str = "",
    interests: list = None,
    pace: str = "Balanced",
    season: str = "Not sure yet",
    neighbor_items: str = "",
    existing_titles: str = "",
    mode: str = "mock",
) -> dict:
    """
    Generate a single replacement item for a specific time block.

    In mock mode, picks a random alternative from a small pool (excludes
    titles already in existing_titles).
    In claude mode, calls the API with full context.
    """
    if mode == "mock":
        import random
        pool = _MOCK_ALTERNATIVES.get(item_type, _MOCK_ALTERNATIVES["activity"])
        # Filter out titles already in the itinerary
        if existing_titles:
            used = {t.strip().lower() for t in existing_titles.split(",")}
            filtered = [a for a in pool if a["title"].lower() not in used]
            pool = filtered if filtered else pool
        alt = random.choice(pool)
        return {
            "time_block": time_block,
            "title": alt["title"],
            "type": item_type,
            "description": alt["description"],
            "estimated_cost": alt["estimated_cost"],
            "location_name": alt["location_name"],
            "latitude": 0.0,
            "longitude": 0.0,
        }

    if mode == "claude":
        from utils.prompts import build_swap_prompt
        system_prompt, user_prompt = build_swap_prompt(
            destination=destination,
            budget_level=budget_level,
            travel_style=travel_style,
            day_number=day_number,
            day_theme=day_theme,
            time_block=time_block,
            current_title=current_title,
            current_description=current_description,
            item_type=item_type,
            notes=notes,
            interests=interests,
            pace=pace,
            season=season,
            neighbor_items=neighbor_items,
            existing_titles=existing_titles,
        )
        raw = _call_claude(system_prompt, user_prompt)
        from utils.parser import _clean_llm_json
        import json
        cleaned = _clean_llm_json(raw)
        return json.loads(cleaned)

    raise ValueError(f"Unknown mode: '{mode}'")
