"""
itinerary_service.py — Orchestration layer for itinerary generation.

Single entry point for the UI. Chains:
  1. LLM generation (or mock data)
  2. Cost enrichment (budget scaling)
  3. Places enrichment (coordinates + metadata)

Also re-exports the formatters for convenience.
"""

from __future__ import annotations

from services.llm_service import generate_itinerary
from services.cost_service import enrich_costs
from services.places_service import enrich_places
from utils.formatters import itinerary_to_json, itinerary_to_text, itinerary_to_summary


def create_itinerary(
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
    Full pipeline: generate → enrich costs → enrich places → return.

    This is the only function the UI needs to call. All orchestration
    logic lives here so app.py stays thin.

    Returns a complete itinerary dict ready for rendering.
    """
    # Step 1: Generate raw itinerary
    itinerary = generate_itinerary(
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
        mode=mode,
    )

    # Step 2: Scale costs to match the selected budget tier
    itinerary = enrich_costs(itinerary, budget_level)

    # Step 3: Enrich items with place metadata and coordinates
    itinerary = enrich_places(itinerary)

    return itinerary
