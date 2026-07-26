import pandas as pd
import numpy as np

HIGH_RISK_COUNTRIES = [
    'UAE', 'Mexico', 'Morocco', 'Turkey', 'Panama', 'Nigeria',
    'Iran', 'Cayman Islands', 'British Virgin Islands', 'Montenegro'
]

STRUCTURING_THRESHOLD = 10000
STRUCTURING_LOWER = 8000

FEATURE_COLS = [
    'Amount', 'hour', 'day_of_week',
    'is_cross_border', 'currency_mismatch',
    'is_high_risk_sender', 'is_high_risk_receiver',
    'amount_below_threshold', 'amount_near_threshold',
    'sender_tx_count', 'sender_avg_amount', 'sender_std_amount',
    'sender_max_amount', 'sender_total_amount', 'sender_unique_receivers',
    'sender_pct_below_10k', 'sender_pct_near_threshold',
    'sender_cross_border_ratio', 'sender_high_risk_ratio',
    'sender_amount_zscore',
    'receiver_tx_count', 'receiver_unique_senders',
    'receiver_avg_incoming', 'receiver_total_incoming',
    'receiver_std_incoming', 'receiver_sender_diversity',
    'is_passthrough_account', 'passthrough_ratio',
    'account_outgoing_count', 'account_total_outgoing',
    'payment_type_encoded',
]


def load_data(path, synth_path=None, sample_frac=0.3, random_state=42):
    """
    Load SAML-D + optional synthetic patterns CSV.
    Keeps all suspicious rows, samples normal rows.
    """
    print(f"Loading data from {path}...")
    df = pd.read_csv(path)
    df['Is_laundering'] = df['Is_laundering'].astype(int)

    suspicious = df[df['Is_laundering'] == 1]
    normal = df[df['Is_laundering'] == 0].sample(frac=sample_frac, random_state=random_state)
    df = pd.concat([suspicious, normal]).reset_index(drop=True)

    if synth_path:
        print(f"Loading synthetic patterns from {synth_path}...")
        synth = pd.read_csv(synth_path)
        synth['Is_laundering'] = synth['Is_laundering'].astype(int)
        df = pd.concat([df, synth], ignore_index=True)
        print(f"Added {len(synth):,} synthetic rows")

    print(f"Total: {len(df):,} rows ({(df['Is_laundering']==1).sum():,} suspicious, {(df['Is_laundering']==0).sum():,} normal)")
    return df


def _parse_datetime(df):
    df['datetime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'])
    df['hour'] = df['datetime'].dt.hour
    df['day_of_week'] = df['datetime'].dt.dayofweek
    return df


def _transaction_level_features(df):
    df['is_cross_border'] = (df['Sender_bank_location'] != df['Receiver_bank_location']).astype(int)
    df['currency_mismatch'] = (df['Payment_currency'] != df['Received_currency']).astype(int)
    df['is_high_risk_sender'] = df['Sender_bank_location'].isin(HIGH_RISK_COUNTRIES).astype(int)
    df['is_high_risk_receiver'] = df['Receiver_bank_location'].isin(HIGH_RISK_COUNTRIES).astype(int)
    df['amount_below_threshold'] = (df['Amount'] < STRUCTURING_THRESHOLD).astype(int)
    df['amount_near_threshold'] = (
        (df['Amount'] >= STRUCTURING_LOWER) & (df['Amount'] < STRUCTURING_THRESHOLD)
    ).astype(int)
    return df


def _sender_features(df):
    agg = df.groupby('Sender_account').agg(
        sender_tx_count=('Amount', 'count'),
        sender_avg_amount=('Amount', 'mean'),
        sender_std_amount=('Amount', 'std'),
        sender_max_amount=('Amount', 'max'),
        sender_total_amount=('Amount', 'sum'),
        sender_unique_receivers=('Receiver_account', 'nunique'),
        sender_pct_below_10k=('amount_below_threshold', 'mean'),
        sender_pct_near_threshold=('amount_near_threshold', 'mean'),
        sender_cross_border_ratio=('is_cross_border', 'mean'),
        sender_high_risk_ratio=('is_high_risk_receiver', 'mean'),
    ).reset_index()

    agg['sender_std_amount'] = agg['sender_std_amount'].fillna(0)
    df = df.merge(agg, on='Sender_account', how='left')
    df['sender_amount_zscore'] = (
        (df['Amount'] - df['sender_avg_amount']) / (df['sender_std_amount'] + 1e-6)
    )
    return df


def _receiver_features(df):
    agg = df.groupby('Receiver_account').agg(
        receiver_tx_count=('Amount', 'count'),
        receiver_unique_senders=('Sender_account', 'nunique'),
        receiver_avg_incoming=('Amount', 'mean'),
        receiver_total_incoming=('Amount', 'sum'),
        receiver_std_incoming=('Amount', 'std'),
    ).reset_index()

    agg['receiver_std_incoming'] = agg['receiver_std_incoming'].fillna(0)
    agg['receiver_sender_diversity'] = (
        agg['receiver_unique_senders'] / agg['receiver_tx_count']
    )
    df = df.merge(agg, on='Receiver_account', how='left')
    return df


def _passthrough_features(df):
    """Detect accounts that receive money and immediately send it out (layering)."""
    passthrough_accounts = set(df['Sender_account'].unique()) & set(df['Receiver_account'].unique())

    outgoing = df.groupby('Sender_account').agg(
        account_outgoing_count=('Amount', 'count'),
        account_total_outgoing=('Amount', 'sum'),
    ).reset_index().rename(columns={'Sender_account': 'Receiver_account'})

    df = df.merge(outgoing, on='Receiver_account', how='left')
    df['account_outgoing_count'] = df['account_outgoing_count'].fillna(0)
    df['account_total_outgoing'] = df['account_total_outgoing'].fillna(0)
    df['is_passthrough_account'] = df['Receiver_account'].isin(passthrough_accounts).astype(int)
    df['passthrough_ratio'] = df['account_total_outgoing'] / (df['receiver_total_incoming'] + 1e-6)
    return df


def _encode_payment_type(df, payment_type_map=None):
    if payment_type_map is None:
        payment_type_map = {t: i for i, t in enumerate(df['Payment_type'].unique())}
    df['payment_type_encoded'] = df['Payment_type'].map(payment_type_map).fillna(-1).astype(int)
    return df, payment_type_map


def engineer_features(df, payment_type_map=None, verbose=True):
    """
    Full feature engineering pipeline.
    Returns (df_with_features, payment_type_map).
    Pass payment_type_map from training time when calling at inference time.
    """
    if verbose:
        print("Engineering features...")
    df = _parse_datetime(df)
    df = _transaction_level_features(df)
    df = _sender_features(df)
    df = _receiver_features(df)
    df = _passthrough_features(df)
    df, payment_type_map = _encode_payment_type(df, payment_type_map)
    if verbose:
        print(f"Done. Feature matrix shape: {df[FEATURE_COLS].shape}")
    return df, payment_type_map


def get_feature_matrix(df):
    return df[FEATURE_COLS].fillna(0)
