"""
Compete prototype — Mindtrip vs Wanderboat competitive eval.

Design:
  - Queries organized by TYPE (transactional, itinerary, personalized, etc.)
    for simplicity and clarity in the dataset.
  - Assertions tagged by CAPABILITY for richer dashboard reporting — you can
    slice results by query type OR by capability without changing the dataset.
  - Scores reported as a profile across capabilities, never collapsed.
  - Each prompt has an assertion set (mix of hard programmatic + soft binary
    LLM-judge checks). The assertion set IS the answer key.

Outputs (scraper-fed) intentionally omitted.
"""

from typing import TypedDict, Literal
import re


# ============================================================
# 1. QUERY TYPES (dataset organization)
# ============================================================
QUERY_TYPES = {
    "transactional": "User wants specific bookable inventory (flights, hotels) with concrete options.",
    "itinerary":     "User wants a multi-day or multi-stop plan they can execute.",
    "personalized":  "User wants recommendations matched to stated taste or preferences.",
    "live_data":     "User wants advice that depends on current conditions (weather, prices, seasonality).",
    "edge_case":     "Ambiguous, vague, or unconventional queries that test interpretation.",
}


# ============================================================
# 2. CAPABILITIES (assertion tags — for cross-cutting analysis)
# ============================================================
# Every assertion is tagged with one capability. This lets the Compete
# dashboard report wins by query type AND by underlying capability, which
# is what makes the eval actionable for PM build/buy decisions.

CAPABILITIES = {
    "grounded_retrieval": {
        "definition": "Surfacing real, verifiable, current entities (flights, hotels, restaurants, prices, hours).",
        "failure_mode": "Defers to 'check Google Flights' or returns generic categories instead of named items.",
    },
    "constraint_satisfaction": {
        "definition": "Honoring every explicit constraint (budget, dates, party size, preferences).",
        "failure_mode": "Drops constraints silently; output violates budget/dates.",
    },
    "multi_step_planning": {
        "definition": "Coherent multi-stop or multi-day plans with realistic transit, timing, sequencing.",
        "failure_mode": "Sequencing ignores geography or operating hours.",
    },
    "preference_inference": {
        "definition": "Inferring taste from sparse signals; recommendations with reasoning tied to the signal.",
        "failure_mode": "Returns popular destinations without explaining the fit.",
    },
    "temporal_reasoning": {
        "definition": "Reasoning about seasonality, booking windows, price trends, operating hours.",
        "failure_mode": "Treats time as a filter, not a variable; static advice for time-sensitive questions.",
    },
    "ambiguity_handling": {
        "definition": "Committing to a specific interpretation/recommendation rather than punting back to the user.",
        "failure_mode": "Either dumps every option or refuses to commit without more info.",
    },
    "epistemic_calibration": {
        "definition": "Knowing what it knows; flagging uncertainty; refusing to hallucinate prices/times.",
        "failure_mode": "Confident specific claims with no grounding.",
    },
}


# ============================================================
# 3. ASSERTION SCHEMA
# ============================================================
class Assertion(TypedDict):
    id: str
    capability: str
    description: str   # human-readable; this IS the answer key
    type: Literal["hard_programmatic", "soft_binary"]
    check: str         # regex pattern, or LLM judge prompt
    critical: bool     # failure here disqualifies the response


class EvalRow(TypedDict):
    id: str
    input: str
    query_type: str              # for dataset organization
    difficulty: Literal["easy", "medium", "hard"]
    user_intent: str             # one-sentence statement of what user wants
    quality_bar: str             # what a "great" response looks like
    assertions: list[Assertion]


# ============================================================
# 4. DATASET
# ============================================================

