# AI Business OS

A **local multi-agent business platform** for developers and operators who want research, document Q&A, finance/analytics helpers, coding assistance, and email drafting — plus trained ML models for churn, credit risk, sales forecast, segmentation, spam, and fraud — without Docker.

You log in, talk to specialized AI agents (or call ML APIs directly), upload private documents for RAG, and keep a task history of every run. The stack is FastAPI + PostgreSQL + CrewAI/Groq on the backend, and a Next.js dashboard on the frontend.

---

## Architecture overview

```text
┌─────────────────────────────┐
│  Next.js UI (:3000)         │
│  Login · Agents · Docs ·    │
│  History                    │
└──────────────┬──────────────┘
               │  JWT + REST (/api/v1/...)
               ▼
┌─────────────────────────────┐
│  FastAPI (:8000)            │
│  Auth · Agents · RAG · ML   │
└──┬──────────┬───────────┬───┘
   │          │           │
   ▼          ▼           ▼
PostgreSQL  Groq LLM   Chroma + MiniLM
(users,     (agents,   (per-user doc
 tasks,      RAG)       chunks)
 documents)
               │
               ▼
        ml/models/*.pkl
        (churn, credit, sales,
         segments, spam, fraud)
```

| Part | Path | Role |
|------|------|------|
| Backend | `agent-backend/` (this repo) | API, agents, ML, RAG, auth |
| Frontend | `../afsuu_Frontend/` | Authenticated dashboard |
| Docs | [BACKEND.md](./BACKEND.md) · [FRONTEND.md](./FRONTEND.md) | Deep dives |

Day-by-day learning notes (`DAY_*.md`, `PROJECT_FULL_STATUS.md`) are optional history; start here for onboarding.

---

## Models (ML / AI)

### Custom-trained (scikit-learn) — weights under `ml/models/`

CSVs and `.pkl` files are **gitignored**. After a fresh clone you must download datasets into `data/` and retrain.

| Model | Type | Input → output | Dataset file | Train | Predict / smoke |
|-------|------|----------------|--------------|-------|-----------------|
| **Churn** | Supervised RandomForest classifier | Telco customer features → Yes/No + probability + top factors | `data/telco_churn.csv` | `python -m ml.train_churn_model` | `ml/predict_churn.py`, `python -m scripts.test_churn_prediction` |
| **Credit risk** | Supervised RandomForest | Loan applicant features → Approve/Reject-style risk + probability | `data/loan_data.csv` | `python -m ml.train_credit_risk_model` | `ml/predict_credit_risk.py` |
| **Sales forecast** | Supervised RandomForest regressor | Calendar / category features → predicted sales | `data/sales_data.csv` | `python -m ml.train_sales_forecast_model` | `ml/predict_sales_forecast.py` |
| **Customer segmentation** | Unsupervised K-Means (+ scaler) | age, income, spending score → segment label + cluster id | `data/mall_customers.csv` | `python -m ml.train_customer_segments` | `ml/predict_customer_segment.py` |
| **Spam** | TF-IDF + MultinomialNB | Message text → spam/ham + confidence | `data/spam_dataset.csv` | `python -m ml.train_spam_classifier` | `ml/predict_spam.py` |
| **Fraud** | IsolationForest (unsupervised) | Transaction features (e.g. V1..V28 + Amount) → anomaly flag + score | `data/fraud_transactions.csv` | `python -m ml.train_fraud_detector` | `ml/predict_fraud.py` |

**Weights path:** `ml/models/<name>.pkl` (plus optional chart PNGs for some trainers).

**Key hyperparameters (from train scripts):**

| Model | Key settings |
|-------|----------------|
| Churn / credit risk | `RandomForestClassifier(n_estimators=200, …)` |
| Sales forecast | `RandomForestRegressor(n_estimators=200, …)` |
| Segmentation | `KMeans(n_clusters=chosen_k, random_state=42, n_init=10)` — `chosen_k` from elbow heuristic |
| Fraud | `IsolationForest(n_estimators=100, contamination=fraud_rate or 0.01)` |
| Spam | TF-IDF + MultinomialNB — see `ml/train_spam_classifier.py` for vectorizer settings |

**Inference via API (JWT):** `POST /api/v1/ml/{churn|credit-risk|sales-forecast|customer-segment|spam-check|fraud-check}` — see [BACKEND.md](./BACKEND.md).

