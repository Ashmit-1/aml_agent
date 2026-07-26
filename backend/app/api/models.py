"""
Pydantic models for the FastAPI chat endpoint request/response schemas.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single message in the conversation history."""

    role: str = Field(description="Either 'user' or 'assistant'")
    content: str = Field(description="The text content of the message")


class ChatRequest(BaseModel):
    """Request body for the ``POST /chat`` endpoint."""

    message: str = Field(
        description="The user's question or instruction for the AML agent.",
        min_length=1,
    )
    history: list[ChatMessage] = Field(
        default_factory=list,
        description="Prior conversation turns. Pass an empty list for a new conversation.",
    )


class ChatResponse(BaseModel):
    """Response body returned by the ``POST /chat`` endpoint."""

    response: str = Field(description="The agent's final answer text.")
    tool_calls: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of tool calls the agent made, with name and arguments.",
    )
    retry_count: int = Field(
        description="Number of consecutive errors encountered during processing.",
    )
