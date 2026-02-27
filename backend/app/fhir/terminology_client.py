"""
Snowstorm Terminology Client — Aarohan++ Phase 3
Async client for NRCeS FHIR Terminology Server (Snowstorm).
Provides SNOMED CT / ICD-10 / LOINC lookups with Redis caching to prevent rate-limiting.
Falls back gracefully if Snowstorm is unavailable.
"""

import hashlib
import json
import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

SNOWSTORM_BASE = os.getenv(
    "SNOWSTORM_URL",
    "https://snowstorm.ihtsdotools.org/fhir"
)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHE_TTL = 86400  # 1 day

# Code system display names
SYSTEM_NAMES = {
    "http://snomed.info/sct": "SNOMED CT",
    "http://hl7.org/fhir/sid/icd-10": "ICD-10",
    "http://loinc.org": "LOINC",
}


def _cache_key(code: str, system: str) -> str:
    h = hashlib.md5(f"{system}|{code}".encode()).hexdigest()
    return f"nhcx:term:{h}"


class SnowstormClient:
    """
    Async terminology client for SNOMED CT / ICD-10 / LOINC lookups.
    Uses Redis for LRU caching. All methods are safe to call in sync mode
    via `asyncio.run()` or as async coroutines.
    """

    def __init__(self):
        self._redis = None
        self._http: Optional[httpx.AsyncClient] = None

    async def _get_redis(self):
        if self._redis is None:
            try:
                import redis.asyncio as aioredis
                self._redis = await aioredis.from_url(REDIS_URL, decode_responses=True)
            except Exception as e:
                logger.warning(f"Redis unavailable — caching disabled: {e}")
                self._redis = False  # Sentinel: tried but failed
        return self._redis if self._redis else None

    def _http_client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(
                base_url=SNOWSTORM_BASE,
                timeout=10.0,
                headers={"Accept": "application/fhir+json"},
            )
        return self._http

    async def lookup(self, code: str, system: str) -> Optional[dict]:
        """
        Look up a code in the terminology server.

        Returns:
            dict with 'code', 'display', 'system', 'valid', or None if lookup fails.
        """
        cache_key = _cache_key(code, system)

        # 1) Check cache
        redis = await self._get_redis()
        if redis:
            try:
                cached = await redis.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception:
                pass

        # 2) HTTP lookup
        params = {
            "code": code,
            "system": system,
        }
        try:
            async with self._http_client() as client:
                resp = await client.get("/CodeSystem/$lookup", params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    display = _extract_display(data)
                    result = {
                        "code": code,
                        "system": system,
                        "display": display,
                        "valid": True,
                        "system_name": SYSTEM_NAMES.get(system, system),
                    }
                    # Cache result
                    if redis:
                        try:
                            await redis.setex(cache_key, CACHE_TTL, json.dumps(result))
                        except Exception:
                            pass
                    return result
                else:
                    logger.debug(f"Snowstorm lookup failed for {code}@{system}: HTTP {resp.status_code}")
                    return {"code": code, "system": system, "display": None, "valid": False}
        except Exception as e:
            logger.debug(f"Snowstorm unreachable: {e}")
            return {"code": code, "system": system, "display": None, "valid": False}

    async def search_concept(self, term: str, system: str, limit: int = 5) -> list:
        """
        Search for concepts matching a text term in the given system.
        Returns a list of candidate {code, display} dicts.
        """
        params = {"url": system, "filter": term, "count": limit}
        try:
            async with self._http_client() as client:
                resp = await client.get("/ValueSet/$expand", params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    contains = (
                        data.get("expansion", {}).get("contains", [])
                    )
                    return [
                        {"code": c.get("code"), "display": c.get("display"), "system": c.get("system", system)}
                        for c in contains
                    ]
        except Exception as e:
            logger.debug(f"Snowstorm search error: {e}")
        return []

    async def close(self):
        if self._http:
            await self._http.aclose()


def _extract_display(fhir_parameters: dict) -> Optional[str]:
    """Extract display text from a FHIR Parameters/$lookup response."""
    for param in fhir_parameters.get("parameter", []):
        if param.get("name") == "display":
            return param.get("valueString")
    return None


# ─── Singleton ────────────────────────────────────────────────────────────────
_client: Optional[SnowstormClient] = None


def get_client() -> SnowstormClient:
    global _client
    if _client is None:
        _client = SnowstormClient()
    return _client


# ─── Sync helper for non-async contexts ──────────────────────────────────────

def lookup_sync(code: str, system: str) -> Optional[dict]:
    """Synchronous wrapper for use in non-async routes."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # In async context — schedule without blocking
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, get_client().lookup(code, system))
                return future.result(timeout=10)
        else:
            return loop.run_until_complete(get_client().lookup(code, system))
    except Exception as e:
        logger.debug(f"lookup_sync failed: {e}")
        return None
