"""JWT, bcrypt, and token helpers."""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings

settings = get_settings()
_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


def validate_password_strength(password: str) -> None:
    """Raise ValueError if password doesn't meet requirements."""
    if len(password) < 8:
        raise ValueError("Mật khẩu tối thiểu 8 ký tự")
    if not any(c.isalpha() for c in password):
        raise ValueError("Mật khẩu phải chứa ít nhất 1 chữ cái")
    if not any(c.isdigit() for c in password):
        raise ValueError("Mật khẩu phải chứa ít nhất 1 chữ số")


def create_access_token(user_id: uuid.UUID, name: str) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_access_ttl_minutes)
    payload = {
        "sub": str(user_id),
        "name": name,
        "type": "access",
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def create_refresh_token() -> tuple[str, str]:
    """Return (raw_token, sha256_hash). Store hash in DB, send raw to client."""
    raw = secrets.token_urlsafe(48)
    return raw, hash_refresh_token(raw)


def hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def decode_access_token(token: str) -> dict:
    """Decode and validate JWT. Raises HTTPException 401 on failure."""
    from fastapi import HTTPException

    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        if payload.get("type") != "access":
            raise JWTError("wrong token type")
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Token không hợp lệ hoặc đã hết hạn")
