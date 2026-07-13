# Day 13 — Coding Agent + Local Code Execution

What was built for Day 13 of the AI Multi-Agent Business Operating System.

## Overview
A **Coding Agent** (Groq + CrewAI) that writes/fixes Python and verifies it by
running code in a **beginner-safe local sandbox** — plus a direct
`execute-code` endpoint for LLM-free “run this snippet” testing.

**No Docker.** Isolation = separate OS process + temp directory + timeout.
This is **not** a production security boundary (see Security below).

---

## Files created / updated

### Tool
| File | Purpose |
|------|---------|
| `tools/code_execution_tool.py` | `execute_python_code(code) → {stdout, stderr, exit_code, success}` via `tempfile` + `subprocess` (10s default timeout); CrewAI/LangChain tool wrapper |

### Agent
| File | Purpose |
|------|---------|
| `agents/coding_agent.py` | Senior Software Engineer agent; always tests via tool; sandbox guardrail in backstory/task |

### API
| Endpoint | Purpose |
|----------|---------|
| `POST /api/v1/agents/coding` | LLM agent (auth, threadpool, **120s** timeout, Task row, `agent_type='coding'`) |
| `POST /api/v1/tools/execute-code` | Direct sandbox run (`{ "code": "..." }`), no LLM |

Schemas: `CodingRequest`, `ExecuteCodeRequest` in `schemas.py`.  
Routers: `routers/agents.py`, new `routers/tools.py` (registered in `main.py`).

### Frontend (`afsuu_Frontend`)
| File | Purpose |
|------|---------|
| `app/agents/coding/page.jsx` | Reuses `AgentChat` (`agentName="Coding"`) |
| `components/AgentChat.jsx` | `rehype-highlight` + monospace code blocks; optional `maxChars` |
| `components/DashboardShell.jsx` | Nav link to Coding Agent |
| Dashboard Quick Action | Link to `/agents/coding` |

### Tests / docs
| File | Purpose |
|------|---------|
| `tests/test_code_execution_tool.py` | Success / error / timeout (2s) / empty |
| `tests/test_coding_router.py` | Coding + execute-code: 401 / 422 / mocked 200 |
| `DAY_13_CODING_AGENT.md` | This summary |
| `README.md` | Day 13 section — honest sandbox limitations |

---

## Security (honest)

| Protected | Not protected |
|-----------|----------------|
| Infinite loops (timeout) | Network access |
| Process crash isolation | Filesystem reads/writes outside temp cwd |
| Temp dir cleanup | Memory / CPU exhaustion |
| Soft LLM prompt rules | `os.system` / `subprocess` / adversarial code |

**Production next step:** Docker, gVisor, Firecracker, or a hosted sandbox
(Judge0, Piston, E2B). Do not run this against untrusted adversarial input
as-is.

---

## Your steps

### 1) Pytest
```bash
source venv/bin/activate
pytest tests/test_code_execution_tool.py tests/test_coding_router.py -q
```

### 2) curl — login
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"YOUR_EMAIL","password":"YOUR_PASSWORD"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

### 3) Direct sandbox (no LLM) — `POST /api/v1/tools/execute-code`
```bash
curl -s -X POST http://localhost:8000/api/v1/tools/execute-code \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"code":"print(2 + 2)\\nprint(\\"hello from sandbox\\")"}'
```

**Successful response shape:**
```json
{
  "success": true,
  "data": {
    "stdout": "4\nhello from sandbox\n",
    "stderr": "",
    "exit_code": 0,
    "success": true
  },
  "message": "Code execution completed",
  "error": null
}
```

**Error / timeout example** (`while True: pass` → `success: false` in `data`,
`stderr` mentions timed out).

### 4) Full Coding Agent — `POST /api/v1/agents/coding`
```bash
curl -s -X POST http://localhost:8000/api/v1/agents/coding \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"request":"write a function to check if a number is prime, and test it"}'
```

**Successful response shape:**
```json
{
  "success": true,
  "data": {
    "result": "... working `is_prime` code, brief explanation, confirmation it was tested ...",
    "task_id": 42
  },
  "message": "Coding completed",
  "error": null
}
```

(May take up to ~2 minutes; needs `GROQ_API_KEY` in `.env`.)

### 5) Frontend
```bash
cd ../afsuu_Frontend
npm install rehype-highlight highlight.js
npm run dev
```
Log in → **Coding Agent** → e.g. “write a function to reverse a string and test it”.
Code blocks in the result should show monospace + syntax coloring.

---

## Not today
- Docker / gVisor / Firecracker hard sandbox
- Memory/CPU limits or network namespace isolation
- Multi-language runners beyond Python
