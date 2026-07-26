# LangGraph Agent for AML Transaction Analysis

A ReAct-style conversational agent that orchestrates structured tools, raw SQL queries, and a Python code sandbox to answer questions about the SAML-D (Synthetic Anti-Money Laundering) dataset containing ~9.5 million financial transactions.

The agent is built with **LangGraph** (`StateGraph`) and supports pluggable LLM backends (Google Gemini or OpenAI-compatible endpoints).

---

## Architecture Overview

The agent is a directed graph with three nodes and conditional routing:

```
                    ┌──────────────────────────────────────────────┐
                    │                   START                      │
                    └────────────────────┬─────────────────────────┘
                                         │
                    ┌────────────────────▼─────────────────────────┐
                    │               agent (LLM)                    │
                    │  - Receives conversation history              │
                    │  - Decides: respond OR call tool(s)           │
                    └────────────────────┬─────────────────────────┘
                                         │
                          ┌──────────────┴──────────────┐
                          │                             │
                    has tool_calls                  no tool_calls
                          │                             │
              ┌───────────▼───────────┐         ┌───────▼────────┐
              │      tools (exc)      │         │      END       │
              │  - Executes all tool  │         │  (return final │
              │    invocations in      │         │   answer)      │
              │    parallel            │         └────────────────┘
              └───────────┬───────────┘
                          │
              ┌───────────▼───────────┐
              │    check_error        │
              │  - Inspects results    │
              │  - Updates retry_count │
              │  - Injects hint or     │
              │    exceeds-msg on fail │
              └───────────┬───────────┘
                          │
              ┌───────────┴───────────┐
              │                       │
     retry_count <= MAX          retry_count > MAX
              │                       │
              ▼                       ▼
         agent (loop)              END (give up)
```

The graph loops until the LLM decides to produce a final answer (no more tool calls), the `retry_count` exceeds the maximum (graceful termination with a message to the user), or the `recursion_limit` of 25 is reached (safety net).

---

## Files

| File | Purpose |
|------|---------|
| `app/agent/__init__.py` | Package exports: `build_agent`, `LLMConfig`, `get_llm`, `AgentState` |
| `app/agent/config.py` | LLM configuration loader (reads `.env`) |
| `app/agent/state.py` | `AgentState` TypedDict definition |
| `app/agent/graph.py` | Graph builder: `build_agent()` — the main entry point |
| `.env.example` | Template showing both LLM provider setups |

---

## State: `AgentState`

Defined in `app/agent/state.py`:

| Field | Type | Description |
|-------|------|-------------|
| `messages` | `list[BaseMessage]` | Full conversation history. Uses `add_messages` reducer to append each turn. |
| `retry_count` | `int` | Counts **consecutive** tool-call errors. Resets to `0` on success. Used to trigger sandbox fallback at 3. |

**Initial state** (required when invoking the agent):

```python
{
    "messages": [("human", "Your question here")],
    "retry_count": 0,
}
```

---

## Graph Nodes

### 1. `agent` — LLM Decision Node

**Function:** `_make_agent_node()` (closure in `graph.py`)

- Receives the full `messages` list (conversation history)
- Calls the LLM with all tools bound via `llm.bind_tools(tools)`
- Returns the LLM response (either an `AIMessage` with `tool_calls`, or a final text answer)

**Tool binding:** `bound_model = llm.bind_tools(tools)` is called **once** during graph construction, not on every invocation, for efficiency.

### 2. `tools` — Tool Execution Node

**Implementation:** `langgraph.prebuilt.ToolNode`

