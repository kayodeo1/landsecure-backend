"""Password hashing (bcrypt) and JWT issue/verify (PyJWT).

Deliberately uses ``bcrypt`` and ``PyJWT`` directly rather than
``passlib``/``python-jose`` — functionally identical to the plan but avoids the
well-known passlib↔bcrypt-4 backend incompatibility, so it installs cleanly.
"""
from __future__ import annotations

import datetime as dt
from typing import Any, Literal

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

_BCRYPT_MAX = 72  # bcrypt only consumes the first 72 bytes


# --- passwords ---------------------------------------------------------------
def hash_password(plain: str) -> str:
    pw = plain.encode("utf-8")[:_BCRYPT_MAX]
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:_BCRYPT_MAX], hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# --- tokens ------------------------------------------------------------------
def _create_token(sub: str, role: str, kind: Literal["access", "refresh"]) -> str:
    now = dt.datetime.now(dt.timezone.utc)
    if kind == "access":
        exp = now + dt.timedelta(minutes=settings.access_token_ttl_min)
    else:
        exp = now + dt.timedelta(days=settings.refresh_token_ttl_days)
    payload: dict[str, Any] = {
        "sub": str(sub),
        "role": role,
        "type": kind,
        "iat": now,
        "exp": exp,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(sub: str, role: str) -> str:
    return _create_token(sub, role, "access")


def create_refresh_token(sub: str, role: str) -> str:
    return _create_token(sub, role, "refresh")


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:  # expired / invalid signature / malformed
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


# --- FastAPI dependencies ----------------------------------------------------
def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong token type")
    user = db.get(User, int(payload["sub"]))
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User no longer exists")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required",
        )
    return user
