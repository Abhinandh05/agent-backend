"""
Finance Agent — Groq LLM + credit-risk + fraud anomaly tools via CrewAI.

Mirrors agents/research_agent.py structure.

# Day 10: document RAG tool (tools/rag_tool.py) can be added here later the
# same way Research does — bind get_rag_tool(user_id=...) from the request.
"""
import os
from crewai import Agent, Task, Crew, Process
from langchain_groq import ChatGroq
from tools.credit_risk_tool import get_credit_risk_tool
from tools.fraud_check_tool import get_fraud_check_tool

DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"


def _check_env_vars():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key or not api_key.startswith("gsk_"):
        raise ValueError(
            "GROQ_API_KEY is missing or invalid. "
            "Get a FREE key at https://console.groq.com/keys and add it to .env"
        )


def build_finance_analyst() -> Agent:
    _check_env_vars()
    model_name = os.environ.get("GROQ_MODEL", DEFAULT_GROQ_MODEL)
    groq_llm = ChatGroq(
        model=model_name,
        api_key=os.environ.get("GROQ_API_KEY"),
        temperature=0.2,
    )
    credit_tool = get_credit_risk_tool()
    fraud_tool = get_fraud_check_tool()

    return Agent(
        role="Financial Analyst",
        goal=(
            "Analyze financial data and provide clear, accurate financial "
            "insights, loan risk assessments, and transaction fraud flags"
        ),
        backstory=(
            "You are a seasoned financial analyst who combines quantitative "
            "models with clear narrative. When the user provides loan "
            "applicant details, you call the credit_risk_predictor tool and "
            "explain the result in plain business language. When they provide "
            "transaction feature vectors (V1..V28, Amount), you call "
            "fraud_transaction_checker to flag anomalous patterns. You also "
            "analyze ratios and write concise investment memos when asked."
        ),
        tools=[credit_tool, fraud_tool],
        verbose=True,
        llm=groq_llm,
        allow_delegation=False,
    )


def build_finance_task(request: str) -> Task:
    analyst = build_finance_analyst()
    return Task(
        description=(
            f"Handle this finance request: '{request}'. "
            "If the request includes loan applicant attributes, call the "
            "credit_risk_predictor tool with a JSON object of those fields, "
            "then explain Approve/Reject and probability. If it includes "
            "transaction features (V1..V28 and Amount), call "
            "fraud_transaction_checker and explain whether the pattern looks "
            "anomalous. Otherwise provide a clear financial analysis, ratios, "
            "or investment memo as asked."
        ),
        expected_output=(
            "A clear, well-organized financial analysis, credit assessment, "
            "or fraud-flag explanation with bullet points and actionable "
            "conclusions"
        ),
        agent=analyst,
    )


def run_finance_analysis(request: str) -> str:
    """Runs the finance crew synchronously and returns the result."""
    task = build_finance_task(request)
    crew = Crew(
        agents=[task.agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True,
    )
    result = crew.kickoff()
    return str(result)
