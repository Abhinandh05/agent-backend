# AI Business OS — Backend

FastAPI backend for the AI Multi-Agent Business Operating System.
Runs locally with a Python venv (no Docker).

## Day 8 — Vector Store

### Why Chroma instead of Qdrant?
The original plan used Qdrant in Docker. This project runs fully local without Docker,
so we use **ChromaDB in persistent-local mode**. It embeds inside the Python process and
writes to a folder on disk — no separate server or port to manage.

### Why sentence-transformers instead of OpenAI embeddings?
Embeddings use **`sentence-transformers`** with model `all-MiniLM-L6-v2` (384-d vectors).
It runs on CPU, is completely free, and needs **no API key**. First run downloads ~80MB
of model weights (internet required once).

### Where is data stored?
Persistent Chroma data lives in:

```
backend/chroma_data/
```

This folder is gitignored — vector indexes should not be committed.

### Modules
| File | Role |
|------|------|
| `vectorstore/client.py` | Chroma `PersistentClient`, `add_chunks`, `query` (filters by `user_id`) |
| `vectorstore/embeddings.py` | `embed_text` / `embed_batch` via MiniLM |
| `vectorstore/chunking.py` | `split_text` via `RecursiveCharacterTextSplitter` |

### Run the smoke test

First install embeddings deps. Prefer **CPU torch** (much smaller than the CUDA build):

```bash
source venv/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install sentence-transformers chromadb langchain-text-splitters
python -m scripts.test_vectorstore
```

**Note:** The first `embed_*` call downloads `all-MiniLM-L6-v2` (~80MB). Needs internet once.

Expected output: chunk count, embedding dimension `384`, then top matching chunks for
`"What were the earnings?"` with distance / similarity scores.

### Unit tests

```bash
pytest tests/test_vectorstore.py -q
```

## Day 9 — Document Upload → Parse → Embed → Chroma

Authenticated upload pipeline that feeds Day 8's vector store.

### Install + migrate
```bash
pip install pdfplumber python-docx openpyxl
alembic upgrade head   # revision c3d9e8f1a2b0 → documents table
```

### API
- `POST /api/v1/documents/upload` — JWT, ≤10MB, `.pdf/.docx/.xlsx/.csv/.txt`
- `GET /api/v1/documents` / `GET|DELETE /api/v1/documents/{id}`

Background indexing: `uploaded` → `processing` → `indexed` (or `failed`).

See `DAY_9_DOCUMENT_UPLOAD.md` for curl examples.

## Day 10 — RAG Query Pipeline

Ask questions over your indexed documents (Chroma + Groq), with source citations.
Research Agent also gets a `document_rag_search` tool bound to the JWT user.

### API
- `POST /api/v1/documents/query` — `{ "question": "..." }` (JWT)

### Frontend
`/documents` — upload, list with status badges, ask + show sources.

See `DAY_10_RAG_QUERY.md` for curl examples and security notes.

## ML Model — Customer Churn Prediction

Real supervised ML (scikit-learn RandomForest) — separate from the Groq LLM agents.
CPU-only; no GPU / TensorFlow / PyTorch required for this model.

### Dataset
1. Download **Telco Customer Churn** from:
   https://www.kaggle.com/datasets/blastchar/telco-customer-churn
2. Place / rename the CSV exactly to:
   ```
   data/telco_churn.csv
   ```
   (folder: `agent-backend/data/`)

Both the CSV and the trained `.pkl` / chart are **gitignored** — retrain after a fresh clone.

### Train (seconds to ~1 minute on CPU)

```bash
source venv/bin/activate
pip install pandas joblib matplotlib scikit-learn
python -m ml.train_churn_model
```

Expect: classification report (accuracy / precision / recall / F1), confusion matrix,
`ml/models/churn_model.pkl`, and `ml/models/feature_importance.png`.

### Predict smoke test

```bash
python -m scripts.test_churn_prediction
```

Prints Yes/No + probability for a loyal customer vs a high-risk month-to-month example.

### Unit test

```bash
pytest tests/test_predict_churn.py -q
```

Skips automatically if the `.pkl` has not been trained yet.

