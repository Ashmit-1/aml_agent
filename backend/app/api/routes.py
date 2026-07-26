"""
FastAPI router for the AML analysis LangGraph agent.

Endpoints
---------
- ``GET /health`` — health check (returns status, agent readiness)
- ``POST /chat`` — (blocking) send a message and receive the agent's response
- ``POST /chat/stream`` — (SSE streaming) process a message with step-by-step
  progress events (thinking, tool calls, results, retries, final response)
"""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from app.agent import build_agent
from app.agent.graph import _MAX_RETRIES, _MAX_RETRY_EXCEEDED_MSG
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
# Shared helpers
# ---------------------------------------------------------------------------


def _build_messages(request: ChatRequest) -> list:
    """Convert a ``ChatRequest`` (message + history) into a LangChain message list."""
    messages: list = []

    for hist_msg in request.history:
        if hist_msg.role == "user":
            messages.append(HumanMessage(content=hist_msg.content))
        elif hist_msg.role == "assistant":
            messages.append(AIMessage(content=hist_msg.content))
        else:
            logger.warning("Skipping unknown role in history: %s", hist_msg.role)

    messages.append(HumanMessage(content=request.message))
    return messages


def _extract_clean_text(content: Any) -> str:
    """Extract human-readable text from an AIMessage content field.

    Handles:
    - plain strings
    - ``None``
    - multi-block lists (e.g. Gemma's thinking + text blocks)
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                texts.append(block.get("text", ""))
            elif isinstance(block, dict) and block.get("type") == "thinking":
                # Include thinking as a reasoning note
                thought = block.get("thinking", "")
                if thought:
                    texts.append(f"[Thinking: {thought}]")
        return "\n".join(texts) if texts else str(content)
    return str(content)


def _summarize_tool_result(content: Any, max_chars: int = 300) -> str:
    """Summarise a tool result for SSE display (truncated)."""
    text = str(content)[:max_chars]
    if len(str(content)) > max_chars:
        text += "…"
    return text


def _sse_event(event: str, data: dict) -> str:
    """Format a Server-Sent Event string."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


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
    """Process a user message through the AML analysis agent (blocking).

    The request includes the new message and optional conversation history.
    The agent will call tools as needed, handle errors with retries, and
    return a final answer. For a streaming experience with step-by-step
    progress updates, use ``POST /chat/stream`` instead.
    """
    agent = _get_agent()
    messages = _build_messages(request)

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
    response_text = _extract_clean_text(last_msg.content if last_msg else None) or "No response."

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


# ---------------------------------------------------------------------------
# Streaming endpoint (Server-Sent Events)
# ---------------------------------------------------------------------------


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    """Process a user message through the AML agent, streaming step-by-step
    progress as Server-Sent Events.

    The stream emits the following event types (all as ``event: step``):

    ``thinking``
        The LLM is reasoning / planning. ``data`` includes ``content``.
    ``tool_call``
        The LLM decided to invoke a tool. ``data`` includes ``tool`` (name)
        and ``arguments``.
    ``tool_result``
        A tool returned a result. ``data`` includes ``tool`` (name) and
        a ``summary`` (truncated result).
    ``retry``
        A tool returned an error and the agent will retry. ``data`` includes
        ``retry_count`` and ``reason``.
    ``response``
        The final answer. ``data`` includes ``content`` (the response text).

    The stream ends with a ``done`` event (no ``data``).

    On error the stream emits an ``error`` event before closing.
    """
    agent = _get_agent()
    messages = _build_messages(request)

    async def _event_stream() -> AsyncGenerator[str, None]:
        # Track the final response text across graph node updates
        stream_state: dict[str, Any] = {"final_text": ""}

        try:
            async for update in agent.astream(
                {"messages": messages, "retry_count": 0},
                stream_mode="updates",
            ):
                for node_name, data in update.items():
                    if node_name == "agent":
                        for event in _handle_agent_event(data, stream_state):
                            yield event

                    elif node_name == "tools":
                        for event in _handle_tools_events(data):
                            yield event

                    elif node_name == "check_error":
                        event, text = _handle_check_error_event(data)
                        if event:
                            yield event
                        if text is not None:
                            stream_state["final_text"] = text

            # Emit the final response
            final_text = stream_state["final_text"] or "I completed the analysis. Please check the results above."
            yield _sse_event("step", {"type": "response", "content": final_text})
            yield _sse_event("done", {})

        except Exception as exc:
            logger.exception("Stream error")
            yield _sse_event("error", {"message": str(exc)})

    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# SSE event handlers (one per graph node)
