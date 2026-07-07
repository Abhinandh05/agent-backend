## Day 5 — Research Agent

Today's goal was to build the first working agent for the AI Multi-Agent Business Operating System, which is the Research Agent using CrewAI.

### What Was Built
- Integrated `crewai` and `duckduckgo-search` into the project.
- Created `tools/search_tool.py` using DuckDuckGo search (completely free, no API key needed).
- Built `agents/research_agent.py` defining the Research Agent and its tasks.
- Created a standalone test script `scripts/test_research_agent.py` to run the agent without the FastAPI server.
- Wrote basic `pytest` cases in `tests/test_research_agent.py` to verify the agent and task initialization.

### Fixes & Updates Made Today

#### 1. Switched DuckDuckGo Search Library
- **Old:** `duckduckgo_search` (deprecated, caused import errors)
- **New:** `ddgs` — the updated replacement package
- Updated `tools/search_tool.py` and `requirements.txt` accordingly.

#### 2. Updated Groq LLM Model
- **Old:** `llama3` (no longer available on Groq)
- **New:** `meta-llama/llama-4-scout` — a supported and active Groq model
- Updated `agents/research_agent.py` with the correct model name.

#### 3. Patched CrewAI `cache_breakpoint` Bug
- CrewAI was sending a `cache_breakpoint` field in messages that Groq's API does not support, causing `400 Bad Request` errors.
- Added a monkey-patch in `agents/research_agent.py` that strips `cache_breakpoint` from messages before they are sent to the provider.

#### 4. Fixed `ModuleNotFoundError: No module named 'dotenv'`
- The `python-dotenv` package was listed in `requirements.txt` but not installed in the active virtual environment.
- Fixed by running `pip install -r requirements.txt` inside the activated `venv`.

#### 5. Fixed Missing / Invalid `GROQ_API_KEY`
- The `.env` file was missing or had a placeholder key.
- Added a valid Groq API key (starting with `gsk_`) to `backend/.env`.

### Environment Configuration
The application requires one API key:
1. `GROQ_API_KEY`: Required for the Groq LLM (`meta-llama/llama-4-scout`) that powers CrewAI. Get yours at https://console.groq.com/keys

You need to create or edit `backend/.env` with a valid key based on `backend/.env.example`.

```env
GROQ_API_KEY=gsk_...
```

### Running the Test Script

To run the standalone test script, first activate your virtual environment:

```bash
source venv/bin/activate
```

Install any new dependencies from `requirements.txt`:

```bash
pip install -r requirements.txt
```

Run the script from the `backend/` directory:

```bash
python -m scripts.test_research_agent
```

You can also pass a custom topic to research:

```bash
python -m scripts.test_research_agent "Latest trends in artificial intelligence for 2026"
```

### Current Status
✅ Research Agent is **fully working** — DuckDuckGo search executes, Groq LLM responds, and the crew completes successfully.
