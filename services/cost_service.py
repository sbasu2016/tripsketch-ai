"""
cost_service.py — Cost estimation engine for TripSketch AI.

Supports three budget tiers (Budget, Moderate, Premium) with separate
multipliers for meals, attractions, and transit. The LLM provides
base "Moderate" estimates; this module scales them up or down.

All costs are in USD. The logic is intentionally simple and
transparent so users can understand and trust the numbers.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Cost multipliers by budget level and item type
# ---------------------------------------------------------------------------
# Structure: MULTIPLIERS[budget_level][item_type]
# "activity" covers sightseeing, attractions, experiences
# "meal" covers all food and drink
# "transit" is a flat daily allowance added on top
MULTIPLIERS = {
    "Budget": {
        "activity": 0.6,
        "meal": 0.55,
        "transit": 8,     # daily transit allowance in USD
    },
    "Moderate": {
        "activity": 1.0,
        "meal": 1.0,
        "transit": 15,
    },
    "Premium": {
        "activity": 1.7,
        "meal": 1.8,
        "transit": 30,
    },
    "Luxury": {
        "activity": 2.5,
        "meal": 2.8,
        "transit": 50,
    },
}

# Friendly labels for the UI
BUDGET_LABELS = {
    "Budget":   "💵 Budget",
    "Moderate": "💳 Moderate",
    "Premium":  "💎 Premium",
    "Luxury":   "👑 Luxury",
}


def get_budget_label(budget_level: str) -> str:
    """Return a display-friendly label for the budget tier."""
    return BUDGET_LABELS.get(budget_level, budget_level)


def _get_multiplier(budget_level: str, item_type: str) -> float:
    """Look up the cost multiplier for a budget level and item type."""
    tier = MULTIPLIERS.get(budget_level, MULTIPLIERS["Moderate"])
    if item_type == "meal":
        return tier["meal"]
    return tier["activity"]


def _get_transit_allowance(budget_level: str) -> float:
    """Return daily transit cost allowance for the budget tier."""
    tier = MULTIPLIERS.get(budget_level, MULTIPLIERS["Moderate"])
    return tier["transit"]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def estimate_item_cost(item: dict, budget_level: str) -> float:
    """
    Estimate the cost of a single itinerary item, scaled by budget.

    Takes the item's base estimated_cost and applies the appropriate
    multiplier based on the item type (meal vs activity).
    """
    base = item.get("estimated_cost", 0)
    item_type = item.get("type", "activity")
    multiplier = _get_multiplier(budget_level, item_type)
    return round(base * multiplier, 2)


def estimate_day_cost(day: dict, budget_level: str) -> float:
    """
    Estimate total cost for a single day.

    Sums scaled item costs plus a daily transit allowance.
    """
    items_total = sum(
        estimate_item_cost(item, budget_level)
        for item in day.get("items", [])
    )
    transit = _get_transit_allowance(budget_level)
    return round(items_total + transit, 2)


def estimate_total_cost(days: list, budget_level: str) -> float:
    """Estimate total trip cost across all days."""
    return round(
        sum(estimate_day_cost(day, budget_level) for day in days),
        2,
    )


def enrich_costs(itinerary: dict, budget_level: str) -> dict:
    """
    Walk through the entire itinerary and recalculate all costs
    based on the budget level.

    Mutates and returns the itinerary dict:
      - Each item gets a scaled estimated_cost
      - Each day gets a recalculated estimated_day_cost
      - Top-level estimated_total_cost and daily_cost_average are updated
    """
    total = 0.0

    for day in itinerary.get("days", []):
        day_total = 0.0
        for item in day.get("items", []):
            scaled = estimate_item_cost(item, budget_level)
            item["estimated_cost"] = scaled
            day_total += scaled

        # Add transit allowance
        transit = _get_transit_allowance(budget_level)
        day_total += transit
        day["estimated_day_cost"] = round(day_total, 2)
        total += day_total

    num_days = len(itinerary.get("days", [])) or 1
    itinerary["estimated_total_cost"] = round(total, 2)
    itinerary["daily_cost_average"] = round(total / num_days, 2)

    return itinerary
