# AML Model Pipeline — Integration Guide

Everything the model pipeline needs is in this folder. You only need to add `SAML-D.csv`.

---

## Big Picture — what this pipeline does

Given transaction data, it flags suspicious transactions, names the money-laundering
pattern, grades how bad it is, traces the evidence, and produces a ready-to-send
explanation prompt. You call **one method** (`analyze`) and get a fully enriched table.

```
raw transactions
      │
      ▼
 feature_engineering  → builds 31 account-level features
      │
      ▼
 Model 1 (binary)     → is it suspicious?      ─── not suspicious → stop
      │ suspicious
      ▼
 Model 2 (type)       → which pattern? (Structuring / Smurfing / Layering / ...)
      │
      ▼
 risk_classifier      → severity 0-100 → low/med/high → monitor/review/report
      │
      ▼
 explainer            → how many rows are responsible + which account + why
      │
      ▼
 build_prompt         → finished LLM prompt string   ─── YOU send this to your LLM
```

## Division of labor

| Layer | Who | Files |
|---|---|---|
| Feature engineering, detection, risk, evidence, prompt generation | **Aditya (this bundle)** | `src/tools/*` |
| Query parsing, tool orchestration, UI, the LLM call itself | **Ashmit (you)** | your app |

You import this bundle as a library and call its methods. Section 5 maps each user query
to the exact method to call.

---

## 1. Install

```bash
pip install -r requirements.txt
# optional, for LLM explanations:
pip install google-generativeai
```

## 2. Folder contents

The actual structure (no `dataset/` subdirectory — `SAML-D.csv` sits directly in this folder):

```
app/data/
├── SAML-D.csv                     # the transaction dataset
├── __init__.py                    # makes app.data a Python package
├── requirements.txt               # Python dependencies
├── README.md                      # this file
├── src/
│   └── tools/
│       ├── __init__.py
│       ├── feature_engineering.py # builds the 31 features
│       ├── inference.py           # AMLDetector — the main entry point
│       ├── risk_classifier.py     # severity / risk level / escalation
│       ├── explainer.py           # evidence tracer + templated explanation
│       └── llm_explainer.py       # LLM prompt builder (optional)
└── models/                        # all 5 .pkl artifacts (ready to use)
    ├── model1_binary.pkl
    ├── model2_type.pkl
    ├── label_encoder.pkl
    ├── payment_type_map.pkl
    └── feature_baselines.pkl
```

If you don't have `SAML-D.csv` yet, download it:

```bash
# From the app/data/ directory:
kaggle datasets download -d berkanoztas/synthetic-transaction-monitoring-dataset-aml -p . --unzip
```

---

## ⚠️ THE ONE RULE — read this

The model's strongest features are **graph aggregations** computed across the whole batch
(e.g. how many unique accounts sent to a receiver). A single transaction in isolation has
no history to aggregate and **cannot be scored accurately**.

| You want to... | Call |
|---|---|
| Analyse a whole dataset | `detector.analyze(df)` |
| Score specific rows / an account | `detector.analyze(rows, reference=full_df)` |

Always pass `reference=full_df` when scoring a subset.

---

## 3. The Main API — one call does everything

```python
import pandas as pd
from src.tools.inference import AMLDetector

df = pd.read_csv('SAML-D.csv')
detector = AMLDetector()          # loads all models once

results = detector.analyze(df)    # score → severity → evidence → explanation
flagged = results[results['is_suspicious'] == 1]
```

### Output columns added to every row

| Column | Meaning |
|---|---|
| `is_suspicious` | 0/1 flag (Model 1) |
| `suspicion_score` | Confidence 0–1 (Model 1) |
| `aml_pattern` | Detected pattern (Model 2), or None |
| `severity_score` | 0–100, how bad (confidence × magnitude) |
| `risk_level` | low / medium / high |
| `escalation` | monitor / review / report |
| `responsible_count` | How many rows drove this flag |
| `evidence_account` | Account the evidence centers on |
| `evidence_side` | sender / receiver / both |
| `explanation` | Human-readable reason |

---

## 4. Query-Specific Methods

