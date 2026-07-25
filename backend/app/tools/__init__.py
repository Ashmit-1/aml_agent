"""
AML Transaction Analysis Tools.

This module provides tools for querying the SAML-D dataset (9.5M+ rows)
using DuckDB for efficient, parameterized SQL queries directly on the CSV.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date, time
from typing import Any, Literal, Optional

import duckdb
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Pydantic models – tool inputs
# ---------------------------------------------------------------------------

class SearchParams(BaseModel):
    """Composite filter parameters for searching transactions."""

    # Date & Time
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None

    # Accounts
    sender_account: Optional[int] = None
    receiver_account: Optional[int] = None

    # Amount
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None

    # Currency
    payment_currency: Optional[str] = None
    received_currency: Optional[str] = None

    # Location
    sender_location: Optional[str] = None
    receiver_location: Optional[str] = None

    # Transaction type
    payment_type: Optional[str] = None

    # Laundering
    is_laundering: Optional[int] = Field(default=None, ge=0, le=1)
    laundering_type: Optional[str] = None

    # Aggregation & output control
    group_by: Optional[list[str]] = None
    aggregate: Optional[Literal["count", "sum", "avg"]] = None
    sort_by: Optional[str] = None
    sort_order: Optional[Literal["ASC", "DESC"]] = "DESC"
    limit: int = Field(default=100, ge=1, le=10_000)
    offset: int = Field(default=0, ge=0)


class HighValueParams(BaseModel):
    """Parameters for the high-value transaction lookup."""

    min_amount: float = Field(default=10_000.0, ge=0)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    payment_currency: Optional[str] = None
    limit: int = Field(default=100, ge=1, le=10_000)


class SuspiciousPatternParams(BaseModel):
    """Parameters for AML pattern detection."""

    min_amount: Optional[float] = Field(default=None, ge=0)
    max_amount: Optional[float] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    sender_location: Optional[str] = None
    receiver_location: Optional[str] = None
    payment_currency: Optional[str] = None
    laundering_type: Optional[str] = None
    limit: int = Field(default=100, ge=1, le=10_000)


class SummaryParams(BaseModel):
    """Parameters for summary / aggregation queries."""

    group_by: list[str] = Field(min_length=1)
    aggregate: Literal["count", "sum", "avg"] = "count"
    aggregate_column: str = "Amount"
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_laundering: Optional[int] = Field(default=None, ge=0, le=1)
    limit: int = Field(default=50, ge=1, le=10_000)


# ---------------------------------------------------------------------------
# Pydantic models – tool outputs
# ---------------------------------------------------------------------------

class Transaction(BaseModel):
    """A single transaction record from the dataset."""

    Time: Optional[str] = None
    Date: Optional[str] = None
    Sender_account: Optional[int] = None
    Receiver_account: Optional[int] = None
    Amount: Optional[float] = None
    Payment_currency: Optional[str] = None
    Received_currency: Optional[str] = None
    Sender_bank_location: Optional[str] = None
    Receiver_bank_location: Optional[str] = None
    Payment_type: Optional[str] = None
    Is_laundering: Optional[int] = None
    Laundering_type: Optional[str] = None


class PaginatedResult(BaseModel):
    """Paginated query result."""

    total_count: int
    limit: int
    offset: int
    results: list[dict[str, Any]]


class SummaryResult(BaseModel):
    """Aggregation/summary result."""

    rows: list[dict[str, Any]]
    total_count: int


# ---------------------------------------------------------------------------
# Query engine
# ---------------------------------------------------------------------------

@dataclass
class QueryEngine:
    """Lightweight DuckDB wrapper that runs SQL directly against the CSV."""

    csv_path: str = field(
        default_factory=lambda: os.path.join(
            os.path.dirname(__file__), "..", "data", "SAML-D.csv"
        )
    )
    _conn: duckdb.DuckDBPyConnection = field(init=False, repr=False)

    def __post_init__(self) -> None:
        resolved = os.path.abspath(self.csv_path)
        if not os.path.isfile(resolved):
            raise FileNotFoundError(f"CSV not found at: {resolved}")
        self._conn = duckdb.connect()
        self._conn.execute(
            f"CREATE VIEW transactions AS SELECT * FROM read_csv_auto('{resolved}')"
        )

    def close(self) -> None:
        self._conn.close()

    # ------------------------------------------------------------------
    # Query builders
    # ------------------------------------------------------------------

    @staticmethod
    def _build_where(params: SearchParams) -> tuple[str, list[Any]]:
        """Build a WHERE clause and parameter list from SearchParams."""
        clauses: list[str] = []
        values: list[Any] = []

        if params.start_date:
            clauses.append("Date >= ?")
            values.append(params.start_date.isoformat())
        if params.end_date:
            clauses.append("Date <= ?")
            values.append(params.end_date.isoformat())
        if params.start_time:
            clauses.append("Time >= ?")
            values.append(params.start_time.isoformat())
        if params.end_time:
            clauses.append("Time <= ?")
            values.append(params.end_time.isoformat())
        if params.sender_account is not None:
            clauses.append("Sender_account = ?")
            values.append(params.sender_account)
        if params.receiver_account is not None:
            clauses.append("Receiver_account = ?")
            values.append(params.receiver_account)
        if params.min_amount is not None:
            clauses.append("Amount >= ?")
            values.append(params.min_amount)
        if params.max_amount is not None:
            clauses.append("Amount <= ?")
            values.append(params.max_amount)
        if params.payment_currency:
            clauses.append("Payment_currency = ?")
            values.append(params.payment_currency)
        if params.received_currency:
            clauses.append("Received_currency = ?")
            values.append(params.received_currency)
        if params.sender_location:
            clauses.append("Sender_bank_location = ?")
            values.append(params.sender_location)
        if params.receiver_location:
            clauses.append("Receiver_bank_location = ?")
            values.append(params.receiver_location)
        if params.payment_type:
            clauses.append("Payment_type = ?")
            values.append(params.payment_type)
        if params.is_laundering is not None:
            clauses.append("Is_laundering = ?")
            values.append(params.is_laundering)
        if params.laundering_type:
            clauses.append("Laundering_type = ?")
            values.append(params.laundering_type)

        where = ""
        if clauses:
            where = " WHERE " + " AND ".join(clauses)
        return where, values

    # ------------------------------------------------------------------
    # Public tool methods
    # ------------------------------------------------------------------

    def search_transactions(self, params: SearchParams) -> PaginatedResult:
        """
        Composite search tool – apply all provided filters and return
        paginated, optionally grouped/aggregated results.
        """
        where, values = self._build_where(params)

        # Count total matching rows (without group/limit/offset)
        count_sql = f"SELECT COUNT(*) AS cnt FROM transactions{where}"
        total = self._conn.execute(count_sql, values).fetchone()[0]

        # Build the main query
        select_cols = "*"
        if params.group_by:
            group_cols = ", ".join(params.group_by)
            agg_col = params.aggregate or "count"
            if agg_col == "count":
                select_cols = f"{group_cols}, COUNT(*) AS count"
            elif agg_col == "sum":
                select_cols = f"{group_cols}, SUM(Amount) AS total_amount"
            elif agg_col == "avg":
                select_cols = f"{group_cols}, AVG(Amount) AS avg_amount"

        order_clause = ""
        if params.sort_by:
            direction = params.sort_order or "DESC"
            order_clause = f" ORDER BY {params.sort_by} {direction}"
        elif params.group_by:
            # Default order by aggregate descending when grouped
            order_clause = f" ORDER BY count DESC"

        group_clause = ""
        if params.group_by:
            group_clause = " GROUP BY " + ", ".join(params.group_by)

        data_sql = (
            f"SELECT {select_cols} FROM transactions{where}"
            f"{group_clause}{order_clause}"
            f" LIMIT ? OFFSET ?"
        )
        data_values = values + [params.limit, params.offset]
        rows = self._conn.execute(data_sql, data_values).fetchall()
        columns = [desc[0] for desc in self._conn.description]

        results = [dict(zip(columns, row)) for row in rows]

        return PaginatedResult(
            total_count=total,
            limit=params.limit,
            offset=params.offset,
            results=results,
        )

    def get_high_value_transactions(
        self, params: HighValueParams
    ) -> PaginatedResult:
        """
        Find high-value transactions (default >= $10K) – a common AML
        red-flag threshold.
        """
        search_params = SearchParams(
            min_amount=params.min_amount,
            start_date=params.start_date,
            end_date=params.end_date,
            payment_currency=params.payment_currency,
            sort_by="Amount",
            sort_order="DESC",
            limit=params.limit,
        )
        return self.search_transactions(search_params)

    def get_suspicious_patterns(
        self, params: SuspiciousPatternParams
    ) -> PaginatedResult:
        """
        Detect suspicious AML patterns: transactions filtered by amount,
        location corridors, currency, and laundering type.
        """
        search_params = SearchParams(
            min_amount=params.min_amount,
            max_amount=params.max_amount,
            start_date=params.start_date,
            end_date=params.end_date,
            sender_location=params.sender_location,
            receiver_location=params.receiver_location,
            payment_currency=params.payment_currency,
            laundering_type=params.laundering_type,
            is_laundering=1,  # always filter for flagged transactions
            sort_by="Amount",
            sort_order="DESC",
            limit=params.limit,
        )
        return self.search_transactions(search_params)

    def get_summary_statistics(
        self, params: SummaryParams
    ) -> SummaryResult:
        """
        Aggregated statistics grouped by a dimension (e.g. currency,
        location, date, laundering type).
        """
        group_cols = ", ".join(params.group_by)
        agg_col = params.aggregate_column or "Amount"

        if params.aggregate == "count":
            select_cols = f"{group_cols}, COUNT(*) AS count"
        elif params.aggregate == "sum":
            select_cols = f"{group_cols}, SUM({agg_col}) AS total_amount"
        else:  # avg
            select_cols = f"{group_cols}, AVG({agg_col}) AS avg_amount"

        where_clauses: list[str] = []
        values: list[Any] = []
        if params.start_date:
            where_clauses.append("Date >= ?")
            values.append(params.start_date.isoformat())
        if params.end_date:
            where_clauses.append("Date <= ?")
            values.append(params.end_date.isoformat())
        if params.is_laundering is not None:
            where_clauses.append("Is_laundering = ?")
            values.append(params.is_laundering)

        where = ""
        if where_clauses:
            where = " WHERE " + " AND ".join(where_clauses)

        sql = (
            f"SELECT {select_cols} FROM transactions{where}"
            f" GROUP BY {group_cols}"
            f" ORDER BY count DESC"
            f" LIMIT ?"
        )
        values.append(params.limit)

        rows = self._conn.execute(sql, values).fetchall()
        columns = [desc[0] for desc in self._conn.description]

        return SummaryResult(
            rows=[dict(zip(columns, row)) for row in rows],
            total_count=len(rows),
        )
