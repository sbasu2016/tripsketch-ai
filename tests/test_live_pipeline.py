"""
test_live_pipeline.py — Tests for the claude/live generation pipeline.

Ensures that removing mock mode as the default didn't break any pipeline
components. Tests prompt building, parsing, validation, cost scaling,
quality checks, and swap — all with non-Kyoto destinations to verify
nothing is hardcoded to the mock data.
"""

from __future__ import annotations

import json


# ---------------------------------------------------------------------------
# Sample Claude-like response for a non-Kyoto destination
# ---------------------------------------------------------------------------
def _claude_response_lisbon():
    """Simulate a realistic Claude API JSON response for Lisbon."""
    return json.dumps({
        "destination": "Lisbon, Portugal",
        "trip_length_days": 3,
        "budget_level": "Moderate",
        "travel_style": ["Culture", "Culinary"],
        "interests": ["Architecture", "Markets", "Street Food"],
        "pace": "Balanced",
        "summary": "Three days exploring Lisbon's historic neighborhoods.",
        "estimated_total_cost": 450,
        "daily_cost_average": 150,
        "days": [
            {
                "day_number": 1,
                "theme": "Alfama & Baixa",
                "estimated_day_cost": 140,
                "items": [
                    {"time_block": "Morning", "title": "Castelo de Sao Jorge", "type": "activity",
                     "description": "Explore the hilltop castle with panoramic views.", "estimated_cost": 10,
                     "location_name": "Castelo de Sao Jorge", "latitude": 38.7139, "longitude": -9.1334},
                    {"time_block": "Lunch", "title": "Time Out Market", "type": "meal",
                     "description": "Lisbon's famous food hall.", "estimated_cost": 20,
                     "location_name": "Time Out Market", "latitude": 38.7069, "longitude": -9.1459},
                    {"time_block": "Afternoon", "title": "Alfama Walking Tour", "type": "activity",
                     "description": "Wander the narrow streets of Alfama.", "estimated_cost": 0,
                     "location_name": "Alfama", "latitude": 38.7114, "longitude": -9.1302},
                    {"time_block": "Dinner", "title": "Cervejaria Ramiro", "type": "meal",
                     "description": "Famous seafood restaurant.", "estimated_cost": 45,
                     "location_name": "Cervejaria Ramiro", "latitude": 38.7208, "longitude": -9.1365},
                ]
            },
            {
                "day_number": 2,
                "theme": "Belem & Waterfront",
                "estimated_day_cost": 160,
                "items": [
                    {"time_block": "Morning", "title": "Mosteiro dos Jeronimos", "type": "activity",
                     "description": "Stunning Manueline monastery.", "estimated_cost": 10,
                     "location_name": "Mosteiro dos Jeronimos", "latitude": 38.6979, "longitude": -9.2068},
                    {"time_block": "Lunch", "title": "Pasteis de Belem", "type": "meal",
                     "description": "The original pastel de nata bakery.", "estimated_cost": 8,
                     "location_name": "Pasteis de Belem", "latitude": 38.6976, "longitude": -9.2030},
                ]
            },
            {
                "day_number": 3,
                "theme": "Bairro Alto & Chiado",
                "estimated_day_cost": 150,
                "items": [
                    {"time_block": "Morning", "title": "LX Factory", "type": "activity",
                     "description": "Creative hub with shops and cafes.", "estimated_cost": 0,
                     "location_name": "LX Factory", "latitude": 38.7038, "longitude": -9.1780},
                ]
            },
        ]
    })


