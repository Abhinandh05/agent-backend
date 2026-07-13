# Backend — AI Business OS

Detailed documentation for the FastAPI backend at `agent-backend/`.  
Written for a **brand-new developer** joining this repo: what each piece is, why it exists, how a request flows, and what to open first.

For the product overview, see [README.md](./README.md). For the UI, see [FRONTEND.md](./FRONTEND.md).

### What you will learn here

- How the API process starts (`main.py`) and how routes are grouped
- The three ways work gets done: **LLM agents**, **direct ML**, and **document RAG**
- How JWT auth ties every task/document/Chroma chunk to a `user_id`
- How to install, set env vars, train `.pkl` models, and run tests
- Step-by-step pipelines for upload/index and RAG query

### Jargon (quick glossary)

| Term | Plain English |
|------|----------------|
| **API** | A server that accepts HTTP requests and returns JSON (or files) |
| **JWT** | A signed token proving “this request is from user X” until it expires |
| **ORM** | Code that maps Python classes to database tables (SQLAlchemy here) |
| **Agent** | An LLM (language model) plus tools that can search, predict, or run code |
| **Tool** | A function the agent is allowed to call (e.g. churn predictor) |
| **RAG** | Retrieval-Augmented Generation: find relevant doc chunks, then ask the LLM |
| **Embedding** | A numeric vector that represents text meaning (for similarity search) |
| **Chroma** | Local vector database folder that stores those embeddings |
| **`.pkl`** | A saved scikit-learn model file loaded with `joblib` for predictions |
| **Background task** | Work that continues after the HTTP response is already sent |

---

## Tech stack

| Layer | Choice | Version (from `requirements.txt` where pinned) |
|--------|--------|------------------------------------------------|
| Language | Python 3 | TODO: confirm exact version in your environment (`NOTE.MD` mentions 3.12) |
| API | FastAPI + Uvicorn + Starlette | `fastapi==0.136.3`, `uvicorn==0.49.0` |
| Validation | Pydantic v2 | `pydantic==2.13.4` |
| Database | PostgreSQL + SQLAlchemy 2 + Alembic | `SQLAlchemy==2.0.50`, `alembic==1.18.5`, `psycopg2-binary==2.9.12` |
| Auth | JWT (`python-jose`) + bcrypt (`passlib`) | `python-jose==3.5.0`, `passlib==1.7.4`, `bcrypt==4.0.1` |
| Agents | CrewAI + LangChain Groq | `crewai==0.30.11`, `langchain-groq` (unpinned) |
| Web search | DuckDuckGo (`duckduckgo-search`) | unpinned |
| Vector store | ChromaDB (local persistent) | unpinned |
| Embeddings | sentence-transformers `all-MiniLM-L6-v2` | unpinned |
| ML | scikit-learn, pandas, joblib, matplotlib | `scikit-learn>=1.4,<1.6` |
| NLP tone | HuggingFace `transformers` (DistilBERT SST-2) | unpinned; install **CPU torch** separately |
| Document parsers | pdfplumber, python-docx, openpyxl | unpinned |
| Config | python-dotenv | `1.2.2` |

**Entry point:** `main.py`  
**Interactive API docs:** `http://localhost:8000/docs`

---

## How the backend works (big picture)

### What this backend is for

This backend is the brain of **AI Business OS**: a local multi-agent business platform. Authenticated users can (1) talk to specialist LLM agents (research, finance, analytics, coding, email, manager), (2) call trained ML models directly for churn/credit/sales/segments/spam/fraud, and (3) upload private documents and ask questions over them with RAG. Everything that belongs to a user — tasks, documents, and Chroma chunks — is scoped by `user_id` from the JWT so one account cannot see another’s data.

### Typical request path (ASCII)

```text
  Browser / Next.js (:3000)
           |
           |  HTTPS/HTTP  Authorization: Bearer <JWT>
           v
  +---------------------+
  | FastAPI (main.py)   |  CORS only allows localhost:3000
  | Uvicorn :8000       |
  +----------+----------+
             |
             v
  +---------------------+
  | Auth dependency     |  decode JWT -> load User -> require is_active
  | get_current_active_ |
  | user                |
  +----------+----------+
             |
             v
  +---------------------+
  | Router              |  auth / users / tasks / agents / ml /
  | (routers/*.py)      |  documents / tools
  +----------+----------+
             |
     +-------+--------+----------------+
     |                |                |
     v                v                v
  Agent (CrewAI)   ML predict     RAG / documents
  + tools          (joblib .pkl)  (embed + Chroma + Groq)
     |                |                |
     +-------+--------+--------+-------+
             |                 |
             v                 v
        PostgreSQL          Chroma (chroma_data/)
        users/tasks/docs    chunks + user_id metadata
             |
             v
          Groq API  (when an LLM answer is needed)
```

### Three modes of work

| Mode | What it is | Example routes | Uses LLM? | Uses `.pkl`? | Uses Chroma? |
|------|------------|----------------|-----------|--------------|--------------|
| **1. LLM agents** | CrewAI agent + tools; creates a `Task` row; client waits | `POST /api/v1/agents/*` | Yes (Groq) | Often (via tools) | Research / Manager research yes |
| **2. Direct ML** | Call `predict_*` only — no agent narrative | `POST /api/v1/ml/*` | No | Yes | No |
| **3. Document RAG** | Upload → index chunks; query → retrieve → answer | `POST /api/v1/documents/upload`, `/query` | Query yes (if chunks found) | No | Yes |

Same ML predictors are shared: agent tools and `/ml/*` both call `ml/predict_*.py`.

### How user isolation works

```text
Login -> JWT with claim sub = user.id
              |
              v
Every protected route: get_current_active_user -> User object
              |
              +--> Task.user_id = current_user.id
              +--> Document.user_id = current_user.id
              +--> Chroma metadata user_id = current_user.id
              +--> Chroma query always where={"user_id": ...}
```

- Tasks and documents are filtered by owner on list/get/delete.
- Research and Manager pass `current_user.id` into RAG tools so retrieval never scans another user’s chunks.
- Direct ML does not store per-user model weights; isolation there is “only logged-in users can call the API,” not per-user models.

---

## Why we use this / why we do not use that

This section explains every major choice in plain language. For each topic: what we picked, **why it is used here**, and **what we deliberately did not use** (and why).

### 1. FastAPI (not Flask / Django / Express)

| | |
|--|--|
| **Used** | FastAPI + Uvicorn |
| **Not used** | Flask, Django REST, Node/Express for the API |

**Why FastAPI is used**

- Built for async APIs and automatic OpenAPI docs at `/docs` — useful while learning and demoing agents.
- Pydantic validates every request body before your code runs (bad ML payloads fail with `422`, not silent bugs).
- Fits Python ML (scikit-learn, transformers) in the **same process** as the API — no separate “ML microservice” for a local project.

**Why Flask / Django are not used**

- Flask needs more boilerplate for validation and OpenAPI; this project leans on FastAPI’s defaults.
- Django is great for full websites + admin, but heavier than needed for a JSON API + agents.
- Express would force a second language (JS) for ML training/inference; keeping one Python backend is simpler for this OS.

---

### 2. PostgreSQL + SQLAlchemy + Alembic (not SQLite / Mongo / raw SQL only)

| | |
|--|--|
| **Used** | PostgreSQL, SQLAlchemy ORM, Alembic migrations |
| **Not used** | SQLite as primary DB, MongoDB, hand-written SQL migrations only |

**Why PostgreSQL is used**

- Real relational DB for users, tasks, and documents with foreign keys (`user_id`).
- Multi-user data isolation is clearer with SQL constraints than with files.
- Matches what production business apps usually run.

**Why SQLAlchemy is used**

- Maps Python classes (`User`, `Task`, `Document`) to tables so routers stay readable.
- `get_db()` session pattern works cleanly with FastAPI dependencies.

**Why Alembic is used**

- Schema changes (e.g. adding `plan_details`, `result_file_path`) are versioned and repeatable: `alembic upgrade head`.
- Without migrations, every machine’s DB drifts and “works on my laptop” breaks.

