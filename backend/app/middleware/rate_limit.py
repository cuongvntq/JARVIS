"""SlowAPI rate limiter setup."""

import structlog
from slowapi import Limiter
from starlette.requests import Request

log = structlog.get_logger()


def _get_rate_limit_key(request: Request) -> str:
    """Use authenticated user ID as rate limit key; fall back to client IP."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
        try:
            from jose import jwt

            from app.config import get_settings

            settings = get_settings()
            payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
            if payload.get("sub"):
                return f"user:{payload['sub']}"
        except Exception:
            pass
    return request.client.host if request.client else "unknown"


def _build_limiter() -> Limiter:
    """Return a Limiter backed by Redis when UPSTASH_REDIS_URL is set, else in-memory."""
    from app.config import get_settings

    settings = get_settings()
    if settings.upstash_redis_url:
        try:
            storage_uri = settings.upstash_redis_url
            log.info("rate_limit.redis_backend", url=storage_uri[:30] + "...")
            return Limiter(key_func=_get_rate_limit_key, storage_uri=storage_uri)
        except Exception as e:
            log.warning("rate_limit.redis_fallback_inmemory", error=str(e))
    return Limiter(key_func=_get_rate_limit_key)


limiter = _build_limiter()
