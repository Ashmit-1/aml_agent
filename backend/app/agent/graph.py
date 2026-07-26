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
from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from app.agent.config import LLMConfig, get_llm
from app.agent.state import AgentState
from app.tools.sandbox import run_code
from app.tools.tool_definitions import TOOLS as PREDEFINED_TOOLS

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

# ---------------------------------------------------------------------------
# Helper predicates
# ---------------------------------------------------------------------------


def _is_error_message(msg: BaseMessage) -> bool:
    """Return ``True`` if *msg* is a ``ToolMessage`` containing an error."""
    if not isinstance(msg, ToolMessage):
        return False
    content = str(msg.content).lower()
    return any(
        keyword in content
        for keyword in ("error", "only select queries", "multi-statement",
                        "unknown column", "failed to start", "timed out",
                        "too many concurrent", "no results returned")
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
        - ``retry_count``: incremented on error, reset to 0 on success.
        - ``messages``: (optional) includes a fallback hint when retries
          are exhausted.
    """
    messages = state["messages"]
    retry_count = state.get("retry_count", 0)
    last_msg = messages[-1] if messages else None

    if isinstance(last_msg, ToolMessage) and _is_error_message(last_msg):
        new_count = retry_count + 1
        logger.info("Tool error detected (retry %d/%d)", new_count, _MAX_RETRIES)
        updates: dict[str, Any] = {"retry_count": new_count}
        if new_count >= _MAX_RETRIES:
            # Inject a fallback hint message so the LLM considers the sandbox
            hint = SystemMessage(content=_FALLBACK_HINT)
            updates["messages"] = [hint]
        return updates

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
        predefined ``TOOLS`` list from ``tool_definitions`` plus a
        ``run_python_code`` tool that wraps the code sandbox.

    Returns
    -------
    CompiledStateGraph
        A ready-to-invoke LangGraph agent.
    """
    # ── Assemble the tool list ──────────────────────────────────────────
    if tools is None:

        @tool
        def run_python_code(
            code: str,
            timeout_seconds: int = 30,
        ) -> dict[str, Any]:
            """Write and execute Python code in a secure sandboxed environment.

            Use this tool when the prebuilt tools cannot answer the user's
            query. Available in the sandbox:
            - ``engine``: QueryEngine (call .search_transactions() or
              .execute_sql() to fetch data)
            - ``pd``: pandas
            - ``np``: numpy
            - Standard library: json, math, re, collections, itertools, etc.

            Set a ``result`` variable at the end to return a value.
            """
            return run_code(
                code=code,
                timeout_seconds=timeout_seconds,
            )

        tools = list(PREDEFINED_TOOLS) + [run_python_code]

    # ── Build the LLM ───────────────────────────────────────────────────
    llm = get_llm(llm_config)

    # ── Graph construction ──────────────────────────────────────────────
    workflow = StateGraph(AgentState)

    workflow.add_node("agent", _make_agent_node(llm, tools))
    workflow.add_node("tools", ToolNode(tools))
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

    # After the error check, route back to the agent for the next iteration
    workflow.add_edge("check_error", "agent")

    return workflow.compile(recursion_limit=25)


__all__ = [
    "build_agent",
]
