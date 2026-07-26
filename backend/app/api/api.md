# AML Transaction Analysis API

LangGraph-powered agent for querying the **SAML-D** (Synthetic Anti-Money Laundering) dataset of ~9.5M transactions. The agent can search transactions, run SQL queries, and execute custom Python code in a sandbox.

---

## Quick Start

```bash
# From the project root
cd backend
python main.py                   # dev server on port 8000
# or
uvicorn app.api:app --reload     # same via uvicorn
```

Open **http://localhost:8000/docs** for the interactive Swagger UI.

---

## Endpoints

| Method | Path              | Description                                                        |
|--------|-------------------|--------------------------------------------------------------------|
| GET    | `/`                | Root — API information and links                                   |
| GET    | `/api/health`      | Health check — server status and agent readiness                   |
| POST   | `/api/chat`        | Blocking chat — send a message, get the final answer               |
| POST   | `/api/chat/stream` | **SSE streaming** — same as `/chat` but with step-by-step events   |

---

## `GET /api/health`

Simple health check.

### Response

```json
{
  "status": "ok",
  "agent_ready": true
}
```

- **`status`** — always `"ok"` when the server is running.
- **`agent_ready`** — `true` after at least one chat request has initialised the LangGraph agent; initially `false`.

---

## `POST /api/chat` (blocking)

Send a message and optional conversation history, receive the agent's final response.

### Request Body

```json
{
  "message": "How many suspicious transactions are there?",
  "history": [
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi! How can I help?"}
  ]
}
```

| Field     | Type   | Required | Description                                |
|-----------|--------|----------|--------------------------------------------|
| `message` | string | ✅       | The user's question or instruction.        |
| `history` | array  | ❌       | Prior conversation turns. Omit or pass `[]` for a new conversation. Each item has `role` (`"user"` or `"assistant"`) and `content` (string). |

### Response

```json
{
  "response": "There are 9,873 suspicious transactions.",
  "tool_calls": [
    {
      "name": "search_transactions",
      "args": {"is_laundering": 1, "aggregate": "count"}
    }
  ],
  "retry_count": 0
}
```

| Field         | Type            | Description                                              |
|---------------|-----------------|----------------------------------------------------------|
| `response`    | string          | The agent's final answer.                                |
| `tool_calls`  | array\[object\] | Every tool call the agent made (name + arguments).       |
| `retry_count` | integer         | Consecutive errors encountered; `0` means no errors.     |

---

## `POST /api/chat/stream` (SSE streaming)

Same as `/api/chat` but the response is a **Server-Sent Events** stream. The frontend receives real-time updates as the agent plans, calls tools, and produces the final answer.

### Request Body

Identical to `/api/chat`:

```json
{
  "message": "Show me high-value suspicious transactions from UAE",
  "history": []
}
```

### Response (SSE stream)

Content-Type: `text/event-stream`

The stream emits several **`event: step`** lines followed by a terminal **`event: done`**. Event data is JSON.

#### Event types

| Step type       | When it fires                                                                 | Data fields                                        |
|-----------------|-------------------------------------------------------------------------------|----------------------------------------------------|
| `thinking`      | The LLM is reasoning / planning.                                             | `content` (text), optional `next` ("tool_call")    |
| `tool_call`     | The LLM decided to invoke a tool.                                            | `tool` (name), `arguments` (object)                |
| `tool_result`   | A tool returned a result.                                                    | `tool` (name), `summary` (truncated result string) |
| `retry`         | A tool errored and the agent is retrying (or giving up).                     | `retry_count`, `reason` (text)                     |
| `response`      | The final answer (always the last `step` before `done`).                     | `content` (final answer text)                      |

#### SSE event: `step` (thinking)

```json
{
  "type": "thinking",
  "content": "I should use search_transactions to find suspicious transactions."
}
```

#### SSE event: `step` (tool_call)

```json
{
  "type": "tool_call",
  "tool": "search_transactions",
  "arguments": {"is_laundering": 1, "aggregate": "count"}
}
```

#### SSE event: `step` (tool_result)

```json
{
  "type": "tool_result",
  "tool": "search_transactions",
  "summary": "{\"total_count\": 9873, \"results\": []}"
}
```

#### SSE event: `step` (retry)

```json
{
  "type": "retry",
  "retry_count": 1,
  "reason": "Tool returned an error. Retrying (1/3)…"
}
```

#### SSE event: `step` (response)

```json
{
  "type": "response",
  "content": "There are 9,873 suspicious transactions. All of them are from UK senders."
}
```

#### SSE event: `done`

```json
{}
```

No data — indicates the stream is complete.

#### Full stream example

```
event: step
data: {"type":"thinking","content":"I'll search for suspicious transactions first."}

event: step
data: {"type":"tool_call","tool":"search_transactions","arguments":{"is_laundering":1,"aggregate":"count"}}

event: step
data: {"type":"tool_result","tool":"search_transactions","summary":"{'total_count': 9873, 'results': []}"}

event: step
data: {"type":"response","content":"There are 9,873 suspicious transactions."}

event: done
data: {}
```

