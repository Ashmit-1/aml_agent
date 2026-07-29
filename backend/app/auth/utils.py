"""Authentication helper functions.

Provides password hashing (bcrypt), session token generation (cryptographic
random), and session validation for the auth middleware and route handlers.
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request
from passlib.context import CryptContext

from app.auth.database import get_connection

logger = logging.getLogger(__name__)

# ── Password hashing context ──────────────────────────────────────────────

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Return the bcrypt hash of *password*."""
    return _pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return ``True`` if *plain_password* matches the bcrypt *hashed_password*."""
    return _pwd_context.verify(plain_password, hashed_password)


# ── Session token management ──────────────────────────────────────────────


def generate_session_token() -> str:
    """Generate a cryptographically random 64-character hex session token."""
    return secrets.token_hex(32)


def _get_session_expiry_days() -> int:
    """Return the session expiry duration in days (from env var or default 7)."""
    import os

    try:
        return int(os.getenv("SESSION_EXPIRY_DAYS", "7"))
    except (ValueError, TypeError):
        return 7


def create_session(user_id: int) -> tuple[str, str]:
    """Create a new session for *user_id*.

    Returns
    -------
    (token, expires_at_iso)
        The generated session token string and the ISO-8601 expiry timestamp.
    """
    token = generate_session_token()
    expiry_days = _get_session_expiry_days()
    expires_at = datetime.now(timezone.utc) + timedelta(days=expiry_days)
    expires_at_str = expires_at.strftime("%Y-%m-%dT%H:%M:%S")

    conn = get_connection()
    conn.execute(
        "INSERT INTO sessions (user_id, token, expires_at) VALUES (?, ?, ?)",
        (user_id, token, expires_at_str),
    )
    conn.commit()

    return token, expires_at_str


# ── Session validation ────────────────────────────────────────────────────


# ── Public path configuration ──────────────────────────────────────────────

# Exact paths that bypass auth entirely (no path-prefix matching).
_PUBLIC_EXACT_PATHS: tuple[str, ...] = (
    "/api/auth/login",
    "/api/auth/signup",
)

# Path prefixes that bypass auth (e.g. "/docs/swagger" should also be public).
# Each entry MUST end with "/" to avoid accidental matches like "/docs-extra".
_PUBLIC_PATH_PREFIXES: tuple[str, ...] = (
    "/docs/",
    "/redoc/",
)

# Also allow the bare /docs, /redoc, /openapi.json (no trailing slash).
_PUBLIC_OPENAPI_PATHS: tuple[str, ...] = (
    "/docs",
    "/redoc",
    "/openapi.json",
)


def is_public_path(path: str) -> bool:
    """Return ``True`` if *path* is a public endpoint that doesn't need auth.

    Public paths can be configured via the ``AUTH_PUBLIC_PATHS`` env var
    (comma-separated list of path prefixes). Defaults are auth routes and
    API documentation.

    Matching rules:
    - ``_PUBLIC_EXACT_PATHS`` — matched with ``==`` (no substring match).
    - ``_PUBLIC_PATH_PREFIXES`` — matched with ``startswith`` (prefix must end
      in ``/`` to avoid over-matching).
    - ``_PUBLIC_OPENAPI_PATHS`` — matched with ``==``.
    - Extra paths from ``AUTH_PUBLIC_PATHS`` env var — matched as prefixes
      (if they end with ``/``) or exact paths (otherwise).
    """
    # Normalise: strip query strings (e.g. "/docs?format=openapi" -> "/docs")
    path = path.split("?", 1)[0]

    # 1. Exact-match auth routes
    if path in _PUBLIC_EXACT_PATHS:
        return True

    # 2. Exact-match openapi bare paths
    if path in _PUBLIC_OPENAPI_PATHS:
        return True

    # 3. Prefix-match documentation paths (trailing "/" prevents overmatching)
    for prefix in _PUBLIC_PATH_PREFIXES:
        if path.startswith(prefix):
            return True

    # 4. Extra paths from env var
    import os

    extra = os.getenv("AUTH_PUBLIC_PATHS", "").strip()
    if extra:
        for p in (p.strip() for p in extra.split(",") if p.strip()):
            if p.endswith("/"):
                if path.startswith(p):
                    return True
            else:
                if path == p:
                    return True

    return False


def validate_session(token: str) -> dict | None:
    """Look up a session token and return the associated user dict.

    Returns ``None`` if the token is invalid, expired, or inactive.
    The returned dict has keys: ``id``, ``username``, ``created_at``.
    """
    conn = get_connection()
    row = conn.execute(
        """
        SELECT u.id, u.username, u.created_at
        FROM sessions s
        JOIN users u ON s.user_id = u.id
        WHERE s.token = ?
          AND s.expires_at > datetime('now')
          AND s.is_active = 1
        """,
        (token,),
    ).fetchone()

    if row is None:
        return None
    return {
        "id": row["id"],
        "username": row["username"],
        "created_at": row["created_at"],
    }


async def get_current_user(request: Request) -> dict:
    """FastAPI dependency that extracts and validates the session token.

    Uses ``request.state.user`` if already set by the auth middleware
    (avoids redundant DB queries). Otherwise extracts from the
    ``Authorization`` header directly.

    Returns
    -------
    dict
        User info with keys: ``id``, ``username``, ``created_at``.

    Raises
    ------
    HTTPException(401)
        If the token is missing, invalid, or expired.
    """
    # Check if middleware already validated this request
    if hasattr(request.state, "user") and request.state.user is not None:
        return request.state.user

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
        )

    token = auth_header[7:]
    # Offload sync SQLite to thread pool to avoid blocking the event loop
    import asyncio
    user = await asyncio.to_thread(validate_session, token)
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session",
        )

    return user
