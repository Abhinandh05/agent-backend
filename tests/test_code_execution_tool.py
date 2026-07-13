"""Tests for tools/code_execution_tool.py (Day 13)."""
from tools.code_execution_tool import execute_python_code


def test_execute_valid_code():
    result = execute_python_code('print("hello")')
    assert result["success"] is True
    assert result["exit_code"] == 0
    assert "hello" in result["stdout"]
    assert result["stderr"] == ""


def test_execute_code_with_error():
    result = execute_python_code("raise ValueError('boom')")
    assert result["success"] is False
    assert result["exit_code"] != 0
    assert "ValueError" in result["stderr"] or "boom" in result["stderr"]


def test_execute_infinite_loop_times_out():
    # Short timeout so the suite stays fast (~2s), not the default 10s.
    result = execute_python_code("while True: pass", timeout=2)
    assert result["success"] is False
    assert result["exit_code"] == -1
    assert "timed out" in result["stderr"].lower()


def test_execute_empty_code():
    result = execute_python_code("   ")
    assert result["success"] is False
    assert "No code provided" in result["stderr"]
