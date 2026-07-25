"""
AML Transaction Analysis Tools.

This module provides tools for querying the SAML-D dataset (9.5M+ rows)
using DuckDB for efficient, parameterized SQL queries directly on the CSV.

Usage::

    from app.tools.tool_definitions import TOOLS

    # Bind TOOLS to a LangChain agent
    agent = create_openai_functions_agent(llm, TOOLS, prompt)
"""

from app.tools.engine import QueryEngine
from app.tools.models import (
    HighValueParams,
    PaginatedResult,
    SearchParams,
    SqlQueryParams,
    SummaryParams,
    SummaryResult,
    SuspiciousPatternParams,
    Transaction,
)
from app.tools.tool_definitions import TOOLS, get_suspicious_patterns, get_summary_statistics, run_sql_query, search_transactions
from app.tools.validators import (
    COLUMN_DESCRIPTIONS,
    COLUMN_META,
    COLUMN_TYPES,
    KNOWN_COLUMNS,
    SCHEMA_DESCRIPTION,
    get_schema_markdown,
    validate_columns,
    validate_sql_select,
)

__all__ = [
    # Models
    "SearchParams",
    "HighValueParams",
    "SuspiciousPatternParams",
    "SummaryParams",
    "SqlQueryParams",
    "Transaction",
    "PaginatedResult",
    "SummaryResult",
    # Engine
    "QueryEngine",
    # LangChain-compatible tool definitions
    "TOOLS",
    "search_transactions",
    "get_suspicious_patterns",
    "get_summary_statistics",
    "run_sql_query",
    # Schema helpers
    "KNOWN_COLUMNS",
    "COLUMN_META",
    "COLUMN_DESCRIPTIONS",
    "COLUMN_TYPES",
    "SCHEMA_DESCRIPTION",
    "get_schema_markdown",
    "validate_columns",
    "validate_sql_select",
]
