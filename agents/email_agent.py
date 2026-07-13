"""
Email Agent — drafts professional emails via Groq + CrewAI.

Output is structured so the API can split subject/body for the editable UI.
Sending is handled separately (optional SendGrid) — this module only drafts.

Spam screening (TF-IDF + Naive Bayes) is available as a tool for pasted /
incoming text the user asks to evaluate. It is *not* meant to gate outgoing
drafts — use POST /api/v1/ml/spam-check for instant screening without the LLM.
"""
from __future__ import annotations

import os
import re
from typing import Optional

from crewai import Agent, Task, Crew, Process
from langchain_groq import ChatGroq
from tools.spam_check_tool import get_spam_check_tool

DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"

_SUBJECT_RE = re.compile(
    r"(?im)^\s*SUBJECT\s*:\s*(.+?)\s*$"
)
_BODY_RE = re.compile(
    r"(?is)^\s*BODY\s*:\s*(.*)$"
)


def _check_env_vars():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key or not api_key.startswith("gsk_"):
        raise ValueError(
            "GROQ_API_KEY is missing or invalid. "
            "Get a FREE key at https://console.groq.com/keys and add it to .env"
        )


def build_email_writer() -> Agent:
    _check_env_vars()
    model_name = os.environ.get("GROQ_MODEL", DEFAULT_GROQ_MODEL)
    groq_llm = ChatGroq(
        model=model_name,
        api_key=os.environ.get("GROQ_API_KEY"),
        temperature=0.4,
    )

    # spam_message_classifier: for screening pasted/incoming text when asked —
    # not for classifying the agent's own drafts (that would be unnatural).
    spam_tool = get_spam_check_tool()

    return Agent(
        role="Business Email Writer",
        goal=(
            "Draft clear, professional business emails with an appropriate "
            "subject line and body based on the user's brief. When the user "
            "pastes a message and asks if it looks like spam, use the "
            "spam_message_classifier tool."
        ),
        backstory=(
            "You are an experienced executive assistant who writes polished "
            "business emails. You match tone to the request (formal, friendly, "
            "apologetic, etc.), keep messages concise, and never invent "
            "facts the user did not provide. You always format output exactly "
            "as instructed so it can be parsed by software. You can also "
            "screen pasted incoming-style messages for spam-like language "
            "when explicitly asked — you do not run spam checks on drafts "
            "you just wrote."
        ),
        tools=[spam_tool],
        verbose=True,
        llm=groq_llm,
        allow_delegation=False,
    )


def build_email_task(
    request: str,
    recipient_hint: Optional[str] = None,
    tone: Optional[str] = None,
) -> Task:
    writer = build_email_writer()
    extras = []
    if recipient_hint:
        extras.append(f"Intended recipient context: {recipient_hint}.")
    if tone:
        extras.append(f"Preferred tone: {tone}.")
    extra_text = (" " + " ".join(extras)) if extras else ""

    return Task(
        description=(
            f"Draft a professional business email for this request: '{request}'. "
            f"{extra_text}"
            "Respond with EXACTLY this format and nothing else before SUBJECT:\n"
            "SUBJECT: <one-line subject>\n"
            "BODY:\n"
            "<email body including greeting and sign-off>\n"
        ),
        expected_output=(
            "SUBJECT: ... line, then BODY: followed by the full email body"
        ),
        agent=writer,
    )


def parse_email_output(raw: str) -> dict:
    """
    Split LLM output into subject + body.

    Expected format:
        SUBJECT: ...
        BODY:
        ...
    Falls back gracefully if the model drifts from the format.
    """
    text = (raw or "").strip()
    subject_match = _SUBJECT_RE.search(text)
    body_match = _BODY_RE.search(text)

    subject = subject_match.group(1).strip() if subject_match else ""
    body = body_match.group(1).strip() if body_match else ""

    if not subject and not body:
        # Entire raw text as body; invent a short subject from first line
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        subject = (lines[0][:80] if lines else "Draft email")
        body = text
    elif not body:
        # Subject found but no BODY marker — everything after subject line
        after = text[subject_match.end() :].strip() if subject_match else text
        body = after
    elif not subject:
        subject = "Draft email"

    return {"subject": subject, "body": body, "raw": text}


def run_email_draft(
    request: str,
    recipient_hint: Optional[str] = None,
    tone: Optional[str] = None,
) -> dict:
    """Runs the email crew and returns {subject, body, raw}."""
    task = build_email_task(request, recipient_hint=recipient_hint, tone=tone)
    crew = Crew(
        agents=[task.agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True,
    )
    result = crew.kickoff()
    return parse_email_output(str(result))