**Why SQLite / Mongo are not the main choice**

- SQLite is fine for tiny demos but weaker for concurrent writes when agents + uploads hit at once.
- Mongo fits document blobs well, but our core entities are relational (user owns many tasks/docs). We already store free-form text in columns (`result`, `plan_details`) when needed.

---

### 3. JWT + bcrypt (not sessions in Redis / OAuth social login)

| | |
|--|--|
| **Used** | JWT access tokens + bcrypt password hashes |
| **Not used** | Server-side session store (Redis), Google/GitHub OAuth, storing plain passwords |

**Why JWT is used**

- Stateless: the API does not need Redis just to know who you are.
- Frontend stores the token and sends `Authorization: Bearer …` — simple for a SPA.
- Every agent/document/ML call can bind work to `user_id` from the token so data does not leak across accounts.

**Why bcrypt is used**

- Passwords must never be stored in plain text. bcrypt is a standard slow hash for passwords.

**Why Redis sessions / social OAuth are not used**

- Redis sessions add another service to run locally; the project goal is **no Docker / minimal deps**.
- Logout is therefore **client-side** (delete token). A stolen token works until expiry — acceptable for local learning, not for hardened production.
- Social OAuth is out of scope; email/password is enough for the learning OS.
- `XAI_API_KEY` in `.env.example` is **not used** by code — leftover / unused config, not part of auth.

---

### 4. Groq + CrewAI (not OpenAI-only / not “LLM for everything”)

| | |
|--|--|
| **Used** | Groq-hosted LLM via LangChain + CrewAI agents |
| **Not used** | OpenAI as the only LLM, local full LLMs (Llama.cpp) as the default, calling the LLM for every numeric prediction |

**Why Groq is used**

- Fast inference API with a free/cheap key model for demos.
- One env var (`GROQ_API_KEY`) powers Research, Finance, Analytics, Coding, Email, Manager, and RAG answers.

**Why CrewAI is used**

- Gives a clear **Agent + Tool + Task** pattern so each specialist (research, finance, …) stays a module.
- Tools wrap real functions (search, `.pkl` predictors, code runner) instead of pretending the LLM “knows” churn scores.

**Why we do not use the LLM for ML predictions**

- Churn / credit / sales / spam / fraud are **trained models**. Calling Groq for “is this customer churning?” would be slower, costlier, and less reproducible than `joblib.load` + `predict_proba`.
- Direct routes under `/api/v1/ml/*` exist so you can score **without** an LLM at all.

**Why OpenAI / local giant models are not the default**

- OpenAI is fine but not required; Groq was chosen for this stack.
- Running a large local LLM needs GPU/RAM the project deliberately avoids (CPU-only story).

---

### 5. DuckDuckGo search (not Google/Bing paid APIs)

| | |
|--|--|
| **Used** | `duckduckgo-search` / DDGS tool for Research Agent |
| **Not used** | Google Custom Search, SerpAPI, Bing API |

**Why DuckDuckGo is used**

- Free web search with **no API key** — Research Agent works after you only set Groq.
- Good enough for “look up a business topic” demos.

**Why paid search APIs are not used**

- Extra billing and keys for a local learning project.
- Search quality tradeoff is accepted; this is not a production search product.

---

### 6. ChromaDB + MiniLM (not Qdrant / OpenAI embeddings / Pinecone)

| | |
|--|--|
| **Used** | Chroma persistent folder + `all-MiniLM-L6-v2` embeddings |
| **Not used** | Qdrant in Docker, Pinecone/Weaviate cloud, OpenAI `text-embedding-*` |

**Why Chroma is used**

- Embeds and stores vectors **inside the Python process**.
- Writes to `chroma_data/` on disk — no separate vector server or port.
- Filters by `user_id` so User A never retrieves User B’s chunks.

**Why Qdrant / Docker vectors are not used**

- Earlier plans used Qdrant-in-Docker; this project runs **fully local without Docker**.
- One less container to install and keep running.

**Why MiniLM (sentence-transformers) is used**

- Free, CPU-friendly, no embedding API key.
- First run downloads ~80MB once; then offline.

**Why OpenAI embeddings are not used**

- Would require another paid key and network call for every chunk.
- Conflicts with the “local + free embeddings” design.

---

### 7. scikit-learn `.pkl` models (not TensorFlow / PyTorch training for tabular)

| | |
|--|--|
| **Used** | scikit-learn + pandas + joblib for churn, credit, sales, segments, spam, fraud |
| **Not used** | TensorFlow/Keras or fine-tuned deep nets for these tabular/NLP baselines |

**Why scikit-learn is used**

- Trains in seconds–minutes on CPU — matches a day-by-day learning build.
- RandomForest / K-Means / Naive Bayes / IsolationForest are standard, explainable baselines.
- `joblib` `.pkl` files load fast for API tools.

**Why deep learning is not used for these tasks**

- Tabular churn/credit rarely needs a neural net for a teaching demo.
- Spam uses TF-IDF + MultinomialNB (classic NLP baseline), not a custom transformer train loop.
- PyTorch **is** installed (CPU) only for **pretrained** MiniLM / DistilBERT inference — not for training our business models.

**Why each algorithm (and not the others)**

| Model | Used | Why used | Not used | Why not |
|-------|------|----------|----------|---------|
| Churn / credit | RandomForest **classifier** | Labels exist (Yes/No, approve/reject); RF handles mixed features after one-hot | Deep nets / logistic-only | Overkill / weaker default for messy categoricals in this demo |
| Sales | RandomForest **regressor** | Predict a continuous number ($) | Classifier | Sales is not a Yes/No label |
| Segments | **K-Means** | No labels — discover groups | Supervised classifier | There is no “segment” column to train on |
| Spam | **TF-IDF + MultinomialNB** | Text → bag-of-words; NB is a classic spam baseline | LLM “is this spam?” | Costly and non-deterministic vs a trained classifier |
| Fraud | **IsolationForest** | Fraud is rare; unsupervised anomaly detection | Supervised RF as the only story | Labels are scarce; IF teaches contamination / anomaly scoring |

Spam tip: only light cleaning (lowercase). Heavy stemming/stopwords are **not** used — they can wipe spam signals like `FREE!!!`.

Fraud tip: `Class` labels are for **evaluation after training**, not for fitting IsolationForest. A pure unsupervised deploy would not need labels at inference.

---

### 8. DistilBERT tone (not training our own sentiment model)

| | |
|--|--|
| **Used** | HuggingFace DistilBERT SST-2 (inference only) on email drafts |
| **Not used** | Training a custom sentiment model, blocking send on negative tone |

**Why DistilBERT is used**

- Pretrained tone check with no training data or GPU.
- Shows “off-the-shelf NLP” next to our custom `.pkl` models.

**Why it does not block send**

- Tone is **advisory** (`tone_warning` only). Bad drafts can still be edited and sent — product choice so UX is not locked by a model error.
- Sentiment failure returns `null`; drafting still succeeds.

**Why SendGrid is optional**

- Drafting must work without email credentials.
- Send is a separate endpoint; empty `SENDGRID_*` means “draft only.”

---

### 9. Agents + tools layout (not one giant prompt / not ML-only)

| | |
|--|--|
| **Used** | Separate agents (`research`, `finance`, …) + LangChain tools + Manager |
| **Not used** | Single mega-prompt for everything; PPT agent (not built yet) |

**Why separate agents**

- Each domain has different tools and timeouts (coding 120s, manager 300s).
- Easier to test and to show in the UI as dedicated pages.

**Why tools exist**

- The LLM must **call** search / predictors / code execution — not invent numbers.

**Why Manager Approach B is used in the API (Approach A is not the default)**

| | Approach A (CrewAI delegation) | Approach B (explicit plan) |
|--|-------------------------------|----------------------------|
| Used by API? | **No** (kept for comparison) | **Yes** |
| Why | Black-box delegation; hard to show steps | Returns `plan` + `step_results` + `final_response` for the UI |
| Controllability | Low | High — we own plan → execute → combine |

**Why PPT is not used yet**

- Day 15 PPT agent is not implemented. Manager **skips** `ppt` steps instead of crashing.

