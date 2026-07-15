"""
redis_cache.py — Redis cache wrapper with graceful in-memory fallback.

If REDIS_URL is set in the environment, uses Redis for distributed caching.
If Redis is unavailable (no env var, connection refused), falls back to an
in-process LRU-style dict so the app still runs without Redis installed.
"""
import os
import json
import time
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Redis client (optional)
# ---------------------------------------------------------------------------
_redis_client = None
_redis_available = False

def _init_redis():
    global _redis_client, _redis_available
    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        logger.info("[Cache] REDIS_URL not set — using in-memory fallback cache.")
        return
    try:
        import redis
        client = redis.Redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=3)
        client.ping()  # verify connectivity
        _redis_client = client
        _redis_available = True
        logger.info("[Cache] Connected to Redis successfully.")
    except Exception as e:
        logger.warning(f"[Cache] Could not connect to Redis ({e}) — using in-memory fallback.")

_init_redis()

# ---------------------------------------------------------------------------
# In-memory fallback
# ---------------------------------------------------------------------------
_mem_cache: dict[str, tuple[Any, float]] = {}  # key -> (value, expires_at)

def _mem_get(key: str) -> Optional[Any]:
    entry = _mem_cache.get(key)
    if entry is None:
        return None
    value, expires_at = entry
    if expires_at and time.time() > expires_at:
        del _mem_cache[key]
        return None
    return value

def _mem_set(key: str, value: Any, ttl: int = 0):
    expires_at = (time.time() + ttl) if ttl else 0
    _mem_cache[key] = (value, expires_at)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def get(key: str) -> Optional[Any]:
    """Retrieve a cached value. Returns None if missing or expired."""
    if _redis_available and _redis_client:
        try:
            raw = _redis_client.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as e:
            logger.warning(f"[Cache] Redis GET failed ({e}), trying memory.")
    return _mem_get(key)


def set(key: str, value: Any, ttl: int = 600):
    """Store a value in cache with an optional TTL in seconds (default 10 min)."""
    if _redis_available and _redis_client:
        try:
            _redis_client.set(key, json.dumps(value), ex=ttl)
            return
        except Exception as e:
            logger.warning(f"[Cache] Redis SET failed ({e}), falling back to memory.")
    _mem_set(key, value, ttl)


def delete(key: str):
    """Remove a cache entry."""
    if _redis_available and _redis_client:
        try:
            _redis_client.delete(key)
        except Exception:
            pass
    _mem_cache.pop(key, None)


def make_flight_key(origin: str, destination: str, date: str, currency: str, direction: str) -> str:
    return f"flight:{direction}:{origin}:{destination}:{date}:{currency}"


def make_hotel_key(city_code: str, currency: str) -> str:
    return f"hotel:{city_code}:{currency}"
