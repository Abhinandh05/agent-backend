"""Unit tests for the Research Agent builders (mocked LLM/tools)."""
from unittest.mock import patch, MagicMock

from langchain.tools import Tool


@patch("agents.research_agent.ChatGroq")
@patch("agents.research_agent.get_search_tool")
@patch("agents.research_agent.os.environ.get")
def test_build_research_task(mock_env_get, mock_get_search_tool, mock_chat_groq):
    mock_env_get.side_effect = lambda k, default=None: (
        "gsk_mock_key" if k == "GROQ_API_KEY" else default
    )
    # Real LangChain Tool — MagicMock breaks CrewAI's executor validator
    mock_get_search_tool.return_value = Tool(
        name="duck_duck_go_search",
        description="Search the web",
        func=lambda q: "no results",
    )
    mock_chat_groq.return_value = MagicMock()

    from agents.research_agent import build_research_task
    from crewai import Task, Agent

    task = build_research_task("AI in Healthcare")

    assert isinstance(task, Task)
    assert task.description is not None
    assert "AI in Healthcare" in task.description
    assert isinstance(task.agent, Agent)
    assert task.agent.role == "Senior Research Analyst"
