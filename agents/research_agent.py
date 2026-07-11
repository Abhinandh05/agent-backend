"""
Research Agent — Groq LLM + DuckDuckGo search via CrewAI.

Uses langchain_groq.ChatGroq for compatibility with CrewAI 0.30.x
(the installed version does not export crewai.LLM).
"""
import os
from crewai import Agent, Task, Crew, Process
from langchain_groq import ChatGroq
from tools.search_tool import get_search_tool

# Preferred Groq model (free tier). Override with GROQ_MODEL in .env if needed.
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"


def _check_env_vars():
    """Checks for required environment variables."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key or not api_key.startswith("gsk_"):
        raise ValueError(
            "GROQ_API_KEY is missing or invalid. "
            "Get a FREE key at https://console.groq.com/keys and add it to .env"
        )


def build_researcher() -> Agent:
    """Builds and returns the Research Agent."""
    _check_env_vars()

    search_tool = get_search_tool()
    model_name = os.environ.get("GROQ_MODEL", DEFAULT_GROQ_MODEL)

    groq_llm = ChatGroq(
        model=model_name,
        api_key=os.environ.get("GROQ_API_KEY"),
        temperature=0.2,
    )

    return Agent(
        role="Senior Research Analyst",
        goal="Find accurate, up-to-date business information from the web",
        backstory=(
            "You are a seasoned research analyst with a knack for finding hidden trends "
            "and factual data. You know how to synthesize complex information into clear, "
            "actionable insights."
        ),
        tools=[search_tool],
        verbose=True,
        llm=groq_llm,
        allow_delegation=False,
    )


def build_research_task(topic: str) -> Task:
    """Builds and returns the research Task for a given topic."""
    researcher = build_researcher()
    return Task(
        description=(
            f"Research the following topic comprehensively: '{topic}'. "
            "Gather key facts, statistics, and the latest developments."
        ),
        expected_output="A clear, well-organized bullet-point summary of key findings with sources",
        agent=researcher,
    )


def run_research(topic: str) -> str:
    """Runs the research crew synchronously and returns the result."""
    task = build_research_task(topic)

    crew = Crew(
        agents=[task.agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff()
    return str(result)
