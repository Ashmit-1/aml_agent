# AML Transaction Analysis Tools

A collection of LangChain-compatible tools for querying the **SAML-D (Synthetic Anti-Money Laundering Dataset)** — approximately 9.5 million financial transactions with metadata about senders, receivers, amounts, currencies, locations, and money-laundering flags.

The tools use **DuckDB** to run efficient, parameterized SQL queries directly on the CSV file via a registered `transactions` SQL view.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    LangChain Agent                           │
│  (LLM decides which tool to call based on user query)        │
└───────────────────┬─────────────────────────────────────────┘
                    │
    ┌───────────────┼───────────────────┐
    ▼               ▼                   ▼
┌─────────┐  ┌────────────┐  ┌──────────────────┐
│ 6 Tools  │  │ Validators  │  │   QueryEngine    │
│ (LangChain│  │ (SQL safety)│  │   (DuckDB)       │
│Structured │  │            │  │                  │
│  Tool)    │  │            │  │  transactions    │
└─────────┘  └────────────┘  │  view → CSV       │
                             └──────────────────┘
```

---

## Quick Start

```python
from app.tools.tool_definitions import TOOLS

# TOOLS is a list of 6 StructuredTool instances
# ready to bind to a LangChain agent:
# agent = create_openai_functions_agent(llm, TOOLS, prompt)
```

---

## Tool Reference

### 1. `search_transactions`

The **primary** tool for querying transactions with any combination of filters.

**Purpose:** Search for transactions by date/time range, amount threshold, currency, location, account, payment type, or laundering status. Supports grouping, aggregation, sorting, and pagination.

**File:** `app/tools/engine.py` → `QueryEngine.search_transactions()`

**Input Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `start_date` | `str` (YYYY-MM-DD) | `None` | Return transactions on or after this date |
| `end_date` | `str` (YYYY-MM-DD) | `None` | Return transactions on or before this date |
| `start_time` | `str` (HH:MM:SS) | `None` | Return transactions at or after this time |
| `end_time` | `str` (HH:MM:SS) | `None` | Return transactions at or before this time |
| `sender_account` | `int` | `None` | Filter by sender account ID |
| `receiver_account` | `int` | `None` | Filter by receiver account ID |
| `min_amount` | `float` | `None` | Minimum transaction amount (>=) |
| `max_amount` | `float` | `None` | Maximum transaction amount (<=) |
| `payment_currency` | `str` | `None` | Payment currency name (e.g. "UK pounds", "US dollar", "Euro") |
| `received_currency` | `str` | `None` | Received currency name (e.g. "UK pounds", "US dollar") |
| `sender_location` | `str` | `None` | Sender's bank location (e.g. "UK", "USA", "France") |
| `receiver_location` | `str` | `None` | Receiver's bank location (e.g. "UK", "USA", "France") |
| `payment_type` | `str` | `None` | Payment method (e.g. "ACH", "Cash Deposit", "Credit card") |
| `is_laundering` | `int` (0/1) | `None` | Filter by laundering flag |
| `laundering_type` | `str` | `None` | Laundering pattern (e.g. "Structuring", "Smurfing") |
| `group_by` | `list[str]` | `None` | Columns to GROUP BY (e.g. `["Payment_currency"]`) |
| `aggregate` | `"count"` / `"sum"` / `"avg"` | `None` | Aggregation function for grouping |
| `sort_by` | `str` | `None` | Column to sort by |
| `sort_order` | `"ASC"` / `"DESC"` | `"DESC"` | Sort direction |
| `limit` | `int` | `100` | Max rows to return (1–10,000) |
| `offset` | `int` | `0` | Pagination offset |

**Output:**
```json
{
  "total_count": 5000,
  "limit": 100,
  "offset": 0,
  "results": [
    {
      "Time": "14:30:00",
      "Date": "2022-10-07",
      "Sender_account": 12345678,
      "Receiver_account": 87654321,
      "Amount": 15000.00,
      "Payment_currency": "UK pounds",
      "Received_currency": "US dollar",
      "Sender_bank_location": "UK",
      "Receiver_bank_location": "USA",
      "Payment_type": "Wire Transfer",
      "Is_laundering": 0,
      "Laundering_type": null
    }
  ]
}
```

---

### 2. `get_high_value_transactions`

**Purpose:** Find transactions above a configurable amount threshold. Default threshold is $10,000 (standard AML reporting requirement). Results sorted by amount descending.

**File:** `app/tools/engine.py` → `QueryEngine.get_high_value_transactions()`

**Input Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `min_amount` | `float` | `10_000.0` | Amount threshold |
| `start_date` | `str` (YYYY-MM-DD) | `None` | Start date filter |
| `end_date` | `str` (YYYY-MM-DD) | `None` | End date filter |
| `payment_currency` | `str` | `None` | Currency name (e.g. "UK pounds") |
| `limit` | `int` | `100` | Max rows to return |

**Output:** Same as `search_transactions`.

---

### 3. `get_suspicious_patterns`

**Purpose:** Analyse transactions flagged as suspicious (where `is_laundering = 1`). Always filters for flagged transactions — the user does not need to specify this.

**File:** `app/tools/engine.py` → `QueryEngine.get_suspicious_patterns()`

**Input Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `min_amount` | `float` | `5_000.0` | Minimum amount |
| `max_amount` | `float` | `None` | Maximum amount |
| `start_date` | `str` (YYYY-MM-DD) | `None` | Start date |
| `end_date` | `str` (YYYY-MM-DD) | `None` | End date |
| `sender_location` | `str` | `None` | Sender location (e.g. "UK", "USA") |
| `receiver_location` | `str` | `None` | Receiver location (e.g. "UK", "USA") |
| `payment_currency` | `str` | `None` | Currency name |
| `laundering_type` | `str` | `None` | Pattern (e.g. "Structuring", "Smurfing") |
| `limit` | `int` | `100` | Max rows to return |

**Output:** Same as `search_transactions`.

---

### 4. `get_summary_statistics`

**Purpose:** Compute aggregated statistics (count, sum, avg) grouped by one or more dimensions like currency, location, date, payment type, or laundering status.

**File:** `app/tools/engine.py` → `QueryEngine.get_summary_statistics()`

**Input Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `group_by` | `list[str]` | *(required)* | Columns to group by (e.g. `["Payment_currency"]`) |
| `aggregate` | `"count"` / `"sum"` / `"avg"` | `"count"` | Aggregation function |
| `aggregate_column` | `str` | `"Amount"` | Column to sum/avg (ignored for count) |
| `start_date` | `str` (YYYY-MM-DD) | `None` | Start date |
| `end_date` | `str` (YYYY-MM-DD) | `None` | End date |
| `is_laundering` | `int` (0/1) | `None` | Filter by laundering flag |
| `limit` | `int` | `50` | Max group rows to return |

**Output:**
```json
{
  "rows": [
    {
      "Payment_currency": "UK pounds",
      "count": 3500000
    },
    {
      "Payment_currency": "US dollar",
      "count": 2800000
    }
  ],
  "returned_count": 2
}
```

---

### 5. `run_sql_query`

**Purpose:** Execute a read-only SQL SELECT query directly against the dataset. Use for complex analytical questions that the structured tools cannot handle: window functions, CTEs, subqueries, conditional logic, multi-level aggregations, etc.

**Safety constraints:**
- Only `SELECT` statements are allowed (CTEs with `WITH` and leading comments are also accepted)
- Multi-statement SQL (semicolons outside string literals) is rejected
- A `LIMIT` clause is automatically applied if one is not present (default 500, max 10,000)
- Column references are **not** validated — full DuckDB SQL is supported

**File:** `app/tools/engine.py` → `QueryEngine.execute_sql()`

**Input Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `sql` | `str` | *(required)* | A read-only SELECT SQL statement (DuckDB dialect) |
| `limit` | `int` | `500` | Max rows (1–10,000) |

**Example queries:**
```sql
-- Window function
SELECT *, ROW_NUMBER() OVER (PARTITION BY Sender_account ORDER BY Amount DESC) AS rn
FROM transactions

