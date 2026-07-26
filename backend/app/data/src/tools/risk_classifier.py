"""
Risk Classification Tool
────────────────────────
Converts a raw suspicion flag into a graded severity — HOW bad / HOW big.

Combines two axes:
  1. CONFIDENCE  — the ML suspicion_score (0-1): how sure we are it's suspicious
  2. MAGNITUDE   — how large the laundering footprint is (money moved, #txns,
                   #linked accounts, cross-border, high-risk geography)

Output per row:
  severity_score : 0-100
  risk_level     : low | medium | high
  escalation     : monitor | review | report
"""
import numpy as np
import pandas as pd

# Escalation mapping per risk level
ESCALATION = {'low': 'monitor', 'medium': 'review', 'high': 'report'}


def _normalize(series, cap):
    """Scale a value to 0-1, capped."""
    return np.clip(series / cap, 0, 1)


def classify_risk(scored_df):
    """
    Args:
        scored_df: output of AMLDetector.predict(), must contain
                   is_suspicious, suspicion_score, and the engineered feature
                   columns (Amount, sender_total_amount, sender_tx_count, etc.)
    Returns:
        DataFrame with added: severity_score, risk_level, escalation
    """
    df = scored_df.copy()

    # ── Magnitude signals (only meaningful for flagged rows) ──────────────────
    amount = df.get('Amount', pd.Series(0, index=df.index)).astype(float)
    total_moved = df.get('sender_total_amount', amount)
    tx_count = df.get('sender_tx_count', pd.Series(1, index=df.index))
    cross_border = df.get('is_cross_border', pd.Series(0, index=df.index)).fillna(0)
    high_risk = df.get('is_high_risk_receiver', pd.Series(0, index=df.index)).fillna(0)

    # Entanglement — DIRECTION-AWARE: how many distinct accounts this one touches.
    #   receiver-side patterns (many → one): count unique SENDERS into the receiver
    #   sender-side patterns  (one → many): count unique RECEIVERS the sender fans out to
    #   take the max so whichever direction is the laundering shape drives the signal.
    senders_in = df.get('receiver_unique_senders', pd.Series(1, index=df.index)).fillna(1)
    receivers_out = df.get('sender_unique_receivers', pd.Series(1, index=df.index)).fillna(1)
    linked = pd.concat([senders_in, receivers_out], axis=1).max(axis=1)

    # Normalize each to 0-1 (caps chosen from dataset scale)
    m_amount = _normalize(amount, 100_000)
    m_total = _normalize(total_moved, 2_000_000)
    m_count = _normalize(tx_count, 50)
    m_linked = _normalize(linked, 40)

    # Magnitude = weighted blend of footprint signals
    magnitude = (
        0.30 * m_total +
        0.25 * m_amount +
        0.20 * m_count +
        0.15 * m_linked +
        0.05 * cross_border +
        0.05 * high_risk
    )

    confidence = df.get('suspicion_score', pd.Series(0, index=df.index)).astype(float)

    # Severity = confidence gates it, magnitude scales it
    #   an unconfident flag can't be high severity;
    #   a confident flag with huge magnitude → max severity
    severity = confidence * (0.5 + 0.5 * magnitude) * 100
    severity = np.where(df['is_suspicious'] == 1, severity, 0)
    df['severity_score'] = np.round(severity, 1)

    # ── Bucket into levels ────────────────────────────────────────────────────
    def level(s, flagged):
        if flagged == 0:
            return 'low'
        if s >= 65:
            return 'high'
        if s >= 35:
            return 'medium'
        return 'low'

    df['risk_level'] = [level(s, f) for s, f in zip(df['severity_score'], df['is_suspicious'])]
    df['escalation'] = df['risk_level'].map(ESCALATION)
    return df


def account_risk_summary(scored_account_df):
    """
    Roll up a single account's transactions into ONE verdict.
    Use after predict_account() to answer 'how bad is this user?'.
    """
    flagged = scored_account_df[scored_account_df['is_suspicious'] == 1]
    n_total = len(scored_account_df)
    n_flagged = len(flagged)

    if n_flagged == 0:
        return {
            'verdict': 'clean',
            'risk_level': 'low',
            'escalation': 'monitor',
            'severity_score': 0.0,
            'flagged_txns': 0,
            'total_txns': n_total,
            'dominant_pattern': None,
        }

    # Account severity = the worst + weight by how pervasive it is
    peak = flagged['severity_score'].max()
    pervasiveness = n_flagged / n_total
    account_severity = round(peak * (0.7 + 0.3 * pervasiveness), 1)
    level = 'high' if account_severity >= 65 else 'medium' if account_severity >= 35 else 'low'

    return {
        'verdict': 'suspicious',
        'risk_level': level,
        'escalation': ESCALATION[level],
        'severity_score': account_severity,
        'flagged_txns': n_flagged,
        'total_txns': n_total,
        'pct_flagged': round(100 * pervasiveness, 1),
        'dominant_pattern': flagged['aml_pattern'].mode().iloc[0],
        'total_amount_involved': round(flagged['Amount'].sum(), 2),
    }
