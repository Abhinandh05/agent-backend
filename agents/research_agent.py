"""
Research Agent — Groq LLM + DuckDuckGo + user-document RAG via CrewAI.

Uses langchain_groq.ChatGroq for compatibility with CrewAI 0.30.x
(the installed version does not export crewai.LLM).
"""
import os
from crewai import Agent, Task, Crew, Process
from langchain_groq import ChatGroq
from tools.search_tool import get_search_tool
from tools.rag_tool import get_rag_tool

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


def build_researcher(user_id: int) -> Agent:
    """Builds and returns the Research Agent for a specific authenticated user."""
    _check_env_vars()

    search_tool = get_search_tool()
    # Bound to this request's user — never a shared/global id (cross-tenant risk).
    rag_tool = get_rag_tool(user_id=user_id)
    model_name = os.environ.get("GROQ_MODEL", DEFAULT_GROQ_MODEL)

    groq_llm = ChatGroq(
        model=model_name,
        api_key=os.environ.get("GROQ_API_KEY"),
        temperature=0.2,
    )

    return Agent(
        role="Senior Research Analyst",
        goal="Find accurate, up-to-date business information from the web and the user's documents",
        backstory=(
            "You are a seasoned research analyst with a knack for finding hidden trends "
            "and factual data. You can search the web and also the user's own uploaded "
            "documents via document_rag_search. Prefer document_rag_search when the "
            "question is about their files; use DuckDuckGo for public/web info. "
            "You know how to synthesize complex information into clear, actionable insights."
        ),
        tools=[search_tool, rag_tool],
        verbose=True,
        llm=groq_llm,
        allow_delegation=False,
    )


def build_research_task(topic: str, user_id: int) -> Task:
    """Builds and returns the research Task for a given topic."""
    researcher = build_researcher(user_id=user_id)
    return Task(
        description=(
            f"Research the following topic comprehensively: '{topic}'. "
            "Gather key facts, statistics, and the latest developments. "
            "If the topic may relate to the user's uploaded documents, also "
            "call document_rag_search."
        ),
        expected_output="A clear, well-organized bullet-point summary of key findings with sources",
        agent=researcher,
    )


def run_research(topic: str, user_id: int) -> str:
    """Runs the research crew synchronously and returns the result."""
    task = build_research_task(topic, user_id=user_id)

    crew = Crew(
        agents=[task.agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff()
    return str(result)