class TestPromptBuildingLive:
    """Verify prompt building works for any destination, not just Kyoto."""

    def test_itinerary_prompt_contains_destination(self):
        from utils.prompts import build_itinerary_prompt
        system, user = build_itinerary_prompt(
            destination="Lisbon, Portugal",
            trip_length_days=3,
            budget_level="Moderate",
            travel_style=["Culture", "Culinary"],
            interests=["Architecture"],
            pace="Balanced",
        )
        assert "Lisbon" in user
        assert "Portugal" in user

    def test_itinerary_prompt_includes_season(self):
        from utils.prompts import build_itinerary_prompt
        _, user = build_itinerary_prompt(
            destination="Barcelona, Spain",
            trip_length_days=5,
            budget_level="Premium",
            travel_style=["Adventure"],
            interests=["Beaches"],
            pace="Packed",
            season="Summer",
        )
        assert "Summer" in user

    def test_itinerary_prompt_includes_notes(self):
        from utils.prompts import build_itinerary_prompt
        _, user = build_itinerary_prompt(
            destination="Tokyo, Japan",
            trip_length_days=4,
            budget_level="Luxury",
            travel_style=["Culinary"],
            interests=["Street Food"],
            pace="Relaxed",
            notes="We are vegan and want to see cherry blossoms",
        )
        assert "vegan" in user
        assert "cherry blossoms" in user

    def test_itinerary_prompt_includes_must_see(self):
        from utils.prompts import build_itinerary_prompt
        _, user = build_itinerary_prompt(
            destination="Paris, France",
            trip_length_days=3,
            budget_level="Moderate",
            travel_style=["Culture"],
            interests=["Museums"],
            pace="Balanced",
            must_see="Eiffel Tower, Louvre, Montmartre",
        )
        assert "Eiffel Tower" in user
        assert "Louvre" in user

    def test_swap_prompt_contains_context(self):
        from utils.prompts import build_swap_prompt
        system, user = build_swap_prompt(
            destination="Lisbon, Portugal",
            budget_level="Moderate",
            travel_style=["Culture"],
            day_number=1,
            day_theme="Alfama",
            time_block="Afternoon",
            current_title="Castle Visit",
            current_description="Old castle tour",
            item_type="activity",
            interests=["Architecture", "Markets"],
            season="Spring",
            notes="vegetarian",
        )
        assert "Lisbon" in user
        assert "Alfama" in user
        assert "Architecture" in user
        assert "vegetarian" in user


class TestParsingLiveResponses:
    """Verify parser handles realistic Claude responses for any destination."""

    def test_parse_lisbon_response(self):
        from utils.parser import parse_itinerary
        result = parse_itinerary(_claude_response_lisbon())
        assert result["destination"] == "Lisbon, Portugal"
        assert len(result["days"]) == 3
        assert result["days"][0]["items"][0]["title"] == "Castelo de Sao Jorge"

    def test_parse_fills_defaults(self):
        from utils.parser import parse_itinerary
        result = parse_itinerary(_claude_response_lisbon())
        # Should have defaults filled
        for day in result["days"]:
            assert "theme" in day
            for item in day["items"]:
                assert "time_block" in item
                assert "latitude" in item
                assert "longitude" in item

    def test_parse_with_trailing_comma(self):
        """Claude sometimes produces trailing commas."""
        from utils.parser import parse_itinerary
        raw = _claude_response_lisbon()
        bad = raw[:-1] + ",}"
        result = parse_itinerary(bad)
        assert result["destination"] == "Lisbon, Portugal"

    def test_parse_with_markdown_fences(self):
        """Claude sometimes wraps JSON in markdown fences."""
        from utils.parser import parse_itinerary
        raw = f"Here's your itinerary:\n```json\n{_claude_response_lisbon()}\n```\nEnjoy!"
        result = parse_itinerary(raw)
        assert result["destination"] == "Lisbon, Portugal"


class TestCostScalingLive:
    """Verify cost scaling works across all tiers for any itinerary."""

    def test_budget_scaling_lisbon(self):
        from services.cost_service import enrich_costs
        from utils.parser import parse_itinerary
        itin = parse_itinerary(_claude_response_lisbon())
        enriched = enrich_costs(itin, "Budget")
        assert enriched["estimated_total_cost"] > 0
        assert enriched["daily_cost_average"] > 0

    def test_luxury_scaling_lisbon(self):
        from services.cost_service import enrich_costs
        from utils.parser import parse_itinerary
        itin = parse_itinerary(_claude_response_lisbon())
        budget = enrich_costs(dict(itin), "Budget")
        luxury = enrich_costs(dict(itin), "Luxury")
        assert luxury["estimated_total_cost"] > budget["estimated_total_cost"]

    def test_all_tiers_produce_different_costs(self):
        from services.cost_service import enrich_costs
        from utils.parser import parse_itinerary
        costs = []
        for tier in ["Budget", "Moderate", "Premium", "Luxury"]:
            itin = parse_itinerary(_claude_response_lisbon())
            enriched = enrich_costs(itin, tier)
            costs.append(enriched["estimated_total_cost"])
        # Each tier should be more expensive than the previous
        assert costs[0] < costs[1] < costs[2] < costs[3]


