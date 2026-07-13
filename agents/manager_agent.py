"""
Manager Agent — orchestrates specialist agents for complex multi-part requests.

Two approaches (compare for learning; production path is Approach B):

Approach A — CrewAI native delegation (`allow_delegation=True`):
  One Crew with Manager + specialists; CrewAI decides what to delegate.
  Simpler to write, but delegation is a black box (hard to debug / control).

Approach B — Explicit plan → execute → combine (recommended for production):
  Manager LLM returns a JSON plan; we call each specialist's `run_*()` in order,
  pass prior outputs as context, then combine. Predictable, debuggable, and
  the structured plan/step_results are useful for the UI and demos.

Recommendation: use Approach B in production. You control ordering, can
survive a mid-chain specialist failure, and return the plan for inspection.
Approach A is fine for demos of CrewAI delegation, not for reliable ops.

PPT agent (Day 15) is not in this repo yet — plans that ask for "ppt" get a
clear skip message instead of crashing the chain.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Optional

from crewai import Agent, Task, Crew, Process
from langchain_groq import ChatGroq

from agents.analytics_agent import build_analytics_analyst, run_analytics
from agents.coding_agent import build_coding_engineer, run_coding_task
from agents.email_agent import build_email_writer, run_email_draft
from agents.finance_agent import build_finance_analyst, run_finance_analysis
from agents.research_agent import build_researcher, run_research

DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"

# Canonical specialist keys used in plans (and aliases the LLM might emit).
SPECIALIST_ALIASES = {
    "research": "research",
    "researcher": "research",
    "finance": "finance",
    "finance_analyst": "finance",
    "financial": "finance",
    "analytics": "analytics",
    "analytics_agent": "analytics",
    "analyst": "analytics",
    "coding": "coding",
    "coder": "coding",
    "code": "coding",
    "email": "email",
    "email_writer": "email",
    "ppt": "ppt",
    "presentation": "ppt",
    "slides": "ppt",
}

AVAILABLE_SPECIALISTS = (
    "research",
    "finance",
    "analytics",
    "coding",
    "email",
    # "ppt" reserved — not implemented yet; handled as a graceful skip
)

_JSON_FENCE_RE = re.compile(
    r"```(?:json)?\s*(\{.*?\})\s*```",
    re.DOTALL | re.IGNORECASE,
)
_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def _check_env_vars():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key or not api_key.startswith("gsk_"):
        raise ValueError(
            "GROQ_API_KEY is missing or invalid. "
            "Get a FREE key at https://console.groq.com/keys and add it to .env"
        )


def _groq_llm(temperature: float = 0.2) -> ChatGroq:
    _check_env_vars()
    model_name = os.environ.get("GROQ_MODEL", DEFAULT_GROQ_MODEL)
    return ChatGroq(
        model=model_name,
        api_key=os.environ.get("GROQ_API_KEY"),
        temperature=temperature,
    )


def build_manager() -> Agent:
    """CrewAI Manager used by Approach A (native delegation)."""
    groq_llm = _groq_llm(temperature=0.2)
    return Agent(
        role="Business Operations Manager",
        goal=(
            "Understand complex business requests, break them into the right "
            "subtasks, delegate to specialist agents, and combine their "
            "outputs into one clear, coherent response"
        ),
        backstory=(
            "A senior operations manager with deep expertise in coordinating "
            "specialist teams. Always plans before acting, verifies each "
            "specialist's output makes sense, and never delivers an incomplete "
            "or contradictory final result."
        ),
        tools=[],
        verbose=True,
        llm=groq_llm,
        allow_delegation=True,
    )


# ── Approach A: CrewAI native delegation ─────────────────────────────────────


def run_manager_delegation(request: str, user_id: int = 1) -> str:
    """
    Approach A — one Crew; Manager delegates via CrewAI's built-in mechanism.
    Less predictable than Approach B; kept for comparison / learning.
    """
    manager = build_manager()
    researcher = build_researcher(user_id=user_id)
    finance_analyst = build_finance_analyst()
    analytics_agent = build_analytics_analyst()
    coder = build_coding_engineer()
    email_writer = build_email_writer()

    task = Task(
        description=(
            f"The user submitted this business request:\n\n{request}\n\n"
            "Break it into subtasks as needed and delegate to the right "
            "specialists (Research, Finance, Analytics, Coding, Email). "
            "Combine their outputs into one coherent final response."
        ),
        expected_output=(
            "A complete response that fully addresses the user's request, "
            "combining specialist outputs as needed"
        ),
        agent=manager,
    )

    crew = Crew(
        agents=[
            manager,
            researcher,
            finance_analyst,
            analytics_agent,
            coder,
            email_writer,
        ],
        tasks=[task],
        process=Process.sequential,
        verbose=True,
    )
    result = crew.kickoff()
    return str(result)


# ── Approach B: explicit plan → execute → combine ────────────────────────────


def _extract_json_object(text: str) -> Optional[dict]:
    """Defensive JSON extraction (strip fences / stray prose)."""
    if not text or not str(text).strip():
        return None
    raw = str(text).strip()

    candidates: list[str] = [raw]
    fence = _JSON_FENCE_RE.search(raw)
    if fence:
        candidates.insert(0, fence.group(1).strip())
    obj_match = _JSON_OBJECT_RE.search(raw)
    if obj_match:
        candidates.append(obj_match.group(0))

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, TypeError):
            continue
    return None


def parse_manager_plan(raw: str) -> list[dict[str, str]]:
    """
    Parse planner LLM output into a list of {agent, subtask}.

    Raises ValueError if nothing usable can be extracted.
    """
    data = _extract_json_object(raw)
    if data is None:
        raise ValueError("Could not parse JSON plan from planner output")

    steps = data.get("steps")
    if not isinstance(steps, list) or not steps:
        raise ValueError("Plan JSON missing a non-empty 'steps' list")

    normalized: list[dict[str, str]] = []
    for item in steps:
        if not isinstance(item, dict):
            continue
        agent_raw = str(item.get("agent") or "").strip().lower()
        subtask = str(item.get("subtask") or item.get("task") or "").strip()
        if not agent_raw or not subtask:
            continue
        agent = SPECIALIST_ALIASES.get(agent_raw, agent_raw)
        normalized.append({"agent": agent, "subtask": subtask})

    if not normalized:
        raise ValueError("Plan had no valid steps after normalization")

    # Cap runaway plans (LLM sometimes over-splits)
    return normalized[:6]


def _planning_prompt(request: str) -> str:
    specialists = ", ".join(AVAILABLE_SPECIALISTS)
    return (
        f"Given this request: '{request}', decide which of these specialists "
        f"are needed and in what order: {specialists}. "
        "Only include specialists that are actually needed. "
        "Prefer 2–4 steps for multi-part requests; use 1 step when one "
        "specialist is enough. "
        "Respond with ONLY valid JSON (no markdown, no commentary) in this "
        "exact shape:\n"
        '{"steps": [{"agent": "research", "subtask": "..."}, ...]}\n'
        "agent must be one of: research, finance, analytics, coding, email. "
        "Each subtask must be a concrete instruction for that specialist."
    )


def _combine_prompt(request: str, step_results: list[dict[str, Any]]) -> str:
    blocks = []
    for i, step in enumerate(step_results, start=1):
        status = step.get("status", "unknown")
        blocks.append(
            f"### Step {i} — {step.get('agent')} ({status})\n"
            f"Subtask: {step.get('subtask')}\n"
            f"Output:\n{step.get('output')}\n"
        )
    joined = "\n".join(blocks)
    return (
        f"Original user request:\n{request}\n\n"
        f"Combine these specialist outputs into one clear final response "
        f"for the user. Acknowledge any failed steps briefly; do not invent "
        f"results for them.\n\n{joined}"
    )


def _llm_text(prompt: str, temperature: float = 0.1) -> str:
    llm = _groq_llm(temperature=temperature)
    response = llm.invoke(prompt)
    content = getattr(response, "content", None)
    if isinstance(content, list):
        # Some LangChain versions return content blocks
        parts = []
        for block in content:
            if isinstance(block, dict) and "text" in block:
                parts.append(block["text"])
            else:
                parts.append(str(block))
        return "".join(parts).strip()
    return str(content if content is not None else response).strip()


def create_plan(request: str) -> list[dict[str, str]]:
    """
    Ask the Manager LLM for a JSON plan; retry once on parse failure;
    fall back to a single research step so the chain still runs.
    """
    prompt = _planning_prompt(request)
    raw = _llm_text(prompt, temperature=0.1)
    try:
        return parse_manager_plan(raw)
    except ValueError:
        retry_prompt = (
            prompt
            + "\n\nYour previous reply was not valid JSON. "
            "Reply again with ONLY the JSON object, nothing else."
        )
        raw_retry = _llm_text(retry_prompt, temperature=0.0)
        try:
            return parse_manager_plan(raw_retry)
        except ValueError:
            # Last resort — keep the request moving
            return [{"agent": "research", "subtask": request}]


def _format_specialist_output(agent: str, result: Any) -> str:
    if agent == "email" and isinstance(result, dict):
        subject = result.get("subject") or ""
        body = result.get("body") or ""
        return f"SUBJECT: {subject}\n\nBODY:\n{body}".strip()
    return str(result)


def _execute_specialist(
    agent: str,
    subtask: str,
    *,
    user_id: int,
    prior_context: str,
) -> str:
    """Call the matching run_* function; never raise — return error text."""
    enriched = subtask
    if prior_context.strip():
        enriched = (
            f"{subtask}\n\n---\nContext from earlier specialist steps "
            f"(use only if relevant):\n{prior_context}"
        )

    try:
        if agent == "research":
            return _format_specialist_output(
                agent, run_research(enriched, user_id=user_id)
            )
        if agent == "finance":
            return _format_specialist_output(
                agent, run_finance_analysis(enriched)
            )
        if agent == "analytics":
            return _format_specialist_output(agent, run_analytics(enriched))
        if agent == "coding":
            return _format_specialist_output(agent, run_coding_task(enriched))
        if agent == "email":
            return _format_specialist_output(
                agent, run_email_draft(enriched)
            )
        if agent == "ppt":
            return (
                "PPT specialist is not available yet (Day 15 not built in "
                "this codebase). Skipping slide-deck generation. Use the "
                "other step outputs for a written summary instead."
            )
        return f"Unknown specialist '{agent}' — step skipped."
    except Exception as exc:
        return f"Specialist '{agent}' failed: {exc}"


def run_manager_explicit_plan(
    request: str,
    user_id: int = 1,
) -> dict[str, Any]:
    """
    Approach B (primary) — plan with LLM, run specialists in order, combine.

    Returns:
        {
          "plan": [{"agent": str, "subtask": str}, ...],
          "step_results": [
            {"agent", "subtask", "status", "output"},
            ...
          ],
          "final_response": str,
        }
    """
    request = (request or "").strip()
    if not request:
        raise ValueError("Request must not be empty")

    plan = create_plan(request)
    step_results: list[dict[str, Any]] = []
    context_chunks: list[str] = []

    for step in plan:
        agent = step["agent"]
        subtask = step["subtask"]
        prior = "\n\n".join(context_chunks[-3:])  # keep prompt size sane
        output = _execute_specialist(
            agent,
            subtask,
            user_id=user_id,
            prior_context=prior,
        )
        failed = output.startswith("Specialist '") and " failed:" in output
        skipped = agent == "ppt" or output.startswith("Unknown specialist")
        status = "failed" if failed else ("skipped" if skipped else "completed")

        step_results.append(
            {
                "agent": agent,
                "subtask": subtask,
                "status": status,
                "output": output,
            }
        )
        if status == "completed":
            context_chunks.append(f"[{agent}]\n{output}")

    try:
        final_response = _llm_text(
            _combine_prompt(request, step_results),
            temperature=0.2,
        )
    except Exception as exc:
        # Still return step outputs if the combine call fails
        pieces = [
            f"**{s['agent']}** ({s['status']}):\n{s['output']}"
            for s in step_results
        ]
        final_response = (
            "Could not generate a combined summary "
            f"({exc}). Individual specialist results:\n\n"
            + "\n\n".join(pieces)
        )

    return {
        "plan": plan,
        "step_results": step_results,
        "final_response": final_response,
    }
