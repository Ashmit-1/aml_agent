"""
Pydantic models for AML transaction analysis tool inputs and outputs.

Every field includes a ``description`` so that LLM function-calling schemas
carry rich context about each parameter's purpose and format.
"""

from __future__ import annotations

from datetime import date, time
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Input models
# ---------------------------------------------------------------------------


class SearchParams(BaseModel):
    """Composite filter parameters for searching AML transactions.

    Use this to search or filter the transaction dataset. All fields are
    optional – only supplied fields are applied as filters.  Supports
    pagination, grouping, and aggregation in a single call.
    """

    # ── Date & Time ────────────────────────────────────────────────────

    start_date: Optional[date] = Field(
        default=None,
        description="Return only transactions on or after this date (ISO format, e.g. 2023-01-15).",
    )
    end_date: Optional[date] = Field(
        default=None,
        description="Return only transactions on or before this date (ISO format, e.g. 2023-06-30).",
    )
    start_time: Optional[time] = Field(
        default=None,
        description="Return only transactions at or after this time (HH:MM:SS format, e.g. 09:00:00).",
    )
    end_time: Optional[time] = Field(
        default=None,
        description="Return only transactions at or before this time (HH:MM:SS format, e.g. 17:00:00).",
    )

    # ── Accounts ───────────────────────────────────────────────────────

    sender_account: Optional[int] = Field(
        default=None,
        description="Filter by the exact sender account numerical identifier.",
    )
    receiver_account: Optional[int] = Field(
        default=None,
        description="Filter by the exact receiver account numerical identifier.",
    )

    # ── Amount ─────────────────────────────────────────────────────────

    min_amount: Optional[float] = Field(
        default=None,
        ge=0,
        description="Minimum transaction amount (inclusive). Useful for finding transactions above a threshold.",
    )
    max_amount: Optional[float] = Field(
        default=None,
        ge=0,
        description="Maximum transaction amount (inclusive). Useful for finding transactions below a threshold.",
    )

    # ── Currency ───────────────────────────────────────────────────────

    payment_currency: Optional[str] = Field(
        default=None,
        description="Filter by the payment currency name (e.g. UK pounds, US dollar, Euro, Swiss franc, Yen, Dirham, Naira). The dataset uses full currency names, NOT ISO codes.",
    )
    received_currency: Optional[str] = Field(
        default=None,
        description="Filter by the received currency name (e.g. UK pounds, US dollar, Euro, Swiss franc, Yen, Dirham, Naira). The dataset uses full currency names, NOT ISO codes.",
    )

    # ── Location ───────────────────────────────────────────────────────

    sender_location: Optional[str] = Field(
        default=None,
        description="Filter by the sender's bank location / country name (e.g. UK, USA, France, Germany, India, UAE). The dataset uses full country names/abbreviations, NOT ISO codes.",
    )
    receiver_location: Optional[str] = Field(
        default=None,
        description="Filter by the receiver's bank location / country name (e.g. UK, USA, France, Germany, India, UAE). The dataset uses full country names/abbreviations, NOT ISO codes.",
    )

    # ── Transaction type ───────────────────────────────────────────────

    payment_type: Optional[str] = Field(
        default=None,
        description="Filter by the payment instrument / type (e.g. ACH, Cash Deposit, Cash Withdrawal, Cheque, Credit card, Cross-border, Debit card).",
    )

    # ── Laundering ─────────────────────────────────────────────────────

    is_laundering: Optional[int] = Field(
        default=None,
        ge=0,
        le=1,
        description="Filter by money-laundering flag. 0 = legitimate, 1 = flagged as suspicious.",
    )
    laundering_type: Optional[str] = Field(
        default=None,
        description="Filter by the specific money-laundering pattern (e.g. Structuring, Smurfing, Behavioural_Change_1, Bipartite, Fan_In, Fan_Out, Scatter-Gather).",
    )

    # ── Aggregation & output control ───────────────────────────────────

    group_by: Optional[list[str]] = Field(
        default=None,
        description="Columns to GROUP BY for aggregation (e.g. ['Payment_currency'], ['Date'], ['Sender_bank_location', 'Receiver_bank_location']). Must be valid column names from the dataset.",
    )
    aggregate: Optional[Literal["count", "sum", "avg"]] = Field(
        default=None,
        description="Aggregation function to apply when group_by is set. 'count' = number of transactions, 'sum' = total amount, 'avg' = average amount. Defaults to 'count' if group_by is set.",
    )
    sort_by: Optional[str] = Field(
        default=None,
        description="Column to sort results by (e.g. 'Amount', 'Date'). Must be a valid column name.",
    )
    sort_order: Optional[Literal["ASC", "DESC"]] = Field(
        default="DESC",
        description="Sort direction: ASC = ascending (smallest/lowest first), DESC = descending (largest/highest first). Defaults to DESC.",
    )
    limit: int = Field(
        default=100,
        ge=1,
        le=10_000,
        description="Maximum number of rows to return (1–10,000). Default 100.",
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Number of rows to skip for pagination. Use with limit to page through results.",
    )


