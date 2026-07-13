"""
Coding Agent — Groq LLM + local Python sandbox via CrewAI.

Uses tools/code_execution_tool.py (subprocess + tempfile + timeout).
That sandbox is beginner-safe only — see the tool module's security notes.
"""
import os
from crewai import Agent, Task, Crew, Process
from langchain_groq import ChatGroq
from tools.code_execution_tool import get_code_execution_tool

DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"

SANDBOX_GUARDRAIL = (
    "Never write code that accesses the network, reads or writes files "
    "outside the current working directory, deletes files, or uses "
    "os.system/subprocess itself. Keep all code self-contained and safe "
    "to execute in an isolated sandbox."
)


def _check_env_vars():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key or not api_key.startswith("gsk_"):
        raise ValueError(
            "GROQ_API_KEY is missing or invalid. "
            "Get a FREE key at https://console.groq.com/keys and add it to .env"
        )


def build_coding_engineer() -> Agent:
    _check_env_vars()
    model_name = os.environ.get("GROQ_MODEL", DEFAULT_GROQ_MODEL)
    groq_llm = ChatGroq(
        model=model_name,
        api_key=os.environ.get("GROQ_API_KEY"),
        temperature=0.2,
    )
    code_tool = get_code_execution_tool()

    return Agent(
        role="Senior Software Engineer",
        goal=(
            "Write correct, clean, well-tested code and explain it clearly; "
            "verify code works by running it before presenting it"
        ),
        backstory=(
            "You are a senior software engineer who always tests code before "
            "showing results. You write clear, idiomatic Python, explain your "
            "approach briefly, and call the execute_python_code tool to verify "
            "behavior (including edge cases) before presenting a final answer. "
            f"{SANDBOX_GUARDRAIL}"
        ),
        tools=[code_tool],
        verbose=True,
        llm=groq_llm,
        allow_delegation=False,
    )


def build_coding_task(request: str) -> Task:
    engineer = build_coding_engineer()
    return Task(
        description=(
            f"Handle this coding request: '{request}'. "
            "Write or fix the requested code, then use execute_python_code to "
            "run meaningful tests or demos before presenting the result. "
            f"{SANDBOX_GUARDRAIL}"
        ),
        expected_output=(
            "Working code with a brief explanation and confirmation it was tested"
        ),
        agent=engineer,
    )


def run_coding_task(request: str) -> str:
    """Runs the coding crew synchronously and returns the result."""
    task = build_coding_task(request)
    crew = Crew(
        agents=[task.agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True,
    )
    result = crew.kickoff()
    return str(result)
