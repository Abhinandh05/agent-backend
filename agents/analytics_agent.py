"""
Analytics Agent — Groq LLM + churn + sales-forecast tools via CrewAI.

Mirrors agents/finance_agent.py / research_agent.py structure.
"""
import os
from crewai import Agent, Task, Crew, Process
from langchain_groq import ChatGroq
from tools.churn_tool import get_churn_tool
from tools.sales_forecast_tool import get_sales_forecast_tool

DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"


def _check_env_vars():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key or not api_key.startswith("gsk_"):
        raise ValueError(
            "GROQ_API_KEY is missing or invalid. "
            "Get a FREE key at https://console.groq.com/keys and add it to .env"
        )


def build_analytics_analyst() -> Agent:
    _check_env_vars()
    model_name = os.environ.get("GROQ_MODEL", DEFAULT_GROQ_MODEL)
    groq_llm = ChatGroq(
        model=model_name,
        api_key=os.environ.get("GROQ_API_KEY"),
        temperature=0.2,
    )
    churn_tool = get_churn_tool()
    sales_tool = get_sales_forecast_tool()

    return Agent(
        role="Business Data Analyst",
        goal=(
            "Analyze business data, identify trends, and provide predictive "
            "insights using both reasoning and trained models"
        ),
        backstory=(
            "You are a senior business data analyst who combines clear "
            "narrative with trained ML models. When the user asks about "
            "customer retention or churn risk, call the churn_predictor tool. "
            "When they ask about future sales, revenue, or demand by period / "
            "category / region, call the sales_forecast_predictor tool. "
            "Always explain model outputs in plain business language and note "
            "limitations (estimates, not guarantees)."
        ),
        tools=[churn_tool, sales_tool],
        verbose=True,
        llm=groq_llm,
        allow_delegation=False,
    )


def build_analytics_task(request: str) -> Task:
    analyst = build_analytics_analyst()
    return Task(
        description=(
            f"Handle this analytics request: '{request}'. "
            "If the request includes customer attributes for churn, call "
            "churn_predictor with a JSON object of those fields. If it asks "
            "for sales / revenue forecasts, call sales_forecast_predictor "
            "with year/month/quarter/category/region (or a date). Otherwise "
            "provide a clear data analysis with trends and actionable insights."
        ),
        expected_output=(
            "A clear, well-organized analytics response with bullet points, "
            "model results when used, and actionable conclusions"
        ),
        agent=analyst,
    )


def run_analytics(request: str) -> str:
    """Runs the analytics crew synchronously and returns the result."""
    task = build_analytics_task(request)
    crew = Crew(
        agents=[task.agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True,
    )
    result = crew.kickoff()
    return str(result)
