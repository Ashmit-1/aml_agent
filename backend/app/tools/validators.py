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
    {"name": "Payment_currency", "type": "TEXT", "description": "Name of the payment currency (e.g. 'UK pounds', 'US dollar', 'Euro', 'Swiss franc', 'Yen', 'Dirham')"},
    {"name": "Received_currency", "type": "TEXT", "description": "Name of the currency received (e.g. 'UK pounds', 'US dollar', 'Euro', 'Swiss franc', 'Yen', 'Dirham')"},
    {"name": "Sender_bank_location", "type": "TEXT", "description": "Country name of sender's bank (e.g. 'UK', 'USA', 'France', 'Germany', 'India', 'UAE')"},
    {"name": "Receiver_bank_location", "type": "TEXT", "description": "Country name of receiver's bank (e.g. 'UK', 'USA', 'France', 'Germany', 'India', 'UAE')"},
    {"name": "Payment_type", "type": "TEXT", "description": "Payment method (e.g. ACH, Cash Deposit, Cash Withdrawal, Cheque, Credit card, Cross-border, Debit card)"},
    {"name": "Is_laundering", "type": "INT (0 or 1)", "description": "Money-laundering flag: 0 = legitimate, 1 = flagged suspicious"},
    {"name": "Laundering_type", "type": "TEXT", "description": "Laundering pattern (e.g. Structuring, Smurfing, Behavioural_Change_1, Bipartite, Fan_In, Fan_Out, Scatter-Gather)"},
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


def _strip_sql_comments(sql: str) -> str:
    """Strip leading SQL comments (-- line comments and /* block comments */)."""
    # Remove single-line comments (-- ...) at the start
    while True:
        stripped = sql.lstrip()
        if stripped.startswith("--"):
            # Find end of line
            nl = stripped.find("\n")
            if nl == -1:
                return ""
            sql = stripped[nl + 1 :]
        elif stripped.startswith("/*"):
            end = stripped.find("*/")
            if end == -1:
                return ""
            sql = stripped[end + 2 :]
        else:
            break
    return sql


def validate_sql_select(sql: str) -> str:
    """Validate that *sql* is a read-only SELECT statement.

    Strips leading whitespace, leading SQL comments (``--`` line comments
    and ``/* */`` block comments), and leading ``WITH`` clauses (CTEs)
    before checking that the statement starts with ``SELECT``.

    Also rejects multi-statement SQL (semicolons within the statement).

    Returns the stripped SQL string on success.
    """
    stripped = sql.strip()

    # Strip leading comments
    no_comments = _strip_sql_comments(stripped)
    if not no_comments:
        raise ValueError(
            "Only SELECT queries are allowed. Received a comment-only or empty statement."
        )

    # Strip leading WITH clause (CTEs) – e.g. "WITH foo AS (...) SELECT ..."
    upper = no_comments.upper().lstrip()
    while upper.startswith("WITH "):
        # Find the matching WITH ... SELECT pattern
        # Look for the final SELECT after the CTE definitions
        # Skip past the CTE by finding the SELECT keyword
        # that is not inside parentheses
        depth = 0
        select_pos = -1
        for i, ch in enumerate(no_comments):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            elif depth == 0 and ch.upper() == "S":
                # Check if this is the start of a SELECT keyword
                if no_comments[i:].upper().startswith("SELECT"):
                    select_pos = i
                    break
        if select_pos == -1:
            raise ValueError(
                "Only SELECT queries are allowed. "
                "Found WITH clause without a following SELECT."
            )
        no_comments = no_comments[select_pos:]
        upper = no_comments.upper().lstrip()

    # Now check for SELECT
    if not upper.startswith("SELECT"):
        raise ValueError(
            "Only SELECT queries are allowed. "
            f"Received SQL starting with: {upper.split()[0] if upper else '(empty)'}"
        )

    # Reject multi-statement SQL — walk through and flag semicolons
    # that appear outside of string literals. Handles SQL-standard `''`
    # escape sequences within strings. Trailing semicolons are allowed
    # (they are stripped before the check).
    check_multi = stripped.rstrip().rstrip(";").rstrip()
    in_string: bool = False
    quote_char: str | None = None
    i = 0
    while i < len(check_multi):
        ch = check_multi[i]
        if in_string:
            if ch == quote_char:
                # SQL-standard escaped quote: '' or "" inside strings
                if i + 1 < len(check_multi) and check_multi[i + 1] == quote_char:
                    i += 2
                    continue
                in_string = False
        elif ch in ("'", '"'):
            in_string = True
            quote_char = ch
        elif ch == ";":
            raise ValueError(
                "Multi-statement SQL is not allowed. "
                "A semicolon was found outside a string literal."
            )
        i += 1

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