**Why RAG is on Research (not yet on Finance/Analytics)**

- Document Q&A pattern is proven on Research + `/documents/query`.
- Wiring the same tool into Finance/Analytics is a follow-up (TODO), not because those agents “should never” use docs.

---

### 10. Direct `/ml/*` routes **and** agent tools (both used on purpose)

| | |
|--|--|
| **Used** | Both `POST /api/v1/ml/...` and agent tools wrapping the same predictors |
| **Not used** | Only chat, or only ML forms |

**Why both**

- **`/ml/*`**: fast, cheap, deterministic scoring — no LLM latency or hallucination.
- **Agent tools**: natural language (“assess this applicant…”) where the LLM decides when to call the model and explains the result.
- Frontend today mostly uses chat; APIs are ready for dedicated ML forms later.

---

### 11. FastAPI `BackgroundTasks` (not Celery / Redis / RQ)

| | |
|--|--|
| **Used** | In-process `BackgroundTasks` for document indexing; threadpool + timeouts for agents |
| **Not used** | Celery, RQ, Dramatiq, Redis queue, APScheduler |

**Why BackgroundTasks is used**

- Upload can return quickly with `status=uploaded` while parse → embed → Chroma runs in the background.
- Zero extra infrastructure for a local OS.

**Why Celery / Redis queues are not used**

- They need Redis/workers/monitoring — overkill for single-machine demos.
- Tradeoff: if the API process dies mid-index, the job is lost (status may stay `processing` / `failed`). Fine for learning; not for large production ingest.

**Why agent work is not a “job queue”**

- Agent runs are request-scoped with timeouts (`90s`–`300s`). Client waits (or times out with `504`). Simpler than polling a job id for this stage.

---

### 12. Local subprocess code runner (not Docker / gVisor / E2B)

| | |
|--|--|
| **Used** | `subprocess` + temp directory + timeout for Coding Agent / `/tools/execute-code` |
| **Not used** | Docker sandbox, gVisor, E2B, full network jail |

**Why local subprocess is used**

- No Docker requirement; Coding Agent can verify snippets on a laptop.
- Timeout stops infinite loops; separate process limits some crash blast radius.

**Why a real sandbox is not used (yet)**

- Production-grade isolation is a separate project. Current runner is **not** safe for untrusted users (network/filesystem not fully locked down). Documented honestly so nobody mistakes it for a jail.

---

### 13. Folder layout: `routers` / `agents` / `tools` / `services` / `ml`

| Folder | Why it exists | What does **not** go here |
|--------|----------------|---------------------------|
| `routers/` | HTTP only — auth, status codes, call services/agents | Heavy business logic / training loops |
| `agents/` | CrewAI run_* orchestration | Raw FastAPI route defs |
| `tools/` | Functions the LLM can call | DB models |
| `services/` | Shared non-HTTP logic (RAG, SendGrid, sentiment) | One-off train scripts |
| `ml/` | Train + predict + `.pkl` | LLM prompts |
| `models/` | SQLAlchemy tables | ML weights (those live in `ml/models/`) |
| `schemas.py` | Request/response shapes | Database engine setup |
| `core/` | Security + shared dependencies | Feature-specific agent code |

**Why split routers instead of one `main.py`**

- Keeps auth, tasks, agents, ml, documents maintainable as the API grows.

**Why `schemas.py` is separate from `models/`**

- **ORM models** = what Postgres stores (including `hashed_password`).
- **Pydantic schemas** = what the API accepts/returns (never leak password hashes).

---

### 14. Env vars: what is used vs listed but unused

| Variable | Used? | Why |
|----------|-------|-----|
| `DATABASE_URL`, `SECRET_KEY`, `GROQ_API_KEY` | **Yes** | Core runtime |
| `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `GROQ_MODEL` | **Yes** (optional defaults) | Tunable JWT / model id |
| `SENDGRID_*` | **Only if sending mail** | Drafting works without them |
| `XAI_API_KEY`, `DEBUG` | **Not read by app code** | Leftover / unused — ignore or clean later |
| `DB_NAME`, `DB_USER`, … | **Not read** | App uses a single `DATABASE_URL` string instead |

**Why one `DATABASE_URL` instead of many `DB_*` parts**

- SQLAlchemy and Alembic expect a full URL. Splitting into host/user/password is redundant unless you build a custom config layer (we did not).

---

### 15. CPU torch install path (not bare `pip install torch`)

| | |
|--|--|
| **Used** | `pip install torch --index-url https://download.pytorch.org/whl/cpu` **before** `requirements.txt` |
| **Not used** | Putting unpinned CUDA `torch` inside `requirements.txt` |

**Why**

- Default PyPI torch often pulls a **multi-GB CUDA** build and can break/pin-fight with `crewai`.
- CPU torch is enough for MiniLM + DistilBERT inference on a laptop.

**Why `regex` is not pinned hard in `requirements.txt`**

- `crewai` and `transformers` disagree on regex versions. Install base deps first; optionally upgrade regex afterward so transformers works without making pip unsolvable.

---

### 16. CORS locked to `localhost:3000` (not `*` )

| | |
|--|--|
| **Used** | `allow_origins=["http://localhost:3000"]` |
| **Not used** | `allow_origins=["*"]` with credentials |

**Why**

- Frontend is expected on Next.js port 3000.
- Wide-open CORS is convenient and unsafe for real deployments — not the default here.

---

## Folder and file structure

### Tree overview

```text
agent-backend/
├── main.py                 # FastAPI app, CORS, router mounts, / and /health
├── database.py             # Engine, SessionLocal, Base, get_db()
├── schemas.py              # Pydantic request/response models
├── requirements.txt        # Python dependencies
├── alembic.ini             # Alembic config (URL overridden by .env)
├── .env.example            # Template for local secrets
│
├── core/                   # Shared security + FastAPI dependencies
│   ├── security.py         # bcrypt hash/verify, JWT create/decode
│   └── dependencies.py     # get_current_user / get_current_active_user
│
├── models/                 # SQLAlchemy ORM tables
│   ├── user.py
│   ├── task.py
│   └── document.py
│
├── routers/                # HTTP endpoints (thin layer)
│   ├── auth.py
│   ├── users.py
│   ├── tasks.py
│   ├── agents.py
│   ├── ml.py
│   ├── documents.py
│   └── tools.py
│
├── agents/                 # CrewAI / orchestration logic
│   ├── research_agent.py
│   ├── finance_agent.py
│   ├── analytics_agent.py
│   ├── coding_agent.py
│   ├── email_agent.py
│   └── manager_agent.py
│
├── tools/                  # LangChain tools the LLM can call
│   ├── search_tool.py
│   ├── rag_tool.py
│   ├── credit_risk_tool.py
│   ├── fraud_check_tool.py
│   ├── churn_tool.py
│   ├── sales_forecast_tool.py
│   ├── segmentation_tool.py
│   ├── spam_check_tool.py
│   └── code_execution_tool.py
│
├── services/               # Shared non-HTTP logic
│   ├── document_service.py
│   ├── rag_service.py
│   ├── llm_service.py
│   ├── sentiment_service.py
│   └── email_send_service.py
│
├── vectorstore/            # Embeddings + Chroma persistence
│   ├── client.py
│   ├── embeddings.py
│   └── chunking.py
│
├── ml/                     # Train + predict; weights in ml/models/*.pkl
│   ├── train_*.py
│   ├── predict_*.py
│   └── models/             # .pkl files (gitignored)
│
├── alembic/versions/       # Schema migrations
├── scripts/                # Manual smoke tests (python -m scripts.*)
├── tests/                  # pytest suite
├── data/                   # Kaggle CSVs for training (gitignored contents)
├── uploads/                # Uploaded user files (gitignored)
└── chroma_data/            # Persistent Chroma index (gitignored)
```

### Root files — what they do