class TestQualityChecksLive:
    """Verify quality checks work on non-Kyoto itineraries."""

    def test_destination_check_passes(self):
        from utils.itinerary_checker import check_destination
        from utils.parser import parse_itinerary
        itin = parse_itinerary(_claude_response_lisbon())
        warnings = check_destination(itin, "Lisbon")
        assert len(warnings) == 0

    def test_destination_mismatch_flagged(self):
        from utils.itinerary_checker import check_destination
        from utils.parser import parse_itinerary
        itin = parse_itinerary(_claude_response_lisbon())
        warnings = check_destination(itin, "Tokyo")
        assert len(warnings) > 0

    def test_trip_length_check_passes(self):
        from utils.itinerary_checker import check_trip_length
        from utils.parser import parse_itinerary
        itin = parse_itinerary(_claude_response_lisbon())
        warnings = check_trip_length(itin, 3)
        assert len(warnings) == 0

    def test_dietary_check_flags_seafood_for_vegetarian(self):
        from utils.itinerary_checker import check_dietary_preferences
        from utils.parser import parse_itinerary
        itin = parse_itinerary(_claude_response_lisbon())
        # Cervejaria Ramiro has "seafood" in description
        warnings = check_dietary_preferences(itin, "vegetarian")
        assert len(warnings) >= 1

    def test_proximity_check_runs(self):
        from utils.itinerary_checker import check_proximity
        from utils.parser import parse_itinerary
        itin = parse_itinerary(_claude_response_lisbon())
        # Should not crash; may or may not have warnings
        warnings = check_proximity(itin)
        assert isinstance(warnings, list)

    def test_full_validation_runs(self):
        from utils.itinerary_checker import validate_itinerary
        from utils.parser import parse_itinerary
        itin = parse_itinerary(_claude_response_lisbon())
        warnings = validate_itinerary(itin, "Lisbon", 3, "")
        assert isinstance(warnings, list)


class TestSwapPipelineLive:
    """Verify swap works for non-Kyoto destinations."""

    def test_swap_returns_valid_item(self):
        from services.llm_service import swap_item
        result = swap_item(
            destination="Lisbon, Portugal",
            budget_level="Moderate",
            travel_style=["Culture"],
            day_number=1,
            day_theme="Alfama",
            time_block="Afternoon",
            current_title="Castle Visit",
            current_description="Old castle",
            item_type="activity",
            mode="mock",  # mock internally, but validates the pipeline
        )
        assert "title" in result
        assert "type" in result
        assert result["type"] == "activity"

    def test_swap_meal_returns_meal(self):
        from services.llm_service import swap_item
        result = swap_item(
            destination="Lisbon, Portugal",
            budget_level="Moderate",
            travel_style=["Culinary"],
            day_number=1,
            day_theme="Alfama",
            time_block="Lunch",
            current_title="Time Out Market",
            current_description="Food hall",
            item_type="meal",
            mode="mock",
        )
        assert result["type"] == "meal"


class TestInputValidationLive:
    """Verify input validation works for real user inputs."""

    def test_various_destinations_pass(self):
        from utils.validators import validate_destination
        for dest in ["Lisbon, Portugal", "Tokyo, Japan", "New York City",
                      "San Francisco, California", "Bangkok, Thailand"]:
            assert validate_destination(dest) == dest

    def test_long_notes_rejected(self):
        from utils.validators import validate_notes, ValidationError
        try:
            validate_notes("x" * 501)
            assert False, "Should have raised"
        except ValidationError:
            pass

    def test_empty_destination_rejected(self):
        from utils.validators import validate_destination, ValidationError
        try:
            validate_destination("")
            assert False, "Should have raised"
        except ValidationError:
            pass


class TestExportLive:
    """Verify all export formats work for non-Kyoto itineraries."""

    def test_json_export(self):
        from utils.parser import parse_itinerary
        from utils.formatters import itinerary_to_json
        itin = parse_itinerary(_claude_response_lisbon())
        result = itinerary_to_json(itin)
        assert "Lisbon" in result
        parsed = json.loads(result)
        assert parsed["destination"] == "Lisbon, Portugal"

    def test_text_export(self):
        from utils.parser import parse_itinerary
        from utils.formatters import itinerary_to_text
        itin = parse_itinerary(_claude_response_lisbon())
        result = itinerary_to_text(itin)
        assert "TRIPSKETCH" in result
        assert "Lisbon" in result
        assert "DAY 1" in result

    def test_summary_export(self):
        from utils.parser import parse_itinerary
        from utils.formatters import itinerary_to_summary
        itin = parse_itinerary(_claude_response_lisbon())
        result = itinerary_to_summary(itin)
        assert "Lisbon" in result
        assert "3 days" in result

    def test_pdf_export(self):
        """PDF should work for non-Kyoto destinations (if fpdf2 installed)."""
        try:
            from utils.pdf_export import itinerary_to_pdf
            from utils.parser import parse_itinerary
            itin = parse_itinerary(_claude_response_lisbon())
            result = itinerary_to_pdf(itin)
            assert isinstance(result, bytes)
            assert len(result) > 500
        except ImportError:
            pass  # fpdf2 not installed in test env
