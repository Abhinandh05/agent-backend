"""
CrewAI/LangChain tool wrapping the trained IsolationForest fraud detector.
"""
from __future__ import annotations

import json
from langchain.tools import Tool

from ml.predict_fraud import check_transaction


def _run_fraud_check(features_json: str) -> str:
    """
    Accepts a JSON string of transaction features matching training columns,
    e.g. '{"V1": -1.3, "V2": 0.1, ..., "Amount": 149.62}'.
    """
    try:
        data = (
            json.loads(features_json)
            if isinstance(features_json, str)
            else features_json
        )
        if not isinstance(data, dict):
            return "Error: input must be a JSON object of transaction features."
        result = check_transaction(data)
        return json.dumps(result)
    except FileNotFoundError as exc:
        return f"Model not trained yet: {exc}"
    except Exception as exc:
        return f"Fraud check failed: {exc}"


def get_fraud_check_tool() -> Tool:
    return Tool(
        name="fraud_transaction_checker",
        description=(
            "Flag suspicious / anomalous credit-card style transactions using a "
            "trained IsolationForest anomaly detector. Input MUST be a JSON "
            "string with numeric fields V1..V28 and Amount (same schema as the "
            "Kaggle credit-card fraud dataset). Returns is_anomalous, "
            "anomaly_score, and risk_note. Use when analyzing transaction "
            "patterns for fraud risk — alongside credit_risk_predictor for loans."
        ),
        func=_run_fraud_check,
    )
