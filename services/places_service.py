"""
places_service.py — Place lookup and enrichment for itinerary items.

Two modes:
  • Mock — reads from data/mock_places.json (no API key needed)
  • Google Places — queries the Google Places API for real data

The public API (enrich_places) is stable. Swapping between modes
doesn't require changes to calling code.
"""

from __future__ import annotations

import json
import os
from pathlib import Path


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MOCK_DATA_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "mock_places.json"
)


def _use_google_places() -> bool:
    """Check at call time (not import time) so .env / secrets are loaded."""
    mode = os.getenv("PLACES_MODE", "")
    if not mode:
        try:
            import streamlit as st
            mode = st.secrets.get("PLACES_MODE", "mock")
        except Exception:
            mode = "mock"
    return mode.lower() == "live"


# ---------------------------------------------------------------------------
# Mock mode
# ---------------------------------------------------------------------------
_mock_cache = None


def _load_mock_data() -> dict:
    """Load and cache mock place data from JSON file."""
    global _mock_cache
    if _mock_cache is None:
        if MOCK_DATA_PATH.exists():
            with open(MOCK_DATA_PATH, "r", encoding="utf-8") as f:
                _mock_cache = json.load(f)
        else:
            _mock_cache = {}
    return _mock_cache


def _mock_lookup(location_name: str, destination: str) -> dict:
    """
    Look up a place in the mock data file.
    Falls back to a minimal record with a Google Maps search link.
    """
    data = _load_mock_data()
    if location_name in data:
        return data[location_name]

    # Fallback: return a minimal record
    query = f"{location_name} {destination}".replace(" ", "+")
    return {
        "display_name": location_name,
        "formatted_address": "",
        "latitude": 0.0,
        "longitude": 0.0,
        "rating": None,
        "maps_url": f"https://www.google.com/maps/search/?api=1&query={query}",
        "source": "mock_fallback",
    }


# ---------------------------------------------------------------------------
# Google Places mode (future integration)
# ---------------------------------------------------------------------------
def _google_lookup(location_name: str, destination: str) -> dict:
    """
    Query Google Places API for place details.

    To integrate:
      1. pip install googlemaps
      2. Set GOOGLE_MAPS_API_KEY in .env
      3. Set PLACES_MODE=live in .env

    Returns dict with: display_name, formatted_address, latitude,
    longitude, rating, maps_url
    """
    try:
        import googlemaps  # type: ignore
    except ImportError:
        # Fall back to mock if googlemaps isn't installed
        return _mock_lookup(location_name, destination)

    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets.get("GOOGLE_MAPS_API_KEY")
        except Exception:
            pass
    if not api_key:
        return _mock_lookup(location_name, destination)

    try:
        client = googlemaps.Client(key=api_key)
        query = f"{location_name}, {destination}"
        results = client.find_place(
            input=query,
            input_type="textquery",
            fields=["name", "formatted_address", "geometry", "rating"],
        )

        if results.get("candidates"):
            place = results["candidates"][0]
            loc = place.get("geometry", {}).get("location", {})
            return {
                "display_name": place.get("name", location_name),
                "formatted_address": place.get("formatted_address", ""),
                "latitude": loc.get("lat", 0.0),
                "longitude": loc.get("lng", 0.0),
                "rating": place.get("rating"),
                "source": "google_places",
            }
    except Exception as exc:
        # Log the error so it's not silently swallowed
        import streamlit as st
        st.warning(f"Google Places lookup failed for '{location_name}': {exc}")

    return _mock_lookup(location_name, destination)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def lookup_place(location_name: str, destination: str) -> dict:
    """
    Look up a single place. Uses Google Places API if configured,
    otherwise falls back to mock data.
    """
    if _use_google_places():
        return _google_lookup(location_name, destination)
    return _mock_lookup(location_name, destination)


def enrich_places(itinerary: dict) -> dict:
    """
    Walk through every item in the itinerary and attach place metadata.
    Updates latitude/longitude if the item has placeholder coordinates.

    Mutates and returns the itinerary dict.
    """
    destination = itinerary.get("destination", "")

    for day in itinerary.get("days", []):
        for item in day.get("items", []):
            loc_name = item.get("location_name", item.get("title", ""))
            place = lookup_place(loc_name, destination)

            # Attach place info
            item["place_info"] = place

            # Update coordinates if item has placeholder zeros
            if item.get("latitude", 0) == 0 and place.get("latitude", 0) != 0:
                item["latitude"] = place["latitude"]
            if item.get("longitude", 0) == 0 and place.get("longitude", 0) != 0:
                item["longitude"] = place["longitude"]

    return itinerary