## Day 11 — Finance Agent + Credit Risk Model

LLM Finance Agent (Groq) plus a trained loan/credit-risk RandomForest.

### Dataset
1. Download a free loan dataset from Kaggle, e.g.  
   https://www.kaggle.com/datasets/altruistdelhite04/loan-prediction-problem-dataset  
2. Place as `data/loan_data.csv` (gitignored).

### Train + smoke test
```bash
python -m ml.train_credit_risk_model
python -m scripts.test_credit_risk_prediction
```

### API
- `POST /api/v1/agents/finance` — LLM agent (JWT)
- `POST /api/v1/ml/credit-risk` — direct model prediction (JWT, no LLM)

### Frontend
`/agents/finance` — reuses `AgentChat`.

See `DAY_11_FINANCE_CREDIT_RISK.md` for full details and curl examples.

## Day 12 — Analytics Agent + Sales Forecast + Churn API

LLM Analytics Agent (Groq) with two trained models as tools, plus direct ML endpoints.

### Dataset (sales)
1. Prefer **Superstore** (simpler columns) from Kaggle:  
   https://www.kaggle.com/datasets/vivek468/superstore-dataset-final  
2. Place as `data/sales_data.csv` (gitignored).

### Train + smoke tests
```bash
python -m ml.train_sales_forecast_model
python -m scripts.test_sales_forecast
python -m scripts.test_churn_prediction
```

### API
- `POST /api/v1/agents/analytics` — LLM agent (JWT)
- `POST /api/v1/ml/churn` — direct churn prediction (JWT, no LLM)
- `POST /api/v1/ml/sales-forecast` — direct sales forecast (JWT, no LLM)
- `POST /api/v1/ml/customer-segment` — direct K-Means segment (JWT, no LLM)

### Frontend
`/agents/analytics` — reuses `AgentChat`.

See `DAY_12_ANALYTICS_AGENT.md` for modeling notes and curl examples.

## ML Model — Customer Segmentation (K-Means, Unsupervised)

Real **unsupervised** ML (scikit-learn K-Means) — no labels to predict.
Unlike churn / credit (classification) or sales forecast (regression), the model
discovers natural customer groups from Age, Annual Income, and Spending Score
on its own. CPU-only; no GPU.

### Why this differs from the earlier models
- **Supervised** models learn from a known target (`Churn=Yes/No`, loan
  Approve/Reject, sales $).
- **K-Means** has **no correct answer** in the CSV — it clusters by distance
  in feature space and we assign business labels afterward from cluster means.

### Dataset
1. Download **Mall Customer Segmentation Data** from Kaggle:
   https://www.kaggle.com/datasets/vjchoudhary7/customer-segmentation-tutorial-in-python  
   (search Kaggle for that exact name — ~200 rows)
2. Place / rename the CSV exactly to:
   ```
   data/mall_customers.csv
   ```
   (folder: `agent-backend/data/`)

Typical columns: `CustomerID`, `Gender` (sometimes `Genre`), `Age`,
`Annual Income (k$)`, `Spending Score (1-100)`. Training prints the actual
header row and resolves income/spending columns flexibly if spacing differs.

The CSV and trained `.pkl` / plots are **gitignored** — retrain after a fresh clone.

### Scaling + choosing k
- **StandardScaler is required** for K-Means (unlike Random Forest): distance
  between points drives cluster assignment, so Age vs Income vs Spending Score
  must share a comparable scale or the largest-range feature dominates.
- **Elbow method**: train K-Means for `k=2..10`, plot inertia, pick the knee
  where adding clusters stops buying much reduction (commonly near `k=5` on
  this dataset). See `ml/models/elbow_plot.png`.

### Train (a few seconds on CPU)

```bash
source venv/bin/activate
python -m ml.train_customer_segments
```

Expect: printed column names, inertia table, chosen `k`, a cluster profile
table with human-readable labels, plus:
- `ml/models/segmentation_model.pkl`
- `ml/models/elbow_plot.png` — inertia vs k (red dashed line = chosen k)
- `ml/models/segments_scatter.png` — Income vs Spending Score, colored by cluster

### Predict smoke test

```bash
python -m scripts.test_segment_prediction
```