DATASET: list[EvalRow] = [

    # ============================================================
    # TRANSACTIONAL
    # ============================================================
    {
        "id": "T1",
        "input": "Find me the cheapest flights from Seattle to Chicago in the next month",
        "query_type": "transactional",
        "difficulty": "easy",
        "user_intent": "User wants to book the cheapest available SEA→ORD/MDW ticket and needs concrete options to compare, not advice on how to search.",
        "quality_bar": (
            "Returns 3-5 named flights with airline, flight number, date, times, and price. "
            "Identifies the cheapest concretely. Covers both ORD and MDW. Notes any price-"
            "trend or booking-window context. Does NOT defer to external search tools."
        ),
        "assertions": [
            {
                "id": "T1.a1", "capability": "grounded_retrieval", "type": "hard_programmatic",
                "description": "Contains at least 3 specific flight prices in USD",
                "check": r"\$\d{2,4}", "critical": True,
            },
            {
                "id": "T1.a2", "capability": "grounded_retrieval", "type": "hard_programmatic",
                "description": "Contains at least 2 named airlines",
                "check": r"(Alaska|United|Delta|American|Southwest|Frontier|Spirit|JetBlue)",
                "critical": True,
            },
            {
                "id": "T1.a3", "capability": "grounded_retrieval", "type": "hard_programmatic",
                "description": "Contains specific departure times",
                "check": r"\d{1,2}:\d{2}\s?(a|p|am|pm|AM|PM)",
                "critical": False,
            },
            {
                "id": "T1.a4", "capability": "grounded_retrieval", "type": "soft_binary",
                "description": "Identifies a single cheapest option explicitly (not just a list)",
                "check": "Does the response explicitly name ONE flight as the cheapest option, rather than just listing prices and letting the reader compare?",
                "critical": False,
            },
            {
                "id": "T1.a5", "capability": "grounded_retrieval", "type": "soft_binary",
                "description": "Does NOT defer to external search tools",
                "check": "Does the response AVOID telling the user to check Google Flights, Skyscanner, Kayak, or similar tools? It should answer directly.",
                "critical": True,
            },
            {
                "id": "T1.a6", "capability": "constraint_satisfaction", "type": "soft_binary",
                "description": "All flights fall within 'next month' window",
                "check": "Do all dated flights mentioned fall within the next 30 days from today?",
                "critical": True,
            },
            {
                "id": "T1.a7", "capability": "constraint_satisfaction", "type": "soft_binary",
                "description": "Covers both Chicago airports or justifies focusing on one",
                "check": "Does the response either include flights to both ORD and MDW, or explicitly explain why it's focusing on just one?",
                "critical": False,
            },
            {
                "id": "T1.a8", "capability": "temporal_reasoning", "type": "soft_binary",
                "description": "Notes booking-window or price-trend context",
                "check": "Does the response include any context about when prices are typically lower, booking timing, or price trends — not just a static list?",
                "critical": False,
            },
        ],
    },
    {
        "id": "T2",
        "input": "Best hotels under $200/night in Tokyo for a solo traveler in April",
        "query_type": "transactional",
        "difficulty": "easy",
        "user_intent": "User wants 3-5 specific bookable Tokyo hotels within budget, suitable for solo travel, with awareness that April is cherry blossom season.",
        "quality_bar": (
            "Names 3-5 specific hotels, all under $200/night, each with neighborhood and a "
            "one-line reason it suits solo travel. Flags that April = cherry blossom season = "
            "surge pricing. Does NOT just list neighborhoods without naming hotels."
        ),
        "assertions": [
            {
                "id": "T2.a1", "capability": "grounded_retrieval", "type": "hard_programmatic",
                "description": "Names at least 3 specific hotels",
                "check": r"(Hotel|Hostel|Ryokan|Inn|Capsule|MUJI|Park Hyatt|Andaz|Aman|Tokyu|Granbell|Citadines|Nine Hours|Khaosan|Nui|Gracery|Mimaru)\s+\w+",
                "critical": True,
            },
            {
                "id": "T2.a2", "capability": "grounded_retrieval", "type": "hard_programmatic",
                "description": "Contains at least 2 specific price points",
                "check": r"\$\d{2,3}",
                "critical": True,
            },
            {
                "id": "T2.a3", "capability": "constraint_satisfaction", "type": "soft_binary",
                "description": "All quoted prices are under $200/night",
                "check": "Are ALL hotel prices mentioned in the response under $200 per night?",
                "critical": True,
            },
            {
                "id": "T2.a4", "capability": "constraint_satisfaction", "type": "soft_binary",
                "description": "Addresses solo-traveler context",
                "check": "Does the response specifically address why these hotels suit a SOLO traveler — single-room pricing, social atmosphere, safety, neighborhood for solo exploration?",
                "critical": False,
            },
            {
                "id": "T2.a5", "capability": "temporal_reasoning", "type": "soft_binary",
                "description": "Flags April cherry-blossom seasonality",
                "check": "Does the response mention that April is cherry blossom (hanami/sakura) season, which affects pricing and availability?",
                "critical": True,
            },
            {
                "id": "T2.a6", "capability": "grounded_retrieval", "type": "soft_binary",
                "description": "Includes neighborhood for each hotel",
                "check": "Is each named hotel paired with its Tokyo neighborhood?",
                "critical": False,
            },
            {
                "id": "T2.a7", "capability": "epistemic_calibration", "type": "soft_binary",
                "description": "Prices are plausible for Tokyo April rates",
                "check": "Are the prices given plausible for Tokyo hotels of the described class in April? (E.g., a luxury hotel quoted at $80 would be implausible.)",
                "critical": False,
            },
        ],
    },
    {
        "id": "T3",
        "input": "Direct flights from SFO to JFK on a Tuesday with morning departures",
        "query_type": "transactional",
        "difficulty": "medium",
        "user_intent": "User wants a list of specific Tuesday morning nonstop SFO-JFK flights with flight numbers and times, not airline brochure copy.",
        "quality_bar": (
            "Lists 4+ specific direct flights, all on a Tuesday, all departing before noon "
            "Pacific. Includes flight numbers, exact times, prices. Notes premium-cabin options."
        ),
        "assertions": [
            {
                "id": "T3.a1", "capability": "grounded_retrieval", "type": "hard_programmatic",
                "description": "Contains at least 3 specific flight times",
                "check": r"\d{1,2}:\d{2}\s?(a|p|am|pm|AM|PM)",
                "critical": True,
            },
            {
                "id": "T3.a2", "capability": "grounded_retrieval", "type": "hard_programmatic",
                "description": "Contains flight numbers",
                "check": r"(B6|DL|AA|UA|AS)\s?\d{1,4}",
                "critical": False,
            },
            {
                "id": "T3.a3", "capability": "constraint_satisfaction", "type": "soft_binary",
                "description": "All flights are direct/nonstop",
                "check": "Are all flights mentioned explicitly direct or nonstop, with no layovers?",
                "critical": True,
            },
            {
                "id": "T3.a4", "capability": "constraint_satisfaction", "type": "soft_binary",
                "description": "All departure times are before 12:00 PM Pacific",
                "check": "Are all departure times mentioned before noon (12:00 PM) Pacific time?",
                "critical": True,
            },
            {
                "id": "T3.a5", "capability": "constraint_satisfaction", "type": "soft_binary",
                "description": "Flights are scheduled for a Tuesday",
                "check": "Does the response either specify Tuesday flights or make clear the schedule applies to Tuesdays?",
                "critical": True,
            },
            {
                "id": "T3.a6", "capability": "grounded_retrieval", "type": "soft_binary",
                "description": "Notes premium-cabin availability",
                "check": "Does the response mention premium cabin or lie-flat options (Mint, Polaris, Delta One, Flagship) — relevant for this business-heavy route?",
                "critical": False,
            },
        ],
    },

    # ============================================================
    # ITINERARY
    # ============================================================
    {
        "id": "I1",
        "input": "Plan a 5-day trip to Lisbon for a couple who likes food and architecture, budget $3000 excluding flights",
        "query_type": "itinerary",
        "difficulty": "medium",
        "user_intent": "User wants a concrete executable 5-day Lisbon plan hitting food and architecture interests within $3000 for two.",
        "quality_bar": (
            "Day-by-day structure for all 5 days. Each day has named restaurants/sites with "
            "rough costs. Lodging recommendation with nightly rate. Budget totals under $3000. "
            "Includes Sintra day trip. Balances food AND architecture."
        ),
        "assertions": [
            {
                "id": "I1.a1", "capability": "multi_step_planning", "type": "hard_programmatic",
                "description": "Contains 5 distinct day markers",
                "check": r"(Day\s?[1-5]|D[1-5]\b)",
                "critical": True,
            },
            {
                "id": "I1.a2", "capability": "constraint_satisfaction", "type": "soft_binary",
                "description": "Includes budget calculation that fits under $3000",
                "check": "Does the response include a total cost calculation or breakdown that sums to $3000 or less for two people?",
                "critical": True,
            },
            {
                "id": "I1.a3", "capability": "grounded_retrieval", "type": "soft_binary",
                "description": "Names at least 5 specific restaurants",
                "check": "Does the response name at least 5 specific restaurants by name (e.g., Belcanto, Cervejaria Ramiro, Time Out Market, Prado, 100 Maneiras)?",
                "critical": True,
            },
            {
                "id": "I1.a4", "capability": "grounded_retrieval", "type": "soft_binary",
                "description": "Names at least 4 specific architectural sites",
                "check": "Does the response name at least 4 specific architectural sites (e.g., Jerónimos Monastery, Belém Tower, Castelo de São Jorge, Carmo Convent, MAAT, Sé Cathedral)?",
                "critical": True,
            },
            {
                "id": "I1.a5", "capability": "multi_step_planning", "type": "soft_binary",
                "description": "Includes Sintra day trip",
                "check": "Does the itinerary include a day trip or significant time in Sintra (Pena Palace, Quinta da Regaleira)?",
                "critical": True,
            },
            {
                "id": "I1.a6", "capability": "multi_step_planning", "type": "soft_binary",
                "description": "Recommends specific lodging with nightly rate",
                "check": "Does the response recommend a specific hotel or area to stay with an approximate nightly rate?",
                "critical": False,
            },
            {
                "id": "I1.a7", "capability": "multi_step_planning", "type": "soft_binary",
                "description": "Days are geographically coherent",
                "check": "Does each day cluster activities geographically (Belém day, Alfama day, Bairro Alto day) rather than ping-ponging across distant neighborhoods?",
                "critical": False,
            },
            {
                "id": "I1.a8", "capability": "constraint_satisfaction", "type": "soft_binary",
                "description": "Balances food AND architecture across all days",
                "check": "Across all 5 days, are BOTH food and architecture meaningfully represented — not one heavily favored over the other?",
                "critical": False,
            },
        ],
    },
    {
        "id": "I2",
        "input": "Build a 10-day Japan itinerary covering Tokyo, Kyoto, and Osaka mixing traditional and modern experiences",
        "query_type": "itinerary",
        "difficulty": "hard",
        "user_intent": "User wants a coherent 10-day plan across three cities with deliberate trad/modern balance, day-by-day structure, and inter-city logistics.",
        "quality_bar": (
            "Allocates 10 days across 3 cities (Tokyo 4, Kyoto 3-4, Osaka 2-3). Each city's "
            "days mix traditional AND modern. Includes shinkansen logistics. JR Pass guidance "
            "with break-even reasoning. Notes booking windows (Ghibli, teamLab)."
        ),
        "assertions": [
            {
                "id": "I2.a1", "capability": "multi_step_planning", "type": "hard_programmatic",
                "description": "Contains markers for 10 distinct days",
                "check": r"(Day\s?(10|[1-9])|D(10|[1-9])\b)",
                "critical": True,
            },
            {
                "id": "I2.a2", "capability": "multi_step_planning", "type": "soft_binary",
                "description": "Allocates days across all 3 cities with explicit counts",
                "check": "Does the response explicitly say how many days are spent in each of Tokyo, Kyoto, and Osaka, summing to 10?",
                "critical": True,
            },
            {
                "id": "I2.a3", "capability": "constraint_satisfaction", "type": "soft_binary",
                "description": "Each city includes traditional AND modern recommendations",
                "check": "For Tokyo, Kyoto, AND Osaka, does the response name at least one traditional experience (temple, shrine, tea ceremony, ryokan) AND one modern experience (teamLab, Shibuya, contemporary museum)?",
                "critical": True,
            },
            {
                "id": "I2.a4", "capability": "multi_step_planning", "type": "soft_binary",
                "description": "Specifies shinkansen routing between cities",
                "check": "Does the response include shinkansen routing (Tokyo→Kyoto, Kyoto→Osaka) with travel time or cost?",
                "critical": True,
            },
            {
                "id": "I2.a5", "capability": "multi_step_planning", "type": "soft_binary",
                "description": "Recommends JR Pass with reasoning",
                "check": "Does the response recommend (or recommend against) the JR Pass with cost/break-even reasoning?",
                "critical": False,
            },
            {
                "id": "I2.a6", "capability": "temporal_reasoning", "type": "soft_binary",
                "description": "Flags advance-booking requirements",
                "check": "Does the response flag items requiring advance booking (Ghibli Museum monthly release, teamLab Planets, popular ryokan)?",
                "critical": False,
            },
            {
                "id": "I2.a7", "capability": "multi_step_planning", "type": "soft_binary",
                "description": "City ordering is logical for arrivals",
                "check": "Does the city order make sense given typical international arrivals (Tokyo → Kyoto → Osaka departing KIX, OR reverse)?",
                "critical": False,
            },
        ],
    },
    {
        "id": "I3",
        "input": "I have a 14-hour layover in Doha — what can I realistically do?",
        "query_type": "itinerary",
        "difficulty": "medium",
        "user_intent": "User has a fixed 14-hour window in Doha and needs a realistic time-blocked plan accounting for airport transit, immigration, and return buffer.",
        "quality_bar": (
            "Time-blocked schedule within 14 hours. Subtracts airport transit and 3h pre-"
            "departure buffer. Names 3-4 Doha sites. Mentions Qatar transit visa or QA city "
            "tour. Recommends what to skip."
        ),
        "assertions": [
            {
                "id": "I3.a1", "capability": "multi_step_planning", "type": "soft_binary",
                "description": "Provides time-blocked schedule",
                "check": "Is the response structured as a time-blocked schedule with explicit hour ranges or times, rather than a flat list of suggestions?",
                "critical": True,
            },
            {
                "id": "I3.a2", "capability": "temporal_reasoning", "type": "soft_binary",
                "description": "Subtracts realistic airport buffer time",
                "check": "Does the response account for airport time (immigration, security, return buffer of at least 2-3 hours before international departure)?",
                "critical": True,
            },
            {
                "id": "I3.a3", "capability": "grounded_retrieval", "type": "soft_binary",
                "description": "Names 3+ specific Doha sites",
                "check": "Does the response name at least 3 specific sites in Doha (Souq Waqif, Museum of Islamic Art, Corniche, Katara Cultural Village, The Pearl, National Museum)?",
                "critical": True,
            },
            {
                "id": "I3.a4", "capability": "grounded_retrieval", "type": "soft_binary",
                "description": "Mentions Qatar transit visa or QA free city tour",
                "check": "Does the response mention the Qatar transit visa, e-visa requirements, or the Qatar Airways complimentary city tour?",
                "critical": False,
            },
            {
                "id": "I3.a5", "capability": "constraint_satisfaction", "type": "soft_binary",
                "description": "Recommends what to skip",
                "check": "Does the response explicitly recommend skipping certain activities (desert safari, far destinations) that wouldn't fit?",
                "critical": False,
            },
            {
                "id": "I3.a6", "capability": "multi_step_planning", "type": "soft_binary",
                "description": "Includes transit method airport↔city",
                "check": "Does the response specify how to get between Hamad International Airport and the city (metro, taxi/Uber, with approximate cost or time)?",
                "critical": False,
            },
        ],
    },

    # ============================================================
    # PERSONALIZED
    # ============================================================
    {
        "id": "P1",
        "input": "I loved my trips to Mexico City and Lisbon. Where should I go next?",
        "query_type": "personalized",
        "difficulty": "medium",
        "user_intent": "User wants destination recommendations matching the vibe of CDMX + Lisbon, with reasoning that demonstrates understanding of what those cities share.",
        "quality_bar": (
            "Identifies shared DNA: walkable neighborhoods, food culture, lived-in "
            "authenticity, layered history. Recommends 3-5 destinations with explicit "
            "reasoning. Strong candidates: Istanbul, Buenos Aires, Naples, Tbilisi, Oaxaca."
        ),
        "assertions": [
            {
                "id": "P1.a1", "capability": "preference_inference", "type": "soft_binary",
                "description": "Articulates shared characteristics of CDMX and Lisbon",
                "check": "Does the response explicitly articulate what CDMX and Lisbon have in common (walkability, food culture, authenticity, layered history) BEFORE giving recommendations?",
                "critical": True,
            },
            {
                "id": "P1.a2", "capability": "preference_inference", "type": "soft_binary",
                "description": "Each rec is tied to inferred preference",
                "check": "For each destination, does the response explain WHY it fits the user's revealed taste — not just generic descriptions?",
                "critical": True,
            },
            {
                "id": "P1.a3", "capability": "preference_inference", "type": "soft_binary",
                "description": "Recs are thoughtful matches, not tourist clichés",
                "check": "Are recommendations thoughtful matches (Istanbul, Buenos Aires, Naples, Tbilisi, Oaxaca, Porto, Tangier, Bogotá) rather than generic 'popular destinations' like Paris, Rome, London?",
                "critical": True,
            },
            {
                "id": "P1.a4", "capability": "ambiguity_handling", "type": "soft_binary",
                "description": "Commits to recommendations",
                "check": "Does the response give concrete destination recommendations rather than ONLY asking clarifying questions?",
                "critical": True,
            },
            {
                "id": "P1.a5", "capability": "preference_inference", "type": "soft_binary",
                "description": "Identifies top pick or differentiates recommendations",
                "check": "Does the response either name a top pick OR explain how the recommendations differ from each other?",
                "critical": False,
            },
        ],
    },
    {
        "id": "P2",
        "input": "Beach destination in November that's not crowded, good food, under 8 hours flight from NYC",
        "query_type": "personalized",
        "difficulty": "hard",
        "user_intent": "User wants a beach trip in November from NYC under 8 hours, optimized against crowds and for food.",
        "quality_bar": (
            "Top recommendation with reasoning (likely Cartagena, Vieques, Holbox, Bacalar, "
            "Belize). Steers AWAY from over-touristed Nov destinations. Mentions specific "
            "restaurants. Notes November as shoulder season."
        ),
        "assertions": [
            {
                "id": "P2.a1", "capability": "constraint_satisfaction", "type": "soft_binary",
                "description": "All recs within 8-hour flight of NYC",
                "check": "Are all recommended destinations realistically within 8 hours of nonstop flight from NYC? (Tahiti, Maldives, Seychelles would fail.)",
                "critical": True,
            },
            {
                "id": "P2.a2", "capability": "temporal_reasoning", "type": "soft_binary",
                "description": "Addresses November seasonality",
                "check": "Does the response address November specifically — weather and whether it's shoulder/peak season for each recommendation?",
                "critical": True,
            },
            {
                "id": "P2.a3", "capability": "constraint_satisfaction", "type": "soft_binary",
                "description": "Honors 'not crowded' constraint",
                "check": "Do the recommendations avoid over-touristed November destinations (peak-season Tulum, Cancún) OR explain why a popular destination is quiet in November?",
                "critical": True,
            },
            {
                "id": "P2.a4", "capability": "preference_inference", "type": "soft_binary",
                "description": "Addresses 'good food' with specifics",
                "check": "Does the response specifically address food — naming restaurants, food scenes, or cuisines rather than just saying 'good food'?",
                "critical": True,
            },
            {
                "id": "P2.a5", "capability": "preference_inference", "type": "soft_binary",
                "description": "Recommends 2-4 options",
                "check": "Does the response recommend 2-4 destinations — curated set rather than single option OR exhaustive list of 8+?",
                "critical": False,
            },
            {
                "id": "P2.a6", "capability": "preference_inference", "type": "soft_binary",
                "description": "Identifies top pick",
                "check": "Does the response identify ONE top recommendation rather than presenting all as equivalent?",
                "critical": False,
            },
        ],
    },

    # ============================================================
    # LIVE DATA
    # ============================================================
    {
        "id": "L1",
        "input": "Is it a good time to book flights to Bali for December, or should I wait?",
        "query_type": "live_data",
        "difficulty": "hard",
        "user_intent": "User wants a defensible book-now-or-wait recommendation grounded in price trends and December seasonality.",
        "quality_bar": (
            "Clear book-now-or-wait recommendation with reasoning. Notes December = peak "
            "holiday + Bali rainy season. Suggests flexible dates. Calibrates confidence."
        ),
        "assertions": [
            {
                "id": "L1.a1", "capability": "temporal_reasoning", "type": "soft_binary",
                "description": "Gives clear directional recommendation",
                "check": "Does the response give an explicit recommendation to either book now or wait, rather than presenting both options as equivalent?",
                "critical": True,
            },
            {
                "id": "L1.a2", "capability": "temporal_reasoning", "type": "soft_binary",
                "description": "Identifies December as peak holiday season",
                "check": "Does the response explicitly note that December is peak holiday travel season and that this affects pricing?",
                "critical": True,
            },
            {
                "id": "L1.a3", "capability": "temporal_reasoning", "type": "soft_binary",
                "description": "Notes Bali's December weather (rainy season)",
                "check": "Does the response mention December is in Bali's rainy season, providing seasonal context beyond price?",
                "critical": False,
            },
            {
                "id": "L1.a4", "capability": "temporal_reasoning", "type": "soft_binary",
                "description": "Suggests date flexibility as a hedge",
                "check": "Does the response suggest shifting dates (earlier December, late November, January) as a price-saving alternative?",
                "critical": False,
            },
            {
                "id": "L1.a5", "capability": "epistemic_calibration", "type": "soft_binary",
                "description": "Calibrates confidence appropriately",
                "check": "Does the response acknowledge uncertainty inherent in price predictions rather than making confident specific claims it cannot back up?",
                "critical": False,
            },
            {
                "id": "L1.a6", "capability": "temporal_reasoning", "type": "soft_binary",
                "description": "Provides price reference points or trends",
                "check": "Does the response include any price reference points (typical ranges, trend direction, comparison to other months)?",
                "critical": False,
            },
        ],
    },
    {
        "id": "L2",
        "input": "Weather in Reykjavik next week and packing recommendations",
        "query_type": "live_data",
        "difficulty": "easy",
        "user_intent": "User wants the coming week's Reykjavik forecast with a packing list calibrated to Iceland's specific weather quirks.",
        "quality_bar": (
            "Specifies temperature range, precipitation, wind, daylight hours. Packing list "
            "addresses Iceland specifics: waterproof shell, layers, waterproof boots, swimsuit "
            "for geothermal pools. No umbrella."
        ),
        "assertions": [
            {
                "id": "L2.a1", "capability": "grounded_retrieval", "type": "hard_programmatic",
                "description": "Contains temperature values",
                "check": r"\d{1,3}\s?°?\s?[FC]",
                "critical": True,
            },
            {
                "id": "L2.a2", "capability": "temporal_reasoning", "type": "soft_binary",
                "description": "Includes daylight-hours context",
                "check": "Does the response mention daylight hours (relevant year-round in Iceland due to extreme variation)?",
                "critical": False,
            },
            {
                "id": "L2.a3", "capability": "temporal_reasoning", "type": "soft_binary",
                "description": "Notes signature Iceland weather (wind, mixed precip)",
                "check": "Does the response note Reykjavik's signature weather — high wind, mixed precipitation (sideways rain), or rapid changes?",
                "critical": False,
            },
            {
                "id": "L2.a4", "capability": "grounded_retrieval", "type": "soft_binary",
                "description": "Packing list addresses Iceland specifics",
                "check": "Does the packing list include Iceland-specific items: waterproof/windproof shell, waterproof boots, swimsuit for geothermal pools?",
                "critical": True,
            },
            {
                "id": "L2.a5", "capability": "grounded_retrieval", "type": "soft_binary",
                "description": "Does NOT recommend an umbrella",
                "check": "Does the response either not recommend an umbrella, or explicitly warn against bringing one (because Iceland's wind makes umbrellas useless)?",
                "critical": False,
            },
            {
                "id": "L2.a6", "capability": "grounded_retrieval", "type": "soft_binary",
                "description": "Layering strategy specified",
                "check": "Does the response specify a layering strategy (base + mid + shell) rather than just 'pack warm clothes'?",
                "critical": False,
            },
        ],
    },

    # ============================================================
    # EDGE CASE
    # ============================================================
    {
        "id": "E1",
        "input": "Find me a flight that lets me sleep in my own bed both nights for a meeting in Denver from Seattle",
        "query_type": "edge_case",
        "difficulty": "hard",
        "user_intent": "User wants a same-day round-trip from Seattle to Denver, sleeping at home both nights surrounding the meeting day.",
        "quality_bar": (
            "Correctly interprets as same-day round trip. Returns specific early-morning SEA→"
            "DEN options and evening returns. Notes DEN-to-downtown transit (A-Line, 30-45 min). "
            "Flags time-zone consideration."
        ),
        "assertions": [
            {
                "id": "E1.a1", "capability": "ambiguity_handling", "type": "soft_binary",
                "description": "Correctly interprets 'sleep in own bed both nights' as same-day round trip",
                "check": "Does the response correctly interpret the constraint as 'same-day round trip with no overnight in Denver'? (Not as a 2-night trip with early-return flights.)",
                "critical": True,
            },
            {
                "id": "E1.a2", "capability": "grounded_retrieval", "type": "soft_binary",
                "description": "Returns specific outbound morning flights",
                "check": "Does the response provide at least 2 specific morning SEA→DEN flights with times and prices?",
                "critical": True,
            },
            {
                "id": "E1.a3", "capability": "grounded_retrieval", "type": "soft_binary",
                "description": "Returns specific evening return flights",
                "check": "Does the response provide at least 2 specific evening DEN→SEA return flights with times and prices?",
                "critical": True,
            },
            {
                "id": "E1.a4", "capability": "temporal_reasoning", "type": "soft_binary",
                "description": "Accounts for time-zone shift",
                "check": "Does the response acknowledge the one-hour time zone difference between SEA (Pacific) and DEN (Mountain)?",
                "critical": False,
            },
            {
                "id": "E1.a5", "capability": "grounded_retrieval", "type": "soft_binary",
                "description": "Mentions DEN-to-downtown transit",
                "check": "Does the response mention transit between DEN airport and downtown Denver (A-Line train, ~30-45 min)?",
                "critical": False,
            },
            {
                "id": "E1.a6", "capability": "ambiguity_handling", "type": "soft_binary",
                "description": "Verifies feasibility",
                "check": "Does the response either confirm the same-day trip is feasible OR flag that meeting timing affects whether it works?",
                "critical": False,
            },
        ],
    },
    {
        "id": "E2",
        "input": "I have 48 hours, $500, leaving from Boston — surprise me",
        "query_type": "edge_case",
        "difficulty": "hard",
        "user_intent": "User invited a single confident recommendation. Should commit to ONE destination with conviction, not punt with a list.",
        "quality_bar": (
            "Commits to ONE primary destination. Stays under $500 total. Fits in 48h from BOS. "
            "Sells the choice with reasoning. Brief plan included. Optional single backup."
        ),
        "assertions": [
            {
                "id": "E2.a1", "capability": "ambiguity_handling", "type": "soft_binary",
                "description": "Commits to ONE primary destination",
                "check": "Does the response commit to ONE primary destination as the main recommendation, rather than presenting 3+ options as equivalent? (One backup option is acceptable as long as the primary is clear.)",
                "critical": True,
            },
            {
                "id": "E2.a2", "capability": "constraint_satisfaction", "type": "soft_binary",
                "description": "Budget breakdown fits within $500",
                "check": "Does the response include a budget breakdown that totals to $500 or less (flight + lodging + food + transit)?",
                "critical": True,
            },
            {
                "id": "E2.a3", "capability": "constraint_satisfaction", "type": "soft_binary",
                "description": "Reachable from BOS in 48 hours",
                "check": "Is the destination realistically reachable from Boston such that travel time leaves meaningful time on the ground in a 48-hour window?",
                "critical": True,
            },
            {
                "id": "E2.a4", "capability": "preference_inference", "type": "soft_binary",
                "description": "Sells the choice with specific reasoning",
                "check": "Does the response explain WHY this destination is the right pick — specific reasoning, not just 'it's affordable and close'?",
                "critical": True,
            },
            {
                "id": "E2.a5", "capability": "ambiguity_handling", "type": "soft_binary",
                "description": "Includes a brief 48-hour plan",
                "check": "Does the response include a brief plan for what to do during the 48 hours, not just naming the destination?",
                "critical": False,
            },
            {
                "id": "E2.a6", "capability": "preference_inference", "type": "soft_binary",
                "description": "Mentions named restaurants, sites, or experiences",
                "check": "Does the response name specific restaurants, neighborhoods, or experiences at the destination?",
                "critical": False,
            },
        ],
    },
]


