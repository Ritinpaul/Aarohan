"""
Seed Database Loader — Aarohan++ Phase 1
Loads states.json, schemes.json, and facilities.json from seed directory
into PostgreSQL on application startup.
Acts as in-memory cache fallback if DB is unavailable.
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_SEED_DIR = Path(__file__).parent.parent.parent / "data" / "seed"

# In-memory cache (populated at startup)
_CACHE: dict[str, Any] = {}


def _load_json(filename: str) -> Any:
    path = _SEED_DIR / filename
    if not path.exists():
        logger.warning(f"Seed file not found: {path}")
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_states() -> list:
    return _CACHE.get("states", {}).get("states", [])


def get_schemes() -> list:
    return _CACHE.get("schemes", {}).get("schemes", [])


def get_facilities() -> dict:
    return _CACHE.get("facilities", {})


async def load_seed_data():
    """
    Load all seed JSON files into memory cache.
    Called on FastAPI application startup.
    """
    logger.info("Loading seed reference data into memory cache...")
    _CACHE["states"] = _load_json("states.json") or {}
    _CACHE["schemes"] = _load_json("schemes.json") or {}
    _CACHE["facilities"] = _load_json("facilities.json") or {}

    states_count = len(get_states())
    schemes_count = len(get_schemes())
    tiers_count = len(get_facilities().get("tiers", {}))

    logger.info(
        f"Seed data loaded — States: {states_count}, Schemes: {schemes_count}, Facility Tiers: {tiers_count}"
    )
    return {
        "states": states_count,
        "schemes": schemes_count,
        "facility_tiers": tiers_count,
    }