### Unit test

```bash
pytest tests/test_predict_customer_segment.py -q
```

Skips automatically if the `.pkl` has not been trained yet.

### Direct API (JWT)

```bash
curl -X POST http://localhost:8000/api/v1/ml/customer-segment \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"customer": {"age": 28, "annual_income": 75, "spending_score": 80}}'
```

### Frontend follow-up
`/agents/analytics` is still chat-only (no dedicated churn / sales / segment
forms yet). A small Age / Income / Spending Score widget calling
`/api/v1/ml/customer-segment` can be added later alongside the other ML forms.

## Day 13 — Coding Agent & Sandbox Limitations

LLM Coding Agent (Groq) plus a **beginner-safe** local Python runner
(`subprocess` + temp directory + timeout). **No Docker.**

### What protection exists
- Separate OS process (crash of the child does not take down the API process)
- Hard wall-clock timeout (default 10s) against infinite loops
- Scratch files live in a temp dir that is deleted after the run

### What does **not** exist (do not oversell this)
- No filesystem jail beyond “please don’t” in the LLM prompt
- No network blocking (`subprocess` will not stop `urllib` / sockets)
- No memory / CPU cgroup limits
- Soft prompt guardrails only against `os.system`, deletes, etc.

This is safe against **accidental** bugs (hangs), **not** against a determined
attacker. Production next step: Docker / gVisor / Firecracker, or a hosted
sandbox (Judge0, Piston, E2B).

### API
- `POST /api/v1/agents/coding` — LLM agent (JWT, 120s timeout, `agent_type='coding'`)
- `POST /api/v1/tools/execute-code` — direct sandbox run, no LLM (JWT)

### Frontend
`/agents/coding` — reuses `AgentChat` with syntax-highlighted markdown.

See `DAY_13_CODING_AGENT.md` for curl examples and test commands.

## Day 14 — Email Agent + Tone Analysis

LLM Email Agent drafts subject/body; a **pre-trained** HuggingFace DistilBERT
model checks tone before send. Advisory only — never blocks sending.

### Email Agent — Tone Analysis
- Model: `distilbert-base-uncased-finetuned-sst-2-english` (HuggingFace, inference only — we did **not** train this)
- Checks drafted email body for unexpectedly negative tone + confidence
- If NEGATIVE with confidence > 0.7 → friendly `tone_warning` in the response / amber banner in UI
- **Never** disables Send; draft/send still succeed if sentiment fails (`sentiment: null`)
- First use downloads ~260MB once (needs internet); later runs are local/CPU and fast

### Install (important — avoid CUDA torch + crewai downgrade)
```bash
source venv/bin/activate
# 1) CPU torch FIRST (do not `pip install torch` from PyPI — that pulls CUDA + can break crewai)
pip install torch --index-url https://download.pytorch.org/whl/cpu
# 2) Then the rest (crewai is pinned to 0.30.11 in requirements.txt)
pip install -r requirements.txt
# 3) Optional: newer regex for transformers (pip will warn about crewai's pin — ignore it)
pip install 'regex>=2025.10.22'
```

### API
- `POST /api/v1/agents/email` — draft + sentiment (`{ request, recipient_hint?, tone? }`)
- `POST /api/v1/agents/email/send` — optional SendGrid (`{ to, subject, body }`)

### Frontend
`/agents/email` — editable To / Subject / Body, tone badge or amber warning, Send.

Optional env: `SENDGRID_API_KEY`, `SENDGRID_FROM_EMAIL` (drafting works without them).

See `DAY_14_EMAIL_SENTIMENT.md` for curl examples and what was built.

## ML Model — Spam Text Classifier (TF-IDF + Naive Bayes)

Self-trained **NLP** model — learns from raw message text (not tabular numbers).
TF-IDF vectorizes text; MultinomialNB classifies spam vs ham. CPU-only.

### Why this differs from earlier models
- Churn / credit / sales / segmentation all use **numeric features**.
- This model uses **words**: TF-IDF turns text into sparse vectors. Fit the
  vectorizer on **train only** (fitting on test leaks IDF information).
- Naive Bayes is a classic, fast baseline for spam-style text classification.