class HighValueParams(BaseModel):
    """Parameters for the high-value transaction lookup.

    Identifies transactions above a configurable amount threshold.
    The default threshold of $10,000 is a common AML regulatory requirement.
    """

    min_amount: float = Field(
        default=10_000.0,
        ge=0,
        description="Minimum transaction amount threshold. Default 10,000 (standard AML reporting threshold).",
    )
    start_date: Optional[date] = Field(
        default=None,
        description="Only consider transactions on or after this date (ISO format, e.g. 2023-01-01).",
    )
    end_date: Optional[date] = Field(
        default=None,
        description="Only consider transactions on or before this date (ISO format, e.g. 2023-12-31).",
    )
    payment_currency: Optional[str] = Field(
        default=None,
        description="Filter by payment currency name (e.g. UK pounds, US dollar, Euro). The dataset uses full currency names, NOT ISO codes.",
    )
    limit: int = Field(
        default=100,
        ge=1,
        le=10_000,
        description="Maximum number of results to return (1–10,000). Default 100.",
    )


class SuspiciousPatternParams(BaseModel):
    """Parameters for AML pattern detection.

    Analyzes transactions that have already been flagged as suspicious
    (is_laundering = 1) with optional filters for amount, location,
    currency, and laundering type.
    """

    min_amount: float = Field(
        default=5_000.0,
        ge=0,
        description="Minimum transaction amount for suspicious transactions. Default 5,000.",
    )
    max_amount: Optional[float] = Field(
        default=None,
        ge=0,
        description="Maximum transaction amount for suspicious transactions.",
    )
    start_date: Optional[date] = Field(
        default=None,
        description="Only consider suspicious transactions on or after this date.",
    )
    end_date: Optional[date] = Field(
        default=None,
        description="Only consider suspicious transactions on or before this date.",
    )
    sender_location: Optional[str] = Field(
        default=None,
        description="Focus on suspicious transactions from this sender location/country name (e.g. UK, USA, France, UAE). The dataset uses full country names, NOT ISO codes.",
    )
    receiver_location: Optional[str] = Field(
        default=None,
        description="Focus on suspicious transactions to this receiver location/country name (e.g. UK, USA, France, UAE). The dataset uses full country names, NOT ISO codes.",
    )
    payment_currency: Optional[str] = Field(
        default=None,
        description="Filter suspicious transactions by payment currency name (e.g. UK pounds, US dollar, Euro). The dataset uses full currency names, NOT ISO codes.",
    )
    laundering_type: Optional[str] = Field(
        default=None,
        description="Filter by specific money-laundering pattern (e.g. Structuring, Smurfing, Behavioural_Change_1, Bipartite, Fan_In).",
    )
    limit: int = Field(
        default=100,
        ge=1,
        le=10_000,
        description="Maximum number of results to return (1–10,000). Default 100.",
    )


class SummaryParams(BaseModel):
    """Parameters for summary / aggregation queries.

    Groups transactions by one or more columns and computes an aggregate
    (count, sum, or average) for each group.
    """

    group_by: list[str] = Field(
        min_length=1,
        description="Columns to group by (e.g. ['Payment_currency'], ['Date'], ['Sender_bank_location', 'Receiver_bank_location']). At least one valid column name is required.",
    )
    aggregate: Literal["count", "sum", "avg"] = Field(
        default="count",
        description="Aggregation function: 'count' = number of transactions, 'sum' = total amount, 'avg' = average amount.",
    )
    aggregate_column: str = Field(
        default="Amount",
        description="Column to apply the aggregate function on (only used for 'sum' or 'avg'). Default 'Amount'.",
    )
    start_date: Optional[date] = Field(
        default=None,
        description="Only include transactions on or after this date.",
    )
    end_date: Optional[date] = Field(
        default=None,
        description="Only include transactions on or before this date.",
    )
    is_laundering: Optional[int] = Field(
        default=None,
        ge=0,
        le=1,
        description="Filter: 0 = legitimate transactions only, 1 = flagged transactions only. Omit for both.",
    )
    limit: int = Field(
        default=50,
        ge=1,
        le=10_000,
        description="Maximum number of group rows to return (1–10,000). Default 50.",
    )


class SqlQueryParams(BaseModel):
    """Parameters for the raw SQL query tool.

    WARNING: Only SELECT statements are allowed. No modifications.
    The LLM must write valid DuckDB SQL against the 'transactions' view.
    """

    sql: str = Field(
        description="A read-only SELECT SQL statement to execute. Query against the 'transactions' view which contains all columns of the dataset. Must be a valid DuckDB SQL query. Only SELECT statements are permitted."
    )
    limit: int = Field(
        default=500,
        ge=1,
        le=10_000,
        description="Maximum number of rows to return. Default 500. Prevents accidental large result sets.",
    )