| Path | What it does | When it runs | Talks to | Open first if… |
|------|--------------|--------------|----------|----------------|
| `main.py` | Creates FastAPI app, CORS, mounts all routers, health routes | Process start (`uvicorn main:app`) | All routers | You need the API entry map |
| `database.py` | SQLAlchemy engine + `get_db()` session generator | Every DB request | PostgreSQL via `DATABASE_URL` | DB connection fails |
| `schemas.py` | Pydantic bodies/responses (validation) | Every typed request/response | Routers only | You need request/response shapes |
| `requirements.txt` | Pip dependencies | Install time | — | Fresh setup |
| `alembic.ini` | Alembic config; URL taken from env in `alembic/env.py` | Migrations | Postgres | Schema drift |
| `.env.example` | Template secrets | Copy once to `.env` | — | First install |

### `core/` — security gate

| Path | One-line purpose | Open first if… |
|------|------------------|----------------|
| `core/security.py` | bcrypt hash/verify + JWT create/decode using `SECRET_KEY` | Login/token bugs |
| `core/dependencies.py` | `OAuth2PasswordBearer` + `get_current_user` / `get_current_active_user` | 401/403 on protected routes |

**When it runs:** On every route that declares `Depends(get_current_active_user)`.  
**Talks to:** JWT header → Postgres `users` table.

### `models/` — database tables

| Path | One-line purpose | Open first if… |
|------|------------------|----------------|
| `models/user.py` | `users` table + relationships to tasks/documents | Auth / profile fields |
| `models/task.py` | `tasks` history rows (agent runs, plan_details, file path) | History / manager plans |
| `models/document.py` | `documents` upload metadata + index status | Upload/index status |

Also present: `models/test.py` — TODO: confirm if leftover scratch (not part of the product schema).

### `routers/` — HTTP only

| Path | One-line purpose | When it runs | Talks to |
|------|------------------|--------------|----------|
| `routers/auth.py` | Register, login, `/me`, logout ack | Auth calls | User model, security |
| `routers/users.py` | Profile get/patch; get user by id | Profile UI | User model |
| `routers/tasks.py` | Create/list/get/delete tasks; file download | History UI | Task model, disk |
| `routers/agents.py` | Run agents; create Task; timeouts | Agent chat pages | `agents/*`, Task |
| `routers/ml.py` | Direct `.pkl` predictions (no LLM) | ML forms / scripts | `ml/predict_*` |
| `routers/documents.py` | Upload, query, list, get, delete | Docs UI | document_service, rag, Chroma |
| `routers/tools.py` | Direct code execution (no LLM) | Coding “run” UI | `code_execution_tool` |

Also present: `routers/test.py` — TODO: confirm leftover.

**New developer tip:** Start with `routers/agents.py` for the Task lifecycle pattern (create → running → completed/failed).

### `agents/` — LLM orchestration

| Path | One-line purpose | Tools used | Timeout (API) |
|------|------------------|------------|---------------|
| `agents/research_agent.py` | Business research via web + user docs | DuckDuckGo, document RAG | 90s |
| `agents/finance_agent.py` | Finance narrative + risk/fraud | credit risk, fraud | 90s |
| `agents/analytics_agent.py` | Analytics narrative + customer/ops ML | churn, sales, segments | 90s |
| `agents/coding_agent.py` | Write/test small Python | `execute_python_code` | 120s |
| `agents/email_agent.py` | Draft subject/body; optional spam tool | spam classifier | 90s |
| `agents/manager_agent.py` | Plan → run specialists → combine (Approach B) | Calls other `run_*` | 300s |

Also present: `agents/exapmle.py` — TODO: confirm leftover example (typo in filename).

**When it runs:** Inside `run_in_threadpool` from `routers/agents.py` while the HTTP request waits.  
**Talks to:** Groq (`ChatGroq`), tools → predictors / search / Chroma / subprocess.

### `tools/` — one-line each

| Path | Purpose |
|------|---------|
| `tools/search_tool.py` | DuckDuckGo web search for Research Agent |
| `tools/rag_tool.py` | User-scoped Chroma RAG search (`document_rag_search`) |
| `tools/credit_risk_tool.py` | Wraps `predict_credit_risk` for Finance Agent |
| `tools/fraud_check_tool.py` | Wraps `check_transaction` for Finance Agent |
| `tools/churn_tool.py` | Wraps `predict_churn` for Analytics Agent |
| `tools/sales_forecast_tool.py` | Wraps `predict_sales` for Analytics Agent |
| `tools/segmentation_tool.py` | Wraps `predict_segment` for Analytics Agent |
| `tools/spam_check_tool.py` | Wraps `classify_message` for Email Agent |
| `tools/code_execution_tool.py` | Local subprocess Python sandbox (timeout 10s default) |

Also present: `tools/test.py` — TODO: confirm leftover.

### `services/` — one-line each

| Path | Purpose |
|------|---------|
| `services/document_service.py` | Extract text → chunk → embed → Chroma; background job entry |
| `services/rag_service.py` | Embed question → Chroma (user filter) → Groq answer + sources |
| `services/llm_service.py` | Simple Groq prompt→text helper (RAG and non-CrewAI calls) |
| `services/sentiment_service.py` | DistilBERT SST-2 tone check for email drafts (advisory) |
| `services/email_send_service.py` | Optional SendGrid v3 send |

Also present: `services/test.py` — TODO: confirm leftover.

### `vectorstore/` — one-line each

| Path | Purpose |
|------|---------|
| `vectorstore/client.py` | Chroma persistent client in `chroma_data/`; add/query/delete by `document_id` |
| `vectorstore/embeddings.py` | MiniLM `all-MiniLM-L6-v2` → 384-d vectors |
| `vectorstore/chunking.py` | RecursiveCharacterTextSplitter (500 chars, 50 overlap) |

### `ml/` — train and predict

| Path | Purpose |
|------|---------|
| `ml/train_churn_model.py` | Train churn RF → `ml/models/churn_model.pkl` |
| `ml/predict_churn.py` | Load churn `.pkl` and score one customer |
| `ml/train_credit_risk_model.py` | Train credit RF → `credit_risk_model.pkl` |
| `ml/predict_credit_risk.py` | Load credit `.pkl` and score one applicant |
| `ml/train_sales_forecast_model.py` | Train sales regressor → `sales_forecast_model.pkl` |
| `ml/predict_sales_forecast.py` | Load sales `.pkl` and forecast |
| `ml/train_customer_segments.py` | Train K-Means → `segmentation_model.pkl` |
| `ml/predict_customer_segment.py` | Load segment `.pkl` and assign cluster |
| `ml/train_spam_classifier.py` | Train TF-IDF+NB → `spam_classifier.pkl` |
| `ml/predict_spam.py` | Load spam `.pkl` and classify text |
| `ml/train_fraud_detector.py` | Train IsolationForest → `fraud_detector.pkl` |
| `ml/predict_fraud.py` | Load fraud `.pkl` and score transaction |

### Other folders

| Path | Role |
|------|------|
| `alembic/versions/` | Ordered schema migrations — always `alembic upgrade head` after pull |
| `scripts/` | Manual smoke tests (`python -m scripts.test_*`) |
| `tests/` | Automated pytest suite |
| `data/` | Place CSVs here before training |
| `uploads/` | Saved multipart uploads (`{uuid}_{filename}`) |
| `chroma_data/` | On-disk Chroma collection `documents` |

---

## Install and run locally

### Prerequisites

