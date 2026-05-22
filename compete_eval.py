"""
Compete prototype: Mindtrip vs Wanderboat head-to-head eval.
"""

from braintrust import Eval
from autoevals import Battle
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
    mindtrip_response: str
    wanderboat_response: str
    expected_winner: Literal["mindtrip", "wanderboat", "tie"]
    rationale: str


DATASET: list[EvalRow] = [
    {
        "id": "T1",
        "input": "Find me the cheapest flights from Seattle to Chicago in the next month",
        "bucket": "transactional",
        "difficulty": "easy",
        "mindtrip_response": (
            "Here are the cheapest SEA→ORD/MDW options for the next 30 days:\n\n"
            "1. Frontier F9 1820, Dec 3, 6:15a SEA → 12:32p MDW, $87 one-way\n"
            "2. Spirit NK 712, Dec 11, 11:40p SEA → 5:55a MDW (red-eye), $94\n"
            "3. Alaska AS 736, Dec 9, 10:05a SEA → 4:18p ORD, $128 (free carry-on)\n"
            "4. United UA 1455, Dec 17, 7:00a SEA → 1:08p ORD, $142\n\n"
            "Cheapest round-trip: Frontier Dec 3–7, $164 total. "
            "Book direct on Frontier — third-party sites adding $20 in fees right now."
        ),
        "wanderboat_response": (
            "Flights from Seattle to Chicago are pretty affordable in December! "
            "You can usually find good deals on budget carriers like Frontier and Spirit, "
            "with prices starting around $90-100 one-way if you're flexible on dates. "
            "Alaska and United also fly the route with more amenities. "
            "I'd recommend checking Google Flights or Skyscanner for the latest prices. "
            "Tuesday and Wednesday departures tend to be cheapest. Want me to help plan "
            "what to do once you arrive in Chicago?"
        ),
        "expected_winner": "mindtrip",
        "rationale": "Mindtrip gives specific flight numbers, dates, prices, and a booking recommendation — directly actionable. Wanderboat gives generic advice and pivots to itinerary planning instead of answering the question.",
    },
    {
        "id": "T2",
        "input": "Best hotels under $200/night in Tokyo for a solo traveler in April",
        "bucket": "transactional",
        "difficulty": "easy",
        "mindtrip_response": (
            "Top picks under $200/night in Tokyo for April (cherry blossom season — book ASAP):\n\n"
            "• Hotel Gracery Shinjuku — $165/night, capsule-meets-business, Godzilla view rooms, "
            "5 min from Shinjuku Station\n"
            "• MUJI Hotel Ginza — $185/night, minimalist design, central Ginza\n"
            "• Nine Hours Shinjuku-North — $55/night, premium capsule, solo-friendly\n"
            "• Citadines Shinjuku — $175/night, apartment-style, kitchenette\n\n"
            "April rates run 20-30% above base — these are current quotes pulled today. "
            "Avoid the week of April 5-12 (peak bloom) if budget-constrained."
        ),
        "wanderboat_response": (
            "Tokyo has amazing options for solo travelers under $200! For April specifically, "
            "I'd suggest looking at neighborhoods like Shinjuku, Shibuya, or Asakusa depending on "
            "your vibe. Shinjuku is great for nightlife and transit access, Shibuya for shopping "
            "and youth culture, and Asakusa for traditional atmosphere near Senso-ji temple.\n\n"
            "Some solid options:\n"
            "- Hotel Gracery Shinjuku (mid-range, fun Godzilla theme)\n"
            "- Khaosan Tokyo Origami (hostel vibes, social)\n"
            "- Nui. Hostel & Bar Lounge in Kuramae (design-forward, great for solo travelers)\n\n"
            "April is cherry blossom season so book early! Yoyogi Park and Meguro River are "
            "must-sees for hanami."
        ),
        "expected_winner": "tie",
        "rationale": "Mindtrip wins on actionability; Wanderboat wins on personalization. Roughly balanced.",
    },
    {
        "id": "T3",
        "input": "Direct flights from SFO to JFK on a Tuesday with morning departures",
        "bucket": "transactional",
        "difficulty": "medium",
        "mindtrip_response": (
            "Tuesday morning SFO→JFK direct options:\n\n"
            "• JetBlue B6 1216 — 6:30a SFO → 3:00p JFK, from $189\n"
            "• Delta DL 414 — 7:00a SFO → 3:35p JFK, from $215\n"
            "• American AA 84 — 7:45a SFO → 4:20p JFK, from $208\n"
            "• United UA 478 — 8:15a SFO → 4:45p JFK, from $234 (Polaris available)\n"
            "• JetBlue B6 1416 — 10:25a SFO → 7:00p JFK, from $179 (Mint upgrades $400)\n\n"
            "Cheapest: JetBlue 10:25a at $179. Lie-flat option: JetBlue Mint or United Polaris."
        ),
        "wanderboat_response": (
            "Several airlines fly SFO to JFK direct in the morning. JetBlue, Delta, American, "
            "and United all have early flights. JetBlue is usually the most affordable and has "
            "good amenities including free WiFi. Delta and United offer premium cabin options "
            "if you want lie-flat seats. Morning flights typically depart between 6am and 10am."
        ),
        "expected_winner": "mindtrip",
        "rationale": "Mindtrip provides actionable specifics, Wanderboat stays at category level.",
    },
    {
        "id": "I1",
        "input": "Plan a 5-day trip to Lisbon for a couple who likes food and architecture, budget $3000 excluding flights",
        "bucket": "itinerary",
        "difficulty": "medium",
        "mindtrip_response": (
            "**Lisbon, 5 days, $3000 for two (ex-flights)**\n\n"
            "**Lodging** ($900): Memmo Alfama, boutique hotel with river views, $180/night × 5\n\n"
            "**Day 1 — Alfama & Fado**\n"
            "• Morning: Sé Cathedral, Castelo de São Jorge ($15 entry)\n"
            "• Lunch: Prado ($60 for two)\n"
            "• Evening: Fado at Mesa de Frades ($120 prix fixe)\n\n"
            "**Day 2 — Belém**\n"
            "• Jerónimos Monastery + Belém Tower ($25)\n"
            "• Pastéis de Belém (original, $8)\n"
            "• MAAT museum ($12)\n"
            "• Dinner: Feitoria, 1 Michelin star ($240)\n\n"
            "**Day 3 — Chiado/Bairro Alto**\n"
            "• Carmo Convent ruins ($7)\n"
            "• Lunch at Time Out Market ($50)\n"
            "• Sunset at Miradouro de Santa Catarina (free)\n"
            "• Dinner: Cervejaria Ramiro, seafood ($90)\n\n"
            "**Day 4 — Sintra day trip**\n"
            "• Pena Palace + Quinta da Regaleira ($30)\n"
            "• Lunch: Tascantiga ($40)\n"
            "• Return for dinner: Bairro do Avillez ($150)\n\n"
            "**Day 5 — LX Factory & departure**\n"
            "• Brunch: Landeau Chocolate\n"
            "• LX Factory shopping & murals\n"
            "• Farewell: 100 Maneiras tasting menu ($280)\n\n"
            "**Total estimated**: $2,847 — leaves $150 buffer."
        ),
        "wanderboat_response": (
            "Lisbon is perfect for food and architecture lovers! Here's a rough plan:\n\n"
            "Stay in Alfama or Chiado for character and walkability. Boutique hotels in these "
            "areas run $150-200/night.\n\n"
            "Must-do food experiences:\n"
            "- Pastéis de Belém for the original custard tarts\n"
            "- Time Out Market for variety\n"
            "- A traditional tasca for bacalhau and grilled sardines\n"
            "- At least one Fado dinner — incredible cultural experience\n\n"
            "Architecture highlights:\n"
            "- Jerónimos Monastery (Manueline style)\n"
            "- Belém Tower\n"
            "- Castelo de São Jorge for the views\n"
            "- Day trip to Sintra — Pena Palace and Quinta da Regaleira are unmissable\n\n"
            "Don't miss a sunset at one of the miradouros — Santa Catarina or Portas do Sol are "
            "favorites. Save a day for Sintra; it deserves the full day.\n\n"
            "Tram 28 is touristy but genuinely fun for the architecture spotting."
        ),
        "expected_winner": "mindtrip",
        "rationale": "Mindtrip delivers day-by-day plan with named restaurants, prices, and budget reconciliation.",
    },
    {
        "id": "I2",
        "input": "Build a 10-day Japan itinerary covering Tokyo, Kyoto, and Osaka mixing traditional and modern experiences",
        "bucket": "itinerary",
        "difficulty": "hard",
        "mindtrip_response": (
            "**10 Days: Tokyo (4) → Kyoto (4) → Osaka (2)**\n\n"
            "**Tokyo D1-4**\n"
            "D1: Shibuya Crossing, Meiji Shrine, dinner at Omoide Yokocho\n"
            "D2: TeamLab Planets (modern), Asakusa/Senso-ji (traditional)\n"
            "D3: Day trip — Hakone (Mt Fuji views, onsen)\n"
            "D4: Tsukiji breakfast, Akihabara, Robot Restaurant\n\n"
            "Shinkansen Tokyo→Kyoto ($95, 2h15m)\n\n"
            "**Kyoto D5-8**\n"
            "D5: Fushimi Inari (sunrise), Tofuku-ji\n"
            "D6: Arashiyama bamboo, Tenryu-ji, Iwatayama monkeys\n"
            "D7: Kinkaku-ji, Ryoan-ji, Nishiki Market\n"
            "D8: Gion district, tea ceremony at Camellia\n\n"
            "Train Kyoto→Osaka ($15, 30m)\n\n"
            "**Osaka D9-10**\n"
            "D9: Dotonbori, Osaka Castle, takoyaki crawl\n"
            "D10: Umeda Sky Building, departure from KIX\n\n"
            "Recommend JR Pass 7-day ($335) — break-even at Tokyo→Kyoto round trip."
        ),
        "wanderboat_response": (
            "Ten days in Japan is the sweet spot for first-timers! Here's how I'd split it:\n\n"
            "**Tokyo (4 days)** — start here for the modern energy. Mix neon and tradition:\n"
            "Shibuya and Shinjuku for the futuristic side, Asakusa and Yanaka for old Tokyo. "
            "TeamLab Planets is a must for the modern art experience. Spend a day in Harajuku/"
            "Omotesando for fashion and people-watching. Consider a Mt. Fuji day trip via Hakone — "
            "the ropeway + onsen combo is magical.\n\n"
            "**Kyoto (4 days)** — the traditional heart. Fushimi Inari at dawn is genuinely "
            "transcendent before the crowds arrive. Arashiyama deserves a full day (bamboo grove "
            "+ monkey park + Tenryu-ji). Don't miss tea ceremony — Camellia in Gion is "
            "tourist-friendly but authentic. Save Kinkaku-ji and Ryoan-ji for a Zen-temple day.\n\n"
            "**Osaka (2 days)** — food capital. Dotonbori is the iconic strip; do a takoyaki and "
            "okonomiyaki crawl. Osaka Castle is worth a half-day. Stay in Namba for nightlife.\n\n"
            "**Logistics**: Get a 7-day JR Pass — it pays for itself with the Tokyo↔Kyoto "
            "shinkansen alone. Activate it when you leave Tokyo. Use Suica/Pasmo for subways.\n\n"
            "**Pro tip**: Book Ghibli Museum tickets the moment they release (10th of each month "
            "for following month) if that's your thing."
        ),
        "expected_winner": "wanderboat",
        "rationale": "Wanderboat reads like a knowledgeable friend — context for why each city, transitions, pro tips.",
    },
    {
        "id": "I3",
        "input": "I have a 14-hour layover in Doha — what can I realistically do?",
        "bucket": "itinerary",
        "difficulty": "medium",
        "mindtrip_response": (
            "**Doha 14h layover plan**\n\n"
            "Qatar offers free transit visa (most nationalities) and Qatar Airways free city tour "
            "if layover is 5-12h — yours is just over, but you can book independently.\n\n"
            "**0-1h**: Clear immigration, store bag at HIA left luggage ($10/bag)\n"
            "**1-2h**: Uber to Souq Waqif ($15, 20min) — traditional market, breakfast\n"
            "**2-4h**: Museum of Islamic Art (closes 6pm, free Tue-Sun)\n"
            "**4-6h**: Corniche walk, skyline photos from MIA Park\n"
            "**6-8h**: Lunch at Parisa Souq Waqif (Persian, $40)\n"
            "**8-10h**: Katara Cultural Village, beach access\n"
            "**10-12h**: Return to HIA via metro ($2, 30min) — must be back 3h before departure\n"
            "**Last 2h**: Al Mourjan Business Lounge if eligible, or HIA gardens\n\n"
            "Skip: Pearl-Qatar (too far for layover), desert safari (need 5-6h)"
        ),
        "wanderboat_response": (
            "Fourteen hours in Doha is actually plenty! Here's what's realistic:\n\n"
            "First, check if you qualify for the free Qatar Airways city tour — it's a great way "
            "to see the highlights without logistics stress.\n\n"
            "If exploring on your own:\n"
            "- Souq Waqif is the must-do — traditional market, falconry, great food\n"
            "- Museum of Islamic Art is genuinely world-class, even if you're not into museums\n"
            "- Walk the Corniche for the skyline\n"
            "- Katara Cultural Village if you have time\n"
            "\n"
            "Budget about 4 hours for airport transit/security/buffer on both ends, leaving you "
            "~10 hours in the city. Plenty for the above.\n"
            "\n"
            "Skip the desert safari — sounds tempting but you'll be cutting it close."
        ),
        "expected_winner": "mindtrip",
        "rationale": "For layover queries, time-blocked precision is exactly what users need.",
    },
    {
        "id": "P1",
        "input": "I loved my trips to Mexico City and Lisbon. Where should I go next?",
        "bucket": "personalized",
        "difficulty": "medium",
        "mindtrip_response": (
            "Based on your preferences (CDMX, Lisbon), here are matched destinations:\n\n"
            "1. **Buenos Aires, Argentina** — similar urban energy, food scene, walkable barrios\n"
            "2. **Istanbul, Turkey** — layered history, food culture, neighborhood character\n"
            "3. **Naples, Italy** — gritty authenticity, food-forward, port city like Lisbon\n"
            "4. **Tbilisi, Georgia** — emerging food scene, walkable, character-rich\n"
            "5. **Bogotá, Colombia** — high-altitude capital like CDMX, food revival\n\n"
            "Top match: Buenos Aires. Flight from your usual departure city + 7-day plan available."
        ),
        "wanderboat_response": (
            "Love this combo — you clearly gravitate toward cities with deep history, incredible "
            "food culture, and that lived-in 'real city' feel rather than polished tourist hubs. "
            "A few that I think you'd genuinely love:\n\n"
            "**Istanbul** is the obvious next step — like Lisbon, it's a port city with empire-"
            "scale history layered into everyday neighborhoods. The food culture rivals Mexico City's "
            "in depth and breadth. Wander Karaköy and Balat the way you wandered Roma Norte or Alfama.\n\n"
            "**Oaxaca** if you haven't gone deeper into Mexico — different from CDMX but the same "
            "DNA you fell for, with arguably better food.\n\n"
            "**Naples** for the Lisbon-coded grit-plus-beauty energy. The pizza is just the entry "
            "point; the city itself is the meal.\n\n"
            "**Tangier** is a curveball — Lisbon's mirror across the Strait, with a literary "
            "history that rewards slow exploration.\n\n"
            "Which season are you thinking? That'd narrow it down a lot."
        ),
        "expected_winner": "wanderboat",
        "rationale": "Wanderboat identifies the pattern and explains each rec through that lens.",
    },
    {
        "id": "P2",
        "input": "Beach destination in November that's not crowded, good food, under 8 hours flight from NYC",
        "bucket": "personalized",
        "difficulty": "hard",
        "mindtrip_response": (
            "Filtered by constraints (≤8h from JFK, Nov shoulder season, food-focused):\n\n"
            "1. **Tulum, Mexico** — 4.5h, $380 RT, dry season starts Nov, food scene strong\n"
            "2. **Cartagena, Colombia** — 5.5h, $420 RT, dry season, growing food scene\n"
            "3. **Vieques, Puerto Rico** — 4h + ferry, $280 RT, bioluminescent bay\n"
            "4. **Lisbon coast (Comporta)** — 7h, $480 RT, off-season, Michelin nearby\n"
            "5. **Barbados** — 5h, $510 RT, food/rum tourism, less crowded than Caribbean peers\n\n"
            "Top pick: Cartagena — best food, best weather, least crowded of the list."
        ),
        "wanderboat_response": (
            "November is actually a sweet spot for this! Here are my picks:\n\n"
            "**Cartagena, Colombia** is where I'd send you first. Walled colonial city right on "
            "the Caribbean, the food scene is having a real moment (try La Cevichería, Carmen, "
            "Celele), and November is dry-season-start before peak crowds arrive in December. "
            "Hop to Barú or Islas del Rosario for beach time.\n\n"
            "**Vieques, Puerto Rico** if you want quieter — wild horses on the beach, "
            "bioluminescent bay, almost no development. Food is more limited but the seclusion "
            "is the point.\n\n"
            "**Tulum** is the obvious pick but I'd actually steer you away — November is when it "
            "starts getting busy again and prices spike. Same vibe with less crowd: try **Bacalar** "
            "(freshwater lagoon, 2h from Tulum) or **Holbox** (no cars, slow island energy).\n\n"
            "All under 8 hours from JFK."
        ),
        "expected_winner": "wanderboat",
        "rationale": "Wanderboat treats constraints as a starting point for genuine recommendation rather than a filter.",
    },
    {
        "id": "L1",
        "input": "Is it a good time to book flights to Bali for December, or should I wait?",
        "bucket": "live_data",
        "difficulty": "hard",
        "mindtrip_response": (
            "Current data: NYC→DPS in December averaging $1,180 RT (Singapore Airlines, EVA).\n"
            "30-day price trend: +8% (rising). 60-day trend: +14%.\n"
            "Historical: December is peak season, prices typically peak 3 weeks pre-departure.\n\n"
            "**Recommendation: book now.** Algorithm confidence 78% that prices rise from here.\n\n"
            "Cheapest dates: Dec 1-7 outbound ($1,050 RT), avoid Dec 18-26 (Christmas surge to $1,800+).\n"
            "Alarm option: track this route, alert if drops below $1,000."
        ),
        "wanderboat_response": (
            "December is peak season for Bali — both because of holiday travel and because it's "
            "actually rainy season there (though still beautiful, just with afternoon storms). "
            "Prices generally rise as you get closer to the date, so booking sooner rather than "
            "later is usually the move for December.\n\n"
            "That said, if your dates are flexible and you can shift even a week or two into "
            "January or November, you'll save a lot and get better weather.\n\n"
            "Hot tip: Google Flights' price tracking feature is your friend here. Set an alert "
            "and book when it tells you to."
        ),
        "expected_winner": "mindtrip",
        "rationale": "Live-data queries reward actual data. Mindtrip surfaces price trends, confidence intervals, specific date ranges.",
    },
    {
        "id": "L2",
        "input": "Weather in Reykjavik next week and packing recommendations",
        "bucket": "live_data",
        "difficulty": "easy",
        "mindtrip_response": (
            "Reykjavik 7-day forecast (Nov 25 - Dec 1):\n"
            "Avg high 36°F / low 28°F, 60% precipitation days, wind 15-25mph.\n"
            "Daylight: 5h (sunrise 10:50a, sunset 3:45p).\n\n"
            "Pack:\n"
            "• Waterproof shell jacket (essential — wind + horizontal rain)\n"
            "• Insulated mid-layer (down or synthetic)\n"
            "• Thermal base layers\n"
            "• Waterproof hiking boots\n"
            "• Wool socks (3+ pairs)\n"
            "• Beanie, gloves, neck gaiter\n"
            "• Swimsuit (Blue Lagoon, Sky Lagoon)\n"
            "• Eye mask (for adjusting to dark days)"
        ),
        "wanderboat_response": (
            "Reykjavik in late November is properly winter — expect temps in the 30s F, lots of "
            "wind, mixed precipitation (rain, sleet, snow), and very short days (about 5 hours "
            "of daylight).\n\n"
            "Pack like you're going somewhere genuinely cold and wet:\n"
            "- Waterproof + windproof shell is non-negotiable\n"
            "- Warm mid-layer (down or fleece)\n"
            "- Thermal base layers top and bottom\n"
            "- Waterproof boots with grip — sidewalks get icy\n"
            "- Hat, gloves, scarf\n"
            "- Swimsuit (yes, really — the geothermal pools are the whole point)\n"
            "\n"
            "Don't bother with an umbrella; the wind will eat it. The short daylight is real — "
            "plan outdoor activities for the 11am-3pm window."
        ),
        "expected_winner": "tie",
        "rationale": "Both responses are strong and substantively identical.",
    },
    {
        "id": "E1",
        "input": "Find me a flight that lets me sleep in my own bed both nights for a meeting in Denver from Seattle",
        "bucket": "edge_case",
        "difficulty": "hard",
        "mindtrip_response": (
            "Same-day round-trip SEA↔DEN options (meeting day TBD — assuming weekday):\n\n"
            "**Outbound (arrive by 9a MT for morning meetings)**:\n"
            "• Alaska AS 612, 6:00a SEA → 9:35a DEN, $189\n"
            "• United UA 1556, 5:55a SEA → 9:30a DEN, $215\n\n"
            "**Return (after 5p MT)**:\n"
            "• Alaska AS 615, 6:25p DEN → 8:05p SEA, $145\n"
            "• Southwest WN 2384, 7:30p DEN → 9:10p SEA, $159\n\n"
            "**Best combo**: Alaska both ways, $334 RT, ~14h door-to-door including ground transit.\n"
            "Buffer: 1h45m between landing and likely 11a meeting start."
        ),
        "wanderboat_response": (
            "Definitely doable! Seattle-Denver is about 2.5 hours flying and the time zone change "
            "actually works in your favor (you gain an hour heading east in the morning).\n\n"
            "Take an early morning flight out — Alaska and United both have flights around 6am "
            "that land in Denver around 9:30am, giving you the full business day. Then catch an "
            "evening flight back; there are options through about 9pm.\n\n"
            "If your meeting is downtown, factor in 30-45 minutes for the train from DEN to Union "
            "Station. The A-Line is direct and runs every 15 minutes.\n\n"
            "Pro move: book Alaska if you have status — same-day flight changes are free in case "
            "the meeting runs long."
        ),
        "expected_winner": "tie",
        "rationale": "Mindtrip nails the structure. Wanderboat adds useful context (A-Line transit, same-day-change tip).",
    },
    {
        "id": "E2",
        "input": "I have 48 hours, $500, leaving from Boston — surprise me",
        "bucket": "edge_case",
        "difficulty": "hard",
        "mindtrip_response": (
            "Filtered by ($500 total, 48h, BOS departure):\n\n"
            "**Option 1: Montréal**\n"
            "• Flight: $180 RT (Porter), 1h35m\n"
            "• Hotel Bonaventure: $145/night × 1 = $145\n"
            "• Food/transit budget: $175\n"
            "• Activities: Mile End, Old Port, Notre-Dame Basilica\n\n"
            "**Option 2: Portland, Maine**\n"
            "• Train: $60 RT (Amtrak Downeaster)\n"
            "• The Press Hotel: $220 × 1 = $220\n"
            "• Food/activities: $220\n"
            "• Activities: Old Port, lobster, Allagash brewery\n\n"
            "**Option 3: Washington DC**\n"
            "• Amtrak: $90 RT\n"
            "• Pod DC: $130 × 1 = $130\n"
            "• Food/museums (free): $280 buffer\n\n"
            "Surprise pick: **Montréal** — most international feel for the price."
        ),
        "wanderboat_response": (
            "Okay, I love this prompt. Here's my surprise pick:\n\n"
            "**Montréal.** \n\n"
            "Hear me out: 90-minute flight from Logan (~$180 round trip on Porter), suddenly "
            "you're in a French-speaking city with proper European bones, world-class food at "
            "American prices, and a completely different energy than anywhere else in driving "
            "distance. Stay in the Plateau or Mile End for the neighborhood vibe.\n\n"
            "48-hour play:\n"
            "**Day 1**: Schwartz's for smoked meat lunch, walk through Mile End and Plateau, "
            "dinner at Joe Beef or Au Pied de Cochon if you can get in\n"
            "**Day 2**: Jean-Talon Market in the morning, Old Montreal in the afternoon, "
            "rooftop drink at Terrasse Place D'Armes before flying home\n\n"
            "Budget breakdown: $180 flight + $145 hotel + ~$175 food/transit = right at $500.\n\n"
            "Bring your passport.\n\n"
            "Backup if you want to stay domestic: Portland, ME by train. Lobster rolls, breweries, "
            "easy walking city, $300 covers everything."
        ),
        "expected_winner": "wanderboat",
        "rationale": "'Surprise me' is a vibes query. Wanderboat picks ONE answer with conviction. Mindtrip listing options defeats the purpose.",
    },
]