**Also wired into agents:** Finance (credit + fraud), Analytics (churn + sales + segments), Email (spam).

### Pretrained / off-the-shelf

| Model | Role | Where weights live | Retrain? |
|-------|------|--------------------|----------|
| **all-MiniLM-L6-v2** (sentence-transformers) | Text → 384-d embeddings for Chroma RAG | HuggingFace cache (downloaded on first use, ~80MB) | No — inference only |
| **DistilBERT SST-2** (`distilbert-base-uncased-finetuned-sst-2-english`) | Email draft tone (positive/negative + optional warning) | HuggingFace cache (~260MB) | No — inference only via `services/sentiment_service.py` |
| **Groq LLM** (default `llama-3.3-70b-versatile`) | All agent reasoning + RAG answers | Hosted API | N/A — set `GROQ_API_KEY` / `GROQ_MODEL` |

---

## Setup (quick)

### 1. Backend

Details: **[BACKEND.md](./BACKEND.md)**

```bash
cd agent-backend
python3 -m venv venv && source venv/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
cp .env.example .env   # set DATABASE_URL, SECRET_KEY, GROQ_API_KEY
alembic upgrade head
# Optional: place CSVs in data/ and run python -m ml.train_*
uvicorn main:app --reload --port 8000
```

### 2. Frontend

Details: **[FRONTEND.md](./FRONTEND.md)**

```bash
cd ../afsuu_Frontend
npm install
cp .env.local.example .env.local   # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

Open `http://localhost:3000` → register → use agents / documents / history.  
API docs: `http://localhost:8000/docs`.

---

## Run end-to-end

### Development

1. Start PostgreSQL; ensure DB matches `DATABASE_URL`.
2. Backend: `uvicorn main:app --reload --port 8000`
3. Frontend: `npm run dev` on port 3000
4. Register a user in the UI (or via `/api/v1/auth/register`)
5. (Optional) Train ML models so `/api/v1/ml/*` and agent tools work

### Production

- Frontend: `npm run build && npm run start`
- Backend: run Uvicorn/Gunicorn behind a reverse proxy — **TODO: confirm** preferred process manager and host
- Update FastAPI CORS beyond `http://localhost:3000` before exposing publicly
- Do **not** treat the coding sandbox as safe for untrusted users (local subprocess only)
- Keep secrets in real env / secret store; never commit `.env`

---

## Tech stack summary

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 16, React 19, Tailwind CSS 4, JavaScript |
| Backend API | FastAPI, Uvicorn, Pydantic v2 |
| Database | PostgreSQL, SQLAlchemy 2, Alembic |
| Auth | JWT (HS256) + bcrypt |
| Agents | CrewAI, LangChain Groq |
| Search | DuckDuckGo |
| Vectors | ChromaDB (local folder), MiniLM embeddings |
| ML | scikit-learn, pandas, joblib |
| Email send | Optional SendGrid |
| Tone analysis | HuggingFace DistilBERT SST-2 |

---

## Known limitations / TODOs

| Item | Notes |
|------|--------|
| PPT Agent | Not built; Manager skips `ppt` steps |
| Settings UI | Nav placeholder only |
| Direct ML forms in UI | APIs exist; no dedicated frontend widgets yet |
| RAG on Finance / Analytics | Pattern exists on Research only |
| Code sandbox | Timeout + temp dir; not a security jail |
| OCR | Scanned/image-only PDFs not extracted |
| JWT logout | Client-side only (no server blacklist) |
| `.pkl` / CSVs | Must retrain after clone |
| Env example clutter | `XAI_API_KEY`, `DEBUG`, `DB_*` largely unused — TODO: clean up |
| Production deploy | No Docker/CI documented yet |

**Verdict:** Solid local learning / demo OS for multi-agent + ML + RAG. Remaining work is polish, PPT, deeper RAG wiring, and production hardening — not the core architecture.

---

## Where to go next

| Goal | Doc |
|------|-----|
| API endpoints, schema, auth, agents | [BACKEND.md](./BACKEND.md) |
| Pages, components, frontend env | [FRONTEND.md](./FRONTEND.md) |
| Feature status by day | `PROJECT_FULL_STATUS.md` |