- Receives the LLM's `tool_calls` from the last `AIMessage`
- Executes **all** tool calls in parallel
- Returns `ToolMessage` results back into the message list
- Tools are expected to **return error strings** rather than raising exceptions (the sandbox's `run_code` already does this)

### 3. `check_error` — Error Detection & Retry Management

**Function:** `_check_error_node()` in `graph.py`

- Inspects the last `ToolMessage` for specific error phrases (see below)
- **On success:** resets `retry_count` to `0`
- **On error with retry_count < 3:** increments `retry_count`, routes back to `agent` — the LLM sees the error and can correct itself
- **On error with retry_count == 3:** injects a `SystemMessage` with the sandbox fallback hint, then routes back to `agent`
- **On error with retry_count > 3:** returns a graceful `_MAX_RETRY_EXCEEDED_MSG` to the user and routes to `END` (prevents infinite looping)

**Error detection** uses specific phrase matching (not a generic "error" keyword, to avoid false positives from data values):

```
"only select queries", "multi-statement",
"unknown column", "failed to start",
"timed out", "too many concurrent"
```

**Routing node:** `_route_after_check_error()` — a conditional edge that checks `retry_count > _MAX_RETRIES` and routes to `END` when exceeded, breaking the agent loop gracefully.

---

## Routing Logic

| From | Condition | To | Description |
|------|-----------|----|-------------|
| `START` | always | `agent` | Entry point |
| `agent` | LLM produced `tool_calls` | `tools` | Execute tools |
| `agent` | LLM produced text (no tool_calls) | `END` | Return final answer |
| `tools` | always | `check_error` | Inspect results |
| `check_error` | `retry_count <= 3` | `agent` | Continue loop (LLM decides next step) |
| `check_error` | `retry_count > 3` | `END` | Graceful termination (max retries exceeded) |

The `recursion_limit=25` on `workflow.compile()` acts as a safety net for unexpected infinite loops (e.g., the LLM making successful tool calls without ever producing a final answer). Under normal conditions, the agent terminates gracefully when `retry_count > _MAX_RETRIES`.

---

## Error Recovery & Sandbox Fallback

The agent has three tiers of problem-solving:

### Tier 1: Structured Tools

The LLM can call any of the predefined tools (`search_transactions`, `get_high_value_transactions`, `get_suspicious_patterns`, `get_summary_statistics`). These cover most common queries.

### Tier 2: Raw SQL (`run_sql_query`)

If the structured tools cannot express the required query (e.g., window functions, CTEs, complex joins), the LLM can write DuckDB SQL directly.

### Tier 3: Code Sandbox (`run_python_code`)

If both Tier 1 and Tier 2 fail (the LLM gets 3 attempts), the `check_error` node injects a **fallback hint** as a `SystemMessage`:

> **Fallback hint:** The structured tools and SQL query tool have failed multiple times. Consider using the **run_python_code** tool instead to write custom Python analysis code. You have access to `engine` (QueryEngine), `pd` (pandas), and `np` (numpy) in the sandbox. Use `engine.execute_sql(...)` or `engine.search_transactions(...)` to fetch data, then process it with Python.

This tells the LLM to try writing Python code in the sandbox. The sandbox has access to:
- `engine` — a `QueryEngine` instance (can call `.search_transactions()` or `.execute_sql()`)
- `pd` — pandas for DataFrames
- `np` — numpy for numerical operations
- Standard library modules (`json`, `math`, `re`, `collections`, `datetime`, etc.)

---

## Configuration

### Environment Variables (`.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `openai` | `"openai"` or `"google"` |
| `LLM_MODEL` | `gpt-4o` | Model name (e.g. `gemini-2.0-flash`, `gemma-4`) |
| `LLM_API_KEY` | *(required)* | API key for the provider |
| `LLM_BASE_URL` | *(optional)* | Custom base URL for OpenAI-compatible endpoints |

### Example: OpenAI-compatible endpoint (Gemma, local LLMs)

```bash
LLM_PROVIDER=openai
LLM_MODEL=gemma-4
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://your-endpoint.example.com/v1
```

### Example: Google Gemini

```bash
LLM_PROVIDER=google
LLM_MODEL=gemini-2.0-flash
LLM_API_KEY=your-google-api-key
```

### Programmatic configuration

```python
from app.agent import LLMConfig, build_agent

config = LLMConfig()
# Override fields directly:
config.provider = "openai"
config.model = "gemma-4"
config.base_url = "https://your-endpoint.example.com/v1"

agent = build_agent(llm_config=config)
```

---

## Tools Available to the Agent

The agent is initialized with **6 tools** by default:

| Tool | Description | Source |
|------|-------------|--------|
| `search_transactions` | Search transactions with filters, grouping, pagination | `app/tools/tool_definitions.py` |
| `get_high_value_transactions` | Find transactions above a threshold (default $10K) | Same |
| `get_suspicious_patterns` | Analyse flagged (laundering) transactions | Same |
| `get_summary_statistics` | Aggregated stats grouped by dimensions | Same |
| `run_sql_query` | Execute raw SELECT SQL (supports CTEs, window functions) | Same |
| `run_python_code` | Execute arbitrary Python in the sandbox (fallback) | `app/tools/sandbox.py` via `graph.py` wrapper |

---

## Extensibility

### Adding new tools

Pass a custom `tools` list to `build_agent()`:

```python
from langchain_core.tools import tool
from app.agent import build_agent
from app.tools.tool_definitions import TOOLS

@tool
def my_custom_tool(param: str) -> str:
    """Description of my custom tool."""
    return f"Processed: {param}"

agent = build_agent(tools=TOOLS + [my_custom_tool])
```

The `tools` parameter fully overrides the default list. To extend the defaults, combine with `PREDEFINED_TOOLS` as shown above.

### Using a custom LLM

You can also pass a pre-configured LLM instance by modifying `get_llm()` in `config.py` or by passing a custom `llm_config`.

---

## Usage Guide

### Basic invocation

```python
from app.agent import build_agent

agent = build_agent()

result = agent.invoke({
    "messages": [("human", "Show me the top 5 high-value transactions from UK")],
    "retry_count": 0,
})

# Print the final answer
print(result["messages"][-1].content)
```

### Streaming response

```python
for chunk in agent.stream({
    "messages": [("human", "What is the total volume by currency?")],
    "retry_count": 0,
}):
    for node_name, output in chunk.items():
        print(f"[{node_name}] {output}")
```

### Inspecting full conversation

```python
result = agent.invoke({...})
for msg in result["messages"]:
    role = type(msg).__name__
    content = msg.content[:200] if msg.content else "(tool call)"
    print(f"[{role}]: {content}")
```

---

## Dependencies

Installed via `uv add`:

| Package | Version | Purpose |
|---------|---------|---------|
| `langgraph` | >= 1.2.9 | Graph-based agent orchestration |
| `langchain-google-genai` | >= 4.3.1 | Google Gemini model integration |
| `langchain-openai` | >= 1.4.1 | OpenAI / OpenAI-compatible model integration |
| `langchain-core` | >= 1.5.1 | Base LangChain abstractions |
| `python-dotenv` | latest | Load `.env` files |
| `duckdb` | >= 1.5.5 | SQL query engine (data access) |
| `pydantic` | >= 2.13.4 | Data models / tool schemas |
