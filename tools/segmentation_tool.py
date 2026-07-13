"""
CrewAI/LangChain tool wrapping the trained customer-segmentation K-Means model.
"""
from __future__ import annotations

import json
from langchain.tools import Tool

from ml.predict_customer_segment import predict_segment


def _run_segmentation(customer_json: str) -> str:
    """
    Accepts a JSON string of customer numeric fields, e.g.
    '{"age": 28, "annual_income": 75, "spending_score": 80}'
    """
    try:
        data = json.loads(customer_json) if isinstance(customer_json, str) else customer_json
        if not isinstance(data, dict):
            return "Error: input must be a JSON object of customer fields."
        result = predict_segment(data)
        return json.dumps(result)
    except FileNotFoundError as exc:
        return f"Model not trained yet: {exc}"
    except Exception as exc:
        return f"Customer segmentation failed: {exc}"


def get_segmentation_tool() -> Tool:
    return Tool(
        name="customer_segment_predictor",
        description=(
            "Assign a mall/retail customer to a discovered segment using a "
            "trained unsupervised K-Means model. Input MUST be a JSON string "
            "with numeric fields: age, annual_income (in k$ if trained on the "
            "Kaggle Mall dataset), and spending_score (1-100). Returns "
            "segment (human-readable label), cluster_id, and profile_note."
        ),
        func=_run_segmentation,
    )
