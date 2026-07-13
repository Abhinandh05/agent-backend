# Spam Classifier + Fraud Anomaly Detection — What Was Done

What was built in this session: **two more self-trained ML models**, each wired
into an existing agent (or a direct ML endpoint), completing the project’s ML
skillset.

| Model | Type | Wired into |
|-------|------|------------|
| Spam / ham text classifier | NLP (TF-IDF + MultinomialNB) | Email Agent tool + `POST /ml/spam-check` |
| Fraud anomaly detector | Unsupervised (IsolationForest) | Finance Agent tool + `POST /ml/fraud-check` |

CPU-only, scikit-learn only. No Docker / GPU / deep learning.

This fills the last gaps after tabular classification (churn, credit),
regression (sales), and clustering (segmentation): **NLP text classification**
and **unsupervised anomaly detection**.

---

## Overview — what was done

1. **Train** a TF-IDF + Multinomial Naive Bayes spam classifier on SMS/email-style text
2. **Train** an IsolationForest fraud detector on anonymized credit-card transactions
3. **Predict** helpers (`classify_message`, `check_transaction`) with joblib bundles
4. **Wire** CrewAI tools + Finance/Email agents; expose direct `/ml/*` endpoints
5. **Test** smoke scripts + pytest (shape + router auth/success)
6. **Document** README sections + this summary

---

## Files created / updated

### ML (new)
| File | Purpose |
|------|---------|
| `ml/train_spam_classifier.py` | Load CSV, print columns, TF-IDF + MultinomialNB, evaluate, save `.pkl` |
| `ml/predict_spam.py` | `classify_message(text) → {is_spam, confidence, label}` |
| `ml/models/spam_classifier.pkl` | Generated after training (gitignored) |
| `ml/train_fraud_detector.py` | Load CSV, scale V1–V28+Amount, IsolationForest, evaluate vs Class |
| `ml/predict_fraud.py` | `check_transaction(features) → {is_anomalous, anomaly_score, risk_note}` |
| `ml/models/fraud_detector.pkl` | Generated after training (gitignored) |
| `scripts/test_spam_classifier.py` | 3 hardcoded messages (spam + business + short ham) |
| `scripts/test_fraud_detection.py` | 1 Class=0 + 1 Class=1 row from the CSV |
| `tests/test_predict_spam.py` | Shape tests (skip if no `.pkl`) |
| `tests/test_predict_fraud.py` | Shape tests (skip if no `.pkl`) |
| `tests/test_ml_spam_fraud_router.py` | Auth + success for both `/ml/*` endpoints |

### Tools + agents
| File | Purpose |
|------|---------|
| `tools/spam_check_tool.py` | LangChain Tool wrapping `classify_message()` |
| `tools/fraud_check_tool.py` | LangChain Tool wrapping `check_transaction()` |
| `agents/email_agent.py` | Added spam tool; comment explains draft vs screen use |
| `agents/finance_agent.py` | Added fraud tool alongside credit-risk |

### API
| Endpoint | Purpose |
|----------|---------|
| `POST /api/v1/ml/spam-check` | Direct spam/ham (JWT, no LLM) — body `{"text": "..."}` |
| `POST /api/v1/ml/fraud-check` | Direct anomaly flag (JWT, no LLM) — body `{"features": {...}}` |

Schemas: `SpamCheckRequest`, `FraudCheckRequest` in `schemas.py`.  
Router: `routers/ml.py` (same pattern as other ML endpoints).

### Docs
| File | Purpose |
|------|---------|
| `DAY_SPAM_FRAUD_ML.md` | This summary |
| `README.md` | Sections for both models |
| `PROJECT_FULL_STATUS.md` | Status + API map updated |

---

## Why these two techniques matter

### TF-IDF + text classification (spam)
Every earlier model used **numeric/tabular** features. This one learns from
**raw words**. TF-IDF turns text into sparse numeric vectors (term frequency ×
inverse document frequency). We fit the vectorizer on **train only** so IDF
weights never see the test set (data leakage). MultinomialNB is a fast classic
baseline that historically works very well for spam-style bag-of-words tasks.

Minimal cleaning only (lowercase + whitespace) — heavy stemming/stopword
removal often strips useful spam signals like `FREE!!!`.

### IsolationForest + contamination (fraud)
This is **unsupervised anomaly detection**, not classification. Fraud is rare
(~0.17% in this dataset). IsolationForest flags unusual points using a
`contamination` rate set from the **real fraud rate in the CSV**, not a
hardcoded guess. Labels (`Class`) are used **only afterward** for a research
sanity-check; a true unsupervised deployment would not have them at inference.

Precision/recall vs `Class` on this run was modest (~0.28) — expected for a
simple IsolationForest baseline on heavily imbalanced PCA features; the point
is the technique and wiring, not beating a supervised fraud classifier.

---

## Datasets — where to get them and where to place them