---

## Frontend SSE Client (JavaScript)

```javascript
// sse-client.js — consume the streaming endpoint

async function sendChatStream(message, history = [], onEvent, onDone, onError) {
  const response = await fetch("http://localhost:8000/api/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history }),
  });

  if (!response.ok) {
    onError?.(new Error(`HTTP ${response.status}`));
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // Parse SSE lines
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";   // Keep incomplete line in buffer

    let currentEvent = null;
    let currentData = "";

    for (const line of lines) {
      if (line.startsWith("event: ")) {
        currentEvent = line.slice(7).trim();
      } else if (line.startsWith("data: ")) {
        currentData = line.slice(6).trim();
      } else if (line === "" && currentEvent && currentData) {
        // Empty line = end of event
        try {
          const parsed = JSON.parse(currentData);
          if (currentEvent === "step") {
            onEvent?.(parsed);
          } else if (currentEvent === "done") {
            onDone?.();
          } else if (currentEvent === "error") {
            onError?.(new Error(parsed.message));
          }
        } catch (e) {
          console.warn("Failed to parse SSE data:", currentData, e);
        }
        currentEvent = null;
        currentData = "";
      }
    }
  }
}

// Usage:
sendChatStream(
  "How many suspicious transactions are there?",
  [],
  (event) => {
    switch (event.type) {
      case "thinking":
        console.log("💭", event.content);
        break;
      case "tool_call":
        console.log("🔧 Calling", event.tool, event.arguments);
        break;
      case "tool_result":
        console.log("📊 Result from", event.tool, "→", event.summary);
        break;
      case "retry":
        console.log("⚠️ Retry", event.retry_count, ":", event.reason);
        break;
      case "response":
        console.log("✅ Final answer:", event.content);
        break;
    }
  },
  () => console.log("🏁 Stream complete"),
  (err) => console.error("❌", err)
);
```

---

## Python SSE Client (for testing)

```python
import httpx
import json

with httpx.stream(
    "POST",
    "http://localhost:8000/api/chat/stream",
    json={"message": "How many suspicious transactions are there?", "history": []},
    timeout=60,
) as resp:
    for line in resp.iter_lines():
        if line.startswith("data: "):
            data = json.loads(line[6:])
            print(json.dumps(data, indent=2))
```

---

## cURL (convenience)

```bash
# Blocking chat
curl -s http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "How many suspicious transactions?", "history": []}'

# Streaming chat (watch events arrive)
curl -N http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "How many suspicious transactions?", "history": []}'
```

The `-N` flag (no-buffer) is important — without it `curl` may buffer the entire stream before printing.

---

## Agent Capabilities

The underlying LangGraph agent has three tiers of problem-solving:

| Tier | Tool(s) | When it's used |
|------|---------|----------------|
| **1. Structured queries** | `search_transactions`, `get_high_value_transactions`, `get_suspicious_patterns`, `get_summary_statistics` | Common analytical questions (counts, sums, grouping, filtering by sender/receiver/currency) |
| **2. Raw SQL** | `run_sql_query` | Queries the structured tools cannot express (window functions, complex joins, date arithmetic) |
| **3. Python sandbox** | `run_python_code` | Universal fallback for custom analysis (statistics, visualisation data, multi-step logic) |

The agent automatically falls back through these tiers. If structured queries fail three times, the LLM receives a hint to use `run_python_code`.

---

## Error Handling

- **Tool errors** (invalid SQL, missing columns, runtime errors) are caught and the agent retries up to 3 times.
- **After 3 retries** the agent returns a graceful apology.
- **SSE errors** (fatal exceptions during streaming) emit an `error` event.
- **HTTP 500** from the blocking `/chat` endpoint indicates an unhandled server error (the exception detail is included).

---

## Environment Variables

| Variable         | Required | Default       | Description                                      |
|------------------|----------|---------------|--------------------------------------------------|
| `LLM_PROVIDER`   | ❌       | `openai`      | `"openai"` or `"google"`                         |
| `LLM_MODEL`      | ❌       | `gpt-4o`      | Model name (e.g. `gemini-2.0-flash`, `gemma-4`) |
| `LLM_API_KEY`    | ✅       | —             | API key for the provider                         |
| `LLM_BASE_URL`   | ❌       | —             | Custom base URL for OpenAI-compatible endpoints  |

---

## Development

### Adding a new tool

1. Define your tool function in a file under `app/tools/`.
2. Register it in `TOOLS` (see `app/tools/tool_definitions.py`).
3. Restart the server — the agent will automatically discover it.

### Testing

```bash
# Run the server
python main.py

# Test the streaming endpoint (separate terminal)
curl -N http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "How many transactions total?", "history": []}'
```
