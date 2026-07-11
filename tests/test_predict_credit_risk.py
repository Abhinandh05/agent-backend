"""Pytest for predict_credit_risk — skips if .pkl not trained yet."""
from pathlib import Path

import pytest

from ml.predict_credit_risk import MODEL_PATH, predict_credit_risk

MODEL_EXISTS = MODEL_PATH.is_file()

SAMPLE_APPLICANT = {
    "Gender": "Male",
    "Married": "Yes",
    "Dependents": "0",
    "Education": "Graduate",
    "Self_Employed": "No",
    "ApplicantIncome": 5000,
    "CoapplicantIncome": 0.0,
    "LoanAmount": 120.0,
    "Loan_Amount_Term": 360.0,
    "Credit_History": 1.0,
    "Property_Area": "Urban",
}


@pytest.mark.skipif(
    not MODEL_EXISTS,
    reason=f"Model not found at {MODEL_PATH}; run: python -m ml.train_credit_risk_model",
)
def test_predict_credit_risk_shape_and_probability():
    result = predict_credit_risk(SAMPLE_APPLICANT)

    assert isinstance(result, dict)
    assert set(result.keys()) >= {
        "risk_prediction",
        "risk_probability",
        "top_factors",
    }
    assert result["risk_prediction"] in ("Approve", "Reject")
    assert 0.0 <= float(result["risk_probability"]) <= 1.0
    assert isinstance(result["top_factors"], list)
