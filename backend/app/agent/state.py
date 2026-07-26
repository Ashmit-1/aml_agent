"""
State definitions for the AML LangGraph agent.

The primary type is :class:`AgentState`, a ``TypedDict`` that holds the
conversation message history and a retry counter for error recovery.
"""

from __future__ import annotations

from typing import Annotated, Sequence

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class AgentState(TypedDict):
    """State of the AML analysis agent at each step of the graph.

    Fields
    ------
    messages:
        The conversation history. Each step appends new messages
        (LLM responses, tool calls, tool results). The ``add_messages``
        reducer merges them correctly.
    retry_count:
        Number of consecutive tool-call errors in the current
        interaction. Reset to ``0`` after a successful tool call or
        when a final answer is produced. Used to trigger the sandbox
        fallback after 3 failures.
    """

    messages: Annotated[Sequence[BaseMessage], add_messages]
    retry_count: int
