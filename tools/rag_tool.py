"""
CrewAI/LangChain tool wrapping RAG over the caller's uploaded documents.

# Same tool can later be added to Finance / Analytics agents the same way
# (bind user_id from the authenticated request when building the agent).
"""
from __future__ import annotations

import json
from langchain.tools import Tool

from services.rag_service import rag_query_sync


def get_rag_tool(user_id: int) -> Tool:
    """
    Build a RAG tool bound to one authenticated user.

    Design (security):
      CrewAI tools have no request context. We must NOT use a global/shared
      user_id (that would leak docs across concurrent users). We also must NOT
      let the LLM invent a user_id in the tool arguments (easy privilege
      escalation / cross-tenant read).

      Instead: the FastAPI route passes current_user.id into
      run_research(..., user_id=...) which calls get_rag_tool(user_id=...).
      The LLM only supplies the natural-language question; user_id is closed
      over in this factory and always forwarded to Chroma's user filter.
    """
    bound_user_id = int(user_id)

    def _run(question: str) -> str:
        # Sync wrapper: CrewAI tools are sync; rag_query_sync avoids
        # asyncio.run() nesting issues inside an already-running event loop
        # (the agent itself runs in a threadpool from FastAPI).
        try:
            result = rag_query_sync(str(question), user_id=bound_user_id, top_k=5)
            return json.dumps(result)
        except Exception as exc:
            return json.dumps({"error": str(exc), "chunks_found": 0})

    return Tool(
        name="document_rag_search",
        description=(
            "Search the current user's uploaded documents (RAG) for answers. "
            "Input should be a natural-language question string. Returns JSON "
            "with answer, sources (filenames), and chunks_found. Prefer this "
            "when the user asks about their own files; use web search for "
            "general/public information."
        ),
        func=_run,
    )
