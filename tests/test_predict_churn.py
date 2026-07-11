"""Pytest for predict_churn — skips gracefully if the .pkl is not trained yet."""
from pathlib import Path

import pytest

from ml.predict_churn import MODEL_PATH, predict_churn

MODEL_EXISTS = MODEL_PATH.is_file()

SAMPLE_CUSTOMER = {
    "gender": "Male",
    "SeniorCitizen": 0,
    "Partner": "No",
    "Dependents": "No",
    "tenure": 5,
    "PhoneService": "Yes",
    "MultipleLines": "No",
    "InternetService": "Fiber optic",
    "OnlineSecurity": "No",
    "OnlineBackup": "No",
    "DeviceProtection": "No",
    "TechSupport": "No",
    "StreamingTV": "Yes",
    "StreamingMovies": "No",
    "Contract": "Month-to-month",
    "PaperlessBilling": "Yes",
    "PaymentMethod": "Electronic check",
    "MonthlyCharges": 80.0,
    "TotalCharges": 400.0,
}


@pytest.mark.skipif(
    not MODEL_EXISTS,
    reason=f"Model not found at {MODEL_PATH}; run: python -m ml.train_churn_model",
)
def test_predict_churn_shape_and_probability():
    result = predict_churn(SAMPLE_CUSTOMER)

    assert isinstance(result, dict)
    assert set(result.keys()) >= {
        "churn_prediction",
        "churn_probability",
        "top_factors",
    }
    assert result["churn_prediction"] in ("Yes", "No")
    assert 0.0 <= float(result["churn_probability"]) <= 1.0
    assert isinstance(result["top_factors"], list)
