"""
CrewAI/LangChain tool wrapping the trained credit-risk RandomForest.

# TODO (Days 9-10): when rag_service.py exists, Finance Agent could also
# retrieve uploaded financial PDFs via RAG — skip until that service is ready.
"""
from __future__ import annotations

import json
from langchain.tools import Tool

from ml.predict_credit_risk import predict_credit_risk


def _run_credit_risk(applicant_json: str) -> str:
    """
    Accepts a JSON string of applicant fields matching the loan CSV columns,
    e.g. '{"ApplicantIncome": 5000, "Credit_History": 1, "LoanAmount": 120, ...}'
    """
    try:
        data = json.loads(applicant_json) if isinstance(applicant_json, str) else applicant_json
        if not isinstance(data, dict):
            return "Error: input must be a JSON object of applicant fields."
        result = predict_credit_risk(data)
        return json.dumps(result)
    except FileNotFoundError as exc:
        return f"Model not trained yet: {exc}"
    except Exception as exc:
        return f"Credit risk prediction failed: {exc}"


def get_credit_risk_tool() -> Tool:
    return Tool(
        name="credit_risk_predictor",
        description=(
            "Predict loan approval / credit risk for a loan applicant using a "
            "trained RandomForest model. Input MUST be a JSON string with fields "
            "like Gender, Married, Dependents, Education, Self_Employed, "
            "ApplicantIncome, CoapplicantIncome, LoanAmount, Loan_Amount_Term, "
            "Credit_History, Property_Area. Returns risk_prediction "
            "(Approve/Reject), risk_probability, and top_factors."
        ),
        func=_run_credit_risk,
    )
