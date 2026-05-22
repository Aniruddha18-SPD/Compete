"""
Rubric and dataset definitions — no braintrust dependency.
compete_eval.py imports from here; runner.py imports from here too.
"""

from typing import TypedDict, Literal


RUBRIC = {
    "actionability": {
        "weight": 0.30,
        "definition": "Can the user act on this response immediately? Concrete bookable options, links, prices, times — not vague suggestions to 'check' or 'consider'.",
        "anchors": {
            1: "Pure prose, no actionable items. User has to start from scratch.",
            3: "Some specifics but user still needs to do significant research.",
            5: "Direct bookable options with prices, dates, links. User can act in one click.",
        },
    },
    "specificity": {
        "weight": 0.25,
        "definition": "Concrete named entities (hotels, neighborhoods, restaurants, flight numbers) vs generic categories.",
        "anchors": {
            1: "Generic categories only ('a nice hotel', 'good restaurants').",
            3: "Mix of named entities and generic recommendations.",
            5: "Every recommendation is a named, verifiable entity with relevant details.",
        },
    },
    "personalization": {
        "weight": 0.25,
        "definition": "Does the response use ALL constraints in the query (budget, dates, preferences, travel style)? Penalize ignored constraints.",
        "anchors": {
            1: "Ignores most stated constraints; generic answer.",
            3: "Uses primary constraints but misses secondary ones.",
            5: "Uses every constraint and infers reasonable defaults for unstated ones.",
        },
    },
    "trustworthiness": {
        "weight": 0.20,
        "definition": "Are factual claims (prices, hours, distances, flight times) plausibly grounded? Penalize obvious hallucinations and outdated info.",
        "anchors": {
            1: "Multiple obvious hallucinations or impossible claims.",
            3: "Mostly plausible but some unverified specifics.",
            5: "All claims grounded; clearly cites or qualifies uncertain data.",
        },
    },
}


class EvalRow(TypedDict):
    id: str
    input: str
    bucket: str
    difficulty: Literal["easy", "medium", "hard"]
    expected_winner: Literal["mindtrip", "wanderboat", "tie"]
    rationale: str


DATASET: list[EvalRow] = [
    {"id": "T1", "input": "Find me the cheapest flights from Seattle to Chicago in the next month",          "bucket": "transactional", "difficulty": "easy",   "expected_winner": "mindtrip",   "rationale": "Transactional query rewards specific flight numbers and prices."},
    {"id": "T2", "input": "Best hotels under $200/night in Tokyo for a solo traveler in April",             "bucket": "transactional", "difficulty": "easy",   "expected_winner": "tie",        "rationale": "Both handle hotel recs reasonably well."},
    {"id": "T3", "input": "Direct flights from SFO to JFK on a Tuesday with morning departures",           "bucket": "transactional", "difficulty": "medium", "expected_winner": "mindtrip",   "rationale": "Specific flight details favour structured response."},
    {"id": "I1", "input": "Plan a 5-day trip to Lisbon for a couple who likes food and architecture, budget $3000 excluding flights", "bucket": "itinerary", "difficulty": "medium", "expected_winner": "mindtrip", "rationale": "Day-by-day plan with budget reconciliation."},
    {"id": "I2", "input": "Build a 10-day Japan itinerary covering Tokyo, Kyoto, and Osaka mixing traditional and modern experiences", "bucket": "itinerary", "difficulty": "hard", "expected_winner": "wanderboat", "rationale": "Reads like a knowledgeable friend — context and pro tips."},
    {"id": "I3", "input": "I have a 14-hour layover in Doha — what can I realistically do?",               "bucket": "itinerary",     "difficulty": "medium", "expected_winner": "mindtrip",   "rationale": "Time-blocked precision wins layover queries."},
    {"id": "P1", "input": "I loved my trips to Mexico City and Lisbon. Where should I go next?",           "bucket": "personalized",  "difficulty": "medium", "expected_winner": "wanderboat", "rationale": "Pattern recognition and explanatory recs."},
    {"id": "P2", "input": "Beach destination in November that's not crowded, good food, under 8 hours flight from NYC", "bucket": "personalized", "difficulty": "hard", "expected_winner": "wanderboat", "rationale": "Constraints as starting point, not filter."},
    {"id": "L1", "input": "Is it a good time to book flights to Bali for December, or should I wait?",     "bucket": "live_data",     "difficulty": "hard",   "expected_winner": "mindtrip",   "rationale": "Price trends and confidence interval data."},
    {"id": "L2", "input": "Weather in Reykjavik next week and packing recommendations",                    "bucket": "live_data",     "difficulty": "easy",   "expected_winner": "tie",        "rationale": "Both responses are substantively equivalent."},
    {"id": "E1", "input": "Find me a flight that lets me sleep in my own bed both nights for a meeting in Denver from Seattle", "bucket": "edge_case", "difficulty": "hard", "expected_winner": "tie", "rationale": "Mindtrip nails structure; Wanderboat adds transit tips."},
    {"id": "E2", "input": "I have 48 hours, $500, leaving from Boston — surprise me",                      "bucket": "edge_case",     "difficulty": "hard",   "expected_winner": "wanderboat", "rationale": "'Surprise me' is a vibes query — one conviction pick wins."},
]
