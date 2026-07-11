"""
CrewAI/LangChain tool wrapping the trained sales-forecast RandomForest.
"""
from __future__ import annotations

import json
from langchain.tools import Tool

from ml.predict_sales_forecast import predict_sales


def _run_sales_forecast(features_json: str) -> str:
    """
    Accepts a JSON string of forecast features, e.g.
    '{"year": 2017, "month": 11, "Category": "Technology", "Region": "West"}'
    or '{"Order Date": "2017-11-15", "Category": "Furniture", "Region": "East"}'
    """
    try:
        data = json.loads(features_json) if isinstance(features_json, str) else features_json
        if not isinstance(data, dict):
            return "Error: input must be a JSON object of forecast features."
        result = predict_sales(data)
        return json.dumps(result)
    except FileNotFoundError as exc:
        return f"Model not trained yet: {exc}"
    except Exception as exc:
        return f"Sales forecast failed: {exc}"


def get_sales_forecast_tool() -> Tool:
    return Tool(
        name="sales_forecast_predictor",
        description=(
            "Predict future / period sales revenue using a trained "
            "RandomForestRegressor. Input MUST be a JSON string with calendar "
            "fields (year, month, day_of_week, quarter) and optional "
            "Category, Region, Segment — or pass Order Date / date and those "
            "will be derived. Returns predicted_sales (float $) and "
            "confidence_note."
        ),
        func=_run_sales_forecast,
    )
