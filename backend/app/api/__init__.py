"""
FastAPI application for the AML analysis LangGraph agent.

Exposes a ``POST /chat`` endpoint that accepts a user message and optional
conversation history, then returns the agent's response.

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
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler — logs startup / shutdown events."""
    logger.info("AML Analysis API starting up…")
    yield
    # Shutdown: close the singleton QueryEngine
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

# ── CORS (permit browser-based UIs during development) ─────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register routers -------------------------------------------------------
app.include_router(router, prefix="/api")

# ── Root redirect ---------------------------------------------------------


@app.get("/")
async def root() -> dict:
    return {
        "application": "AML Transaction Analysis API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/api/health",
        "chat": "/api/chat",
    }
