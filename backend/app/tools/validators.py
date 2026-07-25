"""
Column-name validation and dataset schema helpers for LLM tool calling.

Provides:
- A whitelist of known CSV columns (prevents SQL injection).
- Validation helpers for column references.
- A ``get_schema_markdown()`` function that returns a human/machine-readable
  dataset schema description for LLM context.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Known CSV columns (used for SQL injection prevention)
# ---------------------------------------------------------------------------

#: Human-readable schema description for LLM tool context.
SCHEMA_DESCRIPTION: str = (
    "The SAML-D (Synthetic Anti-Money Laundering Dataset) contains "
    "~9.5 million financial transactions, each with metadata about the "
    "sender, receiver, amount, currencies, locations, and laundering flags."
)

COLUMN_META: list[dict[str, str]] = [
    {"name": "Time", "type": "TIME (HH:MM:SS)", "description": "Time of the transaction"},
    {"name": "Date", "type": "DATE (YYYY-MM-DD)", "description": "Date of the transaction"},
    {"name": "Sender_account", "type": "INTEGER", "description": "Unique sender account identifier"},
    {"name": "Receiver_account", "type": "INTEGER", "description": "Unique receiver account identifier"},
    {"name": "Amount", "type": "FLOAT", "description": "Transaction amount in payment currency"},
    {"name": "Payment_currency", "type": "TEXT", "description": "Currency code of the payment (e.g. USD, EUR, GBP, JPY, CNY, RUB, CHF)"},
    {"name": "Received_currency", "type": "TEXT", "description": "Currency code received (e.g. USD, EUR, GBP, JPY, CNY, RUB, CHF)"},
    {"name": "Sender_bank_location", "type": "TEXT", "description": "Country code of sender's bank (e.g. US, GB, DE, CN, RU, CH, AE, HK)"},
    {"name": "Receiver_bank_location", "type": "TEXT", "description": "Country code of receiver's bank (e.g. US, GB, DE, CN, RU, CH, AE, HK)"},
    {"name": "Payment_type", "type": "TEXT", "description": "Payment method: Wire Transfer, ACH, Check, Cash, Credit Card, Debit Card, Cryptocurrency, etc."},
    {"name": "Is_laundering", "type": "INT (0 or 1)", "description": "Money-laundering flag: 0 = legitimate, 1 = flagged suspicious"},
    {"name": "Laundering_type", "type": "TEXT", "description": "Laundering pattern: Structuring, Smurfing, Trade-based, Cash smuggling, Real estate, Shell company, etc."},
]

KNOWN_COLUMNS: frozenset[str] = frozenset(col["name"] for col in COLUMN_META)

#: Mapping from column name to a short plain-English description.
COLUMN_DESCRIPTIONS: dict[str, str] = {
    col["name"]: col["description"] for col in COLUMN_META
}

#: Mapping from column name to its DuckDB-compatible type hint.
COLUMN_TYPES: dict[str, str] = {
    col["name"]: col["type"] for col in COLUMN_META
}


def get_schema_markdown() -> str:
    """Return a Markdown table describing the dataset schema.

    This is useful for injecting schema context into an LLM prompt or
    tool description so the model understands the available columns,
    their types, and their meanings.
    """
    lines = [
        SCHEMA_DESCRIPTION,
        "",
        "### Dataset Columns",
        "",
        "| Column | Type | Description |",
        "|--------|------|-------------|",
    ]
    for col in COLUMN_META:
        lines.append(f"| {col['name']} | {col['type']} | {col['description']} |")
    lines.extend([
        "",
        "A DuckDB SQL view called ``transactions`` is registered with all of the",
        "above columns. You can query it with ``SELECT ... FROM transactions ...``",
    ])
    return "\n".join(lines)


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


def validate_sql_select(sql: str) -> str:
    """Validate that *sql* is a read-only SELECT statement.

    Strips leading whitespace, uppercases the keyword check, and raises
    ``ValueError`` if the statement doesn't start with ``SELECT``.

    Returns the stripped SQL string on success.
    """
    stripped = sql.strip()
    # Normalise whitespace for the keyword check
    upper = stripped.upper().lstrip()
    if not upper.startswith("SELECT"):
        raise ValueError(
            "Only SELECT queries are allowed. "
            f"Received SQL starting with: {upper.split()[0] if upper else '(empty)'}"
        )
    return stripped


# Re-export for convenience
__all__ = [
    "SCHEMA_DESCRIPTION",
    "COLUMN_META",
    "KNOWN_COLUMNS",
    "COLUMN_DESCRIPTIONS",
    "COLUMN_TYPES",
    "get_schema_markdown",
    "validate_columns",
    "validate_aggregate_column",
    "validate_sql_select",
]
