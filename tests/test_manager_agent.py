"""Unit tests for Manager Agent planning + step execution (Day 16)."""
from unittest.mock import patch

import pytest

from agents.manager_agent import (
    parse_manager_plan,
    run_manager_explicit_plan,
)


SAMPLE_PLAN_JSON = """
Here is the plan:
```json
{
  "steps": [
    {"agent": "research", "subtask": "Research the EV battery market"},
    {"agent": "finance", "subtask": "Assess investment timing using financial reasoning"},
    {"agent": "email", "subtask": "Draft a short summary email of the findings"}
  ]
}
```
"""


def test_parse_manager_plan_strips_fence_and_prose():
    plan = parse_manager_plan(SAMPLE_PLAN_JSON)
    assert len(plan) == 3
    assert plan[0] == {
        "agent": "research",
        "subtask": "Research the EV battery market",
    }
    assert plan[1]["agent"] == "finance"
    assert plan[2]["agent"] == "email"


def test_parse_manager_plan_normalizes_aliases():
    raw = '{"steps": [{"agent": "researcher", "subtask": "Find facts"}, {"agent": "coder", "subtask": "Write a script"}]}'
    plan = parse_manager_plan(raw)
    assert plan[0]["agent"] == "research"
    assert plan[1]["agent"] == "coding"


def test_parse_manager_plan_rejects_empty():
    with pytest.raises(ValueError):
        parse_manager_plan("not json at all")


def test_run_manager_explicit_plan_calls_specialists_in_order():
    plan = [
        {"agent": "research", "subtask": "Research topic X"},
        {"agent": "finance", "subtask": "Analyze investment"},
        {"agent": "analytics", "subtask": "Check churn risk"},
    ]

    with patch(
        "agents.manager_agent.create_plan", return_value=plan
    ), patch(
        "agents.manager_agent.run_research", return_value="research-out"
    ) as mock_research, patch(
        "agents.manager_agent.run_finance_analysis",
        return_value="finance-out",
    ) as mock_finance, patch(
        "agents.manager_agent.run_analytics",
        return_value="analytics-out",
    ) as mock_analytics, patch(
        "agents.manager_agent._llm_text",
        return_value="combined final answer",
    ):
        result = run_manager_explicit_plan(
            "Research topic X, analyze investment, check churn",
            user_id=42,
        )

    assert result["plan"] == plan
    assert result["final_response"] == "combined final answer"
    assert [s["agent"] for s in result["step_results"]] == [
        "research",
        "finance",
        "analytics",
    ]
    assert result["step_results"][0]["output"] == "research-out"
    assert result["step_results"][0]["status"] == "completed"
    assert result["step_results"][1]["output"] == "finance-out"
    assert result["step_results"][2]["output"] == "analytics-out"

    mock_research.assert_called_once()
    assert mock_research.call_args.kwargs.get("user_id") == 42 or (
        len(mock_research.call_args.args) >= 2
        and mock_research.call_args.args[1] == 42
    )
    mock_finance.assert_called_once()
    mock_analytics.assert_called_once()

    # Later steps should receive prior context in the subtask string
    finance_arg = mock_finance.call_args.args[0]
    assert "research-out" in finance_arg
    analytics_arg = mock_analytics.call_args.args[0]
    assert "finance-out" in analytics_arg


def test_run_manager_explicit_plan_survives_specialist_failure():
    plan = [
        {"agent": "research", "subtask": "Research"},
        {"agent": "finance", "subtask": "Analyze"},
    ]

    with patch(
        "agents.manager_agent.create_plan", return_value=plan
    ), patch(
        "agents.manager_agent.run_research",
        side_effect=RuntimeError("boom"),
    ), patch(
        "agents.manager_agent.run_finance_analysis",
        return_value="finance-ok",
    ), patch(
        "agents.manager_agent._llm_text",
        return_value="partial combine",
    ):
        result = run_manager_explicit_plan("Do both", user_id=1)

    assert result["step_results"][0]["status"] == "failed"
    assert "failed" in result["step_results"][0]["output"].lower()
    assert result["step_results"][1]["status"] == "completed"
    assert result["final_response"] == "partial combine"


def test_run_manager_explicit_plan_skips_ppt_gracefully():
    plan = [
        {"agent": "research", "subtask": "Research"},
        {"agent": "ppt", "subtask": "Make slides"},
    ]

    with patch(
        "agents.manager_agent.create_plan", return_value=plan
    ), patch(
        "agents.manager_agent.run_research", return_value="facts"
    ), patch(
        "agents.manager_agent._llm_text",
        return_value="summary without deck",
    ):
        result = run_manager_explicit_plan("Research and deck", user_id=1)

    assert result["step_results"][1]["status"] == "skipped"
    assert "not available" in result["step_results"][1]["output"].lower()
