"""
ML Model Adapter — bridges the ML pipeline (app/data/src/tools/) with the
LLM-facing tool system (app/tools/).

Provides singleton-cached AMLDetector + DataFrame, and thin wrapper functions
that call the ML tools and return JSON-serializable dicts.

Usage by tool_definitions.py::

    from app.tools.ml_adapter import (
        run_aml_analysis,
        investigate_account,
        get_flagged_explanation,
        generate_aml_prompt,
    )
"""

from __future__ import annotations

import os
import sys
from typing import Any

import pandas as pd

# ---------------------------------------------------------------------------
# Paths — resolve relative to THIS file: app/tools/ml_adapter.py
# CSV is at: app/data/SAML-D.csv
# ---------------------------------------------------------------------------
_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(_MODULE_DIR, "..", "data", "SAML-D.csv")

# ---------------------------------------------------------------------------
# Cached singletons (lazy-loaded on first use)
# ---------------------------------------------------------------------------
_detector: Any = None
_dataframe: pd.DataFrame | None = None


def _get_dataframe() -> pd.DataFrame:
    """Load and cache the full dataset as a pandas DataFrame."""
    global _dataframe
    if _dataframe is None:
        if not os.path.isfile(CSV_PATH):
            raise FileNotFoundError(
                f"SAML-D dataset not found at {CSV_PATH}. "
                "Ensure app/data/SAML-D.csv exists."
            )
        _dataframe = pd.read_csv(CSV_PATH)
    return _dataframe


def _get_detector() -> Any:
    """Initialize and cache the AMLDetector singleton."""
    global _detector
    if _detector is None:
        from app.data.src.tools.inference import AMLDetector

        _detector = AMLDetector()
    return _detector


def _resolve_csv_path() -> str:
    """Return the resolved absolute CSV path (for error messages)."""
    return os.path.abspath(CSV_PATH)


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------

_SKIP_COLS = {"__target__"}


def _df_to_records(df: pd.DataFrame, max_rows: int = 200) -> list[dict[str, Any]]:
    """Convert a DataFrame to a JSON-safe list of dicts, limited to *max_rows*."""
    df = df.drop(columns=[c for c in _SKIP_COLS if c in df.columns], errors="ignore")
    records = df.head(max_rows).to_dict(orient="records")

    # Convert numpy types to native Python types for JSON serialization
    cleaned: list[dict[str, Any]] = []
    for rec in records:
        clean: dict[str, Any] = {}
        for k, v in rec.items():
            if isinstance(v, (pd.Timestamp, pd.Timedelta)):
                v = str(v)
            elif hasattr(v, "item"):  # numpy scalars (np.int64, np.float64, etc.)
                v = v.item()
            elif isinstance(v, float) and (pd.isna(v) or pd.isnull(v)):
                v = None
            elif isinstance(v, (dict, list)):
                v = str(v)
            clean[str(k)] = v
        cleaned.append(clean)
    return cleaned


def _summarize_flagged(results: pd.DataFrame) -> dict[str, Any]:
    """Produce a summary dict from a scored DataFrame."""
    flagged = results[results["is_suspicious"] == 1]
    total = len(results)
    n_flagged = len(flagged)

    pattern_breakdown: dict[str, int] = {}
    if n_flagged > 0:
        pattern_breakdown = (
            flagged["aml_pattern"].value_counts().to_dict()
        )

    risk_breakdown: dict[str, int] = {}
    if "risk_level" in flagged.columns:
        risk_breakdown = (
            flagged["risk_level"].value_counts().to_dict()
        )

    return {
        "total_transactions": total,
        "flagged_count": n_flagged,
        "flagged_pct": round(100 * n_flagged / total, 2) if total > 0 else 0.0,
        "pattern_breakdown": pattern_breakdown,
        "risk_breakdown": risk_breakdown,
    }


# ---------------------------------------------------------------------------
# Public tool functions  (called by tool_definitions.py)
# ---------------------------------------------------------------------------


