# Day 12 — Customer Churn ML Model

Summary of what was built for the **Analytics Agent** foundation: a real trained
scikit-learn classifier (not an LLM) that predicts Telco customer churn.

## What this is
| Item | Detail |
|------|--------|
| Problem | Binary classification: will the customer churn? (`Yes` / `No`) |
| Algorithm | `RandomForestClassifier` (`n_estimators=200`, `class_weight='balanced'`, `random_state=42`) |
| Hardware | **CPU only** — no GPU, no TensorFlow, no PyTorch for this model |
| Dataset | Telco Customer Churn (~7k rows) from Kaggle |
| Runtime | Training usually finishes in **seconds to ~1 minute** |

## Files created
```
ml/
├── __init__.py
├── train_churn_model.py   # Train once → saves .pkl + feature chart
├── predict_churn.py       # predict_churn(customer_dict) → result dict
└── models/                # churn_model.pkl, feature_importance.png (gitignored)
data/
└── telco_churn.csv        # You place this manually (gitignored)
scripts/
└── test_churn_prediction.py
tests/
└── test_predict_churn.py
```

## Modeling choices (why)
1. **TotalCharges blanks** — coerce to numeric, **drop** ~11 bad rows (safer than inventing values).
2. **Encoding** — `pandas.get_dummies` on categoricals; save the resulting column list with the model so predict-time alignment matches training (avoids a common train/serve skew bug).
3. **Split** — 80/20 stratified on `Churn`, `random_state=42`.
4. **class_weight='balanced'** — churn is the minority class (~26%); this reduces bias toward always predicting “No”.
5. **top_factors** — global RandomForest feature importances (not per-row SHAP; SHAP is a future enhancement).

## Prediction output shape
```json
{
  "churn_prediction": "Yes",
  "churn_probability": 0.72,
  "top_factors": [
    {"feature": "tenure", "importance": 0.15},
    {"feature": "MonthlyCharges", "importance": 0.12}
  ]
}
```

## Step-by-step for you

### 1) Download the dataset
1. Open https://www.kaggle.com/datasets/blastchar/telco-customer-churn  
2. Download the CSV (free Kaggle account).  
3. Save it as:
   ```
   /home/abhinandh/Desktop/afsuu/agent-backend/data/telco_churn.csv
   ```

### 2) Install deps (if needed) + train
```bash
cd /home/abhinandh/Desktop/afsuu/agent-backend
source venv/bin/activate
pip install pandas joblib matplotlib "scikit-learn>=1.4,<1.6"
python -m ml.train_churn_model
```

**What you should see**
- Row counts + churn rates  
- `classification_report` with accuracy / precision / recall / F1  
- Confusion matrix  
- Paths to `ml/models/churn_model.pkl` and `ml/models/feature_importance.png`  
- Final summary: accuracy + “trained on CPU”

If the CSV is missing, you get a clear error with the exact path and Kaggle link.

### 3) Run prediction smoke test
```bash
python -m scripts.test_churn_prediction
```

**What you should see**
- Loyal long-tenure customer → lower `churn_probability`  
- New month-to-month / high charges → higher `churn_probability`  
- Mid-tenure one-year → somewhere in between  

### 4) Pytest
```bash
pytest tests/test_predict_churn.py -q
```
Skips if the model `.pkl` is not present yet.

## Not in this step (follow-up)
- No FastAPI route yet  
- Not wired into an Analytics Agent / CrewAI tool yet  
- No frontend UI  

Those come after training is confirmed working.

## Gitignore
- `data/telco_churn.csv`  
- `ml/models/*.pkl`  
- `ml/models/*.png`  

Retrain after cloning a fresh copy of the repo.
https://www.kaggle.com/datasets/blastchar/telco-customer-churn