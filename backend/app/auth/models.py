"""Pydantic models for the authentication endpoints.

Defines request and response schemas for signup, login, and user info.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ── Request models ────────────────────────────────────────────────────────


class SignupRequest(BaseModel):
    """Request body for ``POST /api/auth/signup``."""

    username: str = Field(
        description="Desired username. 3–50 alphanumeric characters, underscores, or hyphens.",
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_-]+$",
    )
    password: str = Field(
        description="Password. Minimum 6 characters, maximum 128.",
        min_length=6,
        max_length=128,
    )


class LoginRequest(BaseModel):
    """Request body for ``POST /api/auth/login``."""

    username: str = Field(
        description="Username.",
        min_length=1,
    )
    password: str = Field(
        description="Password.",
        min_length=1,
    )


# ── Response models ───────────────────────────────────────────────────────


class SignupResponse(BaseModel):
    """Response body for a successful signup."""

    status: str = "success"
    message: str = "User created successfully"
    user_id: int


class UserInfo(BaseModel):
    """Public user information returned by auth endpoints."""

    id: int
    username: str


class UserDetail(BaseModel):
    """Detailed user info returned by ``GET /api/auth/me``."""

    id: int
    username: str
    created_at: str


class LoginResponse(BaseModel):
    """Response body for a successful login."""

    status: str = "success"
    token: str
    user: UserInfo
    expires_at: str