def run_aml_analysis(
    max_flagged_results: int = 50,
    min_risk_level: str = "low",
) -> dict[str, Any]:
    """
    Run the full ML-based AML detection pipeline on the dataset.

    Flags suspicious transactions, classifies risk levels, traces evidence,
    and generates explanations.

    Parameters
    ----------
    max_flagged_results:
        Maximum number of flagged transaction records to return (1–500).
        Default 50.
    min_risk_level:
        Minimum risk level to include in results. One of ``"low"``, ``"medium"``,
        or ``"high"``. Default ``"low"`` (includes all flagged).
        - ``"low"`` → all flagged transactions
        - ``"medium"`` → only medium and high severity
        - ``"high"`` → only high severity

    Returns
    -------
    dict with keys:
        success (bool)
        summary (dict): total_transactions, flagged_count, flagged_pct,
                        pattern_breakdown, risk_breakdown
        flagged_transactions (list): top flagged rows with explanations
        total_returned (int): how many rows are in flagged_transactions
        csv_path (str): path to the dataset used
        error (str or None)
    """
    try:
        df = _get_dataframe()
        detector = _get_detector()

        # Run full pipeline: score → risk → evidence → explanation
        results = detector.analyze(df)

        flagged = results[results["is_suspicious"] == 1].copy()

        # Filter by risk level
        if min_risk_level == "high":
            flagged = flagged[flagged["risk_level"] == "high"]
        elif min_risk_level == "medium":
            flagged = flagged[flagged["risk_level"].isin(["medium", "high"])]

        # Sort by severity descending
        if "severity_score" in flagged.columns:
            flagged = flagged.sort_values("severity_score", ascending=False)

        summary = _summarize_flagged(results)
        # Override the summary counts with post-filter values
        summary["returned_flagged_count"] = len(flagged)

        records = _df_to_records(flagged, max_rows=max_flagged_results)

        return {
            "success": True,
            "summary": summary,
            "flagged_transactions": records,
            "total_returned": len(records),
            "csv_path": _resolve_csv_path(),
            "error": None,
        }

    except Exception as exc:
        return {
            "success": False,
            "summary": {},
            "flagged_transactions": [],
            "total_returned": 0,
            "csv_path": _resolve_csv_path(),
            "error": f"{type(exc).__name__}: {exc}",
        }


def investigate_account(
    account_id: int,
) -> dict[str, Any]:
    """
    Analyze a specific account for suspicious activity.

    Scores all transactions involving the account, classifies risk,
    and provides a summary verdict.

    Parameters
    ----------
    account_id:
        The numerical account identifier to investigate (e.g. 4521).

    Returns
    -------
    dict with keys:
        success (bool)
        verdict (str): ``"suspicious"`` or ``"clean"``
        risk_level (str): low / medium / high
        escalation (str): monitor / review / report
        severity_score (float): 0–100
        flagged_txns (int): number of flagged transactions for this account
        total_txns (int): total transactions for this account
        pct_flagged (float or None): percentage of flagged transactions
        dominant_pattern (str or None): most common AML pattern
        total_amount_involved (float or None): sum of flagged amounts
        flagged_transactions (list): the flagged transaction records
        error (str or None)
    """
    try:
        df = _get_dataframe()
        detector = _get_detector()

        from app.data.src.tools.risk_classifier import (
            account_risk_summary,
            classify_risk,
        )
        from app.data.src.tools.explainer import attach_evidence

        # Get all transactions for this account
        mask = (df["Sender_account"] == account_id) | (
            df["Receiver_account"] == account_id
        )
        account_txns = df[mask]
        if len(account_txns) == 0:
            return {
                "success": False,
                "verdict": "not_found",
                "risk_level": None,
                "escalation": None,
                "severity_score": 0.0,
                "flagged_txns": 0,
                "total_txns": 0,
                "pct_flagged": None,
                "dominant_pattern": None,
                "total_amount_involved": None,
                "flagged_transactions": [],
                "error": f"No transactions found for account {account_id}.",
            }

        # Score in full context
        scored = detector.predict(account_txns, reference=df, include_features=True)
        scored = classify_risk(scored)
        scored = attach_evidence(scored, df)

        summary = account_risk_summary(scored)

        # Get flagged transaction records
        flagged = scored[scored["is_suspicious"] == 1]
        flagged_records = _df_to_records(flagged) if len(flagged) > 0 else []

        return {
            "success": True,
            "verdict": summary.get("verdict", "clean"),
            "risk_level": summary.get("risk_level", "low"),
            "escalation": summary.get("escalation", "monitor"),
            "severity_score": summary.get("severity_score", 0.0),
            "flagged_txns": summary.get("flagged_txns", 0),
            "total_txns": summary.get("total_txns", 0),
            "pct_flagged": summary.get("pct_flagged"),
            "dominant_pattern": summary.get("dominant_pattern"),
            "total_amount_involved": summary.get("total_amount_involved"),
            "flagged_transactions": flagged_records,
            "error": None,
        }

    except Exception as exc:
        return {
            "success": False,
            "verdict": "error",
            "risk_level": None,
            "escalation": None,
            "severity_score": 0.0,
            "flagged_txns": 0,
            "total_txns": 0,
            "pct_flagged": None,
            "dominant_pattern": None,
            "total_amount_involved": None,
            "flagged_transactions": [],
            "error": f"{type(exc).__name__}: {exc}",
        }


