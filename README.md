# AML Transaction Analysis Platform

An AI-powered platform for analyzing the **SAML-D (Synthetic Anti-Money Laundering Dataset)** containing ~9.5 million financial transactions. The system uses a LangGraph agent with LLM capabilities to query, search, and analyze transaction data through natural language conversations.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Dataset Download](#dataset-download)
- [Backend Setup](#backend-setup)
- [Frontend Setup](#frontend-setup)
- [Running the Application](#running-the-application)
- [API Documentation](#api-documentation)
- [Agent Architecture](#agent-architecture)
- [Tools Reference](#tools-reference)
- [Dataset Schema](#dataset-schema)
- [Environment Variables](#environment-variables)
- [Development](#development)
- [License](#license)

---

## Overview

This platform provides an intelligent conversational interface for querying and analyzing financial transaction data for anti-money laundering (AML) compliance. Users can ask questions in natural language, and the AI agent will:

1. Understand the query intent
2. Select appropriate tools (structured queries, SQL, or Python code)
3. Execute the analysis
4. Return clear, actionable insights

---

## Features

- **Natural Language Interface** — Ask questions in plain English about transaction data
- **Multi-Tier Analysis** — Automatically selects between structured tools, raw SQL, or Python sandbox
- **Real-Time Streaming** — Server-Sent Events (SSE) for live response updates
- **Conversation History** — Persistent chat sessions with full context
- **Error Recovery** — Automatic retry logic with graceful degradation
- **Sandbox Execution** — Secure Python code execution for custom analysis

---

## Tech Stack

### Backend

| Component | Technology |
|-----------|------------|
| Framework | FastAPI |
| Agent Orchestration | LangGraph |
| LLM Providers | OpenAI / Google Gemini |
| Query Engine | DuckDB |
| Data Processing | Pandas, NumPy |
| Data Models | Pydantic |

### Frontend

| Component | Technology |
|-----------|------------|
| Framework | React 19 |
| Language | TypeScript |
| Build Tool | Vite |
| Styling | Tailwind CSS |
| State Management | Zustand |
| Markdown Rendering | react-markdown |

---

## Project Structure

```
project/
├── backend/                          # Python backend
│   ├── app/
│   │   ├── agent/                    # LangGraph agent
│   │   │   ├── __init__.py
│   │   │   ├── config.py             # LLM configuration
│   │   │   ├── graph.py              # Agent graph builder
│   │   │   └── state.py              # Agent state definition
│   │   ├── api/                      # FastAPI routes
│   │   │   ├── __init__.py
│   │   │   ├── models.py             # API request/response models
│   │   │   └── routes.py             # API endpoints
│   │   ├── tools/                    # Analysis tools
│   │   │   ├── __init__.py
│   │   │   ├── engine.py             # DuckDB query engine
│   │   │   ├── models.py             # Tool input/output models
│   │   │   ├── sandbox.py            # Python code sandbox
│   │   │   ├── tool_definitions.py   # LangChain tool wrappers
│   │   │   └── validators.py         # SQL & column validation
│   │   └── data/                     # Dataset directory
│   │       └── transactions.csv      # SAML-D dataset (after download)
│   ├── main.py                       # Entry point
│   ├── pyproject.toml                # Python dependencies
│   ├── .python-version               # Python 3.12
│   └── .env.example                  # Environment template
│
├── frontend/                         # React frontend
│   ├── src/
│   │   ├── components/               # UI components
│   │   │   ├── ChatInterface.tsx     # Main chat UI
│   │   │   ├── Sidebar.tsx           # Conversation sidebar
│   │   │   └── ui/                   # Reusable UI primitives
│   │   ├── services/                 # API services
│   │   │   ├── chatApi.ts            # Backend API client
│   │   │   └── storage.ts            # Local persistence
│   │   ├── store/                    # State management
│   │   │   └── chatStore.ts          # Zustand store
│   │   ├── types/                    # TypeScript types
│   │   │   └── index.ts
│   │   ├── lib/                      # Utilities
│   │   │   └── utils.ts
│   │   ├── App.tsx                   # Root component
│   │   ├── main.tsx                  # Entry point
│   │   └── index.css                 # Global styles
│   ├── package.json                  # Node dependencies
│   ├── vite.config.ts                # Vite configuration
│   ├── tailwind.config.js            # Tailwind configuration
│   └── tsconfig.json                 # TypeScript configuration
│
└── README.md                         # This file
```

---

## Prerequisites

### System Requirements

- **Python** 3.12 or higher
- **Node.js** 18+ and npm/yarn/pnpm
- **Kaggle Account** (for dataset download)

### LLM API Key

You need an API key from one of these providers:

| Provider | Get API Key |
|----------|-------------|
| OpenAI | [platform.openai.com](https://platform.openai.com/api-keys) |
| Google AI | [aistudio.google.com](https://aistudio.google.com/apikey) |

---

## Dataset Download

The SAML-D (Synthetic Anti-Money Laundering Dataset) must be downloaded before running the application.

### Option 1: Using the Download Script

```bash
# Run the download script from the project root
bash download_dataset.sh
```

The script (`download_dataset.sh`) contains:

```bash
#!/bin/bash
curl -L -o ~/Downloads/synthetic-transaction-monitoring-dataset-aml.zip \
  https://www.kaggle.com/api/v1/datasets/download/berkanoztas/synthetic-transaction-monitoring-dataset-aml
```

### Option 2: Manual Download

1. Visit [Kaggle Dataset Page](https://www.kaggle.com/datasets/berkanoztas/synthetic-transaction-monitoring-dataset-aml)
2. Download the dataset ZIP file
3. Extract the CSV file

### Option 3: Using Kaggle CLI

```bash
# Install Kaggle CLI (if not installed)
pip install kaggle

# Download the dataset
kaggle datasets download -d berkanoztas/synthetic-transaction-monitoring-dataset-aml

# Unzip the downloaded file
unzip synthetic-transaction-monitoring-dataset-aml.zip
```

### Place the Dataset

After downloading, extract the CSV file to the backend data directory:

```bash
# Create data directory if it doesn't exist
mkdir -p backend/app/data

# Extract the ZIP file to the data directory
unzip -o ~/Downloads/synthetic-transaction-monitoring-dataset-aml.zip -d backend/app/data/

# Remove the ZIP file
rm ~/Downloads/synthetic-transaction-monitoring-dataset-aml.zip
```

The expected file path:
```
backend/app/data/SAML-D.csv
```

**Note:** Verify the extracted CSV filename matches `SAML-D.csv`. If the Kaggle download extracts a differently named file, either rename it or update the filename in `backend/app/tools/engine.py`.

---

## Backend Setup

### 1. Navigate to Backend Directory

```bash
cd backend
```

### 2. Create Virtual Environment

The project uses Python 3.12 and `uv` for dependency management.

```bash
# Install uv (if not installed)
pip install uv
# Or using the official installer:
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create and activate virtual environment
uv venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate     # Windows
```

### 3. Install Dependencies

```bash
# Install all dependencies
uv sync

# Or using pip
uv pip install -e .
```

### 4. Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your configuration
nano .env
```

**.env Configuration:**

```bash
# For OpenAI
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
LLM_API_KEY=your-openai-api-key-here

# For Google Gemini
# LLM_PROVIDER=google
# LLM_MODEL=gemini-2.0-flash
# LLM_API_KEY=your-google-api-key-here

# Optional: Custom base URL for OpenAI-compatible endpoints
# LLM_BASE_URL=https://your-endpoint.example.com/v1
```

### 5. Start the Backend Server

```bash
# Using main.py
python main.py

# Or using uvicorn directly
uvicorn app.api:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API Base:** http://localhost:8000
- **Swagger Docs:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

## Frontend Setup

### 1. Navigate to Frontend Directory

```bash
cd frontend
```

### 2. Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env
```

**.env Configuration:**

```bash
# Backend API base URL
VITE_API_BASE_URL=http://localhost:8000
```

### 3. Install Dependencies

```bash
# Using npm
npm install

# Using yarn
yarn install

# Using pnpm
pnpm install
```

### 4. Start Development Server

```bash
npm run dev
```

The frontend will be available at: http://localhost:5173

---

## Running the Application

### Full Stack Development

Open two terminals:

**Terminal 1 — Backend:**
```bash
cd backend
python main.py
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```

### Access the Application

1. Open http://localhost:5173 in your browser
2. Start chatting with the AI assistant
3. Ask questions about the transaction data

### Example Queries

```
How many suspicious transactions are there?
Show me high-value transactions over $50,000 from UK
What are the most common laundering patterns?
Compare transaction volumes by currency
Find transactions between Russian and US accounts
```

---

## API Documentation

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | API information |
| GET | `/api/health` | Health check |
| POST | `/api/chat` | Blocking chat request |
| POST | `/api/chat/stream` | SSE streaming chat |

### Health Check

```bash
curl http://localhost:8000/api/health
```

**Response:**
```json
{
  "status": "ok",
  "agent_ready": true
}
```

### Blocking Chat

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How many suspicious transactions are there?",
    "history": []
  }'
```

**Response:**
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

### Streaming Chat (SSE)

```bash
curl -N http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Show me high-value suspicious transactions",
    "history": []
  }'
```

**Event Types:**

| Type | Description |
|------|-------------|
| `thinking` | LLM reasoning/planning |
| `tool_call` | Tool invocation |
| `tool_result` | Tool execution result |
| `response` | Final answer |
| `done` | Stream complete |

**Example Stream:**
```
event: step
data: {"type":"thinking","content":"I'll search for suspicious transactions."}

event: step
data: {"type":"tool_call","tool":"search_transactions","arguments":{"is_laundering":1}}

event: step
data: {"type":"response","content":"There are 9,873 suspicious transactions."}

event: done
data: {}
```

---

## Agent Architecture

The agent uses a **ReAct (Reasoning + Acting)** pattern built with LangGraph:

```
                    ┌────────────────────────────┐
                    │          START             │
                    └─────────────┬──────────────┘
                                  │
                    ┌─────────────▼──────────────┐
                    │       agent (LLM)          │
                    │  • Receives conversation   │
                    │  • Decides: respond or     │
                    │    call tool(s)            │
                    └─────────────┬──────────────┘
                                  │
                    ┌─────────────┴──────────────┐
                    │                            │
              has tool_calls               no tool_calls
                    │                            │
        ┌───────────▼───────────┐        ┌───────▼──────┐
        │     tools (exec)      │        │     END      │
        │  • Executes tools     │        │  (return     │
        │    in parallel        │        │   answer)    │
        └───────────┬───────────┘        └──────────────┘
                    │
        ┌───────────▼───────────┐
        │     check_error       │
        │  • Inspects results   │
        │  • Updates retry_count│
        │  • Injects hint on    │
        │    failure            │
        └───────────┬───────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
   retry_count <= 3      retry_count > 3
        │                       │
        ▼                       ▼
   agent (loop)           END (give up)
```

### Three-Tier Problem Solving

| Tier | Tool | Use Case |
|------|------|----------|
| **1. Structured** | `search_transactions`, `get_high_value_transactions`, `get_suspicious_patterns`, `get_summary_statistics` | Common analytical queries |
| **2. Raw SQL** | `run_sql_query` | Complex queries with window functions, CTEs |
| **3. Python** | `run_python_code` | Custom analysis, statistics, multi-step logic |

The agent automatically falls back through tiers when errors occur.

---

## Tools Reference

### 1. search_transactions

Primary tool for querying transactions with filters.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `start_date` | str | Start date (YYYY-MM-DD) |
| `end_date` | str | End date (YYYY-MM-DD) |
| `min_amount` | float | Minimum amount |
| `max_amount` | float | Maximum amount |
| `payment_currency` | str | Currency name (e.g., "UK pounds") |
| `sender_location` | str | Sender country (e.g., "UK") |
| `receiver_location` | str | Receiver country |
| `is_laundering` | int | 0 or 1 |
| `laundering_type` | str | Pattern (e.g., "Structuring") |
| `group_by` | list | Columns to group by |
| `aggregate` | str | "count", "sum", or "avg" |
| `limit` | int | Max rows (1-10,000) |

### 2. get_high_value_transactions

Find transactions above a threshold.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `min_amount` | float | 10,000 | Amount threshold |
| `start_date` | str | None | Start date |
| `end_date` | str | None | End date |
| `limit` | int | 100 | Max results |

### 3. get_suspicious_patterns

Analyze flagged transactions.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `min_amount` | float | 5,000 | Minimum amount |
| `sender_location` | str | None | Sender location |
| `receiver_location` | str | None | Receiver location |
| `laundering_type` | str | None | Pattern type |
| `limit` | int | 100 | Max results |

### 4. get_summary_statistics

Aggregated statistics by dimensions.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `group_by` | list | Required | Columns to group |
| `aggregate` | str | "count" | "count", "sum", or "avg" |
| `aggregate_column` | str | "Amount" | Column for sum/avg |
| `is_laundering` | int | None | Filter flag |
| `limit` | int | 50 | Max groups |

### 5. run_sql_query

Execute raw DuckDB SQL.

| Parameter | Type | Description |
|-----------|------|-------------|
| `sql` | str | SELECT statement (DuckDB dialect) |
| `limit` | int | Max rows (default 500) |

**Safety:**
- Only SELECT statements allowed
- CTEs with `WITH` are supported
- Auto-applies LIMIT if missing

### 6. run_python_code

Execute Python in a sandbox.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `code` | str | Required | Python code |
| `timeout_seconds` | int | 30 | Max execution time |

**Available in sandbox:**
- `engine` — QueryEngine instance
- `pd` — pandas
- `np` — numpy
- Standard library modules

---

## Dataset Schema

The `transactions` table contains:

| Column | Type | Description |
|--------|------|-------------|
| `Time` | TIME | Transaction time (HH:MM:SS) |
| `Date` | DATE | Transaction date (YYYY-MM-DD) |
| `Sender_account` | INTEGER | Sender account ID |
| `Receiver_account` | INTEGER | Receiver account ID |
| `Amount` | FLOAT | Transaction amount |
| `Payment_currency` | TEXT | e.g., "UK pounds", "US dollar" |
| `Received_currency` | TEXT | e.g., "UK pounds", "Euro" |
| `Sender_bank_location` | TEXT | Country name (e.g., "UK") |
| `Receiver_bank_location` | TEXT | Country name |
| `Payment_type` | TEXT | Method (ACH, Wire Transfer, etc.) |
| `Is_laundering` | INT | 0 or 1 flag |
| `Laundering_type` | TEXT | Pattern type |

**Important Notes:**
- Currencies use full names: `"UK pounds"`, `"US dollar"`, `"Euro"`
- Locations use country names: `"UK"`, `"USA"`, `"France"`
- Payment types: `ACH`, `Cash Deposit`, `Cheque`, `Credit card`, `Cross-border`, `Debit card`
- Laundering types: `Structuring`, `Smurfing`, `Fan_In`, `Fan_Out`, `Cycle`, etc.
- **Verify the CSV filename**: After extracting the Kaggle dataset, check the actual filename in `backend/app/data/` and update `engine.py` if needed.

---

## Environment Variables

### Backend

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LLM_PROVIDER` | No | `openai` | `"openai"` or `"google"` |
| `LLM_MODEL` | No | `gpt-4o` | Model name |
| `LLM_API_KEY` | Yes | — | API key |
| `LLM_BASE_URL` | No | — | Custom base URL |

### Example Configurations

**OpenAI:**
```bash
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
LLM_API_KEY=sk-...
```

**Google Gemini:**
```bash
LLM_PROVIDER=google
LLM_MODEL=gemini-2.0-flash
LLM_API_KEY=AIza...
```

**Local/OpenAI-Compatible:**
```bash
LLM_PROVIDER=openai
LLM_MODEL=gemma-4
LLM_API_KEY=your-key
LLM_BASE_URL=http://localhost:11434/v1
```

---

## Development

### Backend

```bash
cd backend

# Run with auto-reload
uvicorn app.api:app --reload

# Run tests (if available)
pytest

# Type checking
mypy app/
```

### Frontend

```bash
cd frontend

# Development server
npm run dev

# Build for production
npm run build

# Lint
npm run lint

# Preview production build
npm run preview
```

### Adding New Tools

1. Create tool function in `app/tools/engine.py`
2. Create Pydantic model in `app/tools/models.py`
3. Register in `app/tools/tool_definitions.py`
4. Restart backend server

### Adding New API Endpoints

1. Define request/response models in `app/api/models.py`
2. Add route in `app/api/routes.py`
3. Restart backend server

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError` | Run `uv sync` or `pip install -e .` |
| `Dataset not found` | Ensure CSV is in `backend/app/data/transactions.csv` |
| `API key error` | Check `.env` file and API key validity |
| `Port already in use` | Change port or kill existing process |
| `Agent not ready` | Make first chat request to initialize |

### Checking Health

```bash
curl http://localhost:8000/api/health
```

If `agent_ready` is `false`, send a chat request to initialize the agent.


---

## Acknowledgments

- [SAML-D Dataset](https://www.kaggle.com/datasets/berkanoztas/synthetic-transaction-monitoring-dataset-aml) by Berkay Öztas
- [LangGraph](https://langchain-ai.github.io/langgraph/) for agent orchestration
- [DuckDB](https://duckdb.org/) for efficient SQL queries
- [FastAPI](https://fastapi.tiangolo.com/) for the API framework