-- CTE
WITH high_risk AS (
    SELECT * FROM transactions
    WHERE Sender_bank_location IN ('RU', 'IR', 'KP')
      AND Amount > 10000
)
SELECT Sender_bank_location, COUNT(*) AS cnt
FROM high_risk
GROUP BY Sender_bank_location

-- Complex filtering
SELECT Sender_account, COUNT(*) AS tx_count, SUM(Amount) AS total
FROM transactions
WHERE Payment_currency = 'UK pounds'
  AND Is_laundering = 1
GROUP BY Sender_account
HAVING COUNT(*) > 5
```

**Output:** `list[dict[str, Any]]` — List of row dicts (column_name → value).

---

### 6. `run_python_code`

**Purpose:** Write and execute Python code in a secure sandboxed environment. Use when the prebuilt tools cannot answer the user's query — e.g., multi-step data analysis, statistical computations, advanced filtering, or custom transformations.

**File:** `app/tools/sandbox.py` → `run_code()`

**Input Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `code` | `str` | *(required)* | Python code to execute |
| `timeout_seconds` | `int` | `30` | Max execution time (1–120) |

**Available in the sandbox:**

| Name | Description |
|------|-------------|
| `engine` | `QueryEngine` instance to query the dataset |
| `pd` | `pandas` library (if installed) |
| `np` | `numpy` library (if installed) |
| `json`, `math`, `re` | Standard library modules |
| `collections`, `itertools`, `functools` | Standard library modules |
| `statistics`, `random`, `datetime` | Standard library modules |
| `SearchParams` | Pydantic model for tool parameters |
| `HighValueParams`, `SummaryParams` | Pydantic models |
| `SqlQueryParams` | Pydantic model |
| `SuspiciousPatternParams` | Pydantic model |

**Restrictions:**
- No file I/O (`open`, file writes)
- No network access (`subprocess`, `socket`, `requests`, `os`)
- No system commands (`os.system`, `subprocess`)
- Only whitelisted modules may be imported
- Output truncated after 50,000 characters
- Execution auto-kills after timeout (max 120s)

**How to return results:** Assign a `result` variable at the end of your code. Use `print()` for intermediate debugging.

**Output:**
```json
{
  "success": true,
  "stdout": "Processing 1000 records...\n",
  "result": {"mean_amount": 15000.0, "median_amount": 8500.0},
  "error": null,
  "truncated": false
}
```

---

## Dataset Schema

The `transactions` DuckDB view exposes the following columns from the SAML-D CSV:

| Column | Type | Description |
|--------|------|-------------|
| `Time` | `TIME (HH:MM:SS)` | Time of the transaction |
| `Date` | `DATE (YYYY-MM-DD)` | Date of the transaction |
| `Sender_account` | `INTEGER` | Unique sender account identifier |
| `Receiver_account` | `INTEGER` | Unique receiver account identifier |
| `Amount` | `FLOAT` | Transaction amount in payment currency |
| `Payment_currency` | `TEXT` | Name of the payment currency (e.g. 'UK pounds', 'US dollar') |
| `Received_currency` | `TEXT` | Name of the currency received (e.g. 'UK pounds', 'US dollar') |
| `Sender_bank_location` | `TEXT` | Country name of sender's bank (e.g. 'UK', 'USA') |
| `Receiver_bank_location` | `TEXT` | Country name of receiver's bank (e.g. 'UK', 'USA') |
| `Payment_type` | `TEXT` | Payment method (e.g. ACH, Cash Deposit, Cheque) |
| `Is_laundering` | `INT (0 or 1)` | Money-laundering flag |
| `Laundering_type` | `TEXT` | Laundering pattern (e.g. Structuring, Smurfing) |

**Key notes about the data:**
- Currency columns use **full names** (`"UK pounds"`, `"US dollar"`, `"Euro"`), **not** ISO codes like `"USD"` or `"GBP"`
- Location columns use **country names** (`"UK"`, `"USA"`, `"France"`, `"Germany"`), **not** ISO codes like `"GB"` or `"US"`
- Payment types include: `ACH`, `Cash Deposit`, `Cash Withdrawal`, `Cheque`, `Credit card`, `Cross-border`, `Debit card`
- Laundering types include: `Structuring`, `Smurfing`, `Behavioural_Change_1`, `Behavioural_Change_2`, `Bipartite`, `Cash_Withdrawal`, `Cycle`, `Deposit-Send`, `Fan_In`, `Fan_Out`, `Gather-Scatter`, `Layered_Fan_In`, `Layered_Fan_Out`, `Over-Invoicing`, `Scatter-Gather`, `Single_large`, `Stacked Bipartite`
- Date/Time columns are serialized as ISO strings (e.g. `"2022-10-07"`, `"14:30:00"`)

---

## Validation & Safety

The `app/tools/validators.py` module provides the following safety checks:

| Function | Purpose |
|----------|---------|
| `validate_sql_select(sql)` | Ensures SQL is a read-only SELECT statement (allows CTEs and comments, rejects multi-statement SQL) |
| `validate_columns(names)` | Ensures column names are in the known whitelist (prevents SQL injection via column references) |
| `validate_aggregate_column(name)` | Same as `validate_columns` but for aggregation columns |
| `get_schema_markdown()` | Returns a Markdown table of the dataset schema for LLM tool descriptions |

The `run_sql_query` tool enforces:
1. Only `SELECT` statements (CTEs with `WITH`, and leading `--` / `/* */` comments are accepted)
2. No multi-statement SQL (semicolons outside string literals are rejected)
3. A `LIMIT` clause is always applied (default 500, max 10,000)

The `run_python_code` sandbox enforces:
1. Whitelisted imports only (no `os`, `subprocess`, `socket`, etc.)
2. Thread-based timeout (auto-kills infinite loops)
3. Semaphore limiting to 5 concurrent executions
4. Output size limits (50,000 characters)

---

## File Reference

| File | Purpose |
|------|---------|
| `app/tools/validators.py` | Schema metadata, column validation, SQL SELECT validation |
| `app/tools/models.py` | Pydantic input/output models for all tools |
| `app/tools/engine.py` | `QueryEngine` — DuckDB-backed query engine with all tool methods |
| `app/tools/sandbox.py` | `run_code()` — restricted Python execution sandbox |
| `app/tools/tool_definitions.py` | LangChain `StructuredTool` wrappers and tool registry (`TOOLS` list) |
| `app/tools/__init__.py` | Package exports |
