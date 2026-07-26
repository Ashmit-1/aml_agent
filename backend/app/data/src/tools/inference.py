"""
AML Inference Pipeline
──────────────────────
Returns, per transaction row:
    - is_suspicious   : 0/1 flag        (Model 1)
    - suspicion_score : probability 0-1 (Model 1)
    - aml_pattern     : pattern name    (Model 2, only if suspicious)

IMPORTANT — read this before using
───────────────────────────────────
The model's strongest features are GRAPH AGGREGATIONS computed across the whole
batch you pass in (e.g. how many unique accounts a receiver got money from).
They only make sense when an account's FULL transaction history is present.

  • To analyse a whole dataset  → predict(df)            # df IS the batch
  • To score a few rows/accounts → predict(rows, reference=full_df)
        features are computed over reference+rows, predictions returned for `rows`

Scoring a single isolated transaction with no context WILL be inaccurate — a lone
row has no history to aggregate. Always give the account's context.

Usage (import):
    from src.tools.inference import AMLDetector
    det = AMLDetector()

    # whole dataset
    results = det.predict(df)

    # specific rows, using the full dataset as context
    results = det.predict(some_rows, reference=full_df)

CLI:
    python -m src.tools.inference transactions.csv [output.csv]
"""
import os
import sys
import joblib
import pandas as pd

from app.data.src.tools.feature_engineering import engineer_features, get_feature_matrix

_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
_MODELS_DIR_DEFAULT = os.path.join(_MODULE_DIR, '..', '..', 'models')
MODELS_DIR = os.environ.get('AML_MODELS_DIR', _MODELS_DIR_DEFAULT)

COLUMN_DEFAULTS = {
    'Time': '00:00:00',
    'Date': '2022-01-01',
    'Payment_currency': 'UK pounds',
    'Received_currency': 'UK pounds',
    'Sender_bank_location': 'UK',
    'Receiver_bank_location': 'UK',
    'Payment_type': 'ACH',
}
CRITICAL_COLUMNS = ['Sender_account', 'Receiver_account', 'Amount']
OUTPUT_COLS = ['is_suspicious', 'suspicion_score', 'aml_pattern']


