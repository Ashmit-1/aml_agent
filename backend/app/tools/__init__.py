"""
AML Transaction Analysis Tools.

This module provides tools for querying the SAML-D dataset (9.5M+ rows)
using DuckDB for efficient, parameterized SQL queries directly on the CSV,
plus ML model tools for running the AML detection pipeline.

Usage::

    from app.tools.tool_definitions import TOOLS

    # Bind TOOLS to a LangChain agent
    agent = create_openai_functions_agent(llm, TOOLS, prompt)
"""

from app.tools.engine import QueryEngine
from app.tools.ml_adapter import (
    CSV_PATH as AML_CSV_PATH,
    generate_aml_prompt,
    get_flagged_explanation,
    investigate_account,
    run_aml_analysis,
)
from app.tools.models import (
    AccountInvestigationParams,
    AMLPromptParams,
    FlaggedExplanationParams,
    HighValueParams,
    MLAnalysisParams,
    PaginatedResult,
    SearchParams,
    SqlQueryParams,
    SummaryParams,
    SummaryResult,
    SuspiciousPatternParams,
    Transaction,
)
from app.tools.tool_definitions import (
    TOOLS,
    get_high_value_transactions,
    get_suspicious_patterns,
    get_summary_statistics,
    run_python_code,
    run_sql_query,
    search_transactions,
)
from app.tools.sandbox import run_code
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
    # ML Model parameters
    "MLAnalysisParams",
    "AccountInvestigationParams",
    "FlaggedExplanationParams",
    "AMLPromptParams",
    # Engine
    "QueryEngine",
    # LangChain-compatible tool definitions
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
    "AML_CSV_PATH",
    # Sandbox
    "run_code",
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