- Python 3.x in a venv (project notes mention 3.12 — TODO: confirm on your machine)
- PostgreSQL running locally, with a database that matches `DATABASE_URL`
- A [Groq](https://console.groq.com/) API key starting with `gsk_...` (needed for agents and RAG answers)
- Internet once (download MiniLM ~80MB and DistilBERT ~260MB on first use)

### Step-by-step

#### 1. Enter the repo and create a venv

```bash
cd agent-backend
python3 -m venv venv
source venv/bin/activate
```

**What this does:** Isolates Python packages so they do not fight system Python.  
**Common failure:** `ensurepip` / venv missing on Linux → install `python3.12-venv` (or your version) via apt.

#### 2. Install CPU torch first

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

**What this does:** Installs a small CPU build of PyTorch for MiniLM + DistilBERT inference.  
**Common failure:** Skipping this and installing bare `torch` from PyPI → multi-GB CUDA wheel, slow downloads, and possible conflicts with `crewai`.

#### 3. Install project requirements

```bash
pip install -r requirements.txt
```

**What this does:** Installs FastAPI, CrewAI, Chroma, scikit-learn, etc.  
**Optional follow-up:** `pip install 'regex>=2025.10.22'` if transformers complains about regex (crewai pins an older regex; see requirements comments).

#### 4. Create `.env`

```bash
cp .env.example .env
# Edit: DATABASE_URL, SECRET_KEY, GROQ_API_KEY (required for agents/RAG)
```

**What this does:** Loads secrets via `python-dotenv` in `database.py`, `security.py`, agents, etc.  
**Common failure:** Missing `GROQ_API_KEY` or key not starting with `gsk_` → agents/RAG raise `ValueError` / 502.

#### 5. Create the Postgres database and migrate

```bash
# Create DB named in DATABASE_URL if it does not exist (example name: ai_business_os)
alembic upgrade head
```

**What this does:** Applies all Alembic migrations (users, tasks, documents, plan_details, indexes).  
**Common failure:** Postgres not running or wrong password in `DATABASE_URL` → connection refused / auth failed. Fix Postgres or the URL, then retry.

#### 6. Start the API

```bash
uvicorn main:app --reload --port 8000
```

**What this does:** Serves FastAPI with auto-reload. Open `http://localhost:8000/docs`.  
**Common failure:** Port 8000 in use — pick another port or stop the other process.

#### 7. Train ML models (after clone)

CSVs and `.pkl` files are **gitignored**. Without them, `/api/v1/ml/*` and agent tools that need models return **503** (`FileNotFoundError` → “Model not ready”).

```bash
# Place datasets under data/ (see README for expected filenames), then:
python -m ml.train_churn_model
python -m ml.train_credit_risk_model
python -m ml.train_sales_forecast_model
python -m ml.train_customer_segments
python -m ml.train_spam_classifier
python -m ml.train_fraud_detector
```

**What this does:** Writes `.pkl` files under `ml/models/`.  
**Common failure:** Missing CSV in `data/` → train script fails; missing `.pkl` → API 503 until you train.

### Quick checklist of common failures

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Connection errors on startup / migrations | Postgres down or bad `DATABASE_URL` | Start Postgres; fix URL |
| Agents/RAG fail immediately | Missing/invalid `GROQ_API_KEY` | Set `gsk_...` in `.env` |
| `503 Model not ready` on `/ml/*` | No `.pkl` after clone | Run matching `python -m ml.train_*` |
| Huge pip / CUDA torch | Installed PyPI torch | Use CPU index URL first |
| CORS errors from browser | Frontend not on `:3000` | Run UI on 3000 or change CORS in `main.py` |

---

## Environment variables

Copy from `.env.example`. **Do not commit `.env`.**

Default DB URL if `DATABASE_URL` is unset (in `database.py`):  
`postgresql://admin:secret@localhost:5432/ai_business_os`

| Variable | Required? | Purpose | What breaks if missing/wrong |
|----------|-----------|---------|------------------------------|
| `DATABASE_URL` | Yes (for real use) | Postgres URL for SQLAlchemy + Alembic | App cannot read/write users/tasks/docs; migrations fail. Wrong host/password → connection errors |
| `SECRET_KEY` | Yes for real auth | Signs/verifies JWTs | If unset, code falls back to a hard-coded string (unsafe). If you change it after issuing tokens, all existing JWTs become invalid (401) |
| `ALGORITHM` | No (default `HS256`) | JWT algorithm | Wrong value → encode/decode mismatch → 401 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No (default `30`) | Token lifetime | Too short → frequent re-login; invalid non-int → crash on import of security module |
| `GROQ_API_KEY` | Yes for agents/RAG answers | Groq LLM key; must start with `gsk_` | Agents and RAG LLM calls raise / return 502. Direct `/ml/*` still works without it |
| `GROQ_MODEL` | No (default `llama-3.3-70b-versatile`) | Groq model id | Wrong model id → Groq API errors during agent/RAG calls |
| `SENDGRID_API_KEY` | Only for send | SendGrid API key | Drafting still works; `POST .../email/send` returns 400 with clear config error |
| `SENDGRID_FROM_EMAIL` | Only for send | Verified sender address | Same as above if missing |
| `XAI_API_KEY` | — | Listed in `.env.example` | **Not read by app code** — leftover |
| `DEBUG` | — | Listed in `.env.example` | **Not read by app code** — leftover |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_DIALECT` | — | Documented in example only | **Not read** — app uses single `DATABASE_URL` |

---

## API endpoints

### Response shapes

Most authenticated agent / ML / document / task / tool responses use:

```json
{
  "success": true,
  "data": { },
  "message": "...",
  "error": null
}
```

Auth register/login/me and users routes return Pydantic models directly (no `APIResponse` wrapper).

Send `Authorization: Bearer <access_token>` on protected routes.

### Health

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/` | No | App info |
| GET | `/health` | No | Liveness probe |

Example:

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

**Status codes:** `200` always if the process is up (does not deep-check Postgres).

---

### Auth — `/api/v1/auth`

#### `POST /api/v1/auth/register`

**For:** Create an account.  
**Body:**

```json
{
  "name": "Ada",
  "second_name": "Lovelace",
  "email": "ada@example.com",
  "password": "secret123"
}
```

**Inside the server:** Check email unique → bcrypt hash password → insert `User` → return `UserResponse` (no password).  
**Codes:** `201` created; `400` email already exists; `422` validation.

#### `POST /api/v1/auth/login`

**For:** Get a JWT.  
**Body:**

```json
{ "email": "ada@example.com", "password": "secret123" }
```

**Inside the server:** Find user by email → verify bcrypt → reject if inactive → `create_access_token({"sub": str(user.id)})` → return token + user.  
**Codes:** `200` OK; `401` bad credentials; `403` deactivated; `422` validation.

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"ada@example.com","password":"secret123"}'
```

#### `GET /api/v1/auth/me`

**For:** Who am I?  
**Inside:** `get_current_active_user` → return user.  
**Codes:** `200`; `401` missing/bad token; `403` inactive.

#### `POST /api/v1/auth/logout`

**For:** Acknowledge logout. JWT is **not** blacklisted; client must delete the token.  
**Codes:** `200`; `401` if not logged in.

---

### Users — `/api/v1/users`

| Method | Path | Purpose | Step-by-step | Codes |
|--------|------|---------|--------------|-------|
| GET | `/me` | Current profile (alias of auth/me) | JWT → return user | 200, 401, 403 |
| PATCH | `/me` | Update name / second_name / email | Partial update; email uniqueness check | 200, 400 email taken, 401, 422 |
| GET | `/{user_id}` | Lookup any user by id (any logged-in user) | Query by id | 200, 404, 401 |

---

### Tasks — `/api/v1/tasks`

Tasks are history rows. Agent endpoints also create tasks; you can also create a bare `pending` task via POST.

#### `POST /api/v1/tasks`

**Body:** `{ "agent_type": "research", "prompt": "..." }`  
**Inside:** Insert Task with `user_id` from JWT, `status=pending`. Does **not** run an agent by itself.  
**Codes:** `201`, `401`, `422`.

#### `GET /api/v1/tasks`

**Query:** `agent_type?`, `status?`, `limit` (1–100, default 20), `offset`  
**Inside:** Filter by `current_user.id`; truncate prompt to ~100 chars in list.  
**Codes:** `200`, `401`.

#### `GET /api/v1/tasks/{task_id}`

**Inside:** Owner-only fetch; full `result`, `plan_details`, `result_file_path`.  
**Codes:** `200`, `404` (missing or not yours), `401`.

#### `GET /api/v1/tasks/{task_id}/download`

**Inside:** If `result_file_path` set and file exists, stream it. (PPT artifacts are the intended use; PPT agent not built yet.)  
**Codes:** `200` file; `404` no file / not owner / missing on disk.

#### `DELETE /api/v1/tasks/{task_id}`

**Inside:** Owner delete row; unlink `result_file_path` if present.  
**Codes:** `200`, `404`, `401`.

---

### Agents — `/api/v1/agents` (all JWT)

**Shared lifecycle for every agent run:**

```text
1. Validate body (Pydantic + strip length checks)
2. INSERT Task(user_id, agent_type, prompt, status="running")
3. run_in_threadpool(run_*) inside asyncio.wait_for(timeout)
4a. success -> status="completed", result=...  (+ plan_details for manager)
4b. TimeoutError -> status="failed", HTTP 504
4c. Exception -> status="failed", HTTP 502
5. Return APIResponse with task_id
```

**Common codes:** `200` success; `401` auth; `422` validation; `504` timeout; `502` upstream agent/LLM error. Email send also uses `400` for SendGrid config/rejection.

#### `POST /api/v1/agents/research` (90s)

**For:** Research a topic using web search + this user’s documents.  
**Body:** `{ "topic": "AI in retail logistics" }`  
**Inside:** Task `agent_type=research` → `run_research(topic, user_id)` → CrewAI with DuckDuckGo + RAG tool.  
**Success data:** `{ "result": "...", "task_id": 123 }`

```bash
curl -X POST http://localhost:8000/api/v1/agents/research \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"topic":"SMB cash flow tips"}'
```

#### `POST /api/v1/agents/finance` (90s)

**For:** Finance narrative; may call credit-risk and fraud tools.  
**Body:** `{ "request": "Assess this applicant: {...}" }`  
**Success data:** `{ "result", "task_id" }`

#### `POST /api/v1/agents/analytics` (90s)

**For:** Analytics narrative; may call churn, sales forecast, segmentation tools.  
**Body:** `{ "request": "Will this customer churn? {...}" }`

#### `POST /api/v1/agents/coding` (120s)

**For:** Write and verify small Python via local sandbox.  
**Body:** `{ "request": "Write a function that ..." }`  
**Note:** Longer timeout because sandbox runs take time.

#### `POST /api/v1/agents/email` (90s)

**For:** Draft subject/body; then optional DistilBERT tone (never blocks draft).  
**Body:**

```json
{
  "request": "Apologize for late shipment to Acme",
  "recipient_hint": "ops@acme.com",
  "tone": "formal"
}
```

**Success data:** `{ "subject", "body", "raw", "sentiment", "task_id" }`  
`sentiment` may be `null` if the tone model fails.

#### `POST /api/v1/agents/email/send`

**For:** Send a (possibly edited) draft via SendGrid.  
**Body:** `{ "to": "a@b.com", "subject": "...", "body": "..." }`  
**Inside:** Task `agent_type=email_send` → `send_email`.  
**Codes:** `200` sent; `400` missing SendGrid config or rejection; `502` other upstream errors.

#### `POST /api/v1/agents/manager` (300s)

**For:** Multi-step orchestration (Approach B).  
**Body:** `{ "request": "Research X, then draft an email summarizing..." }`  
**Inside:** `run_manager_explicit_plan` → plan JSON → run specialists → combine → store `plan_details` JSON on Task.  
**Success data:** `{ "plan", "step_results", "final_response", "task_id" }`  
**PPT:** Steps named `ppt` are **skipped** with a message (agent not built).

---

### Documents — `/api/v1/documents`

#### `POST /api/v1/documents/upload`

**For:** Upload a file to index for RAG.  
**Request:** multipart form field `file` (≤10MB; `.pdf` `.docx` `.xlsx` `.csv` `.txt`).  
**Inside:** Validate type/size → save under `uploads/{uuid}_{name}` → Document row `status=uploaded` → `BackgroundTasks.add_task(process_document_job)` → return immediately.  
**Codes:** `200` accepted; `400` bad type/empty; `413` too large; `401`.

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@./notes.pdf"
```

