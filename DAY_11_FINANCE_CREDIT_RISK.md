# Day 11 — Finance Agent + Credit Risk ML

What was built for Day 11 of the AI Multi-Agent Business Operating System.

## Overview
Two capabilities, combined:

1. **LLM Finance Agent** (Groq + CrewAI) — financial analysis, ratios, investment memos  
2. **Trained credit-risk RandomForest** — numeric loan Approve/Reject scoring, callable as an agent tool and via a direct FastAPI endpoint  

CPU-only; no Docker / GPU.

---

## Files created / updated

### ML
| File | Purpose |
|------|---------|
| `ml/train_credit_risk_model.py` | Train RF on `data/loan_data.csv` (auto-detects columns) |
| `ml/predict_credit_risk.py` | `predict_credit_risk(applicant) → dict` |
| `ml/models/credit_risk_model.pkl` | Generated after training (gitignored) |
| `ml/models/credit_feature_importance.png` | Top-10 chart (gitignored) |
| `scripts/test_credit_risk_prediction.py` | 3 hardcoded applicants |
| `tests/test_predict_credit_risk.py` | Shape/probability tests (skips if no `.pkl`) |

### Agent + tools
| File | Purpose |
|------|---------|
| `agents/finance_agent.py` | CrewAI Finance Analyst + `run_finance_analysis()` |
| `tools/credit_risk_tool.py` | LangChain Tool wrapping the RF model |

### API
| Endpoint | Purpose |
|----------|---------|
| `POST /api/v1/agents/finance` | LLM agent (auth, threadpool, 90s timeout, Task row) |
| `POST /api/v1/ml/credit-risk` | Direct model prediction (no LLM, fast) |

Routers: `routers/agents.py` (finance route), `routers/ml.py` (new), registered in `main.py`.  
Schemas: `FinanceRequest`, `CreditRiskRequest` in `schemas.py`.

### Frontend
| File | Purpose |
|------|---------|
| `afsuu_Frontend/app/agents/finance/page.jsx` | Reuses `AgentChat` |
| Dashboard nav + Quick Action | Links to `/agents/finance` |

### Tests
| File | Purpose |
|------|---------|
| `tests/test_finance_router.py` | 401 / 200 / 422 for finance route |

### Docs
| File | Purpose |
|------|---------|
| `DAY_11_FINANCE_CREDIT_RISK.md` | This summary |
| `README.md` | Day 11 section added |

---

## Modeling notes
- Prints real CSV headers first; auto-detects label (`Loan_Status`, `default`, …) and ID columns  
- Missing values: **median** (numeric), **mode** (categorical)  
- Encoding: `get_dummies` + saved column list (same pattern as churn)  
- RF: `n_estimators=200`, `class_weight='balanced'`, `random_state=42`  
- API labels: `Approve` / `Reject` + `risk_probability` = P(Approve)

---

## TODO (skipped today)
- `services/rag_service.py` does not exist yet — RAG for financial PDFs noted as TODO in finance agent / credit tool comments (Days 9–10).

---

## Your steps

### 1) Dataset
Download e.g.  
https://www.kaggle.com/datasets/altruistdelhite04/loan-prediction-problem-dataset  

Place as:
```text
agent-backend/data/loan_data.csv
```

### 2) Train
```bash
source venv/bin/activate
python -m ml.train_credit_risk_model
```
Expect: printed columns, imputation logs, classification report, confusion matrix,  
saved `credit_risk_model.pkl` + `credit_feature_importance.png`.

### 3) Prediction smoke test
```bash
python -m scripts.test_credit_risk_prediction
```

### 4) curl (with JWT)

```bash
# Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"YOUR_EMAIL","password":"YOUR_PASSWORD"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Direct ML (fast, no LLM)
curl -s -X POST http://localhost:8000/api/v1/ml/credit-risk \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "applicant": {
      "Gender":"Male","Married":"Yes","Dependents":"0","Education":"Graduate",
      "Self_Employed":"No","ApplicantIncome":5849,"CoapplicantIncome":0,
      "LoanAmount":120,"Loan_Amount_Term":360,"Credit_History":1,
      "Property_Area":"Urban"
    }
  }'

# Finance LLM agent
curl -s -X POST http://localhost:8000/api/v1/agents/finance \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"request":"Assess loan for applicant income 5849, credit history 1, loan amount 120, urban property"}'
```

### 5) Frontend
```bash
cd ../afsuu_Frontend && npm run dev
```
Log in → **Finance Agent** → submit a request.