class AMLDetector:
    def __init__(self, models_dir=MODELS_DIR):
        self.model1 = joblib.load(os.path.join(models_dir, 'model1_binary.pkl'))
        self.model2 = joblib.load(os.path.join(models_dir, 'model2_type.pkl'))
        self.label_encoder = joblib.load(os.path.join(models_dir, 'label_encoder.pkl'))
        self.payment_type_map = joblib.load(os.path.join(models_dir, 'payment_type_map.pkl'))

    # ── prep ──────────────────────────────────────────────────────────────────
    @staticmethod
    def _to_df(obj):
        if isinstance(obj, dict):
            return pd.DataFrame([obj])
        if isinstance(obj, list):
            return pd.DataFrame(obj)
        return obj.copy()

    def _prepare(self, df):
        df = self._to_df(df)
        missing = [c for c in CRITICAL_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(
                f"Missing critical column(s): {missing}. Required, cannot be defaulted."
            )
        for col, default in COLUMN_DEFAULTS.items():
            if col not in df.columns:
                df[col] = default
        return df

    def _score(self, X):
        flags = self.model1.predict(X).astype(int)
        scores = self.model1.predict_proba(X)[:, 1].round(4)
        patterns = pd.Series([None] * len(X), index=X.index, dtype=object)
        sus_idx = X.index[flags == 1]
        if len(sus_idx) > 0:
            codes = self.model2.predict(X.loc[sus_idx])
            patterns.loc[sus_idx] = self.label_encoder.inverse_transform(codes)
        return flags, scores, patterns

    # ── main API ──────────────────────────────────────────────────────────────
    def predict(self, rows, reference=None, include_features=True):
        """
        Args:
            rows: DataFrame / dict / list-of-dicts — the transactions to score
            reference: optional DataFrame — full context to compute features against.
                       If given, features are engineered over reference+rows and only
                       `rows` predictions are returned. Use this for scoring a subset.
            include_features: if True, engineered feature columns are attached to the
                       output (needed by risk_classifier and explainer).
        Returns:
            DataFrame: `rows` + is_suspicious, suspicion_score, aml_pattern
                       (+ engineered features if include_features)
        """
        rows = self._prepare(rows)

        if reference is not None:
            reference = self._prepare(reference)
            rows = rows.copy()
            rows['__target__'] = True
            reference = reference.copy()
            reference['__target__'] = False
            combined = pd.concat([reference, rows], ignore_index=True)

            feat, _ = engineer_features(combined, payment_type_map=self.payment_type_map, verbose=False)
            X = get_feature_matrix(feat)
            target_mask = feat['__target__'].values
            Xt = X[target_mask].reset_index(drop=True)

            flags, scores, patterns = self._score(Xt)
            out = rows.drop(columns='__target__').reset_index(drop=True)
            feat_target = Xt
        else:
            if len(rows) < 50:
                self._small_batch_warning(len(rows))
            feat, _ = engineer_features(rows, payment_type_map=self.payment_type_map, verbose=False)
            X = get_feature_matrix(feat)
            flags, scores, patterns = self._score(X)
            out = rows.reset_index(drop=True)
            feat_target = X.reset_index(drop=True)

        out['is_suspicious'] = flags.values if hasattr(flags, 'values') else flags
        out['suspicion_score'] = scores.values if hasattr(scores, 'values') else scores
        out['aml_pattern'] = patterns.values

        if include_features:
            # attach engineered feature columns not already present in `out`
            new_cols = [c for c in feat_target.columns if c not in out.columns]
            out = pd.concat([out, feat_target[new_cols].reset_index(drop=True)], axis=1)
        return out

    def predict_one(self, row, reference=None):
        """Score a single transaction. Returns a dict. Pass `reference` for accuracy."""
        r = self.predict(row, reference=reference).iloc[0]
        return {
            'is_suspicious': int(r['is_suspicious']),
            'suspicion_score': float(r['suspicion_score']),
            'aml_pattern': r['aml_pattern'],
        }

    def analyze(self, rows, reference=None):
        """
        Full pipeline in one call: score → severity → evidence + explanation.
        Returns a single enriched table with all columns a reviewer needs:
            is_suspicious, suspicion_score, aml_pattern,
            severity_score, risk_level, escalation,
            responsible_count, evidence_account, evidence_side, explanation
        """
        from app.data.src.tools.risk_classifier import classify_risk
        from app.data.src.tools.explainer import attach_evidence

        scored = self.predict(rows, reference=reference, include_features=True)
        scored = classify_risk(scored)
        ctx = reference if reference is not None else rows
        scored = attach_evidence(scored, self._prepare(ctx))
        return scored

    def predict_account(self, account_id, reference):
        """
        Score every transaction involving an account, in full context.
        Use this for 'Is account X suspicious?' queries.
        """
        reference = self._prepare(reference)
        mask = (reference['Sender_account'] == account_id) | (reference['Receiver_account'] == account_id)
        rows = reference[mask]
        if len(rows) == 0:
            raise ValueError(f"No transactions found for account {account_id}")
        return self.predict(rows, reference=reference)

    @staticmethod
    def _small_batch_warning(n):
        print(
            f"[warning] Scoring {n} row(s) with no reference context. Graph features "
            f"need full account history — predictions may be inaccurate. "
            f"Pass reference=<full_df> for correct results.",
            file=sys.stderr,
        )


# ── CLI ────────────────────────────────────────────────────────────────────────
def _main():
    if len(sys.argv) < 2:
        print("Usage: python -m src.tools.inference <transactions.csv> [output.csv]")
        sys.exit(1)

    df = pd.read_csv(sys.argv[1])
    out_path = sys.argv[2] if len(sys.argv) > 2 else None

    result = AMLDetector().predict(df)
    flagged = result[result['is_suspicious'] == 1]

    print(f"\nProcessed {len(result):,} transactions")
    print(f"Flagged suspicious: {len(flagged):,}")
    if len(flagged) > 0:
        print("\nPattern breakdown:")
        print(flagged['aml_pattern'].value_counts().to_string())
        show = [c for c in ['Sender_account', 'Receiver_account', 'Amount',
                            'suspicion_score', 'aml_pattern'] if c in flagged.columns]
        print("\nTop flagged:")
        print(flagged.sort_values('suspicion_score', ascending=False)[show].head(10).to_string(index=False))

    if out_path:
        result.to_csv(out_path, index=False)
        print(f"\nResults written to {out_path}")


if __name__ == '__main__':
    _main()
