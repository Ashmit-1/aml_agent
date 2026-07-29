"""FastAPI router for the authentication endpoints.

Provides user registration (signup), authentication (login), and session
verification (me).

Routes
------
- ``POST /auth/signup`` — Create a new user account (public)
- ``POST /auth/login`` — Authenticate and receive a session token (public)
- ``GET /auth/me`` — Get current user from session token (protected)
"""

from __future__ import annotations

import logging
import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from app.auth.database import get_connection
from app.auth.models import (
    LoginRequest,
    LoginResponse,
    SignupRequest,
    SignupResponse,
    UserDetail,
    UserInfo,
)
from app.auth.utils import (
    create_session,
    get_current_user,
    hash_password,
    verify_password,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── Signup ────────────────────────────────────────────────────────────────


@router.post("/signup", response_model=SignupResponse, status_code=201)
def signup(request: SignupRequest) -> SignupResponse:
    """Register a new user account.

    The username is lowercased before storage (case-insensitive).
    The password is hashed with bcrypt — the plaintext is never stored.
    This endpoint does **not** auto-login the user (no session created).

    Raises ``409`` if the username is already taken.
    """
    username_lower = request.username.strip().lower()
    password_hash = hash_password(request.password)

    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username_lower, password_hash),
        )
        conn.commit()
        user_id = cursor.lastrowid
        logger.info("User created: id=%d username=%s", user_id, username_lower)
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="Username already exists",
        )
    except Exception as exc:
        logger.exception("Signup failed for username=%s", username_lower)
        raise HTTPException(
            status_code=500,
            detail="Internal server error",
        ) from exc

    return SignupResponse(user_id=user_id)


# ── Login ─────────────────────────────────────────────────────────────────


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest) -> LoginResponse:
    """Authenticate a user and return a session token.

    The token must be sent as ``Authorization: Bearer <token>`` on subsequent
    requests. Tokens expire after 7 days (configurable via ``SESSION_EXPIRY_DAYS``
    env var).

    Raises ``401`` if the username or password is incorrect.
    """
    username_lower = request.username.strip().lower()

    conn = get_connection()
    row = conn.execute(
        "SELECT id, username, password FROM users WHERE username = ?",
        (username_lower,),
    ).fetchone()

    if row is None or not verify_password(request.password, row["password"]):
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
        )

    token, expires_at = create_session(row["id"])
    logger.info(
        "User logged in: id=%d username=%s",
        row["id"],
        row["username"],
    )

    return LoginResponse(
        token=token,
        user=UserInfo(id=row["id"], username=row["username"]),
        expires_at=expires_at,
    )


# ── Me ────────────────────────────────────────────────────────────────────


@router.get("/me", response_model=UserDetail)
def me(current_user: dict = Depends(get_current_user)) -> UserDetail:
    """Return the authenticated user's details.

    Requires a valid ``Authorization: Bearer <token>`` header.
    Useful for verifying a session token is still valid on app startup.
    """
    return UserDetail(
        id=current_user["id"],
        username=current_user["username"],
        created_at=current_user["created_at"],
    )