### 1) Spam / text classifier
1. Download **SMS Spam Collection Dataset** (or Spam Text Message Classification)
   from Kaggle:
   - https://www.kaggle.com/datasets/uciml/sms-spam-collection-dataset
   - https://www.kaggle.com/datasets/team-ai/spam-text-message-classification  
   Or the UCI archive: https://archive.ics.uci.edu/dataset/228/sms+spam+collection  
2. Place / rename exactly to:
   ```
   data/spam_dataset.csv
   ```
   Typical columns: `label`/`v1` (spam|ham) and `text`/`v2` (message). Training
   prints actual headers and renames internally.

### 2) Fraud / anomaly detection
1. Download **Credit Card Fraud Detection** from Kaggle:
   - https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud  
2. Place / rename exactly to:
   ```
   data/fraud_transactions.csv
   ```
   Typical columns: `Time`, `V1`…`V28`, `Amount`, `Class` (0=normal, 1=fraud).
   ~284k rows; CSV is gitignored.

---

## How to train (exact commands)

```bash
source venv/bin/activate

# Spam — a few seconds on ~5k messages
python -m ml.train_spam_classifier

# Fraud — ~minutes on ~280k rows (CPU)
python -m ml.train_fraud_detector
```

### What metrics / output to expect

**Spam (`train_spam_classifier`)**
- Prints actual CSV column names, then label/text mapping
- Stratified 80/20 split (`random_state=42`)
- Expect roughly: Accuracy ~0.98, Precision ~0.98, Recall ~0.89, F1 ~0.94
  (ham vs spam report + confusion matrix)
- Writes `ml/models/spam_classifier.pkl` (model + fitted TfidfVectorizer)

**Fraud (`train_fraud_detector`)**
- Prints columns, feature list (V1–V28 + Amount), fraud rate (~0.001727)
- Sets `contamination` from that rate
- Sanity-check vs `Class`: precision/recall often ~0.25–0.35 for this baseline
- Writes `ml/models/fraud_detector.pkl` (model + StandardScaler)

---

## Smoke tests + unit tests

```bash
python -m scripts.test_spam_classifier
python -m scripts.test_fraud_detection

pytest tests/test_predict_spam.py tests/test_predict_fraud.py tests/test_ml_spam_fraud_router.py -q
```

Predict tests skip gracefully if `.pkl` files are missing. Router tests mock
predictions and always check 401 without JWT + 200 success shape.

---

## curl — direct ML endpoints (JWT)

```bash
# Login first and export TOKEN from the response
TOKEN="<your_jwt>"

# Spam check
curl -X POST http://localhost:8000/api/v1/ml/spam-check \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text": "WIN FREE MONEY NOW CLICK HERE to claim your prize!!!"}'

# Fraud check (V1..V28 + Amount — use real feature values from a CSV row)
curl -X POST http://localhost:8000/api/v1/ml/fraud-check \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"features": {"V1": -1.36, "V2": -0.07, "V3": 2.54, "V4": 1.38, "V5": -0.34, "V6": 0.46, "V7": 0.24, "V8": 0.10, "V9": 0.36, "V10": 0.09, "V11": -0.55, "V12": -0.62, "V13": -0.99, "V14": -0.31, "V15": 1.47, "V16": -0.47, "V17": 0.21, "V18": 0.03, "V19": 0.40, "V20": 0.25, "V21": -0.02, "V22": 0.28, "V23": -0.11, "V24": 0.07, "V25": 0.13, "V26": -0.19, "V27": 0.13, "V28": -0.02, "Amount": 149.62}}'
```

Example spam response shape:
```json
{
  "success": true,
  "data": {"is_spam": true, "confidence": 1.0, "label": "spam"},
  "message": "Spam check completed",
  "error": null
}
```

Example fraud response shape:
```json
{
  "success": true,
  "data": {
    "is_anomalous": false,
    "anomaly_score": 0.283031,
    "risk_note": "This transaction's pattern looks consistent with typical activity; no anomaly flag raised."
  },
  "message": "Fraud check completed",
  "error": null
}
```

---

## Agent wiring notes

### Email Agent
Spam screening is more natural for **incoming / pasted** text than for
outgoing drafts. The tool is on the agent for “is this message spam-like?”
questions; the practical primary path is **`POST /api/v1/ml/spam-check`**
(instant, no LLM).

### Finance Agent
`fraud_transaction_checker` sits next to `credit_risk_predictor` so the agent
can flag suspicious transaction patterns **and** score loan applicants.

---

## Training results from this build (reference)

| Model | Key result |
|-------|------------|
| Spam | Acc 0.9839 · P 0.9852 · R 0.8926 · F1 0.9366 on held-out test |
| Fraud | contamination=0.001727 · P/R vs Class ≈ 0.28 (sanity-check only) |

All 7 targeted pytest cases passed after training.
