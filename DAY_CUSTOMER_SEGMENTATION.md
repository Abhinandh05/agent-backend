# Customer Segmentation — K-Means (Unsupervised)

What was built for the **Analytics Agent extension**: a self-trained unsupervised
ML model for customer segmentation using K-Means clustering.

CPU-only; no Docker / GPU. No labels in the data — the model discovers groups
from Age, Annual Income, and Spending Score on its own.

---

## Why Customer Segmentation (K-Means) matters

Customer segmentation (K-Means) matters in this project for two reasons:
**what it teaches you**, and **what a business would actually use it for**.

### Why it’s important for this project

Your other models are all **supervised**:

| Model | Type | Output |
|-------|------|--------|
| Churn | Classification | Yes / No |
| Credit risk | Classification | Approve / Reject |
| Sales forecast | Regression | A number ($) |

**Segmentation is unsupervised**: there is no label in the data. The model
finds groups from Age, Income, and Spending Score on its own. That fills a
real gap in the ML skills this OS demonstrates.

It’s also wired into the **Analytics Agent** so the system can answer
“what kind of customer is this?” the same way it already answers churn or
sales questions.

### What a business would actually use it for

Retail / marketing teams use segments to treat customers differently instead
of one-size-fits-all:

| Segment (example) | Typical use |
|-------------------|-------------|
| Premium Customers | Keep them with VIP offers, loyalty perks |
| Aspirational Spenders | Discounts, payment plans, entry luxury |
| Cautious High-Earners | Value messaging, quality over flashy promos |
| Budget-Conscious | Clear pricing, essentials, coupons |

In the API / agent flow: pass `age`, `annual_income`, `spending_score` → get a
**segment name + profile note** → use that in analytics chat or a future
frontend form.

---

## Overview — what was done

1. **Train** a K-Means model on Mall Customer Segmentation data (elbow method + scaling)
2. **Predict** a human-readable segment for a single customer
3. **Wire** it as a CrewAI tool on the Analytics Agent
4. **Expose** a direct ML endpoint (no LLM)
5. **Document / test** with smoke script + pytest

---

## Files created / updated

### ML (new)
| File | Purpose |
|------|---------|
| `ml/train_customer_segments.py` | Load CSV, scale features, elbow `k=2..10`, train K-Means, label clusters, save plots + `.pkl` |
| `ml/predict_customer_segment.py` | `predict_segment(customer) → {segment, cluster_id, profile_note}` |
| `ml/models/segmentation_model.pkl` | Generated after training (gitignored) |
| `ml/models/elbow_plot.png` | Inertia vs k (gitignored) |
| `ml/models/segments_scatter.png` | Income vs Spending Score by cluster (gitignored) |
| `scripts/test_segment_prediction.py` | 3 hardcoded customers for sanity-check |
| `tests/test_predict_customer_segment.py` | Shape tests (skips if no `.pkl`) |

### Agent + tool
| File | Purpose |
|------|---------|
| `tools/segmentation_tool.py` | LangChain Tool wrapping `predict_segment()` |
| `agents/analytics_agent.py` | Added `customer_segment_predictor` alongside churn + sales tools |

### API
| Endpoint | Purpose |
|----------|---------|
| `POST /api/v1/ml/customer-segment` | Direct segment prediction (JWT, no LLM) |

Schema: `CustomerSegmentRequest` in `schemas.py`.  
Router: `routers/ml.py`.

### Frontend
| File | Purpose |
|------|---------|
| `afsuu_Frontend/app/agents/analytics/page.jsx` | Copy updated to mention segmentation; quick ML form widgets still a follow-up |

### Docs
| File | Purpose |
|------|---------|
| `DAY_CUSTOMER_SEGMENTATION.md` | This summary |
| `README.md` | Section: **ML Model — Customer Segmentation (K-Means, Unsupervised)** |
| `PROJECT_FULL_STATUS.md` | Status + API map updated |

---

## Modeling notes (why scaling + elbow)

### Feature scaling (required for K-Means)
K-Means uses **Euclidean distance**. Age, income (k$), and spending score live
on different scales. Without `StandardScaler`, the largest-range feature would
dominate clustering. Random Forest does not need this (it splits one feature at
a time); K-Means does.

### Elbow method (choosing `k`)
- Train K-Means for `k = 2` through `k = 10`, record **inertia**
- Plot inertia vs k → `ml/models/elbow_plot.png`
- Pick the “knee” where adding clusters stops buying much reduction

On the Mall Customers CSV with **Age + Income + Spending**, the elbow often
lands near **k=4** (tutorials that use only Income + Spending often quote
**k=5**). Always re-check the plot for your CSV.

### Cluster labels
After fitting, mean Age / Income / Spending per cluster are computed and
mapped to business labels (e.g. Premium Customers, Aspirational Spenders).
Labels adapt to whatever centers the data actually produces — they are not
hardcoded as five fixed personas.

---

## Dataset

1. Download **Mall Customer Segmentation Data** from Kaggle:  
   https://www.kaggle.com/datasets/vjchoudhary7/customer-segmentation-tutorial-in-python  
2. Place / rename exactly to:
   ```
   data/mall_customers.csv
   ```

Typical columns: `CustomerID`, `Gender` (sometimes `Genre`), `Age`,
`Annual Income (k$)`, `Spending Score (1-100)`. Training prints actual headers
and resolves income/spending columns flexibly if naming differs.

CSV + `.pkl` + plots are **gitignored** — retrain after a fresh clone.

---

## How to run

### Train
```bash
source venv/bin/activate
python -m ml.train_customer_segments
```

Expect: printed columns, inertia table, chosen `k`, cluster profile table, plus
`segmentation_model.pkl`, `elbow_plot.png`, `segments_scatter.png`.

### Smoke test
```bash
python -m scripts.test_segment_prediction
```

### Unit test
```bash
pytest tests/test_predict_customer_segment.py -q
```

### Direct API (JWT)
```bash
curl -X POST http://localhost:8000/api/v1/ml/customer-segment \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"customer": {"age": 28, "annual_income": 75, "spending_score": 80}}'
```

Example response shape:
```json
{
  "success": true,
  "data": {
    "segment": "Premium Customers",
    "cluster_id": 1,
    "profile_note": "This customer fits the 'Premium Customers' profile: ..."
  },
  "message": "Customer segmentation completed",
  "error": null
}
```

---

## How to read the charts

| File | How to interpret |
|------|------------------|
| `ml/models/elbow_plot.png` | Y-axis = inertia (tighter clusters = lower). Look for the bend; red dashed line = chosen `k`. |
| `ml/models/segments_scatter.png` | Classic Income vs Spending Score view; each color is a segment; black X = centroids. |

---

## TODO (follow-up)

- Optional quick widget under Analytics chat for Age / Income / Spending Score
  → `POST /api/v1/ml/customer-segment` (same pattern as future churn / sales forms).
