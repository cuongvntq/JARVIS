"""SlowAPI rate limiter setup."""

from slowapi import Limiter
from starlette.requests import Request


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


limiter = Limiter(key_func=_get_rate_limit_key)
