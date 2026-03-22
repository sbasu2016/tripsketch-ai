"""
test_swap.py — Tests for the item swap feature in services/llm_service.py

Covers: mock swap returns valid item, correct type preserved,
correct time block preserved, different title each time (probabilistic),
and required fields present.
"""

import pytest
from services.llm_service import swap_item


def _swap_kwargs(**overrides):
    defaults = {
        "destination": "Kyoto, Japan",
        "budget_level": "Moderate",
        "travel_style": ["Culinary", "Culture"],
        "day_number": 1,
        "day_theme": "Historic Kyoto",
        "time_block": "Morning",
        "current_title": "Fushimi Inari Shrine",
        "current_description": "Walk the torii gates.",
        "item_type": "activity",
        "mode": "mock",
    }
    defaults.update(overrides)
    return defaults


class TestSwapMockActivity:
    def test_returns_dict(self):
        result = swap_item(**_swap_kwargs())
        assert isinstance(result, dict)

    def test_preserves_time_block(self):
        result = swap_item(**_swap_kwargs(time_block="Afternoon"))
        assert result["time_block"] == "Afternoon"

    def test_preserves_activity_type(self):
        result = swap_item(**_swap_kwargs(item_type="activity"))
        assert result["type"] == "activity"

    def test_has_required_fields(self):
        result = swap_item(**_swap_kwargs())
        required = {"time_block", "title", "type", "description", "estimated_cost", "location_name"}
        assert required.issubset(set(result.keys()))

    def test_title_is_nonempty(self):
        result = swap_item(**_swap_kwargs())
        assert len(result["title"]) > 0

    def test_description_is_nonempty(self):
        result = swap_item(**_swap_kwargs())
        assert len(result["description"]) > 0

    def test_cost_is_number(self):
        result = swap_item(**_swap_kwargs())
        assert isinstance(result["estimated_cost"], (int, float))


class TestSwapMockMeal:
    def test_preserves_meal_type(self):
        result = swap_item(**_swap_kwargs(item_type="meal"))
        assert result["type"] == "meal"

    def test_meal_has_required_fields(self):
        result = swap_item(**_swap_kwargs(item_type="meal"))
        required = {"time_block", "title", "type", "description", "estimated_cost"}
        assert required.issubset(set(result.keys()))

    def test_meal_title_nonempty(self):
        result = swap_item(**_swap_kwargs(item_type="meal"))
        assert len(result["title"]) > 0


class TestSwapVariety:
    def test_produces_variety_over_multiple_swaps(self):
        """Swap 10 times and check we get at least 2 different titles."""
        titles = set()
        for _ in range(10):
            result = swap_item(**_swap_kwargs())
            titles.add(result["title"])
        assert len(titles) >= 2, f"Only got: {titles}"

    def test_meal_variety(self):
        titles = set()
        for _ in range(10):
            result = swap_item(**_swap_kwargs(item_type="meal"))
            titles.add(result["title"])
        assert len(titles) >= 2


class TestSwapInvalidMode:
    def test_unknown_mode_raises(self):
        with pytest.raises(ValueError, match="Unknown mode"):
            swap_item(**_swap_kwargs(mode="gpt"))


class TestSwapNotes:
    def test_notes_accepted(self):
        """swap_item should accept a notes parameter without error."""
        result = swap_item(**_swap_kwargs(notes="I'm vegan, no dairy"))
        assert isinstance(result, dict)

    def test_notes_in_prompt(self):
        """build_swap_prompt should include notes in the prompt text."""
        from utils.prompts import build_swap_prompt
        _, prompt = build_swap_prompt(
            destination="Kyoto",
            budget_level="Moderate",
            travel_style=["Culinary"],
            day_number=1,
            day_theme="Test",
            time_block="Lunch",
            current_title="Old Place",
            current_description="desc",
            item_type="meal",
            notes="I'm vegan, no dairy",
        )
        assert "vegan" in prompt.lower()
        assert "no dairy" in prompt.lower()


