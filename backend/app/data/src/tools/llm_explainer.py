"""
LLM Prompt Builder
──────────────────
Extracts the pattern-relevant facts from a scored row and assembles a finished
LLM prompt asking WHY the model assigned that pattern — grounded strictly in
those facts. Prompt generation only; the app sends the prompt to its own LLM.

Flow:
    scored_row ──► build_fact_sheet() ──► build_prompt() ──► (app's LLM)
                        │
                (pick relevant cols + baseline comparisons)

The model decides flag + type. The prompt supplies the facts. The app narrates.
"""
import os

# Load per-feature baselines once (normal avg + pattern-typical avg)
try:
    import joblib
    _MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
    _BASELINES_PATH = os.path.join(_MODULE_DIR, '..', '..', 'models', 'feature_baselines.pkl')
    _BASELINES = joblib.load(_BASELINES_PATH)
except Exception:
    _BASELINES = None


def _compare(feature, value, pattern):
    """Return a comparative string: value vs normal vs this-pattern-typical."""
    if _BASELINES is None:
        return round(value, 3)
    normal = _BASELINES['normal'].get(feature)
    typical = _BASELINES['pattern'].get(pattern, {}).get(feature)
    parts = [f"{round(value, 3)}"]
    if normal is not None and normal != 0:
        ratio = value / normal
        direction = 'above' if ratio >= 1 else 'below'
        parts.append(f"normal avg {normal} ({ratio:.1f}x {direction})")
    elif normal is not None:
        parts.append(f"normal avg {normal}")
    if typical is not None:
        parts.append(f"typical {pattern} {typical}")
    return " | ".join(parts)

# ── Which feature columns matter for each pattern ────────────────────────────
PATTERN_FACTS = {
    'Structuring':        ['sender_tx_count', 'sender_pct_near_threshold',
                           'sender_total_amount', 'sender_std_amount'],
    'Smurfing':           ['receiver_unique_senders', 'receiver_sender_diversity',
                           'receiver_avg_incoming'],
    'Layering':           ['passthrough_ratio', 'is_passthrough_account',
                           'account_total_outgoing'],
    'Fan_In':             ['receiver_unique_senders', 'receiver_sender_diversity'],
    'Fan_Out':            ['sender_unique_receivers', 'sender_tx_count'],
    'Cash_Withdrawal':    ['Amount', 'receiver_total_incoming'],
    'Deposit-Send':       ['passthrough_ratio', 'account_total_outgoing'],
    'Over-Invoicing':     ['Amount', 'currency_mismatch', 'is_cross_border',
                           'is_high_risk_receiver'],
    'Single_large':       ['Amount', 'sender_amount_zscore', 'sender_avg_amount'],
    'Behavioural_Change': ['sender_amount_zscore', 'sender_std_amount', 'sender_avg_amount'],
    'Bipartite':          ['receiver_unique_senders', 'sender_unique_receivers'],
}

# ── One-line definition + what normal looks like, per pattern ─────────────────
PATTERN_REFERENCE = {
    'Structuring':        "One account splits money into many transactions just below the "
                          "$10,000 reporting threshold. Normal accounts don't cluster near it.",
    'Smurfing':           "Many accounts ('mules') send small amounts to one collection hub. "
                          "Normal receivers get money from 2-5 senders; smurfing hubs have 30+.",
    'Layering':           "Money is received then immediately forwarded through a pass-through "
                          "account to obscure its origin. Pass-through ratio near 1.0 is a red flag.",
    'Fan_In':             "Many accounts funnel funds into one. High unique-sender count.",
    'Fan_Out':            "One account distributes funds to many receivers. High unique-receiver count.",
    'Cash_Withdrawal':    "Large cash withdrawal shortly after receiving transfers; cash breaks the trail.",
    'Deposit-Send':       "Funds deposited then immediately sent onward; account is a conduit.",
    'Over-Invoicing':     "Inflated cross-border payment with currency mismatch to move value abroad.",
    'Single_large':       "One transaction far larger than the account's normal behaviour.",
    'Behavioural_Change': "Account's transaction pattern deviates sharply from its own history.",
    'Bipartite':          "A group of accounts transacts with another group in a coordinated block.",
}


def build_fact_sheet(row):
    """Pull the pattern-relevant facts out of a scored row into a small dict."""
    if hasattr(row, 'to_dict'):
        row = row.to_dict()

    pattern = row.get('aml_pattern')
    facts = {
        'transaction': f"{row.get('Amount', 0):,.0f} from {row.get('Sender_account')} "
                       f"to {row.get('Receiver_account')}",
        'route': f"{row.get('Sender_bank_location')} to {row.get('Receiver_bank_location')} "
                 f"via {row.get('Payment_type')}",
        'model_verdict': f"{pattern} (confidence {row.get('suspicion_score', 0):.2f})",
        'risk_level': row.get('risk_level'),
        'evidence_rows': int(row.get('responsible_count', 0) or 0),
    }
    for feat in PATTERN_FACTS.get(pattern, []):
        val = row.get(feat)
        if val is not None:
            facts[feat] = _compare(feat, float(val), pattern)
    return facts


def build_prompt(row):
    """Assemble the full LLM prompt from a scored row."""
    pattern = row['aml_pattern'] if hasattr(row, '__getitem__') else row.get('aml_pattern')
    facts = build_fact_sheet(row)
    definition = PATTERN_REFERENCE.get(pattern, "A suspicious money-laundering pattern.")

    fact_lines = "\n".join(f"  {k}: {v}" for k, v in facts.items())

    return f"""You are an AML compliance analyst. Explain WHY this transaction was flagged \
as the stated pattern, using ONLY the facts below. Do not invent anything. If a \
fact does not support the pattern, say so honestly.

PATTERN DEFINITION:
{pattern} — {definition}

FACTS:
{fact_lines}

Write a concise 2-3 sentence explanation for a compliance officer, citing the \
specific numbers that justify the flag."""


def build_prompts(scored_df):
    """
    Convenience: return a list of (index, prompt) for every flagged row in a
    scored/analyzed DataFrame. The app sends each prompt to its own LLM.
    """
    flagged = scored_df[scored_df['is_suspicious'] == 1]
    return [(idx, build_prompt(row)) for idx, row in flagged.iterrows()]