# ============================================================
# 5. ASSERTION EVALUATION
# ============================================================

def evaluate_hard_assertion(response_text: str, pattern: str) -> bool:
    """Regex match. Deterministic and free."""
    return bool(re.search(pattern, response_text, re.IGNORECASE))


def evaluate_soft_assertion(response_text: str, criterion: str, user_input: str) -> bool:
    """LLM judge answers binary yes/no. Binary calibrates much better than 1-5."""
    judge_prompt = f"""You are evaluating a travel-AI response against a single specific criterion.

User's original query: {user_input}

Response being evaluated:
---
{response_text}
---

Criterion to evaluate:
{criterion}

Answer ONLY 'YES' or 'NO'. Do not explain. Do not hedge. If the criterion is not clearly and explicitly satisfied, answer NO.

Answer:"""
    raise NotImplementedError("Wire up to your judge model")


def score_response(response_text: str, row: EvalRow, user_input: str) -> dict:
    """Score one response against all assertions for a row.

    Returns a profile: per-capability pass rate, list of failed critical
    assertions, overall pass rate.
    """
    results_by_capability: dict[str, list[bool]] = {}
    critical_failures: list[str] = []

    for assertion in row["assertions"]:
        cap = assertion["capability"]
        results_by_capability.setdefault(cap, [])

        if assertion["type"] == "hard_programmatic":
            passed = evaluate_hard_assertion(response_text, assertion["check"])
        else:
            passed = evaluate_soft_assertion(response_text, assertion["check"], user_input)

        results_by_capability[cap].append(passed)
        if not passed and assertion["critical"]:
            critical_failures.append(assertion["id"])

    capability_profile = {
        cap: {
            "passed": sum(results),
            "total": len(results),
            "pass_rate": sum(results) / len(results) if results else 0.0,
        }
        for cap, results in results_by_capability.items()
    }

    return {
        "row_id": row["id"],
        "query_type": row["query_type"],
        "capability_profile": capability_profile,
        "critical_failures": critical_failures,
        "disqualified": len(critical_failures) > 0,
    }