class CodeSandboxParams(BaseModel):
    """Parameters for the Python code sandbox tool.

    Use this as a fallback when the prebuilt tools cannot answer the
    user's query. Write arbitrary Python to perform custom analysis,
    statistical computations, or multi-step data transformations.
    """

    code: str = Field(
        description=(
            "Python code to execute in the sandbox. Available variables: "
            "`engine` (QueryEngine — call .search_transactions() or .execute_sql() "
            "to fetch data), `pd` (pandas), `np` (numpy), plus standard library "
            "modules (json, math, re, collections, itertools, functools, "
            "statistics, random, datetime, typing, string). "
            "Set a `result` variable to return a value. "
            "Restricted: no file I/O, no network, no subprocess, no os."
        )
    )
    timeout_seconds: int = Field(
        default=30,
        ge=1,
        le=120,
        description="Maximum execution time in seconds (1–120). Default 30.",
    )


# ---------------------------------------------------------------------------
# Output models
# ---------------------------------------------------------------------------


class Transaction(BaseModel):
    """A single transaction record from the AML dataset."""

    Time: Optional[str] = Field(default=None, description="Time of transaction (HH:MM:SS format).")
    Date: Optional[str] = Field(default=None, description="Date of transaction (YYYY-MM-DD format).")
    Sender_account: Optional[int] = Field(default=None, description="Unique sender account identifier.")
    Receiver_account: Optional[int] = Field(default=None, description="Unique receiver account identifier.")
    Amount: Optional[float] = Field(default=None, description="Transaction amount in the payment currency.")
    Payment_currency: Optional[str] = Field(default=None, description="Name of the payment currency (e.g. UK pounds, US dollar).")
    Received_currency: Optional[str] = Field(default=None, description="Name of the currency received (e.g. UK pounds, US dollar).")
    Sender_bank_location: Optional[str] = Field(default=None, description="Country name of the sender's bank (e.g. UK, USA).")
    Receiver_bank_location: Optional[str] = Field(default=None, description="Country name of the receiver's bank (e.g. UK, USA).")
    Payment_type: Optional[str] = Field(default=None, description="Method of payment (e.g. ACH, Cash Deposit, Cheque, Credit card, Cross-border, Debit card).")
    Is_laundering: Optional[int] = Field(default=None, description="Binary flag: 0 = legitimate, 1 = flagged as money laundering.")
    Laundering_type: Optional[str] = Field(default=None, description="Category of money laundering pattern (if flagged).")


class PaginatedResult(BaseModel):
    """Paginated query result with total count for context."""

    total_count: int = Field(description="Total number of matching transactions (ignoring pagination).")
    limit: int = Field(description="The limit that was applied to this query.")
    offset: int = Field(description="The offset that was applied to this query.")
    results: list[dict[str, Any]] = Field(description="List of transaction records matching the query.")


class SummaryResult(BaseModel):
    """Aggregation / group-by result."""

    rows: list[dict[str, Any]] = Field(description="List of aggregated rows, one per group.")
    returned_count: int = Field(description="Number of rows returned in this result set.")


# ---------------------------------------------------------------------------
# ML Model Tool input models
# ---------------------------------------------------------------------------


class MLAnalysisParams(BaseModel):
    """Parameters for the full AML ML pipeline analysis."""

    max_flagged_results: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Maximum number of flagged transaction records to return (1–500). Default 50.",
    )
    min_risk_level: str = Field(
        default="low",
        description=(
            "Minimum risk level to include. "
            "'low' = all flagged, 'medium' = medium+high, 'high' = high only. Default 'low'."
        ),
    )


class AccountInvestigationParams(BaseModel):
    """Parameters for investigating a specific account."""

    account_id: int = Field(
        description="The numerical account identifier to investigate (e.g. 4521). Must be a valid account ID from the dataset."
    )


class FlaggedExplanationParams(BaseModel):
    """Parameters for getting an explanation for a flagged transaction."""

    sender_account: int = Field(
        description="The sender account numerical identifier of the flagged transaction."
    )
    receiver_account: int = Field(
        description="The receiver account numerical identifier of the flagged transaction."
    )
    amount: float = Field(
        ge=0,
        description="The transaction amount (used for exact matching). Must match the flagged transaction amount.",
    )


class AMLPromptParams(BaseModel):
    """Parameters for generating an LLM explanation prompt for a flagged transaction."""

    sender_account: int = Field(
        description="The sender account numerical identifier of the flagged transaction."
    )
    receiver_account: int = Field(
        description="The receiver account numerical identifier of the flagged transaction."
    )
    amount: float = Field(
        ge=0,
        description="The transaction amount (used for exact matching). Must match the flagged transaction amount.",
    )
