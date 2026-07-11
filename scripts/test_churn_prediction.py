"""
Sanity-check the churn model with a few hardcoded customers.

Usage (from backend root, after training):
    python -m scripts.test_churn_prediction
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.predict_churn import model_ready, predict_churn


# Shared baseline fields so each example only overrides what matters
_BASE = {
    "gender": "Female",
    "SeniorCitizen": 0,
    "Partner": "Yes",
    "Dependents": "No",
    "PhoneService": "Yes",
    "MultipleLines": "No",
    "InternetService": "Fiber optic",
    "OnlineSecurity": "No",
    "OnlineBackup": "No",
    "DeviceProtection": "No",
    "TechSupport": "No",
    "StreamingTV": "No",
    "StreamingMovies": "No",
    "PaperlessBilling": "Yes",
    "PaymentMethod": "Electronic check",
}


EXAMPLES = [
    {
        "name": "Loyal long-tenure customer (expect low churn)",
        "customer": {
            **_BASE,
            "tenure": 60,
            "Contract": "Two year",
            "MonthlyCharges": 35.0,
            "TotalCharges": 2100.0,
            "InternetService": "DSL",
            "OnlineSecurity": "Yes",
            "TechSupport": "Yes",
            "PaymentMethod": "Bank transfer (automatic)",
        },
    },
    {
        "name": "New month-to-month high-charge (expect high churn)",
        "customer": {
            **_BASE,
            "tenure": 1,
            "Contract": "Month-to-month",
            "MonthlyCharges": 95.0,
            "TotalCharges": 95.0,
            "InternetService": "Fiber optic",
            "PaymentMethod": "Electronic check",
        },
    },
    {
        "name": "Mid-tenure one-year contract (mixed)",
        "customer": {
            **_BASE,
            "tenure": 24,
            "Contract": "One year",
            "MonthlyCharges": 65.0,
            "TotalCharges": 1560.0,
            "Partner": "Yes",
            "Dependents": "Yes",
        },
    },
]


def main() -> int:
    if not model_ready():
        print(
            "ERROR: Model file missing. Train first:\n"
            "  python -m ml.train_churn_model"
        )
        return 1

    print("=== Churn prediction smoke test ===\n")
    for ex in EXAMPLES:
        result = predict_churn(ex["customer"])
        print(f"→ {ex['name']}")
        print(json.dumps(result, indent=2))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