EXPECTED_AGGREGATE = {
    "overall": {"mindtrip_wins": 5, "wanderboat_wins": 4, "ties": 3},
    "by_bucket": {
        "transactional": {"mindtrip": 2, "wanderboat": 0, "tie": 1},
        "itinerary":     {"mindtrip": 2, "wanderboat": 1, "tie": 0},
        "personalized":  {"mindtrip": 0, "wanderboat": 2, "tie": 0},
        "live_data":     {"mindtrip": 1, "wanderboat": 0, "tie": 1},
        "edge_case":     {"mindtrip": 0, "wanderboat": 1, "tie": 1},
    },
}


def make_braintrust_dataset():
    return [
        {
            "input": {
                "prompt": row["input"],
                "bucket": row["bucket"],
                "difficulty": row["difficulty"],
                "mindtrip_response": row["mindtrip_response"],
                "wanderboat_response": row["wanderboat_response"],
            },
            "expected": row["expected_winner"],
            "metadata": {
                "id": row["id"],
                "rationale": row["rationale"],
            },
        }
        for row in DATASET
    ]


def task(input: dict) -> dict:
    return {
        "mindtrip": input["mindtrip_response"],
        "wanderboat": input["wanderboat_response"],
    }


def battle_scorer(output, expected, input, metadata):
    rubric_text = "\n".join(
        f"- {axis} (weight {spec['weight']}): {spec['definition']}"
        for axis, spec in RUBRIC.items()
    )
    return Battle().eval(
        instructions=(
            f"Compare two travel-AI responses to: '{input['prompt']}'\n\n"
            f"Capability tested: {input['bucket']} ({input['difficulty']}).\n\n"
            f"Score on these axes (1-5 each, weighted):\n{rubric_text}\n\n"
            "Pick a winner only if the weighted score difference exceeds 0.5 points. "
            "Otherwise call it a tie."
        ),
        output=output["mindtrip"],
        expected=output["wanderboat"],
        input=input["prompt"],
    )


if __name__ == "__main__":
    Eval(
        "compete-travel-mindtrip-vs-wanderboat-v1",
        data=make_braintrust_dataset,
        task=task,
        scores=[battle_scorer],
        metadata={
            "product": "Compete",
            "comparison": "mindtrip_vs_wanderboat",
            "expected_thesis": EXPECTED_AGGREGATE,
        },
    )