class TestSwapFullContext:
    def test_interests_in_prompt(self):
        from utils.prompts import build_swap_prompt
        _, prompt = build_swap_prompt(
            destination="Kyoto",
            budget_level="Moderate",
            travel_style=["Culture"],
            day_number=1,
            day_theme="Test",
            time_block="Morning",
            current_title="X",
            current_description="Y",
            item_type="activity",
            interests=["Temples", "Markets"],
        )
        assert "Temples" in prompt
        assert "Markets" in prompt

    def test_season_in_prompt(self):
        from utils.prompts import build_swap_prompt
        _, prompt = build_swap_prompt(
            destination="Kyoto",
            budget_level="Moderate",
            travel_style=["Culture"],
            day_number=1,
            day_theme="Test",
            time_block="Morning",
            current_title="X",
            current_description="Y",
            item_type="activity",
            season="Spring (Mar-May)",
        )
        assert "Spring" in prompt

    def test_neighbor_items_in_prompt(self):
        from utils.prompts import build_swap_prompt
        _, prompt = build_swap_prompt(
            destination="Kyoto",
            budget_level="Moderate",
            travel_style=["Culture"],
            day_number=1,
            day_theme="Test",
            time_block="Afternoon",
            current_title="X",
            current_description="Y",
            item_type="activity",
            neighbor_items="  - Morning: Kinkaku-ji (35.04, 135.73)\n  - Lunch: Ramen Shop (35.03, 135.72)",
        )
        assert "Kinkaku-ji" in prompt
        assert "35.04" in prompt

    def test_existing_titles_in_prompt(self):
        from utils.prompts import build_swap_prompt
        _, prompt = build_swap_prompt(
            destination="Kyoto",
            budget_level="Moderate",
            travel_style=["Culture"],
            day_number=1,
            day_theme="Test",
            time_block="Morning",
            current_title="X",
            current_description="Y",
            item_type="activity",
            existing_titles="Fushimi Inari, Kinkaku-ji, Nishiki Market",
        )
        assert "Fushimi Inari" in prompt
        assert "Kinkaku-ji" in prompt
        assert "Nishiki Market" in prompt


class TestSwapMockDedup:
    def test_filters_existing_titles(self):
        """Mock swap should avoid titles already in the itinerary."""
        # Get all possible activity titles from pool
        from services.llm_service import _MOCK_ALTERNATIVES
        all_activity_titles = [a["title"] for a in _MOCK_ALTERNATIVES["activity"]]

        # Mark all but one as existing
        existing = ", ".join(all_activity_titles[:-1])
        results = set()
        for _ in range(10):
            r = swap_item(**_swap_kwargs(existing_titles=existing))
            results.add(r["title"])
        # Should only get the one title NOT in existing
        assert all_activity_titles[-1] in results

    def test_fallback_when_all_used(self):
        """If all titles are used, mock swap should still return something."""
        from services.llm_service import _MOCK_ALTERNATIVES
        all_titles = ", ".join(a["title"] for a in _MOCK_ALTERNATIVES["activity"])
        result = swap_item(**_swap_kwargs(existing_titles=all_titles))
        assert isinstance(result, dict)
        assert len(result["title"]) > 0


class TestMockRegenerateVariety:
    def test_regenerate_produces_different_results(self):
        """Multiple mock generations should not all be identical."""
        from services.itinerary_service import create_itinerary
        results = []
        for _ in range(5):
            itin = create_itinerary(
                destination="Kyoto", trip_length_days=4, budget_level="Moderate",
                travel_style=["Culture"], interests=["Temples"], pace="Balanced",
                mode="mock",
            )
            titles = tuple(
                item["title"] for day in itin["days"] for item in day["items"]
            )
            results.append(titles)
        unique = len(set(results))
        assert unique >= 2, f"Expected variety, got {unique} unique out of 5"