```python
# "Analyse this dataset"
detector.analyze(df)

# "Is account 4521 suspicious?"
detector.predict_account(4521, reference=df)     # all txns of that account, in context

# Score a few rows in full context
detector.analyze(some_rows, reference=df)

# Single transaction (dict)
detector.predict_one({
    'Sender_account': 8724731955, 'Receiver_account': 2769355426,
    'Amount': 9500.00, 'Payment_type': 'Cross-border',
    'Sender_bank_location': 'UK', 'Receiver_bank_location': 'UAE',
}, reference=df)
# → {'is_suspicious': 1, 'suspicion_score': 0.98, 'aml_pattern': 'Structuring'}
```

### Mapping agent queries → calls

| User query | Call |
|---|---|
| "Analyse this dataset for suspicious activity" | `analyze(df)` |
| "Is account 4521 suspicious?" | `predict_account(4521, reference=df)` |
| "Flag high-risk transactions" | `analyze(df)` then filter `risk_level == 'high'` |
| "Show me structuring patterns" | `analyze(df)` then filter `aml_pattern == 'Structuring'` |

---

## 5. Input Schema

**Critical (error if missing):** `Sender_account`, `Receiver_account`, `Amount`

**Optional (auto-defaulted):** `Payment_type`, `Sender_bank_location`, `Receiver_bank_location`,
`Payment_currency`, `Received_currency`, `Time`, `Date`

---

## 6. LLM Explanation — YOUR PART

**The handoff is one function: `build_prompt(row)`.**

We generate a complete, ready-to-send prompt string for each flagged row. You take that
string and send it to whatever LLM you want (Gemini, Groq, OpenAI, local — your choice).
No API key or LLM library is needed on our side; `build_prompt` is fully offline.

```python
from src.tools.llm_explainer import build_prompt, build_prompts

# one row
prompt = build_prompt(flagged.iloc[0])
answer = your_llm.generate(prompt)      # ← YOU do this with any LLM

# or all flagged rows at once → list of (row_index, prompt)
for idx, prompt in build_prompts(results):
    answer = your_llm.generate(prompt)
```

### What the prompt already contains
- The analyst role instruction
- An anti-hallucination guardrail ("use ONLY these facts, say so if they don't fit")
- The pattern definition + what "normal" looks like
- The **fact sheet**: pattern-relevant feature values, each compared against the
  normal average and the pattern-typical average (e.g.
  `receiver_unique_senders: 32 | normal avg 5.5 (5.8x above) | typical Smurfing 11.6`)

So the LLM's only job is to phrase it — all the reasoning inputs are already in the prompt.

### Inspect a prompt before wiring your LLM
```python
print(build_prompt(flagged.iloc[0]))   # prints the full text that goes to the LLM
```

**`llm_explainer.py` exposes exactly two functions you need:** `build_prompt(row)` and
`build_prompts(results)`. There is no built-in LLM call and no fallback — prompt
generation is the whole job on our side.

> Note: even without any LLM, every flagged row already has a plain-English `explanation`
> column from `analyze()`. The LLM is an optional upgrade to that, not a requirement.

---

## 7. Possible Pattern Values

```
Structuring   Smurfing    Layering    Cash_Withdrawal   Deposit-Send
Behavioural_Change   Bipartite   Fan_In   Fan_Out   Over-Invoicing   Single_large
```

---

## 8. Quick CLI Test

Run from the `app/data/` directory:

```bash
cd app/data
python -m src.tools.inference SAML-D.csv results.csv
```

Prints a summary + pattern breakdown and writes full results to `results.csv`.

---

## 9. Integration with LLM Tools (app.tools.ml_adapter)

The ML pipeline is also exposed as LangChain-compatible tools for the LLM agent
(via `app/tools/ml_adapter.py`):

| Tool | What it does |
|---|---|
| `run_aml_analysis` | Full pipeline: score → risk → evidence → explanation |
| `investigate_account` | Analyze a specific account's risk profile |
| `get_flagged_explanation` | Get explanation for a specific flagged transaction |
| `generate_aml_prompt` | Generate a ready-to-send LLM explanation prompt |
