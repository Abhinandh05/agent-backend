"""
DuckDuckGo search tool for CrewAI (free, no API key).

Compatible with CrewAI 0.30.x via LangChain Tool wrappers.
"""
from langchain.tools import Tool
from duckduckgo_search import DDGS


def _duckduckgo_search(query: str) -> str:
    results = list(DDGS().text(query, max_results=5))
    return str(results) if results else "No results found."


def get_search_tool() -> Tool:
    """
    Returns the DuckDuckGo search tool for web searching.
    No API key is required.
    """
    return Tool(
        name="duck_duck_go_search",
        description="Search the web for information on a given topic using DuckDuckGo.",
        func=_duckduckgo_search,
    )
