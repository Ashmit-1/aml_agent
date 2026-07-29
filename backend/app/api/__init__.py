"""
FastAPI application for the AML analysis LangGraph agent.

Provides chat endpoints (blocking and SSE streaming) and authentication
(signup, login, session management).

Quick start::

    # From the project root:
    fastapi dev app/api/__init__.py

    # Or programmatically:
    from app.api import app
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
"""

from __future__ import annotations

import logging

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router as chat_router
from app.auth.routes import router as auth_router
from app.auth.utils import is_public_path, validate_session

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler — initialises auth DB, logs events."""
    logger.info("AML Analysis API starting up…")

    # Initialise the auth database (creates tables if needed)
    from app.auth.database import init_auth_db
    init_auth_db()
    logger.info("Auth database ready.")

    yield

    # Shutdown: close auth DB and query engine
    from app.auth.database import close_auth_db
    close_auth_db()

    from app.tools.tool_definitions import close_engine
    close_engine()
    logger.info("AML Analysis API shut down.")


# ── Application factory ----------------------------------------------------
app = FastAPI(
    title="AML Transaction Analysis API",
    description=(
        "LangGraph-powered agent for querying the SAML-D "
        "(Synthetic Anti-Money Laundering) dataset of ~9.5M transactions. "
        "The agent can search transactions, run SQL queries, and execute "
        "custom Python code in a sandbox."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# ── Authentication middleware (registered FIRST so CORS wraps it) ──────────
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Protect all API routes except public auth and docs paths.

    Expects a ``Authorization: Bearer <token>`` header on protected routes.
    Returns 401 with a ``redirect`` field for the frontend to navigate to login.

    Note: Registered BEFORE CORS middleware so that CORS wraps auth.
    This ensures every response (including 401) gets CORS headers.
    """
    # Skip auth for public paths
    if is_public_path(request.url.path):
        return await call_next(request)

    # Check for valid session token
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JSONResponse(
            status_code=401,
            content={
                "detail": "Authentication required",
                "redirect": "/login",
            },
        )

    token = auth_header[7:]
    # Offload sync SQLite to thread pool to avoid blocking the event loop
    import asyncio
    user = await asyncio.to_thread(validate_session, token)
    if user is None:
        return JSONResponse(
            status_code=401,
            content={
                "detail": "Invalid or expired session",
                "redirect": "/login",
            },
        )

    # Attach user info to request state so route handlers can reuse it
    request.state.user = user
    return await call_next(request)


# ── CORS (registered AFTER auth so it wraps auth as the outermost layer) ────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Register routers -------------------------------------------------------
app.include_router(chat_router, prefix="/api")
app.include_router(auth_router, prefix="/api")


# ── Root endpoint ----------------------------------------------------------


@app.get("/")
async def root() -> dict:
    return {
        "application": "AML Transaction Analysis API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/api/health",
        "chat": "/api/chat",
        "chat_stream": "/api/chat/stream",
    }
