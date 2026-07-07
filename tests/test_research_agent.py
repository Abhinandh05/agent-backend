import pytest
from unittest.mock import patch, MagicMock

@patch('agents.research_agent.os.environ.get')
@patch('agents.research_agent.get_search_tool')
def test_build_research_task(mock_get_search_tool, mock_env_get):
    # Mock the environment variable to bypass the key check
    mock_env_get.side_effect = lambda k: 'gsk_mock_key' if k == 'GROQ_API_KEY' else None
    
    # Mock the search tool to avoid hitting real APIs or failing on missing keys
    mock_get_search_tool.return_value = MagicMock()
    
    from agents.research_agent import build_research_task
    from crewai import Task, Agent
    
    task = build_research_task("AI in Healthcare")
    
    assert isinstance(task, Task)
    assert task.description is not None
    assert "AI in Healthcare" in task.description
    assert isinstance(task.agent, Agent)
    assert task.agent.role == 'Senior Research Analyst'
