# Day 6–8 Build Summary

## Day 6 — Research Agent API
- `POST /api/v1/agents/research` in `routers/agents.py`
- JWT required (`get_current_active_user`)
- Runs `run_research` via `run_in_threadpool` + 90s `asyncio.wait_for`
- Persists `Task` rows (`running` → `completed` / `failed`)
- Standard response: `{ success, data, message, error }`
- Tests: `tests/test_agents_router.py`

### Manual curl test
```bash
# 1) Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"yourpassword"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 2) Research
curl -s -X POST http://localhost:8000/api/v1/agents/research \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"topic":"AI trends for small businesses 2026"}'
```

Success shape:
```json
{
  "success": true,
  "data": { "result": "...", "task_id": 1 },
  "message": "Research completed",
  "error": null
}
```

## Day 7 — Frontend Research UI
- Page: `/agents/research` → `afsuu_Frontend/app/agents/research/page.jsx`
- Component: `components/AgentChat.jsx`
- API helper: `lib/api.js` → `runAgent()`
- Env: `.env.local` with `NEXT_PUBLIC_API_URL=http://localhost:8000`
- Dashboard sidebar + Quick Action link to Research Agent

### Manual E2E
1. Backend: `uvicorn main:app --reload` (port 8000)
2. Frontend: `cd ../afsuu_Frontend && npm run dev` (port 3000)
3. Log in → open **Research Agent** → submit a topic → loading → markdown result

## Day 8 — Chroma vector store
- `vectorstore/{client,embeddings,chunking}.py`
- Data dir: `chroma_data/` (gitignored)
- Embeddings: local `all-MiniLM-L6-v2` (384-d, free, no API key)
- Chunking: `RecursiveCharacterTextSplitter` via `langchain-text-splitters`

```bash
# Prefer CPU torch (avoids multi-GB CUDA downloads)
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install sentence-transformers chromadb langchain-text-splitters
python -m scripts.test_vectorstore
```

First embedding run downloads ~80MB model — needs internet once.

## Note on Day 5 agent compatibility
Installed CrewAI is `0.30.x` (no `crewai.LLM`). Research agent now uses `langchain_groq.ChatGroq` + LangChain `Tool` for DuckDuckGo so the API boots cleanly.
