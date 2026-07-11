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
