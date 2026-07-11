"""
CrewAI/LangChain tool wrapping the trained churn RandomForest.
"""
from __future__ import annotations

import json
from langchain.tools import Tool

from ml.predict_churn import predict_churn


def _run_churn(customer_json: str) -> str:
    """
    Accepts a JSON string of Telco customer fields, e.g.
    '{"tenure": 2, "Contract": "Month-to-month", "MonthlyCharges": 70.5, ...}'
    """
    try:
        data = json.loads(customer_json) if isinstance(customer_json, str) else customer_json
        if not isinstance(data, dict):
            return "Error: input must be a JSON object of customer fields."
        result = predict_churn(data)
        return json.dumps(result)
    except FileNotFoundError as exc:
        return f"Model not trained yet: {exc}"
    except Exception as exc:
        return f"Churn prediction failed: {exc}"


def get_churn_tool() -> Tool:
    return Tool(
        name="churn_predictor",
        description=(
            "Predict whether a telecom customer will churn using a trained "
            "RandomForest model. Input MUST be a JSON string with fields like "
            "tenure, Contract, MonthlyCharges, TotalCharges, InternetService, "
            "PaymentMethod, gender, Partner, Dependents, etc. (Telco churn CSV "
            "columns). Returns churn_prediction (Yes/No), churn_probability, "
            "and top_factors."
        ),
        func=_run_churn,
    )
