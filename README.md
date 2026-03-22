# ✈️ TripSketch AI

> AI-powered travel itinerary generator — enter a destination and preferences, get a structured day-by-day plan with cost estimates, an interactive map, and a shareable link.

**[Live Demo →](https://sbasu2016-tripsketch-ai.streamlit.app)** · Built with Python, Streamlit, Claude API, Leaflet, and Google Maps tiles

---

## What it does

TripSketch AI takes a destination, budget, travel style, and interests as input and generates a complete multi-day itinerary with:

- **Area-by-area routing** — explores one neighborhood at a time, no zigzagging across town
- **Day-by-day schedule** grouped by Morning / Lunch / Afternoon / Dinner / Evening
- **Restaurant and activity suggestions** with descriptions and cost estimates
- **Budget-aware pricing** across Budget, Moderate, Premium, and Luxury tiers
- **Season-aware planning** that adjusts for weather, crowds, and local events
- **First visit vs. returning visitor** mode that skips tourist hits for deeper alternatives
- **Must-see list** support — far-apart places are spread across different days
- **🌧️ Rainy day mode** that swaps outdoor activities for indoor alternatives
- **🔄 Swap individual items** — don't like a suggestion? Swap uses your full context (dietary needs, interests, proximity) and never repeats
- **⚠️ Post-generation quality checks** — flags dietary conflicts, proximity issues, timing mismatches, and more
- **Interactive map** with Google Maps tiles, color-coded markers, tooltips, and a legend
- **📍 Google Places ratings** when configured with a Google Maps API key
- **Google Maps links** that open the actual place listing with reviews and photos
- **🔗 Shareable trip link** — generate a URL anyone can open to see your itinerary
- **Export options** — download as JSON, plain text, or copy a quick summary
- **Regenerate trip** button to start fresh

It works instantly in mock mode (no API key needed) or generates real itineraries via the Claude API.

---

## Screenshots

*Coming soon — add screenshots of the trip overview, day tabs, and map view here.*

---

## Quick Start

```bash
git clone https://github.com/sbasu2016/tripsketch-ai.git
cd tripsketch-ai
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your Anthropic key
streamlit run app.py
```

Mock mode runs immediately with no API key.

---

## Architecture

```
User Input (sidebar form)
    ↓
Streamlit UI (app.py)
    ↓
itinerary_service.py  ← orchestrator
    ├── llm_service.py       ← Claude API / mock + swap_item()
    ├── cost_service.py      ← budget scaling (4 tiers)
    ├── places_service.py    ← Google Places API / mock
    └── parser.py            ← JSON validation
    ↓
Structured itinerary JSON
    ↓
itinerary_checker.py  ← post-generation quality checks
    ↓
UI rendering + Leaflet map + export + share link
```

## Project Structure

```
tripsketch-ai/
├── app.py                           # Streamlit UI — all screens
├── services/
│   ├── llm_service.py               # Claude API + mock + item swap
│   ├── itinerary_service.py         # Orchestration pipeline
│   ├── cost_service.py              # Budget scaling engine (4 tiers)
│   └── places_service.py            # Google Places API + mock fallback
├── utils/
│   ├── prompts.py                   # LLM prompt templates + swap prompt
│   ├── parser.py                    # JSON parsing + validation
│   ├── formatters.py                # JSON + text + summary export
│   ├── validators.py                # Input validation
│   └── itinerary_checker.py         # Post-generation quality checks
├── data/
│   ├── sample_trip.json             # 4-day Kyoto mock itinerary
│   └── mock_places.json             # Mock place metadata with ratings
├── tests/
│   ├── test_parser.py               # Parser + JSON repair (28 tests)
│   ├── test_costs.py                # Cost engine — all 4 tiers (18 tests)
│   ├── test_formatters.py           # Export format tests (17 tests)
│   ├── test_swap.py                 # Item swap + context + dedup + regenerate (22 tests)
│   ├── test_share.py                # Share link encode/decode (11 tests)
│   ├── test_itinerary_checker.py    # Preference matching (43 tests)
│   ├── test_proximity.py            # Geographic proximity (17 tests)
│   ├── test_theme.py                # CSS color scheme + WCAG contrast (37 tests)
│   └── test_validators.py           # Input validation + char limits (37 tests)
├── assets/
│   └── logo.svg
├── requirements.txt
├── .env.example
├── .gitignore
├── DEPLOYMENT.md
├── PORTFOLIO.md
└── README.md
```

---

## User Inputs

| Field | Type | Description |
|-------|------|-------------|
| Destination | Text | City and country |
| Trip length | Slider (1–14) | Number of days |
| Budget level | Slider | Budget · Moderate · Premium · Luxury |
| Travel style | Multi-select (up to 3) | Culture, Culinary, Adventure, Relaxation, Romance, Family, Solo Explorer, Social |
| Interests | Multi-select (up to 5) | Temples, Museums, Street Food, Fine Dining, Markets, Hiking, Architecture, Art, Beaches, Gardens, Photography, History, Shopping, Live Music, Nightlife & Bars, Craft Beer & Wine, Local Neighborhoods, Amusement Parks |
| Trip pace | Radio | Relaxed · Balanced · Packed |
| Trip season | Dropdown | Not sure yet, Spring, Summer, Fall, Winter |
| Been before? | Radio | First visit · Returning visitor |
| Must-see places | Text | Comma-separated place names |
| Rainy day mode | Toggle | Prefer indoor activities |
| Optional notes | Text area | Free-form (dietary, timing, etc.) |

---

## Key Features

### 🗺️ Area-by-Area Routing
The AI plans each day so the traveler explores one area or cluster of nearby areas before moving on — the way locals recommend doing Tokyo neighborhood by neighborhood. No zigzagging across town. Meals are placed near activities unless the traveler prioritizes food quality (Culinary / Street Food / Fine Dining style).

### ⚠️ Post-Generation Quality Checks
After every generation, 7 automated validators run and flag issues:
- Late start preference vs. morning items
- Early end preference vs. evening items on last day
- Dietary preferences vs. meal descriptions (vegetarian, vegan, halal, kosher, gluten-free, seafood-free)
- Trip length mismatch
- Destination mismatch
- Rainy day mode vs. outdoor activities
- Geographic proximity — flags consecutive items >8km apart

### 🔄 Swap Individual Items
Each item has a Swap button that generates a replacement for that specific time block. The swap uses your full trip context — destination, budget, style, interests, pace, season, and notes (including dietary needs). It also knows every other item in your itinerary to avoid duplicates, and stays in the same area as the day's other activities. In mock mode it picks from a curated pool with dedup filtering; in Claude mode it calls the API with all context.

### 🌧️ Rainy Day Mode
Toggle in the sidebar. Instructs the AI to prefer indoor activities — museums, covered markets, workshops, cafés, galleries, cooking classes.

### 🔗 Shareable Trip Link
After generating a trip, the export section shows a compressed URL you can copy and share. Anyone who opens it sees the full itinerary with map, tabs, and export — no account or API key needed.

### 📍 Google Maps & Places Integration
Every item links to its Google Maps listing with reviews and photos. The map uses Google Maps tiles via Leaflet with color-coded markers. Optionally connect a Google Places API key for real ratings and addresses.

---

## Budget Tiers

| Tier | Activity Multiplier | Meal Multiplier | Daily Transit |
|------|-------------------|-----------------|---------------|
| Budget | 0.6x | 0.55x | $8 |
| Moderate | 1.0x | 1.0x | $15 |
| Premium | 1.7x | 1.8x | $30 |
| Luxury | 2.5x | 2.8x | $50 |

---

## Generation Modes

| Mode | API Key? | Description |
|------|----------|-------------|
| **Mock** | No | Instant demo with bundled Kyoto data |
| **Claude** | Yes | Real AI generation via Anthropic Messages API |

---

## Running Tests

```bash
pytest tests/ -v
```

230 tests across 9 test files.

---

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for the full Streamlit Community Cloud deployment guide.

---

## V2 Roadmap

Features under consideration for future versions:

- **Queue time and peak hour awareness** — factor in wait times, suggest optimal visit times, warn about peak-season crowds
- **Transit routing** — show specific train/bus routes between stops with estimated times and costs
- **Hotel-area-aware planning** — start each day's route from the traveler's accommodation
- **Cuisine filters** — vegetarian, halal, gluten-free as first-class form inputs
- **PDF export** — styled downloadable itinerary
- **Save, favorite, and revisit past trips** — persist itineraries to a database, mark favorites, and reload or share them later
- **Regenerate one full day** — rebuild a single day without touching the rest
- **Multi-city trips** — itineraries spanning multiple destinations with inter-city transit
- **Reservation and booking alerts** — flag places that require advance tickets, reservations, or bookings, with links to purchase and recommended lead times

---

## Tech Stack

- **Python 3.9+**
- **Streamlit** — interactive UI
- **Anthropic Claude API** — itinerary generation + item swap
- **Leaflet + Google Maps tiles** — map visualization
- **Google Places API** — place ratings and metadata (optional)
- **python-dotenv** — environment management
- **pytest** — 230 tests across 9 files

---

## License

MIT
