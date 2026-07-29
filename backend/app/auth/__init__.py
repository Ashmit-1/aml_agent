"""Authentication package for the AML Analysis API.

Provides session-based authentication using SQLite for storage,
bcrypt for password hashing, and cryptographically random session tokens.

Quick start::

    # The auth router is registered in app/api/__init__.py
    # Auth middleware protects all routes except /api/auth/* and /docs

    from app.auth.routes import router as auth_router
"""

from __future__ import annotations

from app.auth.database import close_auth_db, init_auth_db
from app.auth.routes import router as auth_router
from app.auth.utils import get_current_user, validate_session

__all__ = [
    "auth_router",
    "get_current_user",
    "validate_session",
    "init_auth_db",
    "close_auth_db",
]
