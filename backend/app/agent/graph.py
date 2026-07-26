"""
LangGraph agent for AML transaction analysis.

Builds a ``CompiledGraph`` that orchestrates the LLM with three tiers of
problem-solving:

1. **Structured tools** (``search_transactions``, ``get_high_value_transactions``,
   ``get_suspicious_patterns``, ``get_summary_statistics``)
2. **Raw SQL** (``run_sql_query``) for queries the structured tools cannot
   express
3. **Code sandbox** (``run_python_code``) as a universal fallback for custom
   analysis

The graph uses a custom ``StateGraph`` with:
- An ``agent`` node that calls the LLM (bound to all tools).
- A ``tools`` node that executes tool invocations.
- A ``check_error`` node that inspects tool results, updates ``retry_count``,
  and optionally injects a sandbox fallback hint after 3 consecutive errors.

Usage::

    from app.agent.graph import build_agent

    agent = build_agent()
    for chunk in agent.stream(
        {"messages": [("human", "…")], "retry_count": 0},
    ):
        print(chunk)
"""

from __future__ import annotations

import logging
from typing import Any, Literal

from langchain_core.messages import AIMessage, BaseMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from app.agent.config import LLMConfig, get_llm
from app.agent.state import AgentState
from app.tools.tool_definitions import TOOLS as PREDEFINED_TOOLS


def _tool_error_handler(error: Exception) -> str:
    """Custom ToolNode error handler — catches tool exceptions and returns
    them as structured error messages instead of crashing the agent."""
    name = type(error).__name__
    return f"Tool error ({name}): {error}"

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAX_RETRIES: int = 3

_FALLBACK_HINT = (
    "\n\n**Fallback hint:** The structured tools and SQL query tool have "
    "failed multiple times. Consider using the **run_python_code** tool "
    "instead to write custom Python analysis code. You have access to "
    "`engine` (QueryEngine), `pd` (pandas), and `np` (numpy) in the sandbox. "
    "Use `engine.execute_sql(...)` or `engine.search_transactions(...)` to "
    "fetch data, then process it with Python."
)

_MAX_RETRY_EXCEEDED_MSG = (
    "I'm sorry, I was unable to complete your request after multiple attempts. "
    "The tools kept failing and I've exhausted my retry limit. "
    "Please try rephrasing your question or breaking it into smaller steps."
)

# ---------------------------------------------------------------------------
# Helper predicates
# ---------------------------------------------------------------------------


def _is_error_message(msg: BaseMessage) -> bool:
    """Return ``True`` if *msg* is a ``ToolMessage`` containing an error.

    Uses specific error-phrase matching to avoid false positives from
    data values that happen to contain the word *error*.
    """
    if not isinstance(msg, ToolMessage):
        return False
    content = str(msg.content).lower()
    return any(
        keyword in content
        for keyword in (
            "tool error",
            "only select queries",
            "multi-statement",
            "unknown column",
            "failed to start",
            "timed out",
            "too many concurrent",
        )
    )


# ---------------------------------------------------------------------------
# Graph nodes
# ---------------------------------------------------------------------------


def _make_agent_node(llm: Any, tools: list) -> callable:
    """Return the ``agent`` node: invokes the LLM and returns its response."""
    bound_model = llm.bind_tools(tools)

    def agent_node(state: AgentState) -> dict[str, Any]:
        """Call the LLM with the current messages and return the response."""
        response = bound_model.invoke(state["messages"])
        return {"messages": [response]}

    return agent_node


def _check_error_node(state: AgentState) -> dict[str, Any]:
    """Inspect the last tool result and update ``retry_count``.

    Returns
    -------
    dict
        - ``retry_count``: incremented on error, reset to 0 on success,
          or set to ``_MAX_RETRIES + 1`` to signal termination.
        - ``messages``: (optional) includes a fallback hint when retries
          first reach the limit, or a final error when giving up.
    """
    messages = state["messages"]
    retry_count = state.get("retry_count", 0)
    last_msg = messages[-1] if messages else None

    if isinstance(last_msg, ToolMessage) and _is_error_message(last_msg):
        new_count = retry_count + 1
        logger.info("Tool error detected (retry %d/%d)", new_count, _MAX_RETRIES)

        if new_count > _MAX_RETRIES:
            # Already injected the hint on a previous iteration but the
            # LLM still called a failing tool — give up gracefully.
            return {
                "retry_count": new_count,
                "messages": [AIMessage(content=_MAX_RETRY_EXCEEDED_MSG)],
            }

        if new_count == _MAX_RETRIES:
            # First time hitting the retry limit — inject fallback hint
            hint = SystemMessage(content=_FALLBACK_HINT)
            return {"retry_count": new_count, "messages": [hint]}

        return {"retry_count": new_count}

    # Tool succeeded → reset the retry counter
    return {"retry_count": 0}


# ---------------------------------------------------------------------------
# Routing helpers
# ---------------------------------------------------------------------------


def _route_after_agent(state: AgentState) -> Literal["tools", "__end__"]:
    """After the LLM responds: go to ``tools`` if tool calls are present,
    otherwise end the graph."""
    last = state["messages"][-1] if state["messages"] else None
    if isinstance(last, AIMessage) and last.tool_calls:
        return "tools"
    return END


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------


def _route_after_check_error(state: AgentState) -> Literal["agent", "__end__"]:
    """Decide whether to continue the agent loop or terminate.

    - ``retry_count > MAX_RETRIES`` → END (all retries exhausted)
    - otherwise → ``agent`` (continue the loop)
    """
    if state.get("retry_count", 0) > _MAX_RETRIES:
        logger.warning("Max retries exceeded, terminating agent loop")
        return END
    return "agent"


def build_agent(
    llm_config: LLMConfig | None = None,
    tools: list | None = None,
) -> Any:
    """Build and return a compiled LangGraph agent.

    Parameters
    ----------
    llm_config:
        Optional ``LLMConfig``. If ``None``, defaults from environment
        variables (see :class:`~app.agent.config.LLMConfig`).
    tools:
        Optional list of tools to register. If ``None``, uses the
        predefined ``TOOLS`` list from ``tool_definitions`` which
        includes all structured tools, SQL queries, and the Python
        code sandbox.

    Returns
    -------
    CompiledStateGraph
        A ready-to-invoke LangGraph agent.
    """
    # ── Assemble the tool list ──────────────────────────────────────────
    if tools is None:
        tools = list(PREDEFINED_TOOLS)

    # ── Build the LLM ───────────────────────────────────────────────────
    llm = get_llm(llm_config)

    # ── Graph construction ──────────────────────────────────────────────
    workflow = StateGraph(AgentState)

    workflow.add_node("agent", _make_agent_node(llm, tools))
    workflow.add_node("tools", ToolNode(tools, handle_tool_errors=_tool_error_handler))
    workflow.add_node("check_error", _check_error_node)

    workflow.add_edge(START, "agent")

    # After the agent: route to tools or end
    workflow.add_conditional_edges(
        "agent",
        _route_after_agent,
        {"tools": "tools", END: END},
    )

    # After tools execute, always check for errors first
    workflow.add_edge("tools", "check_error")

    # After the error check: route to agent or end based on retry state
    workflow.add_conditional_edges(
        "check_error",
        _route_after_check_error,
        {"agent": "agent", END: END},
    )

    return workflow.compile()


__all__ = [
    "build_agent",
]
