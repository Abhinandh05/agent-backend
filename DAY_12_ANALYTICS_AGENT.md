# Day 12 — Analytics Agent + Churn Tool + Sales Forecasting

What was built for Day 12 of the AI Multi-Agent Business Operating System.

## Overview
Three capabilities, combined:

1. **LLM Analytics Agent** (Groq + CrewAI) — trends, insights, and model-backed answers  
2. **Churn model wired as a tool + direct API** — existing Day-8 `predict_churn()`  
3. **Sales forecasting RandomForestRegressor** — new regression model on Superstore-style sales data  

CPU-only; no Docker / GPU. Widgets for direct ML forms noted as a follow-up (chat page shipped today).

---

## Files created / updated

### ML (sales forecast — new)
| File | Purpose |
|------|---------|
| `ml/train_sales_forecast_model.py` | Train RF regressor on `data/sales_data.csv` (prints columns, auto-detects) |
| `ml/predict_sales_forecast.py` | `predict_sales(features) → {predicted_sales, confidence_note}` |
| `ml/models/sales_forecast_model.pkl` | Generated after training (gitignored) |
| `ml/models/sales_forecast_accuracy.png` | Actual vs predicted chart (gitignored) |
| `scripts/test_sales_forecast.py` | 3 hardcoded forecast examples |
| `tests/test_predict_sales_forecast.py` | Shape tests (skips if no `.pkl`) |

### Churn wiring (existing model)
| File | Purpose |
|------|---------|
| `tools/churn_tool.py` | LangChain Tool wrapping `predict_churn()` |
| `POST /api/v1/ml/churn` | Direct prediction (no LLM) |

### Agent + sales tool
| File | Purpose |
|------|---------|
| `agents/analytics_agent.py` | CrewAI Business Data Analyst + `run_analytics()` |
| `tools/sales_forecast_tool.py` | LangChain Tool wrapping `predict_sales()` |

### API
| Endpoint | Purpose |
|----------|---------|
| `POST /api/v1/agents/analytics` | LLM agent (auth, threadpool, 90s timeout, Task row, `agent_type='analytics'`) |
| `POST /api/v1/ml/churn` | Direct churn prediction |
| `POST /api/v1/ml/sales-forecast` | Direct sales forecast |

Schemas: `AnalyticsRequest`, `ChurnRequest`, `SalesForecastRequest` in `schemas.py`.  
Routers: `routers/agents.py`, `routers/ml.py`.

### Frontend
| File | Purpose |
|------|---------|
| `afsuu_Frontend/app/agents/analytics/page.jsx` | Reuses `AgentChat` (`agentName="Analytics"`) |
| Dashboard nav + Quick Action | Links to `/agents/analytics` |

### Tests / docs
| File | Purpose |
|------|---------|
| `tests/test_analytics_router.py` | 401 / 200 / 422 for analytics route |
| `DAY_12_ANALYTICS_AGENT.md` | This summary |
| `README.md` | Day 12 section added |

(`DAY_12_CHURN_ML.md` remains the earlier churn-training notes.)

---

## Modeling notes (sales forecast)
- Prints real CSV headers first; auto-detects date (`Order Date`, …) and sales (`Sales`, `Revenue`, …)
- **Calendar features** (`year`, `month`, `day_of_week`, `quarter`) — main retail seasonality signal
- **Aggregation**: daily totals by Category / Region / Segment (line-items → sensible forecast grain)
- **Time-based 80/20 split** — train on earlier dates, test on later; **no shuffle** (avoids future leakage)
- **RandomForestRegressor** (`n_estimators=200`, `random_state=42`) — CPU-friendly baseline (Prophet/ARIMA/XGBoost are advanced alternatives)
- Metrics: **MAE** and **RMSE** in dollars (not classification accuracy)

---

## TODO (follow-up)
- Optional quick widgets under the Analytics chat for `/ml/churn` and `/ml/sales-forecast` (LLM-free).

---

## Your steps

### 1) Dataset (recommended: Superstore)
**Recommend Superstore** over Store Sales Time Series — cleaner `Order Date` / `Sales` / `Category` / `Region` for a first regression model.

Download e.g.  
https://www.kaggle.com/datasets/vivek468/superstore-dataset-final  

Place as:
```text
agent-backend/data/sales_data.csv
```

(A Superstore CSV may already be present for local training; it is gitignored.)

### 2) Train sales forecast
```bash
source venv/bin/activate
python -m ml.train_sales_forecast_model
```
Expect: printed columns, aggregation row count, time-based split sizes,  
`MAE (average error): $…`, `RMSE …: $…`,  
saved `sales_forecast_model.pkl` + `sales_forecast_accuracy.png`.

On Sample Superstore (~10k line-items → ~6k daily Category/Region/Segment slices), expect roughly:

- **MAE ≈ $450–550** (average absolute $ error on held-out later dates)  
- **RMSE ≈ $900–1000**  

Exact numbers vary slightly by environment; this run printed **MAE $489.42 / RMSE $962.00**.

### 3) Prediction smoke tests
```bash
python -m scripts.test_churn_prediction
python -m scripts.test_sales_forecast
```

### 4) Pytest
```bash
pytest tests/test_predict_sales_forecast.py tests/test_analytics_router.py -q
```

### 5) curl (with JWT)

```bash
# Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"YOUR_EMAIL","password":"YOUR_PASSWORD"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Direct churn (fast, no LLM)
curl -s -X POST http://localhost:8000/api/v1/ml/churn \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "customer": {
      "gender":"Female","SeniorCitizen":0,"Partner":"Yes","Dependents":"No",
      "tenure":1,"PhoneService":"No","MultipleLines":"No phone service",
      "InternetService":"DSL","OnlineSecurity":"No","OnlineBackup":"Yes",
      "DeviceProtection":"No","TechSupport":"No","StreamingTV":"No",
      "StreamingMovies":"No","Contract":"Month-to-month",
      "PaperlessBilling":"Yes","PaymentMethod":"Electronic check",
      "MonthlyCharges":29.85,"TotalCharges":29.85
    }
  }'

# Direct sales forecast (fast, no LLM)
curl -s -X POST http://localhost:8000/api/v1/ml/sales-forecast \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "features": {
      "year": 2017, "month": 11, "day_of_week": 1, "quarter": 4,
      "Category": "Technology", "Region": "West", "Segment": "Consumer"
    }
  }'

# Analytics LLM agent
curl -s -X POST http://localhost:8000/api/v1/agents/analytics \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"request":"Forecast Technology sales in the West for November, and explain seasonality"}'
```

### 6) Frontend
```bash
cd ../afsuu_Frontend && npm run dev
```
Log in → **Analytics Agent** → submit a request.
