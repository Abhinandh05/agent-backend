from crewai.tools import BaseTool
from ddgs import DDGS
from pydantic import Field


class DuckDuckGoSearchTool(BaseTool):
    """DuckDuckGo web search tool for CrewAI."""
    name: str = "duck_duck_go_search"
    description: str = "Search the web for information on a given topic using DuckDuckGo."

    def _run(self, query: str) -> str:
        results = list(DDGS().text(query, max_results=5))
        return str(results) if results else "No results found."


def get_search_tool() -> DuckDuckGoSearchTool:
    """
    Returns the DuckDuckGo search tool for web searching.
    No API key is required.
    """
    return DuckDuckGoSearchTool()