Poll `GET /documents/{id}` until `status` is `indexed` or `failed`.

#### `POST /api/v1/documents/query` (60s timeout)

**For:** Ask a question over **your** indexed docs.  
**Body:** `{ "question": "What is our refund policy?" }`  
**Inside:** `rag_query` — if no chunks, returns fixed “couldn’t find…” **without** calling Groq.  
**Success data:** `{ "answer", "sources", "chunks_found" }`  
**Codes:** `200`, `422`, `504`, `502`, `401`.

#### `GET /api/v1/documents`

List current user’s documents (newest first).

#### `GET /api/v1/documents/{document_id}`

Owner-only summary (`status`, `chunk_count`, `error_message`, …). `404` if not yours.

#### `DELETE /api/v1/documents/{document_id}`

Owner-only: delete Chroma chunks by `document_id`, DB row, and file on disk.

**Document status flow:** `uploaded` → `processing` → `indexed` | `failed`

---

### ML (direct, no LLM) — `/api/v1/ml` (all JWT)

All routes: validate body → call `predict_*` → on `FileNotFoundError` return **503 Model not ready**.

| Method | Path | Body | Success `data` (shape) |
|--------|------|------|------------------------|
| POST | `/credit-risk` | `{ "applicant": { ... } }` | `risk_prediction`, `risk_probability`, `top_factors` |
| POST | `/churn` | `{ "customer": { ... } }` | `churn_prediction`, `churn_probability`, `top_factors` |
| POST | `/sales-forecast` | `{ "features": { ... } }` | `predicted_sales`, `confidence_note` |
| POST | `/customer-segment` | `{ "customer": { ... } }` | `segment`, `cluster_id`, `profile_note` |
| POST | `/spam-check` | `{ "text": "..." }` | `is_spam`, `confidence`, `label` |
| POST | `/fraud-check` | `{ "features": { ... } }` | `is_anomalous`, `anomaly_score`, `risk_note` |

Example:

```bash
curl -X POST http://localhost:8000/api/v1/ml/spam-check \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"text":"FREE PRIZE click now!!!"}'
```

**Codes:** `200`; `422` empty/invalid; `503` missing `.pkl`; `502` other predict errors; `401`.

---

### Tools — `/api/v1/tools`

#### `POST /api/v1/tools/execute-code`

