"""
prompts.py — Prompt templates for TripSketch AI itinerary generation.

Core philosophy: MINIMIZE TRANSIT, MAXIMIZE EXPLORATION. The traveler
should explore one area thoroughly before moving to the next — the way
locals recommend doing Tokyo neighborhood by neighborhood.

The prompt enforces strict JSON output with no markdown fences or extra
text. The schema matches the app's data model exactly.
"""

from __future__ import annotations


SYSTEM_PROMPT = """\
You are TripSketch AI, an expert travel planner who builds itineraries
that minimize commuting and maximize time spent exploring.

OUTPUT RULES:
1. Respond ONLY with a valid JSON object.
2. Do NOT include markdown, backticks, explanation, or any text outside JSON.
3. Follow the exact schema provided in the user message.

ROUTING RULES (HIGH PRIORITY):
4. Plan each day so the traveler explores one area or a cluster of nearby
   areas before moving on. Think "neighborhood by neighborhood"
   — see everything nearby, then move on. A day CAN cover more than one
   area if there isn't enough to fill the day, but the route should flow
   in one direction, not zigzag across the city.
5. NEVER double back. If the traveler starts in the north and moves
   south, don't send them back north later that day.
6. Minimize the number of major transit trips per day. A couple of short
   rides are fine; repeatedly crossing the city is not.
7. Place meals at restaurants NEAR the day's current area — unless the
   traveler's style is Culinary, Street Food, or Fine Dining, in which
   case prioritize food quality and try to strike a balance between
   quality and proximity.
8. If must-see places are in different parts of the city, put them on
   different days and build nearby activities around each one.

CONTENT RULES:
9. 4-7 items per day covering Morning, Lunch, Afternoon, Dinner, and
   optionally Evening.
10. Meal suggestions must name SPECIFIC restaurants or food stalls —
    not just "have lunch." Pick places that locals actually go to.
11. Cost estimates must be realistic for the stated budget level, in USD.
12. Each day needs a creative theme that captures the day's vibe.
13. Descriptions should be vivid, specific, and 1-2 sentences. Include
    what makes this place special and any useful practical tips.
14. Factor in seasonal realities when relevant: weather, crowds, seasonal
    events, and closures. Mention these naturally in descriptions rather
    than in a separate section.
"""


USER_PROMPT_TEMPLATE = """\
Plan a trip with these details:

Destination: {destination}
Trip length: {trip_length_days} days
Budget: {budget_level}
Travel style: {travel_style}
Interests: {interests}
Pace: {pace}
Season: {season}
Visitor type: {first_visit}
Must-see places: {must_see}
Notes: {notes}

PLANNING GUIDELINES:
- Plan each day so the traveler explores one area or cluster of nearby
  areas before moving on. The route should flow naturally — no jumping
  across town and back again.
- If there isn't enough to fill a full day in one area, it's fine to
  move to a nearby area in the afternoon. Just keep the route logical.
- Choose restaurants near the day's activities. Exception: if the travel
  style includes Culinary, Street Food, or Fine Dining, prioritize food
  quality — but still try to keep meals reasonably close.
- If must-see places are far apart, spread them across different days
  and build each day around that area.
- If the traveler is a returning visitor, skip the most obvious tourist
  spots and suggest deeper or lesser-known alternatives.
- Adjust for the season: mention crowd levels, weather, or seasonal
  events naturally in descriptions when relevant.
- Respect any dietary preferences, timing preferences, or other notes
  the traveler has included.

Return a JSON object matching this schema EXACTLY:

{{
  "destination": "<string>",
  "trip_length_days": <int>,
  "budget_level": "<string>",
  "travel_style": [<strings>],
  "interests": [<strings>],
  "pace": "<string>",
  "summary": "<2-3 sentence trip overview>",
  "estimated_total_cost": <number in USD>,
  "daily_cost_average": <number in USD>,
  "days": [
    {{
      "day_number": <int>,
      "theme": "<creative day theme>",
      "estimated_day_cost": <number in USD>,
      "items": [
        {{
          "time_block": "<Morning|Lunch|Afternoon|Dinner|Evening>",
          "title": "<specific place or restaurant name>",
          "type": "<activity|meal>",
          "description": "<1-2 sentences — what makes it special, practical tips>",
          "estimated_cost": <number in USD>,
          "location_name": "<official place name for map lookup>",
          "latitude": <float>,
          "longitude": <float>
        }}
      ]
    }}
  ]
}}

Return ONLY the JSON object. No other text.
"""


# ---------------------------------------------------------------------------
# Single-item swap prompt
# ---------------------------------------------------------------------------
SWAP_ITEM_PROMPT = """\
You are TripSketch AI, an expert travel planner.
Respond ONLY with a valid JSON object. No markdown, no backticks, no text.

TRIP CONTEXT:
- Destination: {destination}
- Budget: {budget_level}
- Travel style: {travel_style}
- Interests: {interests}
- Pace: {pace}
- Season: {season}
- Traveler notes: {notes}

The traveler is on Day {day_number} ("{day_theme}") and wants to REPLACE:
  Time block: {time_block}
  Current: {current_title} — {current_description}

NEARBY ITEMS ON THIS DAY (stay in this area):
{neighbor_items}

ALREADY IN THE ITINERARY (do NOT suggest any of these):
{existing_titles}

REQUIREMENTS:
- Suggest ONE alternative that is a completely DIFFERENT place — not
  something already listed above.
- Stay in the same general area as the day's other items listed above.
  Do not suggest somewhere that requires crossing the city.
- Appropriate for a {budget_level} budget.
- Must be a specific, real place with accurate coordinates.
- MUST respect the traveler's notes (dietary needs, preferences, etc.).
- Should match the traveler's interests and style.

Return ONLY this JSON:
{{
  "time_block": "{time_block}",
  "title": "<new suggestion — NOT any title from the list above>",
  "type": "{item_type}",
  "description": "<1-2 sentences — what makes it special>",
  "estimated_cost": <number in USD>,
  "location_name": "<official place name>",
  "latitude": <float>,
  "longitude": <float>
}}
"""


def build_itinerary_prompt(
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
) -> tuple:
    """
    Build (system_prompt, user_prompt) ready for the Anthropic Messages API.

    Parameters are the user's form inputs. The returned prompts are
    provider-agnostic but optimized for Claude.
    """
    user_msg = USER_PROMPT_TEMPLATE.format(
        destination=destination,
        trip_length_days=trip_length_days,
        budget_level=budget_level,
        travel_style=", ".join(travel_style) if travel_style else "General",
        interests=", ".join(interests) if interests else "General sightseeing",
        pace=pace,
        season=season,
        first_visit=first_visit,
        must_see=must_see or "None specified",
        notes=notes or "None",
    )
    return SYSTEM_PROMPT, user_msg


def build_swap_prompt(
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
) -> tuple:
    """Build (system_prompt, user_prompt) for swapping a single item."""
    user_msg = SWAP_ITEM_PROMPT.format(
        destination=destination,
        budget_level=budget_level,
        travel_style=", ".join(travel_style) if travel_style else "General",
        interests=", ".join(interests) if interests else "General",
        pace=pace,
        season=season,
        day_number=day_number,
        day_theme=day_theme,
        time_block=time_block,
        current_title=current_title,
        current_description=current_description,
        item_type=item_type,
        notes=notes or "None",
        neighbor_items=neighbor_items or "  (none)",
        existing_titles=existing_titles or "  (none)",
    )
    return SYSTEM_PROMPT, user_msg
