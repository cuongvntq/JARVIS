"""Idempotency-Key middleware for POST /todos, /notes, /memories, /reminders.

Uses an in-memory TTL cache rather than Redis. The desktop app runs single-process,
single-user (no horizontal scaling), so an in-memory dict is sufficient and avoids
requiring Upstash/Redis setup just for this. This deviates from
`.claude/rules/05_security.md` ("cache bằng Redis"), which was written for the prior
multi-instance cloud deployment.
"""

import hashlib
import time
from collections.abc import Awaitable, Callable
from typing import NamedTuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import get_settings

_IDEMPOTENT_PREFIXES = ("/v1/todos", "/v1/notes", "/v1/memories", "/v1/reminders")


class _CacheEntry(NamedTuple):
    request_hash: str
    status_code: int
    body: bytes
    headers: dict[str, str]
    expires_at: float


_cache: dict[tuple[str, str], _CacheEntry] = {}


def _get_user_id(request: Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth[7:]
    try:
        from jose import jwt

        settings = get_settings()
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        sub = payload.get("sub")
        return str(sub) if sub else None
    except Exception:
        return None


def _prune_expired() -> None:
    now = time.monotonic()
    expired = [key for key, entry in _cache.items() if entry.expires_at < now]
    for key in expired:
        del _cache[key]


class IdempotencyMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        idempotency_key = request.headers.get("Idempotency-Key")
        if (
            request.method != "POST"
            or not idempotency_key
            or not request.url.path.startswith(_IDEMPOTENT_PREFIXES)
        ):
            return await call_next(request)

        user_id = _get_user_id(request)
        if not user_id:
            return await call_next(request)

        body = await request.body()
        request_hash = hashlib.sha256(body).hexdigest()

        _prune_expired()
        cache_key = (user_id, idempotency_key)
        cached = _cache.get(cache_key)

        if cached:
            if cached.request_hash != request_hash:
                request_id = getattr(request.state, "request_id", "unknown")
                return JSONResponse(
                    status_code=409,
                    content={
                        "error": {
                            "code": "idempotency_conflict",
                            "message": "Idempotency-Key đã được dùng với nội dung khác",
                            "details": {"idempotency_key": idempotency_key},
                            "request_id": request_id,
                        }
                    },
                )
            return Response(
                content=cached.body,
                status_code=cached.status_code,
                headers=cached.headers,
            )

        response = await call_next(request)

        if 200 <= response.status_code < 300:
            response_body = b""
            async for chunk in response.body_iterator:  # type: ignore[attr-defined]
                response_body += chunk if isinstance(chunk, bytes) else bytes(chunk)

            cache_headers = {
                k: v for k, v in response.headers.items() if k.lower() != "content-length"
            }
            ttl = get_settings().idempotency_key_ttl_seconds
            _cache[cache_key] = _CacheEntry(
                request_hash=request_hash,
                status_code=response.status_code,
                body=response_body,
                headers=cache_headers,
                expires_at=time.monotonic() + ttl,
            )
            return Response(
                content=response_body,
                status_code=response.status_code,
                headers=cache_headers,
                background=getattr(response, "background", None),
            )

        return response
