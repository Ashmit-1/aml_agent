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
from app.tools.ml_adapter import (
    generate_aml_prompt as _generate_aml_prompt,
    get_flagged_explanation as _get_flagged_explanation,
    investigate_account as _investigate_account,
    run_aml_analysis as _run_aml_analysis,
)
from app.tools.models import (
    AccountInvestigationParams,
    AMLPromptParams,
    CodeSandboxParams,
    FlaggedExplanationParams,
    HighValueParams,
    MLAnalysisParams,
    SearchParams,
    SqlQueryParams,
    SummaryParams,
    SuspiciousPatternParams,
)
from app.tools.sandbox import run_code
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


def close_engine() -> None:
    """Explicitly close the singleton engine connection (if open)."""
    global _engine
    if _engine is not None:
        _engine.close()
        _engine = None


import atexit
atexit.register(close_engine)


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


def run_python_code(
    code: str,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    """Write and execute Python code in a secure sandboxed environment.

    Use this tool when the prebuilt tools cannot answer the user's query.
    Examples of what you can do with code:
    - Multi-step data analysis: query data via engine, then process it
    - Statistical computations (mean, median, std, correlations, distributions)
    - Advanced filtering and pattern detection beyond SQL capabilities
    - Data transformation, normalization, feature engineering
    - Finding accounts with specific behavioural patterns

    **Available in the sandbox:**
    - ``engine``: a ``QueryEngine`` instance to query the AML dataset.
      Call ``engine.search_transactions(...)`` or ``engine.execute_sql(...)``
      to get data as dicts. Then process with pandas/numpy.
    - ``pd``: ``pandas`` for DataFrames, groupby, aggregations, merging
    - ``np``: ``numpy`` for numerical operations
    - ``json``, ``math``, ``re``, ``collections``, ``itertools``,
      ``functools``, ``statistics``, ``random``, ``datetime``, etc.

    **Restrictions:**
    - No file I/O (``open``, file writes)
    - No network access (``subprocess``, ``socket``, ``requests``, ``os``)
    - No system commands (``os.system``, ``subprocess``)
    - Maximum execution time: 120 seconds
    - Output truncated after 50,000 characters

    **How to return results:**
    Assign your answer to a variable named ``result`` at the end of your
    code. The ``result`` value will be returned to the user. Use ``print()``
    for intermediate debugging output.

    Returns a dict with: success (bool), stdout (str), result (any),
    error (str or null), truncated (bool).
    """

    return run_code(
        code=code,
        timeout_seconds=timeout_seconds,
        query_engine=_get_engine(),
    )


# ── ML Model tools ────────────────────────────────────────────────────────────


def run_aml_analysis(
    max_flagged_results: int = 50,
    min_risk_level: str = "low",
) -> dict[str, Any]:
    """Run the full ML-based AML detection pipeline on the transaction dataset.

    Flags suspicious transactions using trained ML models (binary classifier +
    pattern classifier), grades severity, traces evidence, and generates
    human-readable explanations. Best suited for:
    - "Analyse this dataset for suspicious activity"
    - "Flag suspicious transactions for review"
    - "Run the AML model on the transaction data"

    Returns a summary with total/flagged counts, pattern and risk breakdowns,
    and a list of the top flagged transactions with explanations.

    The pipeline runs:
        1. Feature engineering (31 account-level features)
        2. Model 1: binary classifier → is_suspicious (0/1) + suspicion_score
        3. Model 2: pattern classifier → aml_pattern (Structuring, Smurfing, etc.)
        4. Risk classifier → severity_score (0-100), risk_level, escalation
        5. Evidence tracer → responsible_count, evidence_account
        6. Explanation generator → human-readable explanation

    Returns a dict with: success (bool), summary (dict), flagged_transactions
    (list of records), total_returned (int), csv_path (str), error (str or null).
    """
    return _run_aml_analysis(
        max_flagged_results=max_flagged_results,
        min_risk_level=min_risk_level,
    )


def investigate_account(
    account_id: int,
) -> dict[str, Any]:
    """Analyse a specific account for suspicious activity.

    Scores all transactions involving the account using the full ML pipeline,
    with the entire dataset as context (ensures graph features are accurate).
    Returns a verdict (suspicious/clean), risk level, severity score, pattern
    breakdown, and flagged transaction details.

    Best suited for:
    - "Is account 4521 suspicious?"
    - "What is the risk profile of account 8724731955?"
    - "Check account 2769355426 for money laundering"

    Returns a dict with: success (bool), verdict (str), risk_level (str),
    escalation (str), severity_score (float), flagged_txns (int),
    total_txns (int), pct_flagged (float or null), dominant_pattern (str or null),
    total_amount_involved (float or null), flagged_transactions (list),
    error (str or null).
    """
    return _investigate_account(
        account_id=account_id,
    )


def get_flagged_explanation(
    sender_account: int,
    receiver_account: int,
    amount: float,
) -> dict[str, Any]:
    """Get the human-readable explanation for a specific flagged transaction.

    Finds the matching transaction in the scored dataset and returns the
    explanation, pattern, risk, and evidence details.

    Best suited for:
    - "Why was transaction from X to Y for $Z flagged?"
    - "Explain the flag on this transaction"
    - After running ``run_aml_analysis``, diving deeper into a specific result

    Returns a dict with: success (bool), found (bool), is_suspicious (int),
    explanation (str or null), pattern (str or null), suspicion_score (float
    or null), risk_level (str or null), escalation (str or null),
    severity_score (float or null), evidence_count (int or null),
    evidence_account (int or null), evidence_side (str or null),
    error (str or null).
    """
    return _get_flagged_explanation(
        sender_account=sender_account,
        receiver_account=receiver_account,
        amount=amount,
    )


def generate_aml_prompt(
    sender_account: int,
    receiver_account: int,
    amount: float,
) -> dict[str, Any]:
    """Generate a structured prompt for an LLM to explain a flagged transaction.

    Builds a complete, ready-to-send prompt string that includes the pattern
    definition, a fact sheet with baseline comparisons (e.g. "32 unique senders
    vs normal avg 5.5 → 5.8x above normal"), and analyst instructions.

    Best suited for:
    - "Generate an LLM prompt explaining this flagged transaction"
    - "Why does the model think this is Structuring? Give me a narrative"
    - After ``run_aml_analysis``, generating a detailed narrative for review

    Returns a dict with: success (bool), found (bool), prompt (str or null),
    fact_sheet (dict or null), error (str or null).
    """
    return _generate_aml_prompt(
        sender_account=sender_account,
        receiver_account=receiver_account,
        amount=amount,
    )


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
    StructuredTool.from_function(
        name="run_python_code",
        func=run_python_code,
        description=(
            "Write and execute Python code in a sandboxed environment. "
            "Use this when the prebuilt tools cannot answer the query. "
            "Has access to: engine (QueryEngine), pd (pandas), np (numpy), "
            "and standard library modules. No file/network/system access. "
            "Set `result` variable to return a value. Auto-kills on timeout."
        ),
        args_schema=CodeSandboxParams,
    ),
    # ── ML Model tools ─────────────────────────────────────────────────
    StructuredTool.from_function(
        name="run_aml_analysis",
        func=run_aml_analysis,
        description=(
            "Run the full ML-based AML detection pipeline on the transaction "
            "dataset. Flags suspicious transactions (Model 1), classifies the "
            "money-laundering pattern (Model 2), grades severity, traces evidence, "
            "and generates human-readable explanations. Returns summary stats "
            "(total/flagged counts, pattern breakdown, risk breakdown) and the "
            "top flagged transaction records. Use this for 'analyse this dataset "
            "for suspicious activity' or 'flag suspicious transactions' queries."
        ),
        args_schema=MLAnalysisParams,
    ),
    StructuredTool.from_function(
        name="investigate_account",
        func=investigate_account,
        description=(
            "Analyse a specific account for suspicious money-laundering activity. "
            "Scores all transactions involving that account using the full ML "
            "pipeline with the entire dataset as context. Returns a verdict "
            "(suspicious/clean), risk level, severity score, dominant pattern, "
            "and flagged transaction details. Use this for 'is account X "
            "suspicious?' or 'check account X for money laundering' queries."
        ),
        args_schema=AccountInvestigationParams,
    ),
    StructuredTool.from_function(
        name="get_flagged_explanation",
        func=get_flagged_explanation,
        description=(
            "Get the human-readable explanation for a specific flagged transaction. "
            "Returns why the ML model flagged it, the AML pattern detected, risk "
            "level, evidence count, and which account the evidence centers on. "
            "Use after run_aml_analysis to dive deeper into a specific result. "
            "Provide the sender account, receiver account, and exact amount "
            "to identify the transaction."
        ),
        args_schema=FlaggedExplanationParams,
    ),
    StructuredTool.from_function(
        name="generate_aml_prompt",
        func=generate_aml_prompt,
        description=(
            "Generate a structured, ready-to-send LLM prompt explaining why a "
            "specific transaction was flagged. The prompt includes the AML pattern "
            "definition, a fact sheet with baseline comparisons (feature values "
            "vs normal avg vs pattern-typical avg), and analyst instructions. "
            "Use after run_aml_analysis to get a detailed narrative explanation "
            "from an external LLM. Provide the sender account, receiver account, "
            "and exact amount to identify the transaction."
        ),
        args_schema=AMLPromptParams,
    ),
]

__all__ = [
    "TOOLS",
    "search_transactions",
    "get_high_value_transactions",
    "get_suspicious_patterns",
    "get_summary_statistics",
    "run_sql_query",
    "run_python_code",
    # ML Model tools
    "run_aml_analysis",
    "investigate_account",
    "get_flagged_explanation",
    "generate_aml_prompt",
]