def get_flagged_explanation(
    sender_account: int,
    receiver_account: int,
    amount: float,
) -> dict[str, Any]:
    """
    Get the human-readable explanation for why a specific transaction was flagged.

    Use this after ``run_aml_analysis`` to dive deeper into why a specific
    transaction was marked suspicious. Finds the closest matching transaction
    in the scored dataset.

    Parameters
    ----------
    sender_account:
        The sender account numerical identifier.
    receiver_account:
        The receiver account numerical identifier.
    amount:
        The transaction amount (used for exact matching).

    Returns
    -------
    dict with keys:
        success (bool)
        found (bool): whether a matching flagged transaction was found
        explanation (str or None): human-readable explanation
        pattern (str or None): AML pattern assigned
        suspicion_score (float or None): model confidence 0–1
        risk_level (str or None): low / medium / high
        escalation (str or None): monitor / review / report
        severity_score (float or None): 0–100
        evidence_count (int or None): how many related transactions
        evidence_account (int or None): account the evidence centers on
        evidence_side (str or None): sender / receiver / both
        error (str or None)
    """
    try:
        df = _get_dataframe()
        detector = _get_detector()

        from app.data.src.tools.risk_classifier import classify_risk
        from app.data.src.tools.explainer import attach_evidence

        # Score with full context
        results = detector.predict(df, include_features=True)
        results = classify_risk(results)
        results = attach_evidence(results, df)

        # Find the specific transaction
        mask = (
            (results["Sender_account"] == sender_account)
            & (results["Receiver_account"] == receiver_account)
            & (results["Amount"] == amount)
        )
        match = results[mask]
        if len(match) == 0:
            return {
                "success": True,
                "found": False,
                "explanation": None,
                "pattern": None,
                "suspicion_score": None,
                "risk_level": None,
                "escalation": None,
                "severity_score": None,
                "evidence_count": None,
                "evidence_account": None,
                "evidence_side": None,
                "error": (
                    f"No matching transaction found for "
                    f"Sender={sender_account}, Receiver={receiver_account}, "
                    f"Amount={amount}."
                ),
            }

        row = match.iloc[0]
        return {
            "success": True,
            "found": True,
            "is_suspicious": int(row.get("is_suspicious", 0)),
            "explanation": row.get("explanation"),
            "pattern": row.get("aml_pattern"),
            "suspicion_score": (
                float(row["suspicion_score"])
                if pd.notna(row.get("suspicion_score"))
                else None
            ),
            "risk_level": row.get("risk_level"),
            "escalation": row.get("escalation"),
            "severity_score": (
                float(row["severity_score"])
                if pd.notna(row.get("severity_score"))
                else None
            ),
            "evidence_count": (
                int(row["responsible_count"])
                if pd.notna(row.get("responsible_count"))
                else 0
            ),
            "evidence_account": (
                int(row["evidence_account"])
                if pd.notna(row.get("evidence_account"))
                else None
            ),
            "evidence_side": row.get("evidence_side"),
            "error": None,
        }

    except Exception as exc:
        return {
            "success": False,
            "found": False,
            "explanation": None,
            "pattern": None,
            "suspicion_score": None,
            "risk_level": None,
            "escalation": None,
            "severity_score": None,
            "evidence_count": None,
            "evidence_account": None,
            "evidence_side": None,
            "error": f"{type(exc).__name__}: {exc}",
        }


def generate_aml_prompt(
    sender_account: int,
    receiver_account: int,
    amount: float,
) -> dict[str, Any]:
    """
    Generate a structured LLM prompt explaining why a transaction was flagged.

    The prompt is ready to send to any LLM. It includes the pattern definition,
    relevant feature values with baseline comparisons, and analyst instructions.

    Use this after ``run_aml_analysis`` to get a detailed narrative explanation
    from an external LLM.

    Parameters
    ----------
    sender_account:
        The sender account numerical identifier.
    receiver_account:
        The receiver account numerical identifier.
    amount:
        The transaction amount (used for exact matching).

    Returns
    -------
    dict with keys:
        success (bool)
        found (bool): whether a matching flagged transaction was found
        prompt (str or None): the LLM prompt string
        fact_sheet (dict or None): the structured fact sheet
        error (str or None)
    """
    try:
        df = _get_dataframe()
        detector = _get_detector()

        from app.data.src.tools.risk_classifier import classify_risk
        from app.data.src.tools.explainer import attach_evidence
        from app.data.src.tools.llm_explainer import (
            build_fact_sheet,
            build_prompt,
        )

        # Score with full context
        results = detector.predict(df, include_features=True)
        results = classify_risk(results)
        results = attach_evidence(results, df)

        # Find the specific transaction
        mask = (
            (results["Sender_account"] == sender_account)
            & (results["Receiver_account"] == receiver_account)
            & (results["Amount"] == amount)
        )
        match = results[mask]
        if len(match) == 0:
            return {
                "success": True,
                "found": False,
                "prompt": None,
                "fact_sheet": None,
                "error": (
                    f"No matching flagged transaction found for "
                    f"Sender={sender_account}, Receiver={receiver_account}, "
                    f"Amount={amount}."
                ),
            }

        row = match.iloc[0]
        prompt_text = build_prompt(row)
        fact_sheet = build_fact_sheet(row)

        return {
            "success": True,
            "found": True,
            "prompt": prompt_text,
            "fact_sheet": fact_sheet,
            "error": None,
        }

    except Exception as exc:
        return {
            "success": False,
            "found": False,
            "prompt": None,
            "fact_sheet": None,
            "error": f"{type(exc).__name__}: {exc}",
        }


__all__ = [
    "run_aml_analysis",
    "investigate_account",
    "get_flagged_explanation",
    "generate_aml_prompt",
    "CSV_PATH",
]
