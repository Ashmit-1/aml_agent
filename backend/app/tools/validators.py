"""
Column-name validation for AML transaction analysis tools.

Provides the whitelist of known CSV columns and a validation helper
to prevent SQL injection via dynamic column references (GROUP BY, ORDER BY).
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Known CSV columns (used for SQL injection prevention)
# ---------------------------------------------------------------------------

KNOWN_COLUMNS: frozenset[str] = frozenset({
    "Time",
    "Date",
    "Sender_account",
    "Receiver_account",
    "Amount",
    "Payment_currency",
    "Received_currency",
    "Sender_bank_location",
    "Receiver_bank_location",
    "Payment_type",
    "Is_laundering",
    "Laundering_type",
})


def validate_columns(names: list[str]) -> None:
    """Raise ValueError if any column name is not in KNOWN_COLUMNS."""
    for name in names:
        if name not in KNOWN_COLUMNS:
            raise ValueError(
                f"Unknown column '{name}'. "
                f"Valid columns: {sorted(KNOWN_COLUMNS)}"
            )


def validate_aggregate_column(name: str) -> None:
    """Raise ValueError if the aggregation column is invalid."""
    if name not in KNOWN_COLUMNS:
        raise ValueError(
            f"Unknown column '{name}' for aggregation. "
            f"Valid columns: {sorted(KNOWN_COLUMNS)}"
        )


# Re-export for convenience
__all__: list[str] = [
    "KNOWN_COLUMNS",
    "validate_columns",
    "validate_aggregate_column",
]
