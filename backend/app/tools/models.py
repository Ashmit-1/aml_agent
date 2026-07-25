"""
Pydantic models for AML transaction analysis tool inputs and outputs.
"""

from __future__ import annotations

from datetime import date, time
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Input models
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

    min_amount: float = Field(default=5_000.0, ge=0)
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
# Output models
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
    returned_count: int
