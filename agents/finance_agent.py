"""
Finance Agent — Groq LLM + trained credit-risk tool via CrewAI.

Mirrors agents/research_agent.py structure.
"""
import os
from crewai import Agent, Task, Crew, Process
from langchain_groq import ChatGroq
from tools.credit_risk_tool import get_credit_risk_tool

# TODO: integrate RAG (services/rag_service.py) once Days 9-10 document upload exist.

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

    return Agent(
        role="Financial Analyst",
        goal=(
            "Analyze financial data and provide clear, accurate financial "
            "insights and risk assessments"
        ),
        backstory=(
            "You are a seasoned financial analyst who combines quantitative "
            "credit models with clear narrative. When the user provides loan "
            "applicant details, you call the credit_risk_predictor tool and "
            "explain the result in plain business language. You also analyze "
            "ratios, ratios, and write concise investment memos when asked."
        ),
        tools=[credit_tool],
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
            "then explain Approve/Reject and probability. Otherwise provide "
            "a clear financial analysis, ratios, or investment memo as asked."
        ),
        expected_output=(
            "A clear, well-organized financial analysis or credit assessment "
            "with bullet points and actionable conclusions"
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
