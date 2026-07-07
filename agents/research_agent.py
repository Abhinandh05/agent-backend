import os
from crewai import Agent, Task, Crew, Process, LLM
from tools.search_tool import get_search_tool

# ── Groq compatibility fix ────────────────────────────────────────────────────
# CrewAI marks system messages with `cache_breakpoint: True` for prompt caching.
# Its `_format_messages_for_provider` only strips this key for Anthropic models,
# so it leaks into every litellm call for other providers (Groq, OpenAI-compat,
# etc.). Groq rejects the field with a 400 BadRequestError.
#
# Workaround: wrap the method so the key is always stripped before litellm sees it.
_original_fmt = LLM._format_messages_for_provider

def _patched_fmt(self, messages):
    CACHE_KEY = "cache_breakpoint"
    cleaned = [{k: v for k, v in m.items() if k != CACHE_KEY} for m in messages]
    return _original_fmt(self, cleaned)

LLM._format_messages_for_provider = _patched_fmt
# ─────────────────────────────────────────────────────────────────────────────

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

    # CrewAI v1.x uses LiteLLM under the hood.
    # For xAI/Grok, pass the key via XAI_API_KEY and use the "xai/" provider prefix.
    search_tool = get_search_tool()

    groq_llm = LLM(
        model="groq/meta-llama/llama-4-scout-17b-16e-instruct",
        api_key=os.environ.get("GROQ_API_KEY"),
    )

    return Agent(
        role='Senior Research Analyst',
        goal='Find accurate, up-to-date business information from the web',
        backstory=(
            "You are a seasoned research analyst with a knack for finding hidden trends "
            "and factual data. You know how to synthesize complex information into clear, "
            "actionable insights."
        ),
        tools=[search_tool],
        verbose=True,
        llm=groq_llm
    )

def build_research_task(topic: str) -> Task:
    """Builds and returns the research Task for a given topic."""
    researcher = build_researcher()
    return Task(
        description=(
            f"Research the following topic comprehensively: '{topic}'. "
            "Gather key facts, statistics, and the latest developments."
        ),
        expected_output='A clear, well-organized bullet-point summary of key findings with sources',
        agent=researcher
    )

def run_research(topic: str) -> str:
    """Runs the research crew synchronously and returns the result."""
    task = build_research_task(topic)

    crew = Crew(
        agents=[task.agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True
    )

    result = crew.kickoff()
    return str(result)
