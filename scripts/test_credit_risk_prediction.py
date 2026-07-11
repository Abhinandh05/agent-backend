"""
Sanity-check credit risk predictions with hardcoded applicants.

Usage (after training):
    python -m scripts.test_credit_risk_prediction
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.predict_credit_risk import model_ready, predict_credit_risk

# Fields match the common Dream Housing / Loan Prediction Problem Dataset.
# If your CSV uses different names, training still works; adjust these examples
# to match your headers when testing.
EXAMPLES = [
    {
        "name": "Low-risk: good credit history, stable income, modest loan",
        "applicant": {
            "Gender": "Male",
            "Married": "Yes",
            "Dependents": "0",
            "Education": "Graduate",
            "Self_Employed": "No",
            "ApplicantIncome": 5849,
            "CoapplicantIncome": 0.0,
            "LoanAmount": 120.0,
            "Loan_Amount_Term": 360.0,
            "Credit_History": 1.0,
            "Property_Area": "Urban",
        },
    },
    {
        "name": "Higher-risk: no credit history, high loan vs income",
        "applicant": {
            "Gender": "Male",
            "Married": "No",
            "Dependents": "3+",
            "Education": "Not Graduate",
            "Self_Employed": "Yes",
            "ApplicantIncome": 1500,
            "CoapplicantIncome": 0.0,
            "LoanAmount": 300.0,
            "Loan_Amount_Term": 180.0,
            "Credit_History": 0.0,
            "Property_Area": "Rural",
        },
    },
    {
        "name": "Mid-risk: average income, some co-applicant support",
        "applicant": {
            "Gender": "Female",
            "Married": "Yes",
            "Dependents": "1",
            "Education": "Graduate",
            "Self_Employed": "No",
            "ApplicantIncome": 3200,
            "CoapplicantIncome": 1500.0,
            "LoanAmount": 150.0,
            "Loan_Amount_Term": 360.0,
            "Credit_History": 1.0,
            "Property_Area": "Semiurban",
        },
    },
]


def main() -> int:
    if not model_ready():
        print(
            "ERROR: Model file missing. Train first:\n"
            "  python -m ml.train_credit_risk_model"
        )
        return 1

    print("=== Credit risk prediction smoke test ===\n")
    for ex in EXAMPLES:
        result = predict_credit_risk(ex["applicant"])
        print(f"→ {ex['name']}")
        print(json.dumps(result, indent=2))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