**For:** Run Python without an LLM (frontend “Run code”).  
**Body:** `{ "code": "print(1+1)" }` (1–20000 chars)  
**Inside:** `execute_python_code` → subprocess in temp dir, default timeout 10s.  
**Success data:** `{ "stdout", "stderr", "exit_code", "success" }`  
**Codes:** `200`, `422`, `502`, `401`.  
**Security:** Not a production jail — see [§12](#12-local-subprocess-code-runner-not-docker--gvisor--e2b).

---

## Database schema

### ER diagram (ASCII)

```text
┌──────────────────────┐
│ users                │
│──────────────────────│
│ id PK                │
│ email UNIQUE         │
│ name, second_name    │
│ hashed_password      │
│ is_active            │
│ created_at, updated  │
└──────────┬───────────┘
           │ 1
           │
     ┌─────┴──────┐
     │            │
     │ *          │ *
┌────▼─────────┐  ┌▼────────────────┐
│ tasks        │  │ documents       │
│──────────────│  │─────────────────│
│ id PK        │  │ id PK           │
│ user_id FK   │  │ user_id FK      │
│ agent_type   │  │ filename        │
│ prompt       │  │ file_path       │
│ result       │  │ file_type       │
│ plan_details │  │ status          │
│ result_file_ │  │ chunk_count     │
│   path       │  │ error_message   │
│ status       │  │ created_at,...  │
│ created_at,  │  └────────┬────────┘
│ updated_at   │           │
└──────────────┘           │ (logical, not SQL FK)
                           ▼
                    Chroma collection
                    metadata: user_id,
                    document_id, filename,
                    chunk_index
```

### `users` — why columns exist

| Column | Why it exists |
|--------|----------------|
| `id` | Primary key; stored in JWT `sub` |
| `email` | Login identifier; unique |
| `name`, `second_name` | Profile display |
| `hashed_password` | bcrypt only — never plain text |
| `is_active` | Soft-disable without deleting history |
| `created_at`, `updated_at` | Audit / UI |

### `tasks` — why columns exist

| Column | Why it exists |
|--------|----------------|
| `user_id` | Ownership / isolation |
| `agent_type` | Which agent (or `email_send`) created the row |
| `prompt` | Original user input |
| `result` | Final text output (or error message on failure) |
| `plan_details` | Manager plan + step_results as JSON text for UI |
| `result_file_path` | Optional downloadable artifact path (PPT-ready; unused until PPT exists) |
| `status` | Lifecycle for history filters |

**Task status values**

| Status | Meaning |
|--------|---------|
| `pending` | Created via `POST /tasks` but not run yet |
| `running` | Agent endpoint started work |
| `completed` | Finished successfully |
| `failed` | Timeout or exception (message often in `result`) |

Index `(user_id, created_at)` speeds history lists.

### `documents` — why columns exist

| Column | Why it exists |
|--------|----------------|
| `user_id` | Ownership |
| `filename` | Original name for UI/sources |
| `file_path` | Where bytes live under `uploads/` |
| `file_type` | Extension for parser dispatch |
| `status` | Upload/index pipeline state |
| `chunk_count` | How many Chroma chunks after success |
| `error_message` | Why indexing failed |

**Document status values:** `uploaded` → `processing` → `indexed` | `failed`

### Migrations (Alembic)

1. `aa75432bb21f` — users + tasks  
2. `60b15242eb7c` — `users.second_name`  
3. `c3d9e8f1a2b0` — documents  
4. `d4e8a1b2c3f0` — `tasks.plan_details`  
5. `e5f1a2b3c4d0` — `tasks.result_file_path` + indexes  

Always run `alembic upgrade head` after pull.

---

## Document upload & indexing pipeline

```text
multipart upload
      |
      v
validate extension + size (<=10MB) + non-empty
      |
      v
save bytes -> uploads/{uuid}_{original_name}
      |
      v
INSERT documents (status=uploaded, chunk_count=0)
      |
      v
HTTP 200 returns {document_id, filename, status}
      |
      v  (BackgroundTasks — after response)
process_document_job(document_id)
      |
      v
status=processing
      |
      v
extract_text(file_path, file_type)
  .pdf  -> pdfplumber (text layer only — NO OCR)
  .docx -> python-docx paragraphs
  .xlsx/.csv -> pandas rows as "col=value | ..."
  .txt  -> utf-8 (replace errors)
      |
      v
split_text (500 chars, 50 overlap)
      |
      v
embed_batch (MiniLM)
      |
      v
Chroma add_chunks with metadata:
  {user_id, document_id, filename, chunk_index}
  ids: doc{id}_chunk{i}
      |
      +--> success: status=indexed, chunk_count=N
      +--> error:   status=failed, error_message=...
```

**Supported types:** `.pdf`, `.docx`, `.xlsx`, `.csv`, `.txt`  
**No OCR:** scanned/image-only PDFs often yield empty text → `failed` with “No extractable text…”. OCR is an explicit future enhancement (not installed).

**If the API process dies mid-job:** the background work is lost; the row may stay `processing` or later `failed` depending on timing — acceptable for local learning (no Celery).

---

## RAG query pipeline

```text
POST /documents/query { question }
      |
      v
auth -> user_id
      |
      v
embed_text(question)   # MiniLM
      |
      v
Chroma query(embedding, where user_id=..., top_k=5)
      |
      +-- no matches --> return fixed NO_CONTEXT_ANSWER
      |                  sources=[], chunks_found=0
      |                  *** does NOT call Groq ***
      |
      +-- matches --> build prompt with excerpts
                        |
                        v
                   ask_llm_sync (Groq)
                        |
                        v
                   { answer, sources[{filename, chunk_preview}], chunks_found }
```

**Why skip the LLM when there is no context:** Empty context invites hallucination. The service returns a clear “upload/index first” style message instead.

**Research Agent:** Uses `tools/rag_tool.py` (`document_rag_search`) bound to the same `user_id` filter — same isolation idea inside CrewAI.

Timeout on the HTTP route: **60 seconds**.

---

## ML train → predict → API lifecycle

```text
data/*.csv
    |
    v
python -m ml.train_<name>
    |
    v
joblib.dump(artifact) -> ml/models/<name>.pkl
    |
    +------------------+------------------+
    |                                     |
    v                                     v
ml/predict_*.py                      (optional charts .png)
load once (module cache)
    |
    +------------+------------+
    |                         |
    v                         v
POST /api/v1/ml/*          tools/*_tool.py
(routers/ml.py)            (called by agents)
```

If `.pkl` is missing: `FileNotFoundError` → API **503**; agent tools surface an error string to the LLM.

### All 6 custom models

| Model | Algorithm | Train module | Predict module | `.pkl` file | Dataset (expected) | Used by |
|-------|-----------|--------------|----------------|-------------|--------------------|---------|
| Churn | RandomForest classifier | `train_churn_model` | `predict_churn` | `churn_model.pkl` | `data/telco_churn.csv` | `/ml/churn`, Analytics |
| Credit risk | RandomForest classifier | `train_credit_risk_model` | `predict_credit_risk` | `credit_risk_model.pkl` | `data/loan_data.csv` | `/ml/credit-risk`, Finance |
| Sales forecast | RandomForest regressor | `train_sales_forecast_model` | `predict_sales_forecast` | `sales_forecast_model.pkl` | `data/sales_data.csv` | `/ml/sales-forecast`, Analytics |
| Segments | K-Means (+ scaler) | `train_customer_segments` | `predict_customer_segment` | `segmentation_model.pkl` | `data/mall_customers.csv` | `/ml/customer-segment`, Analytics |
| Spam | TF-IDF + MultinomialNB | `train_spam_classifier` | `predict_spam` | `spam_classifier.pkl` | `data/spam_dataset.csv` | `/ml/spam-check`, Email |
| Fraud | IsolationForest | `train_fraud_detector` | `predict_fraud` | `fraud_detector.pkl` | `data/fraud_transactions.csv` | `/ml/fraud-check`, Finance |

**Also (not `.pkl` in this repo):** MiniLM embeddings and DistilBERT tone — downloaded from HuggingFace on first use.

---

## Authentication / authorization

*(Rationale: [§3 JWT + bcrypt](#3-jwt--bcrypt-not-sessions-in-redis--oauth-social-login).)*

### Sequence (register → login → protected call)

```text
Client                    FastAPI                     Postgres
  |                          |                           |
  | POST /auth/register      |                           |
  |------------------------->| hash password             |
  |                          |-------------------------->| INSERT users
  |                          |<--------------------------|
  | 201 UserResponse         |                           |
  |<-------------------------|                           |
  |                          |                           |
  | POST /auth/login         |                           |
  |------------------------->| verify bcrypt             |
  |                          |-------------------------->| SELECT user
  |                          | create JWT(sub=user.id)   |
  | 200 {access_token,user}  |                           |
  |<-------------------------|                           |
  |                          |                           |
  | GET /agents/...          |                           |
  | Authorization: Bearer …  |                           |
  |------------------------->| get_current_user:         |
  |                          |  decode JWT               |
  |                          |  load User by sub         |
  |                          |  reject if inactive       |
  |                          | run agent / ML / ...      |
```

### What `get_current_active_user` does

Defined in `core/dependencies.py`:

1. `OAuth2PasswordBearer` reads `Authorization: Bearer …`
2. `decode_access_token` with `SECRET_KEY` / `ALGORITHM`
3. Read `sub` as user id; load `User` from DB
4. If missing user → **401**
5. If `is_active` is false → **403**
6. Else inject `User` into the route

`get_current_active_user` is a thin alias over `get_current_user` (same behavior; clearer name for routes).

### Ownership checks

| Resource | Rule |
|----------|------|
| Tasks | Queries always include `Task.user_id == current_user.id` for get/delete/download |
| Documents | Same for get/delete; list filters by `user_id` |
| Chroma | `where={"user_id": user_id}` on query; chunks written with that metadata at index time |
| Users `GET /{user_id}` | Any logged-in user can look up another profile (by design today) |

### Logout

API returns success; frontend deletes token from storage. Tokens remain valid until expiry (no Redis blacklist).

---

## Agents and tools (deep dive)

*(Rationale: [§9](#9-agents--tools-layout-not-one-giant-prompt--not-ml-only), [§10](#10-direct-ml-routes-and-agent-tools-both-used-on-purpose).)*

### Research Agent

| | |
|--|--|
| **When to use** | Web research and/or questions about **this user’s** uploaded docs |
| **Tools** | `duck_duck_go_search`, `document_rag_search` |
| **Typical flow** | CrewAI Task → LLM may call search and/or RAG → bullet summary |
| **Timeout** | 90s |
| **Needs** | `GROQ_API_KEY`; RAG only useful if user has `indexed` docs |

### Finance Agent

| | |
|--|--|
| **When to use** | Loan risk, fraud anomaly narrative, finance memos |
| **Tools** | `credit_risk_predictor`, `fraud_transaction_checker` |
| **Typical flow** | LLM decides whether to call tools with JSON features → explains numbers |
| **Timeout** | 90s |
| **Needs** | Groq; `.pkl` for tools or tool returns “train first” style errors |

### Analytics Agent

| | |
|--|--|
| **When to use** | Churn, sales forecast, customer segments in natural language |
| **Tools** | `churn_predictor`, `sales_forecast_predictor`, `customer_segment_predictor` |
| **Timeout** | 90s |

### Coding Agent

| | |
|--|--|
| **When to use** | Small Python write/test loops |
| **Tools** | `execute_python_code` (subprocess, default 10s per run) |
| **Timeout** | 120s (HTTP) |
| **Caveat** | Soft sandbox only — not safe for untrusted users |

### Email Agent

| | |
|--|--|
| **When to use** | Draft professional emails; optionally screen pasted text for spam |
| **Tools** | `spam_message_classifier` (for pasted/incoming-style text when asked) |
| **Typical flow** | Draft → parse SUBJECT/BODY → optional DistilBERT sentiment (advisory) |
| **Timeout** | 90s |
| **Send** | Separate endpoint; SendGrid optional |

### Manager Agent (Approach B — used by API)

| | |
|--|--|
| **When to use** | Multi-part requests needing several specialists |
| **Tools** | None of its own — calls other agents’ `run_*` |
| **Timeout** | 300s |

**Approach B steps:**

```text
1. create_plan(request)
   - LLM returns JSON: {"steps":[{"agent":"research","subtask":"..."}, ...]}
   - Parse/normalize aliases; cap at 6 steps
   - On parse failure: retry once; then fall back to single research step

2. For each step in order:
   - Enrich subtask with prior step context (last 3 outputs)
   - Call matching run_research / run_finance_analysis / ...
   - ppt -> skip message (not built)
   - Record step_results[{agent, subtask, status, output}]

3. Combine step_results with another LLM call -> final_response

4. Router stores final_response in Task.result and
   plan+step_results JSON in Task.plan_details
```

**Approach A** (`run_manager_delegation`, CrewAI `allow_delegation=True`) exists for learning/comparison only — **HTTP API does not call it**.

**PPT skip:** Plans that include `ppt` / presentation / slides get a clear skip string instead of crashing the chain.

### Shared LLM

Agents build `langchain_groq.ChatGroq` with `GROQ_MODEL` (default `llama-3.3-70b-versatile`). RAG uses `services/llm_service.py` for simple completions.

---

## Background jobs / queues

*(Rationale: [§11](#11-fastapi-backgroundtasks-not-celery--redis--rq).)*

### Contrast: BackgroundTasks vs waiting agent requests

| | Document indexing | Agent / RAG / ML predict |
|--|-------------------|---------------------------|
| **Mechanism** | FastAPI `BackgroundTasks` | Same HTTP request waits |
| **Client sees** | Immediate `{status: uploaded}` | Blocks until done or timeout |
| **Timeout** | None on background job itself | 60–300s via `asyncio.wait_for` |
| **Process die mid-work** | Job lost; row may stick | Client gets error; Task often `failed` |
| **Extra infra** | None | None |

- **No Celery, Redis queue, RQ, or APScheduler** in this project.
- Document indexing: `services/document_service.py` → `process_document_job` opens its own DB session.
- Agent/RAG work: `run_in_threadpool` / `asyncio.to_thread` so the async event loop stays responsive, but the **client still waits**.
- JWT logout is client-side only (no Redis token blacklist).

---

## Tests

### How to run

```bash
source venv/bin/activate
pytest -q
```

One file:

```bash
pytest tests/test_predict_churn.py -q
pytest tests/test_documents_router.py -q
```

### What pytest covers (high level)

| Area | Example files | Notes |
|------|---------------|-------|
| ML predictors | `test_predict_churn.py`, `test_predict_credit_risk.py`, `test_predict_sales_forecast.py`, `test_predict_customer_segment.py`, `test_predict_spam.py`, `test_predict_fraud.py` | Often `@pytest.mark.skipif` when `.pkl` missing |
| ML router spam/fraud | `test_ml_spam_fraud_router.py` | API-level |
| Agents / routers | `test_agents_router.py`, `test_finance_router.py`, `test_analytics_router.py`, `test_coding_router.py`, `test_email_router.py`, `test_manager_router.py`, `test_manager_agent.py`, `test_research_agent.py` | May need env/mocks — TODO: confirm which need live Groq |
| Documents / RAG / vectorstore | `test_documents_router.py`, `test_rag_service.py`, `test_vectorstore.py` | |
| Tasks / code tool / sentiment | `test_tasks_router.py`, `test_code_execution_tool.py`, `test_sentiment_service.py` | Sentiment skips if DistilBERT cannot load |

### Skip-if-no-pkl behavior

Predict tests check whether the model file exists (or call a helper like `model_ready()`). If training was never run on this machine, those tests **skip** instead of failing the whole suite. Train models locally if you want those tests to execute.

### Smoke scripts (manual)

```bash
python -m scripts.test_vectorstore
python -m scripts.test_churn_prediction
python -m scripts.test_credit_risk_prediction
python -m scripts.test_sales_forecast
python -m scripts.test_segment_prediction
python -m scripts.test_spam_classifier
python -m scripts.test_fraud_detection
python -m scripts.test_research_agent
```

These are for interactive checks, not a substitute for `pytest`.

---

## Third-party services

*(Rationale: [§4](#4-groq--crewai-not-openai-only--not-llm-for-everything)–[§6](#6-chromadb--minilm-not-qdrant--openai-embeddings--pinecone), [§8](#8-distilbert-tone-not-training-our-own-sentiment-model), [§16](#16-cors-locked-to-localhost3000-not-).)*

| Service | Role | API key? | Used because… | Not replaced by… |
|---------|------|----------|---------------|------------------|
| **Groq** | All LLM agents + RAG answers | Yes — `GROQ_API_KEY` | Fast hosted LLM for demos | Local giant LLMs / OpenAI-as-default |
| **DuckDuckGo** | Research web search | No | Free, no key | Google/SerpAPI billing |
| **ChromaDB** | Local vector index in `chroma_data/` | No | No Docker vector server | Qdrant/Pinecone |
| **sentence-transformers** | MiniLM embeddings (~80MB once) | No | Free CPU embeddings | OpenAI embedding API |
| **HuggingFace transformers** | DistilBERT SST-2 email tone (~260MB once) | No | Pretrained tone, no training | Custom sentiment training |
| **SendGrid** | Optional email delivery | Optional | Real send when configured | Required mail for drafts |
| **Kaggle CSVs** | Offline training under `data/` | Manual download | Reproducible local ML | Calling LLM instead of `.pkl` |

No Docker, OpenAI-as-default, or Qdrant in the current design. CORS allows `http://localhost:3000` only (`main.py`).

---

## Related day writeups

Day-by-day notes (`DAY_*.md`, `PROJECT_FULL_STATUS.md`) live in this repo for learning history. Prefer this file + README for onboarding.

### Known gaps / TODO markers in this doc

- Exact Python version in every environment — TODO: confirm (`NOTE.MD` mentions 3.12)
- Whether leftover `*/test.py` and `agents/exapmle.py` are intentional — TODO: confirm
- Which router tests require a live Groq key vs mocks — TODO: confirm
- Production process manager (Gunicorn vs Uvicorn workers) — TODO: confirm (see README)
