"""
AML Transaction Analysis Tools.

This module provides tools for querying the SAML-D dataset (9.5M+ rows)
using DuckDB for efficient, parameterized SQL queries directly on the CSV.
"""

from app.tools.models import (
    HighValueParams,
    PaginatedResult,
    SearchParams,
    SummaryParams,
    SummaryResult,
    SuspiciousPatternParams,
    Transaction,
)
from app.tools.engine import QueryEngine
from app.tools.validators import KNOWN_COLUMNS, validate_columns

__all__ = [
    # Input models
    "SearchParams",
    "HighValueParams",
    "SuspiciousPatternParams",
    "SummaryParams",
    # Output models
    "Transaction",
    "PaginatedResult",
    "SummaryResult",
    # Engine
    "QueryEngine",
    # Validation
    "KNOWN_COLUMNS",
    "validate_columns",
]
