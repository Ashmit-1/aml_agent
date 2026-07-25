"""
LangChain-compatible tool definitions for the AML transaction analysis system.

Each tool is a ``StructuredTool`` instance (compatible with LangChain,
OpenAI function calling, and Anthropic tool use) that wraps a method on
:class:`~app.tools.engine.QueryEngine`.

Usage by an agent::

    from app.tools.tool_definitions import TOOLS
    # TOOLS is a list of StructuredTool ready to be bound to a LangChain agent.
"""

from __future__ import annotations

from typing import Any

from langchain_core.tools import StructuredTool

from app.tools.engine import QueryEngine
from app.tools.models import (
    HighValueParams,
    SearchParams,
    SqlQueryParams,
    SummaryParams,
    SuspiciousPatternParams,
)
from app.tools.validators import get_schema_markdown

# ---------------------------------------------------------------------------
# Tool factory helpers
# ---------------------------------------------------------------------------

_engine: QueryEngine | None = None


def _get_engine() -> QueryEngine:
    """Return a singleton ``QueryEngine`` instance."""
    global _engine
    if _engine is None:
        _engine = QueryEngine()
    return _engine


# ---------------------------------------------------------------------------
# Tool-callable functions
# ---------------------------------------------------------------------------


def search_transactions(
    start_date: str | None = None,
    end_date: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    sender_account: int | None = None,
    receiver_account: int | None = None,
    min_amount: float | None = None,
    max_amount: float | None = None,
    payment_currency: str | None = None,
    received_currency: str | None = None,
    sender_location: str | None = None,
    receiver_location: str | None = None,
    payment_type: str | None = None,
    is_laundering: int | None = None,
    laundering_type: str | None = None,
    group_by: list[str] | None = None,
    aggregate: str | None = None,
    sort_by: str | None = None,
    sort_order: str = "DESC",
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    """Search for transactions in the AML dataset using any combination of filters.

    Use this tool for the majority of user queries about financial transactions.
    Supports date/time ranges, amount thresholds, currency/account/location filters,
    money-laundering flags, grouping, aggregation, and pagination.

    Dataset columns: Time, Date, Sender_account, Receiver_account, Amount,
    Payment_currency, Received_currency, Sender_bank_location,
    Receiver_bank_location, Payment_type, Is_laundering, Laundering_type.

    Returns a dict with total_count, limit, offset, and results (list of records).
    """
    params = SearchParams(
        start_date=start_date,
        end_date=end_date,
        start_time=start_time,
        end_time=end_time,
        sender_account=sender_account,
        receiver_account=receiver_account,
        min_amount=min_amount,
        max_amount=max_amount,
        payment_currency=payment_currency,
        received_currency=received_currency,
        sender_location=sender_location,
        receiver_location=receiver_location,
        payment_type=payment_type,
        is_laundering=is_laundering,
        laundering_type=laundering_type,
        group_by=group_by,
        aggregate=aggregate,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset,
    )
    result = _get_engine().search_transactions(params)
    return result.model_dump()


def get_high_value_transactions(
    min_amount: float = 10_000.0,
    start_date: str | None = None,
    end_date: str | None = None,
    payment_currency: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """Find high-value transactions above a configurable amount threshold.

    Best suited for queries about "large", "big", or "high-value" transactions.
    The default threshold (10,000) corresponds to the standard AML Currency
    Transaction Report (CTR) filing requirement.

    Returns a dict with total_count, limit, offset, and results (descending by amount).
    """
    params = HighValueParams(
        min_amount=min_amount,
        start_date=start_date,
        end_date=end_date,
        payment_currency=payment_currency,
        limit=limit,
    )
    result = _get_engine().get_high_value_transactions(params)
    return result.model_dump()


def get_suspicious_patterns(
    min_amount: float = 5_000.0,
    max_amount: float | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    sender_location: str | None = None,
    receiver_location: str | None = None,
    payment_currency: str | None = None,
    laundering_type: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """Analyse transactions flagged as suspicious money-laundering activity.

    Best suited for queries about "suspicious", "flagged", or "laundering"
    transactions. Only returns transactions where is_laundering == 1.
    Supports filtering by high-risk country corridors, currencies, and
    specific laundering techniques (e.g. Structuring, Smurfing, Trade-based).

    Returns a dict with total_count, limit, offset, and results (descending by amount).
    """
    params = SuspiciousPatternParams(
        min_amount=min_amount,
        max_amount=max_amount,
        start_date=start_date,
        end_date=end_date,
        sender_location=sender_location,
        receiver_location=receiver_location,
        payment_currency=payment_currency,
        laundering_type=laundering_type,
        limit=limit,
    )
    result = _get_engine().get_suspicious_patterns(params)
    return result.model_dump()


def get_summary_statistics(
    group_by: list[str],
    aggregate: str = "count",
    aggregate_column: str = "Amount",
    start_date: str | None = None,
    end_date: str | None = None,
    is_laundering: int | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Compute aggregated statistics grouped by one or more dimensions.

    Best suited for "how many", "total volume", "average amount" questions
    grouped by currency, location, date, payment type, or laundering status.
    Examples:
    - "How many transactions per currency?" -> group_by=['Payment_currency']
    - "Total volume by sender location and currency?" -> group_by=['Sender_bank_location', 'Payment_currency']
    - "Average transaction by payment type?" -> aggregate='avg', group_by=['Payment_type']

    Returns a dict with rows (one per group) and returned_count.
    """
    params = SummaryParams(
        group_by=group_by,
        aggregate=aggregate,
        aggregate_column=aggregate_column,
        start_date=start_date,
        end_date=end_date,
        is_laundering=is_laundering,
        limit=limit,
    )
    result = _get_engine().get_summary_statistics(params)
    return result.model_dump()


def run_sql_query(
    sql: str,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Execute a read-only SQL SELECT query directly against the AML dataset.

    Use this tool for complex analytical questions that cannot be expressed
    using the structured ``search_transactions`` tool. Examples:
    - Window functions (RANK, LAG, LEAD, ROW_NUMBER over partitions)
    - Complex conditional logic (CASE WHEN with multiple conditions)
    - Correlated subqueries or CTEs (WITH ... AS)
    - Finding accounts with patterns like "more than N transactions in M days"
    - Ranking accounts by total volume across specific corridors

    **Write SQL queries against the ``transactions`` view** which has all
    dataset columns (see schema below). Only ``SELECT`` statements are
    allowed. A ``LIMIT`` clause is automatically enforced.

    **Dataset columns:**
    - Time (TIME), Date (DATE), Sender_account (INT), Receiver_account (INT)
    - Amount (FLOAT), Payment_currency (TEXT), Received_currency (TEXT)
    - Sender_bank_location (TEXT), Receiver_bank_location (TEXT)
    - Payment_type (TEXT), Is_laundering (INT 0/1), Laundering_type (TEXT)

    Returns a list of row dicts (column_name -> value).
    """
    params = SqlQueryParams(sql=sql, limit=limit)
    return _get_engine().execute_sql(params)


# ---------------------------------------------------------------------------
# Tool registry  –  export this list so an agent can bind it
# ---------------------------------------------------------------------------

TOOLS: list[StructuredTool] = [
    StructuredTool.from_function(
        name="search_transactions",
        func=search_transactions,
        description=(
            "Search for financial transactions using any combination of filters "
            "(date, time, amount, currency, location, account, payment type, "
            "laundering status). Supports grouping, aggregation, sorting, and "
            "pagination. The default tool for most transaction queries."
        ),
        args_schema=SearchParams,
    ),
    StructuredTool.from_function(
        name="get_high_value_transactions",
        func=get_high_value_transactions,
        description=(
            "Find transactions above a configurable amount threshold. "
            "Default threshold is $10,000 (standard AML reporting requirement). "
            "Results are sorted by amount descending. Use when the user asks "
            "about 'large', 'big', or 'high-value' transactions."
        ),
        args_schema=HighValueParams,
    ),
    StructuredTool.from_function(
        name="get_suspicious_patterns",
        func=get_suspicious_patterns,
        description=(
            "Analyse transactions flagged as suspicious money laundering "
            "(is_laundering = 1). Filter by amount, location corridor, "
            "currency, or laundering technique. Use when the user asks about "
            "'suspicious', 'flagged', 'laundering', or 'AML' transactions."
        ),
        args_schema=SuspiciousPatternParams,
    ),
    StructuredTool.from_function(
        name="get_summary_statistics",
        func=get_summary_statistics,
        description=(
            "Compute aggregated statistics (count, sum, avg) grouped by "
            "one or more dimensions like currency, location, date, or "
            "payment type. Use for 'how many', 'total volume', 'average "
            "amount' questions."
        ),
        args_schema=SummaryParams,
    ),
    StructuredTool.from_function(
        name="run_sql_query",
        func=run_sql_query,
        description=(
            "Execute a read-only SQL SELECT query against the AML dataset. "
            "Use this for complex analysis that the structured tools cannot "
            "handle: window functions, CTEs, subqueries, multi-step filtering, "
            "conditional logic. Only SELECT statements are allowed. The dataset "
            f"schema is:\n{get_schema_markdown()}"
        ),
        args_schema=SqlQueryParams,
    ),
]

__all__ = [
    "TOOLS",
    "search_transactions",
    "get_high_value_transactions",
    "get_suspicious_patterns",
    "get_summary_statistics",
    "run_sql_query",
]