# ---------------------------------------------------------------------------


def _handle_agent_event(data: dict, state: dict[str, Any]) -> list[str]:
    """Process an ``agent`` node update — emit events for AI thinking and tool calls.

    Parameters
    ----------
    data
        The raw state update dict from the ``agent`` node.
    state
        Mutable dict shared across the stream. If the AI produces pure text
        (no tool calls), ``state["final_text"]`` is updated so the stream can
        emit a ``response`` event later.
    """
    events: list[str] = []
    msgs = data.get("messages", [])
    if not msgs:
        return events
    last_msg = msgs[-1]

    if not isinstance(last_msg, AIMessage):
        return events

    # 1. Emit the AI's reasoning / thinking as a ``thinking`` event
    thought = _extract_clean_text(last_msg.content)
    if thought:
        events.append(
            _sse_event("step", {"type": "thinking", "content": thought})
        )

    # 2. Emit ``tool_call`` events for each tool the LLM decided to invoke
    if last_msg.tool_calls:
        for tc in last_msg.tool_calls:
            events.append(
                _sse_event(
                    "step",
                    {
                        "type": "tool_call",
                        "tool": tc.get("name", ""),
                        "arguments": tc.get("args", {}),
                    },
                )
            )
    else:
        # Plain text (no tool calls) — this is the final response
        if thought:
            state["final_text"] = thought

    return events


def _handle_tools_events(data: dict) -> list[str]:
    """Process a ``tools`` node update — emit ``tool_call`` (for the recorded
    call) and ``tool_result`` events."""
    events: list[str] = []

    for msg in data.get("messages", []):
        if isinstance(msg, ToolMessage) and hasattr(msg, "name") and msg.name:
            result_summary = _summarize_tool_result(msg.content)
            events.append(
                _sse_event(
                    "step",
                    {
                        "type": "tool_result",
                        "tool": msg.name,
                        "summary": result_summary,
                    },
                )
            )

    return events


def _handle_check_error_event(
    data: dict,
) -> tuple[str | None, str | None]:
    """Process a ``check_error`` node update.

    Returns
    -------
    (sse_event, final_text)
        ``sse_event`` is an SSE string (or ``None`` if no event needed).
        ``final_text`` is a non-empty string when the agent has given up
        (or ``None`` otherwise).
    """
    rc = data.get("retry_count", 0)
    last_msg = _get_last_message(data)

    if rc > _MAX_RETRIES:
        # All retries exhausted — extract the final apology message
        apology = _extract_clean_text(last_msg.content if last_msg else None)
        return (
            _sse_event(
                "step",
                {
                    "type": "retry",
                    "retry_count": rc,
                    "reason": "All retries exhausted. Giving up.",
                },
            ),
            apology or _MAX_RETRY_EXCEEDED_MSG,
        )

    if rc == _MAX_RETRIES and isinstance(last_msg, SystemMessage):
        # Fallback hint injected
        return (
            _sse_event(
                "step",
                {
                    "type": "retry",
                    "retry_count": rc,
                    "reason": "Structured tools keep failing. The LLM has been instructed to use run_python_code instead.",
                },
            ),
            None,
        )

    if rc > 0:
        # Regular retry
        return (
            _sse_event(
                "step",
                {
                    "type": "retry",
                    "retry_count": rc,
                    "reason": f"Tool returned an error. Retrying ({rc}/{_MAX_RETRIES})…",
                },
            ),
            None,
        )

    # Success (retry_count reset to 0) — no event
    return (None, None)


def _get_last_message(data: dict) -> Any | None:
    """Get the last message from a state update dict."""
    msgs = data.get("messages")
    if msgs:
        return msgs[-1]
    return None
