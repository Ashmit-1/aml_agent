"""
AML Analysis LangGraph Agent.

This package provides a LangGraph-powered agent that orchestrates the
AML transaction analysis tools. It supports:

- Structured transaction search / filtering
- Raw SQL queries for complex analysis
- Python code sandbox for custom computations
- Automatic error recovery with retry logic
- Sandbox fallback after repeated failures

Quick start::

    from app.agent.graph import build_agent
    from app.agent.config import LLMConfig

    config = LLMConfig()  # reads from environment
    agent = build_agent(llm_config=config)

    result = agent.invoke({
        "messages": [("human", "Show me high-value transactions over $50K")],
        "retry_count": 0,
    })
"""

from app.agent.config import LLMConfig, get_llm
from app.agent.graph import build_agent
from app.agent.state import AgentState

__all__ = [
    "LLMConfig",
    "get_llm",
    "build_agent",
    "AgentState",
]
