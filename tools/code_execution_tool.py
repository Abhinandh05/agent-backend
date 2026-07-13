"""
Lightweight local Python code-execution tool (Day 13).

SECURITY — beginner-safe sandbox, NOT production-hardened
=========================================================
This runs AI-generated (or user-supplied) code in a **separate OS process**
via ``subprocess``, inside a temporary directory that is deleted afterward,
with a hard wall-clock timeout.

What this DOES protect against (accidental bugs):
  - Infinite loops / hung scripts (timeout kills the child process)
  - Leaving scratch files around (temp dir is cleaned up)

What this does NOT protect against (a determined attacker):
  - Network access (subprocess does not block sockets)
  - Reading/writing files outside the temp directory
  - Spawning shells, importing dangerous modules, exhausting memory/CPU
  - Escape via ``os.system``, ``subprocess``, ``ctypes``, etc.

Guardrails beyond process isolation + timeout are **soft**: the Coding Agent
system prompt tells the LLM not to write malicious code. Do **not** run this
against untrusted / adversarial input in a real production deployment.

Production-grade next steps: Docker / gVisor / Firecracker, or a hosted
sandbox API (Judge0, Piston, E2B, etc.).
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from langchain.tools import Tool

DEFAULT_TIMEOUT_SECONDS = 10


def execute_python_code(code: str, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> dict:
    """
    Run ``code`` as a separate Python process in a temporary directory.

    Returns:
        ``{"stdout": str, "stderr": str, "exit_code": int, "success": bool}``

    On timeout, ``success`` is False, ``exit_code`` is -1, and ``stderr``
    explains that execution timed out (possible infinite loop).
    """
    if not isinstance(code, str) or not code.strip():
        return {
            "stdout": "",
            "stderr": "No code provided.",
            "exit_code": -1,
            "success": False,
        }

    with tempfile.TemporaryDirectory(prefix="coding_sandbox_") as temp_dir:
        script_path = Path(temp_dir) / "user_code.py"
        script_path.write_text(code, encoding="utf-8")

        try:
            completed = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=temp_dir,
            )
            return {
                "stdout": completed.stdout or "",
                "stderr": completed.stderr or "",
                "exit_code": completed.returncode,
                "success": completed.returncode == 0,
            }
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": (
                    f"execution timed out after {timeout} seconds "
                    "(possible infinite loop)"
                ),
                "exit_code": -1,
                "success": False,
            }
        except Exception as exc:
            return {
                "stdout": "",
                "stderr": f"Execution failed: {exc}",
                "exit_code": -1,
                "success": False,
            }
    # temp_dir is deleted when the ``with`` block exits


def _run_execute_python_code(code: str) -> str:
    """LangChain/CrewAI tool adapter — returns a JSON string for the LLM."""
    result = execute_python_code(code)
    return json.dumps(result)


def get_code_execution_tool() -> Tool:
    return Tool(
        name="execute_python_code",
        description=(
            "Execute a Python code snippet in an isolated temporary directory "
            "with a hard timeout. Input MUST be the full Python source as a "
            "plain string (not JSON). Returns a JSON object with stdout, "
            "stderr, exit_code, and success. Use this to verify that code "
            "you write actually runs before presenting it to the user. "
            "NEVER pass code that accesses the network, reads/writes outside "
            "the working directory, deletes files, or uses os.system / "
            "subprocess."
        ),
        func=_run_execute_python_code,
    )
