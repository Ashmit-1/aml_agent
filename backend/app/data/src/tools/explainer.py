"""
Explanation Component + Evidence Tracer
────────────────────────────────────────
For any flagged transaction, answers two questions:

  1. WHY was it flagged?  → a human-readable explanation tied to the AML pattern
  2. WHAT is the evidence? → the exact set of supporting rows that drove the flag,
                             and how many there are

The evidence is the group of transactions whose aggregation produced the
suspicious feature values. Which group depends on the pattern:

  Sender-side patterns  (Structuring, Fan_Out, Deposit-Send, Cash_Withdrawal,
                         Single_large, Over-Invoicing, Behavioural_Change)
        → all transactions sharing the same Sender_account
  Receiver-side patterns (Smurfing, Fan_In, Bipartite)
        → all transactions sharing the same Receiver_account
  Layering              → both sides (the account acting as a pass-through)
"""
import pandas as pd

SENDER_SIDE = {
    'Structuring', 'Fan_Out', 'Deposit-Send', 'Cash_Withdrawal',
    'Single_large', 'Over-Invoicing', 'Behavioural_Change',
}
RECEIVER_SIDE = {'Smurfing', 'Fan_In', 'Bipartite'}
BOTH_SIDE = {'Layering'}


def get_evidence(row, reference):
    """
    Given one flagged row (a Series or dict) and the full reference DataFrame,
    return the supporting transactions.

    Returns dict:
        responsible_count : how many rows are responsible
        responsible_rows  : the DataFrame of those rows
        evidence_focus    : which account the evidence centers on
        side              : 'sender' | 'receiver' | 'both'
    """
    if isinstance(row, dict):
        row = pd.Series(row)

    pattern = row.get('aml_pattern')
    sender = row['Sender_account']
    receiver = row['Receiver_account']

    if pattern in RECEIVER_SIDE:
        mask = reference['Receiver_account'] == receiver
        focus, side = receiver, 'receiver'
    elif pattern in BOTH_SIDE:
        # the pass-through account is the receiver of this hop
        mask = (reference['Receiver_account'] == receiver) | (reference['Sender_account'] == receiver)
        focus, side = receiver, 'both'
    else:  # sender-side (default)
        mask = reference['Sender_account'] == sender
        focus, side = sender, 'sender'

    rows = reference[mask]
    return {
        'responsible_count': len(rows),
        'responsible_rows': rows,
        'evidence_focus': focus,
        'side': side,
    }


def attach_evidence(scored_df, reference):
    """
    Enrich a scored DataFrame with evidence + explanation COLUMNS, so the whole
    result is one inspectable table. Adds:
        responsible_count : how many rows drove each flag
        evidence_account  : the account the evidence centers on
        evidence_side     : sender | receiver | both
        explanation       : human-readable reason

    Efficient: precomputes per-account group sizes once instead of filtering
    the reference per row.
    """
    df = scored_df.copy()

    # Precompute involvement counts once
    sender_sizes = reference.groupby('Sender_account').size()
    receiver_sizes = reference.groupby('Receiver_account').size()

    counts, accounts, sides, explanations = [], [], [], []
    for _, row in df.iterrows():
        if row.get('is_suspicious', 0) != 1:
            counts.append(0); accounts.append(None); sides.append(None); explanations.append(None)
            continue

        pattern = row.get('aml_pattern')
        sender, receiver = row['Sender_account'], row['Receiver_account']

        if pattern in RECEIVER_SIDE:
            cnt = int(receiver_sizes.get(receiver, 0)); acc, side = receiver, 'receiver'
        elif pattern in BOTH_SIDE:
            cnt = int(receiver_sizes.get(receiver, 0) + sender_sizes.get(receiver, 0))
            acc, side = receiver, 'both'
        else:
            cnt = int(sender_sizes.get(sender, 0)); acc, side = sender, 'sender'

        counts.append(cnt); accounts.append(acc); sides.append(side)
        explanations.append(_pattern_sentence(pattern, row, cnt))

    df['responsible_count'] = counts
    df['evidence_account'] = accounts
    df['evidence_side'] = sides
    df['explanation'] = explanations
    return df


def explain(row, reference=None):
    """
    Build a full explanation for one flagged row.

    Returns dict:
        explanation       : human-readable sentence
        pattern           : the AML pattern
        evidence          : output of get_evidence (if reference given)
        key_signals       : the feature values that justify the flag
    """
    if isinstance(row, dict):
        row = pd.Series(row)

    pattern = row.get('aml_pattern')
    score = row.get('suspicion_score', 0)

    ev = get_evidence(row, reference) if reference is not None else None
    n = ev['responsible_count'] if ev else None

    text = _pattern_sentence(pattern, row, n)
    return {
        'pattern': pattern,
        'explanation': text,
        'suspicion_score': float(score),
        'risk_level': row.get('risk_level'),
        'escalation': row.get('escalation'),
        'severity_score': row.get('severity_score'),
        'evidence': ev,
    }


def _pattern_sentence(pattern, row, n):
    amt = row.get('Amount', 0)
    tx_count = int(row.get('sender_tx_count', 0) or 0)
    total = row.get('sender_total_amount', 0) or 0
    near = row.get('sender_pct_near_threshold', 0) or 0
    unique_senders = int(row.get('receiver_unique_senders', 0) or 0)
    passthrough = row.get('passthrough_ratio', 0) or 0
    ev_txt = f" Backed by {n} related transactions." if n is not None else ""

    if pattern == 'Structuring':
        return (f"Account made {tx_count} transactions totalling {total:,.0f}, with "
                f"{near*100:.0f}% falling just below the $10,000 reporting threshold — "
                f"consistent with structuring to evade reporting.{ev_txt}")
    if pattern == 'Smurfing':
        return (f"Receiver collected funds from {unique_senders} different senders in small "
                f"amounts — consistent with smurfing via money mules.{ev_txt}")
    if pattern == 'Layering':
        return (f"Account received and immediately forwarded funds (pass-through ratio "
                f"{passthrough:.2f}) — consistent with layering to obscure the money trail.{ev_txt}")
    if pattern == 'Fan_In':
        return (f"Many accounts funnel into this receiver ({unique_senders} unique senders) — "
                f"a fan-in aggregation pattern.{ev_txt}")
    if pattern == 'Fan_Out':
        return (f"Account distributes funds to many receivers in a fan-out pattern.{ev_txt}")
    if pattern == 'Cash_Withdrawal':
        return (f"Suspicious cash withdrawal of {amt:,.0f} following incoming transfers.{ev_txt}")
    if pattern == 'Deposit-Send':
        return (f"Funds deposited then immediately sent onward — rapid pass-through.{ev_txt}")
    if pattern == 'Over-Invoicing':
        return (f"Large cross-border payment of {amt:,.0f} with currency mismatch — "
                f"possible trade-based laundering via over-invoicing.{ev_txt}")
    if pattern == 'Single_large':
        return (f"Single anomalously large transaction of {amt:,.0f} with no matching "
                f"history.{ev_txt}")
    if pattern == 'Behavioural_Change':
        return (f"Account's transaction behaviour deviates sharply from its own history.{ev_txt}")
    if pattern == 'Bipartite':
        return (f"Coordinated group-to-group transfer pattern detected.{ev_txt}")
    return (f"Transaction flagged as suspicious ({pattern}).{ev_txt}")
