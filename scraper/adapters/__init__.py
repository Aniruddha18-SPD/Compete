from scraper.adapters.mindtrip import MindTripAdapter
from scraper.adapters.wanderboat import WanderboatAdapter

REGISTRY: dict[str, type] = {
    "mindtrip": MindTripAdapter,
    "wanderboat": WanderboatAdapter,
}
