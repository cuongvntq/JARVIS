"""Unified error handling for JARVIS API."""

import uuid

from fastapi import Request
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class JarvisError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: dict | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.request_id = str(uuid.uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"http_{exc.status_code}",
                "message": str(exc.detail),
                "details": {},
                "request_id": request_id,
            }
        },
    )


async def jarvis_exception_handler(request: Request, exc: JarvisError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "request_id": request_id,
            }
        },
    )


def _sanitize_validation_errors(errors: list) -> list:
    """Pydantic v2 model_validator raises put the Exception instance in ctx.error —
    not JSON-serializable. Convert to string so JSONResponse doesn't blow up."""
    sanitized = []
    for err in errors:
        clean = {k: v for k, v in err.items() if k != "url"}
        if "ctx" in clean and isinstance(clean["ctx"].get("error"), Exception):
            clean = {**clean, "ctx": {"error": str(clean["ctx"]["error"])}}
        sanitized.append(clean)
    return sanitized


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "validation_error",
                "message": "Dữ liệu đầu vào không hợp lệ",
                "details": {"errors": _sanitize_validation_errors(exc.errors())},
                "request_id": request_id,
            }
        },
    )
