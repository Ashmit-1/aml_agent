"""
FastAPI router for the AML analysis LangGraph agent.

Endpoints
---------
- ``GET /health`` — health check (returns status, agent readiness)
- ``POST /chat`` — send a message and receive the agent's response
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from langchain_core.messages import AIMessage, HumanMessage

from app.agent import build_agent
from app.api.models import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Agent singleton (lazily initialised on first request) ──────────────────
_agent: Any = None


def _get_agent() -> Any:
    """Return the singleton agent instance, creating it if necessary."""
    global _agent
    if _agent is None:
        logger.info("Initialising LangGraph agent (first request)…")
        _agent = build_agent()
        logger.info("Agent ready.")
    return _agent


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """Return the current service status."""
    agent_ready = _agent is not None
    return {
        "status": "ok",
        "agent_ready": agent_ready,
    }


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:  # sync — agent.invoke() is blocking
    """Process a user message through the AML analysis agent.

    The request includes the new message and optional conversation history.
    The agent will call tools as needed, handle errors with retries, and
    return a final answer.
    """
    agent = _get_agent()

    # ── Build LangChain message list from request history ─────────────────
    messages: list = []

    # Append prior history
    for hist_msg in request.history:
        if hist_msg.role == "user":
            messages.append(HumanMessage(content=hist_msg.content))
        elif hist_msg.role == "assistant":
            messages.append(AIMessage(content=hist_msg.content))
        else:
            logger.warning("Skipping unknown role in history: %s", hist_msg.role)

    # Append the new user message
    messages.append(HumanMessage(content=request.message))

    # ── Invoke the agent ──────────────────────────────────────────────────
    try:
        result = agent.invoke(
            {"messages": messages, "retry_count": 0},
        )
    except Exception as exc:
        logger.exception("Agent invocation failed")
        raise HTTPException(
            status_code=500,
            detail=f"Agent invocation failed: {exc}",
        ) from exc

    # ── Build the response ────────────────────────────────────────────────
    final_messages = result.get("messages", [])
    last_msg = final_messages[-1] if final_messages else None
    response_text = str(last_msg.content) if last_msg else "No response."

    # Extract tool calls made during the conversation
    tool_calls: list[dict[str, Any]] = []
    for msg in final_messages:
        if isinstance(msg, AIMessage) and hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append({
                    "name": tc.get("name", ""),
                    "args": tc.get("args", {}),
                })

    retry_count = result.get("retry_count", 0)

    return ChatResponse(
        response=response_text,
        tool_calls=tool_calls,
        retry_count=retry_count,
    )