# ============================================================
# 6. DASHBOARD AGGREGATION
# ============================================================

def aggregate_results(
    mindtrip_scores: list[dict],
    wanderboat_scores: list[dict],
) -> dict:
    """Compete dashboard view: wins sliced by query type AND by capability."""
    wins_by_query_type: dict[str, dict[str, int]] = {
        qt: {"mindtrip": 0, "wanderboat": 0, "tie": 0} for qt in QUERY_TYPES
    }
    wins_by_capability: dict[str, dict[str, int]] = {
        cap: {"mindtrip": 0, "wanderboat": 0, "tie": 0} for cap in CAPABILITIES
    }
    needs_review: list[str] = []

    for m, w in zip(mindtrip_scores, wanderboat_scores):
        # Roll up to query type by averaging capability pass rates
        m_overall = sum(c["pass_rate"] for c in m["capability_profile"].values()) / len(m["capability_profile"])
        w_overall = sum(c["pass_rate"] for c in w["capability_profile"].values()) / len(w["capability_profile"])

        qt = m["query_type"]
        if abs(m_overall - w_overall) < 0.15:
            wins_by_query_type[qt]["tie"] += 1
        elif m_overall > w_overall:
            wins_by_query_type[qt]["mindtrip"] += 1
        else:
            wins_by_query_type[qt]["wanderboat"] += 1

        # Per-capability comparison
        for cap in m["capability_profile"]:
            m_rate = m["capability_profile"][cap]["pass_rate"]
            w_rate = w["capability_profile"].get(cap, {}).get("pass_rate", 0)
            if abs(m_rate - w_rate) < 0.15:
                wins_by_capability[cap]["tie"] += 1
            elif m_rate > w_rate:
                wins_by_capability[cap]["mindtrip"] += 1
            else:
                wins_by_capability[cap]["wanderboat"] += 1

        if m["disqualified"] and w["disqualified"]:
            needs_review.append(f"Both DQ'd on {m['row_id']}")

    return {
        "wins_by_query_type": wins_by_query_type,
        "wins_by_capability": wins_by_capability,
        "critical_failure_rate": {
            "mindtrip": sum(1 for s in mindtrip_scores if s["disqualified"]) / len(mindtrip_scores),
            "wanderboat": sum(1 for s in wanderboat_scores if s["disqualified"]) / len(wanderboat_scores),
        },
        "needs_human_review": needs_review,
    }


# ============================================================
# 7. DATASET STATS
# ============================================================
if __name__ == "__main__":
    total_assertions = sum(len(r["assertions"]) for r in DATASET)
    critical_assertions = sum(1 for r in DATASET for a in r["assertions"] if a["critical"])

    by_type: dict[str, int] = {qt: 0 for qt in QUERY_TYPES}
    for r in DATASET:
        by_type[r["query_type"]] += 1

    by_capability: dict[str, int] = {cap: 0 for cap in CAPABILITIES}
    for r in DATASET:
        for a in r["assertions"]:
            by_capability[a["capability"]] += 1

    print(f"Prompts: {len(DATASET)}")
    print(f"Total assertions: {total_assertions}")
    print(f"Critical assertions: {critical_assertions}")
    print(f"Avg assertions/prompt: {total_assertions/len(DATASET):.1f}")

    print(f"\nPrompts per query type:")
    for qt, n in by_type.items():
        print(f"  {qt}: {n}")

    print(f"\nAssertions per capability:")
    for cap, n in sorted(by_capability.items(), key=lambda x: -x[1]):
        print(f"  {cap}: {n}")
