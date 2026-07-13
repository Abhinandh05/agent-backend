"""
Shared Groq LLM helper for RAG and other non-CrewAI call sites.

Agents still build their own ChatGroq for CrewAI; this module is for
simple prompt → text replies (e.g. Day 10 RAG).
"""
from __future__ import annotations

import asyncio
import os

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"


def _check_env() -> None:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key or not str(api_key).startswith("gsk_"):
        raise ValueError(
            "GROQ_API_KEY is missing or invalid. "
            "Get a FREE key at https://console.groq.com/keys and add it to .env"
        )


def ask_llm_sync(prompt: str, *, temperature: float = 0.2) -> str:
    """Synchronous Groq chat completion — used by CrewAI tools and tests."""
    _check_env()
    model_name = os.environ.get("GROQ_MODEL", DEFAULT_GROQ_MODEL)
    llm = ChatGroq(
        model=model_name,
        api_key=os.environ.get("GROQ_API_KEY"),
        temperature=temperature,
    )
    result = llm.invoke([HumanMessage(content=prompt)])
    content = getattr(result, "content", None)
    if content is None:
        return str(result)
    if isinstance(content, list):
        # Some providers return content blocks
        parts = []
        for block in content:
            if isinstance(block, dict) and "text" in block:
                parts.append(block["text"])
            else:
                parts.append(str(block))
        return "".join(parts)
    return str(content)


async def ask_llm(prompt: str, *, temperature: float = 0.2) -> str:
    """Async wrapper — runs the blocking Groq call off the event loop."""
    return await asyncio.to_thread(ask_llm_sync, prompt, temperature=temperature)
