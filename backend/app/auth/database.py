"""SQLite connection management for the authentication database.

Maintains a singleton connection to ``auth.db`` and ensures the
``users`` and ``sessions`` tables exist on startup.

Usage::

    from app.auth.database import get_connection, init_auth_db, close_auth_db

    init_auth_db()          # called on app startup
    conn = get_connection()  # get the singleton connection
    conn.execute("SELECT ...")
    close_auth_db()          # called on app shutdown
"""

from __future__ import annotations

import logging
import os
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Singleton ─────────────────────────────────────────────────────────────

_connection: sqlite3.Connection | None = None

# Default database path (relative to current working directory)
_DEFAULT_DB_PATH = "auth.db"


def _get_db_path() -> str:
    """Return the database path from env var or default.

    The ``DATABASE_URL`` env var can override the path. Relative paths
    are resolved from the project root (directory containing this package).
    """
    path = os.getenv("DATABASE_URL", _DEFAULT_DB_PATH)
    if not os.path.isabs(path):
        # Resolve relative to project root (3 levels up: database.py -> auth -> app -> project)
        path = str(Path(__file__).resolve().parent.parent.parent / path)
    return path


def get_connection() -> sqlite3.Connection:
    """Return the singleton SQLite connection, creating it if necessary."""
    global _connection
    if _connection is None:
        db_path = _get_db_path()
        logger.info("Opening auth database: %s", db_path)
        # Ensure the parent directory exists so sqlite3 can create the DB file.
        # Without this, a missing directory raises "unable to open database file".
        parent = os.path.dirname(db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        _connection = sqlite3.connect(db_path, check_same_thread=False)
        _connection.row_factory = sqlite3.Row
        _connection.execute("PRAGMA journal_mode=DELETE")
        _connection.execute("PRAGMA foreign_keys=ON")
    return _connection


def _cleanup_expired_sessions() -> None:
    """Delete expired session rows from the database.

    Called during startup to prevent unbounded growth of the sessions table.
    """
    conn = get_connection()
    cursor = conn.execute(
        "DELETE FROM sessions WHERE expires_at <= datetime('now')"
    )
    conn.commit()
    deleted = cursor.rowcount
    if deleted:
        logger.info("Cleaned up %d expired session(s).", deleted)


def init_auth_db() -> None:
    """Create the ``users`` and ``sessions`` tables if they don't exist.

    Safe to call multiple times — uses ``CREATE TABLE IF NOT EXISTS``.
    Called during application startup.
    """
    conn = get_connection()

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT    NOT NULL UNIQUE,
            password    TEXT    NOT NULL,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token       TEXT    NOT NULL UNIQUE,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
            expires_at  TEXT    NOT NULL,
            is_active   INTEGER NOT NULL DEFAULT 1
        );

        CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);
        CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
    """)
    conn.commit()
    logger.info("Auth database tables initialised.")

    # Clean up expired sessions on every startup
    _cleanup_expired_sessions()


def close_auth_db() -> None:
    """Close the singleton database connection (if open).

    Called during application shutdown.
    """
    global _connection
    if _connection is not None:
        _connection.close()
        _connection = None
        logger.info("Auth database connection closed.")
