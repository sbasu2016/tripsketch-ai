"""
test_costs.py — Tests for services/cost_service.py

Covers: item-level scaling for all 4 tiers, day-level totals with transit,
total cost, unknown budget fallback, zero-cost items, full enrichment,
and budget labels.
"""

import pytest
from services.cost_service import (
    estimate_item_cost,
    estimate_day_cost,
    estimate_total_cost,
    enrich_costs,
    get_budget_label,
)


def _meal(cost=20):
    return {"title": "Lunch", "type": "meal", "estimated_cost": cost}


def _activity(cost=10):
    return {"title": "Temple", "type": "activity", "estimated_cost": cost}


def _day(items):
    return {"day_number": 1, "items": items}


class TestEstimateItemCost:
    def test_moderate_meal_unchanged(self):
        assert estimate_item_cost(_meal(20), "Moderate") == 20.0

    def test_budget_meal(self):
        assert estimate_item_cost(_meal(20), "Budget") == 11.0

    def test_premium_meal(self):
        assert estimate_item_cost(_meal(20), "Premium") == 36.0

    def test_luxury_meal(self):
        assert estimate_item_cost(_meal(20), "Luxury") == 56.0

    def test_budget_activity(self):
        assert estimate_item_cost(_activity(10), "Budget") == 6.0

    def test_premium_activity(self):
        assert estimate_item_cost(_activity(10), "Premium") == 17.0

    def test_luxury_activity(self):
        assert estimate_item_cost(_activity(10), "Luxury") == 25.0

    def test_zero_cost_stays_zero(self):
        assert estimate_item_cost({"type": "activity", "estimated_cost": 0}, "Luxury") == 0.0

    def test_unknown_budget_defaults_to_moderate(self):
        assert estimate_item_cost(_meal(20), "UltraLux") == 20.0


class TestEstimateDayCost:
    def test_moderate_day(self):
        day = _day([_meal(20), _activity(10)])
        assert estimate_day_cost(day, "Moderate") == 45.0  # 20+10+15

    def test_budget_day(self):
        day = _day([_meal(20), _activity(10)])
        assert estimate_day_cost(day, "Budget") == 25.0  # 11+6+8

    def test_luxury_day(self):
        day = _day([_meal(20), _activity(10)])
        assert estimate_day_cost(day, "Luxury") == 131.0  # 56+25+50

    def test_empty_day_still_has_transit(self):
        assert estimate_day_cost(_day([]), "Moderate") == 15.0


class TestEstimateTotalCost:
    def test_multi_day(self):
        days = [_day([_meal(20)]), _day([_activity(10)])]
        assert estimate_total_cost(days, "Moderate") == 60.0

    def test_empty_trip(self):
        assert estimate_total_cost([], "Moderate") == 0.0


class TestEnrichCosts:
    def test_enriches_premium(self):
        itin = {"days": [{"day_number": 1, "items": [
            {"title": "A", "type": "meal", "estimated_cost": 20},
            {"title": "B", "type": "activity", "estimated_cost": 10},
        ]}]}
        result = enrich_costs(itin, "Premium")
        assert result["days"][0]["items"][0]["estimated_cost"] == 36.0
        assert result["days"][0]["items"][1]["estimated_cost"] == 17.0
        assert result["days"][0]["estimated_day_cost"] == 83.0
        assert result["estimated_total_cost"] == 83.0
        assert result["daily_cost_average"] == 83.0


class TestBudgetLabels:
    def test_all_known_labels(self):
        assert "Budget" in get_budget_label("Budget")
        assert "Moderate" in get_budget_label("Moderate")
        assert "Premium" in get_budget_label("Premium")
        assert "Luxury" in get_budget_label("Luxury")

    def test_unknown_label(self):
        assert get_budget_label("UltraLux") == "UltraLux"