### Dataset
1. Download **SMS Spam Collection** (or Spam Text Message Classification) from Kaggle:
   - https://www.kaggle.com/datasets/uciml/sms-spam-collection-dataset
2. Place / rename exactly to:
   ```
   data/spam_dataset.csv
   ```
   Columns are auto-detected (`label`/`v1` + `text`/`v2`). Training prints headers first.

### Train + smoke test
```bash
python -m ml.train_spam_classifier
python -m scripts.test_spam_classifier
pytest tests/test_predict_spam.py tests/test_ml_spam_fraud_router.py -q
```

Expect ~98% accuracy on the SMS spam set; writes `ml/models/spam_classifier.pkl`.

### API + Email Agent
- `POST /api/v1/ml/spam-check` — body `{"text": "..."}` (JWT, no LLM) — preferred path for screening pasted/incoming text
- Email Agent also has `spam_message_classifier` for “is this spam?” questions (not for gating drafts)

```bash
curl -X POST http://localhost:8000/api/v1/ml/spam-check \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text": "WIN FREE MONEY NOW CLICK HERE"}'
```

See `DAY_SPAM_FRAUD_ML.md` for full details.

## ML Model — Fraud Anomaly Detection (IsolationForest)

Self-trained **unsupervised anomaly detection** on credit-card transactions.
Unlike credit-risk classification, IsolationForest flags unusual patterns using
a `contamination` rate matched to the real fraud rate in the CSV. CPU-only.

### Why this differs from everything else
- Fraud is rare (&lt;1%). Supervised classifiers struggle with that imbalance.
- IsolationForest does **not** need balanced labels to train; `Class` is used
  only afterward as a research sanity-check.
- Features are scaled with `StandardScaler` (same distance/density reasoning as K-Means).

### Dataset
1. Download **Credit Card Fraud Detection** from Kaggle:
   - https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud
2. Place / rename exactly to:
   ```
   data/fraud_transactions.csv
   ```
   Typical columns: `Time`, `V1`…`V28`, `Amount`, `Class`.

### Train + smoke test
```bash
python -m ml.train_fraud_detector
python -m scripts.test_fraud_detection
pytest tests/test_predict_fraud.py -q
```

Writes `ml/models/fraud_detector.pkl` (model + scaler). Expect modest precision/recall
vs `Class` (~0.25–0.35) for this baseline — technique demo, not a production fraud SOTA.

### API + Finance Agent
- `POST /api/v1/ml/fraud-check` — body `{"features": {"V1": ..., "Amount": ...}}` (JWT, no LLM)
- Finance Agent tool: `fraud_transaction_checker` alongside `credit_risk_predictor`

```bash
curl -X POST http://localhost:8000/api/v1/ml/fraud-check \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"features": {"V1": -1.36, "V2": -0.07, "V3": 2.54, "V4": 1.38, "V5": -0.34, "V6": 0.46, "V7": 0.24, "V8": 0.10, "V9": 0.36, "V10": 0.09, "V11": -0.55, "V12": -0.62, "V13": -0.99, "V14": -0.31, "V15": 1.47, "V16": -0.47, "V17": 0.21, "V18": 0.03, "V19": 0.40, "V20": 0.25, "V21": -0.02, "V22": 0.28, "V23": -0.11, "V24": 0.07, "V25": 0.13, "V26": -0.19, "V27": 0.13, "V28": -0.02, "Amount": 149.62}}'
```

See `DAY_SPAM_FRAUD_ML.md` for full details.

## Day 16 — Manager Agent

Orchestrates Research / Finance / Analytics / Coding / Email from **one** request.

- **Approach B (API default):** JSON plan → call each `run_*()` → combine  
- **Approach A (secondary):** CrewAI `allow_delegation=True` for comparison  
- `POST /api/v1/agents/manager` — JWT, **300s** timeout, returns `plan` + `step_results` + `final_response`  
- Frontend: `/agents/manager` (flagship nav + dashboard card)  
- DB: `tasks.plan_details` stores the plan/step JSON  

See `DAY_16_MANAGER_AGENT.md` for curl, timing, and approach comparison.

