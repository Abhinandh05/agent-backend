# Day 10 — RAG Query Pipeline

What was built for Day 10 of the AI Multi-Agent Business Operating System.

## Overview
Users (and the Research Agent) can ask questions over **their own** uploaded
documents: embed question → Chroma (filtered by `user_id`) → Groq answer with
source filenames. No Docker; Chroma + sentence-transformers + Groq only.

---

## Files created / updated

### Services
| File | Purpose |
|------|---------|
| `services/rag_service.py` | `rag_query` / `rag_query_sync` — embed, retrieve, prompt, answer |
| `services/llm_service.py` | Shared `ask_llm` / `ask_llm_sync` (Groq ChatGroq) |

Zero matching chunks → **no LLM call**; returns a clear “couldn’t find anything relevant…” answer (avoids hallucination).

### Tool + Research Agent
| File | Purpose |
|------|---------|
| `tools/rag_tool.py` | CrewAI `document_rag_search` tool |
| `agents/research_agent.py` | Adds RAG tool; `run_research(topic, user_id)` |
| `routers/agents.py` | Passes `current_user.id` into `run_research` |

**Security:** `user_id` is bound when building the tool from the JWT user — the
LLM never supplies `user_id` (cross-tenant leak risk). Chroma always filters by
that id.

**Agents updated today:** Research only.  
Finance / Analytics: comments note how to add the same tool later (not wired).

### API
| Endpoint | Purpose |
|----------|---------|
| `POST /api/v1/documents/query` | Direct RAG (`{ question }`), JWT, 60s timeout |

Schema: `DocumentQueryRequest` in `schemas.py`.  
Router: `routers/documents.py` (before `/{id}` routes).

### Frontend
| File | Purpose |
|------|---------|
| `afsuu_Frontend/app/documents/page.jsx` | List + upload + ask (shows answer **and sources**) |
| Dashboard nav / Quick Action | Link to `/documents` |
| `lib/api.js` | `runAgent` supports optional GET method |

### Tests / docs
| File | Purpose |
|------|---------|
| `tests/test_rag_service.py` | Zero-chunk skips LLM; matches call LLM |
| `tests/test_documents_router.py` | Query 401 / 422 / 200 |
| `tests/test_research_agent.py` | Updated for `user_id` + RAG tool mock |
| `DAY_10_RAG_QUERY.md` | This summary |
| `README.md` | Day 10 section |

---

## Your steps

### 1) Ensure Day 9 docs are indexed
Upload a `.txt` (or other supported type), wait until `status` is `indexed`.

### 2) curl — upload then query

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"YOUR_EMAIL","password":"YOUR_PASSWORD"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

echo "Q3 revenue grew 12 percent driven by enterprise renewals in North America." > /tmp/day10_earnings.txt

curl -s -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/day10_earnings.txt"

# Wait a few seconds for indexing, then:
curl -s http://localhost:8000/api/v1/documents \
  -H "Authorization: Bearer $TOKEN"

# Relevant question — expect answer + sources
curl -s -X POST http://localhost:8000/api/v1/documents/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"What happened to Q3 revenue?"}'
```

**Good response shape:**
```json
{
  "success": true,
  "data": {
    "answer": "Q3 revenue grew 12% …",
    "sources": [
      {"filename": "day10_earnings.txt", "chunk_preview": "Q3 revenue grew 12 percent…"}
    ],
    "chunks_found": 1
  },
  "message": "RAG query completed",
  "error": null
}
```

**Unrelated / no docs:**
```json
{
  "success": true,
  "data": {
    "answer": "I couldn't find anything relevant in your uploaded documents. …",
    "sources": [],
    "chunks_found": 0
  },
  ...
}
```

### 3) Pytest
```bash
pytest tests/test_rag_service.py tests/test_documents_router.py tests/test_research_agent.py -q
```

### 4) Frontend
```bash
cd ../afsuu_Frontend && npm run dev
```
Log in → **Documents** → upload → wait for `indexed` → ask a question.

---

## Not today
- Wiring RAG into Finance / Analytics agents (pattern documented; Research only)
- Drag-and-drop upload UI
