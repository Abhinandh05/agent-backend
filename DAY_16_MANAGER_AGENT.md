# Day 16 — Manager Agent (Orchestrates All Agents)

What was built for **Day 16** of the AI Multi-Agent Business Operating System:
the **Manager Agent** — the centerpiece that turns separate specialist endpoints
into a real multi-agent system.

No Docker. Primary path is **Approach B** (explicit plan → execute → combine).

---

## Why this matters

Until Day 16, each agent was a silo: Research, Finance, Analytics, Coding,
Email each had their own API and UI. A user who wanted “research + finance
analysis + email summary” had to call three endpoints and stitch answers by
hand.

The Manager:

1. Receives **one** complex request  
2. **Plans** which specialists are needed (and in what order)  
3. **Delegates** by calling each existing `run_*()` function  
4. **Combines** outputs into one coherent final response  

That is the demo moment for the whole OS.

---

## Two approaches (both implemented)

| | Approach A | Approach B (default / production) |
|---|------------|-----------------------------------|
| Function | `run_manager_delegation()` | `run_manager_explicit_plan()` |
| How it works | One CrewAI Crew; Manager has `allow_delegation=True` | LLM returns a JSON plan → we call specialists in order → combine |
| Controllability | Low (black-box delegation) | High (you own the plan + execution) |
| UI value | Final text only | Returns `plan` + `step_results` + `final_response` |
| Used by API? | No (comparison / learning) | **Yes** — `POST /api/v1/agents/manager` |

**Recommendation:** Approach B for anything you care about debugging or showing
in a UI. Approach A is simpler to write but harder to trust in production.

---

## Files created / updated

### Backend
| File | Purpose |
|------|---------|
| `agents/manager_agent.py` | Manager Agent + Approach A + Approach B |
| `routers/agents.py` | `POST /api/v1/agents/manager` (300s timeout) |
| `schemas.py` | `ManagerRequest`; `TaskResponse.plan_details` |
| `models/task.py` | Nullable `plan_details` Text column |
| `alembic/versions/d4e8a1b2c3f0_add_plan_details_to_tasks.py` | Migration |
| `tests/test_manager_agent.py` | Plan parse + ordered specialist calls (mocked) |
| `tests/test_manager_router.py` | 401 / 422 / mocked 200 |

### Frontend (`afsuu_Frontend`)
| File | Purpose |
|------|---------|
| `app/agents/manager/page.jsx` | Flagship UI: request → plan → step results → final |
| `components/DashboardShell.jsx` | Manager link first after Dashboard |
| `app/page.jsx` | Manager as top Quick Action |

### Docs
| File | Purpose |
|------|---------|
| `DAY_16_MANAGER_AGENT.md` | This summary |

---

## API

### `POST /api/v1/agents/manager`

**Auth:** Bearer JWT (`get_current_active_user`)

**Body:**
```json
{ "request": "your complex multi-part business request…" }
```

- `request`: 3–8000 characters (after trim)

**Timeout:** **300 seconds** (5 minutes). Intentionally longer than other agent
routes (~90–120s) because this call may chain several LLM agent runs.

**Success `data`:**
```json
{
  "plan": [
    { "agent": "research", "subtask": "…" },
    { "agent": "finance", "subtask": "…" }
  ],
  "step_results": [
    {
      "agent": "research",
      "subtask": "…",
      "status": "completed",
      "output": "…"
    }
  ],
  "final_response": "Combined answer for the user…",
  "task_id": 123
}
```

Task row: `agent_type='manager'`, `result` = final response text,
`plan_details` = JSON of `{plan, step_results}`.

---

## Specialists available today

| Key | Calls |
|-----|--------|
| `research` | `run_research(topic, user_id)` |
| `finance` | `run_finance_analysis(request)` |
| `analytics` | `run_analytics(request)` |
| `coding` | `run_coding_task(request)` |
| `email` | `run_email_draft(request)` → formatted subject/body |

**PPT:** Day 15 PPT agent is **not** in this repo yet. If a plan somehow
includes `ppt`, that step is **skipped** with a clear message (chain continues).
When PPT lands, wire `run_ppt` into `_execute_specialist` the same way.

---

## Resilience (edge cases)

| Case | Behavior |
|------|----------|
| Malformed plan JSON | Retry planner once; then fall back to a single `research` step |
| Specialist throws mid-chain | Step marked `failed` with error text; remaining steps still run |
| Combine LLM fails | Returns concatenated step outputs instead of crashing |
| Unknown / ppt agent | Step `skipped` with explanation |

---

## Your steps

### 1) Migrate DB
```bash
cd agent-backend
source venv/bin/activate
alembic upgrade head
```

### 2) Run tests
```bash
pytest tests/test_manager_agent.py tests/test_manager_router.py -q
```

### 3) Start API + frontend
```bash
# backend
uvicorn main:app --reload --port 8000

# frontend (separate terminal)
cd ../afsuu_Frontend
npm run dev
```

Open **Manager Agent** in the nav (or `/agents/manager`).

---

## Manual test

### Good example request (exercises multiple agents)

> Research the current EV battery market, analyze whether it's a good time to
> invest using financial reasoning, and draft a short summary email of the
> findings for a colleague.

(Avoid asking for a slide deck until the PPT agent exists — or expect that
step to be skipped.)

### curl

```bash
TOKEN="YOUR_JWT_HERE"

curl -s -X POST "http://localhost:8000/api/v1/agents/manager" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "request": "Research the current EV battery market, analyze whether it is a good time to invest using financial reasoning, and draft a short summary email of the findings for a colleague"
  }' | python -m json.tool
```

Login first if needed:
```bash
curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"yourpassword"}'
```

### What you should see

```json
{
  "success": true,
  "data": {
    "plan": [ /* 2–3 steps: research, finance, email */ ],
    "step_results": [ /* each with status + output */ ],
    "final_response": "…",
    "task_id": 1
  },
  "message": "Manager orchestration completed",
  "error": null
}
```

### Timing expectations

| Steps | Rough wait |
|-------|------------|
| 1 specialist | ~15–45s |
| 2–3 specialists | **~30s–2 min** |
| 4+ specialists | 2–5 min (hits the 300s ceiling only if something hangs) |

Multiple Groq/CrewAI kicks in sequence are much slower than any single agent
call — that is expected.

---

## Approach A vs B (quick mental model)

```
Approach A (CrewAI delegation)
  User request → Manager Crew (allow_delegation) → black-box handoffs → text

Approach B (explicit — API default)
  User request
       ↓
  Plan JSON  { steps: [{agent, subtask}, ...] }
       ↓
  for each step: run_*()  (+ prior context)
       ↓
  Combine LLM → final_response
       ↓
  Return plan + step_results + final_response
```
