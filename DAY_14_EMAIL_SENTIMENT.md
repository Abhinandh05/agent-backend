# Day 14 — Email Agent + HuggingFace Tone Analysis

What was built for Day 14 of the AI Multi-Agent Business Operating System
(including the Day 14 Extension: pre-trained sentiment analysis).

## Overview

1. **Email Agent** (Groq + CrewAI) — drafts a professional subject + body from a brief  
2. **Optional SendGrid send** — `POST /api/v1/agents/email/send` (needs env keys)  
3. **Tone analysis** — pre-trained HuggingFace DistilBERT on the drafted body  
   (`distilbert-base-uncased-finetuned-sst-2-english`)

No Docker, no GPU, no training. Sentiment is **inference-only** and **advisory** —
it never blocks drafting or sending. Separate from scikit-learn churn/credit models.

**First sentiment call** downloads the model (~**260MB**). Expect a one-time delay
(and internet). Later calls are local CPU inference (usually well under a second).

---

## Files created / updated

### Agent + send
| File | Purpose |
|------|---------|
| `agents/email_agent.py` | Draft via Groq; `parse_email_output()` → subject/body/raw |
| `services/email_send_service.py` | Optional SendGrid v3 send via `httpx` |

### Sentiment (extension)
| File | Purpose |
|------|---------|
| `services/sentiment_service.py` | Load pipeline once; `analyze_sentiment(text) → {label, confidence, tone_warning, truncated}` |

Tone warning when `label == NEGATIVE` and `confidence > 0.7`. Long bodies are
truncated **only for the tone check** (~first 2000 chars ≈ 500 tokens); the email
content itself is never truncated. Model load errors match Day 8 embedding style.

### API
| Endpoint | Purpose |
|----------|---------|
| `POST /api/v1/agents/email` | Draft + non-blocking sentiment (`sentiment` may be `null` on failure) |
| `POST /api/v1/agents/email/send` | Send edited draft (SendGrid); **not** gated by sentiment |

Schemas: `EmailRequest`, `EmailSendRequest` in `schemas.py`.  
Router: `routers/agents.py`.

### Frontend (`afsuu_Frontend`)
| File | Purpose |
|------|---------|
| `app/agents/email/page.jsx` | Brief → draft; editable To/Subject/Body; amber warning or subtle Positive badge; Send never disabled by tone |
| `components/DashboardShell.jsx` | Nav link |
| `app/page.jsx` | Quick Action card |

### Tests / docs
| File | Purpose |
|------|---------|
| `tests/test_sentiment_service.py` | Real model when available; skips offline/missing deps |
| `tests/test_email_router.py` | Parse + draft/send routes (mocked LLM/sentiment) |
| `DAY_14_EMAIL_SENTIMENT.md` | This summary |
| `README.md` | Day 14 + Tone Analysis section |
| `requirements.txt` | `transformers`, `torch` + CPU-install tip |

---

## Test choice (sentiment)

**Real model when loadable; skip otherwise.** DistilBERT SST-2 is small/fast enough
to run in local pytest after one download. CI without internet/cache skips cleanly
so the suite stays green. Router tests mock `analyze_sentiment` so API behavior
(including `sentiment: null` on failure) is covered without downloading weights.

---

## Your steps

### 1) Install deps
```bash
source venv/bin/activate
# Tip: smaller CPU-only torch (avoids large CUDA wheels)
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install transformers
# Or pull everything: pip install -r requirements.txt
```

### 2) Pytest
```bash
pytest tests/test_sentiment_service.py tests/test_email_router.py -q
```

### 3) curl — login
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"YOUR_EMAIL","password":"YOUR_PASSWORD"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

### 4) Draft + sentiment — `POST /api/v1/agents/email`
```bash
curl -s -X POST http://localhost:8000/api/v1/agents/email \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"request":"Write a firm but polite email telling a vendor their late delivery is unacceptable and we are disappointed."}' \
  | python3 -m json.tool
```

**Successful response shape:**
```json
{
  "success": true,
  "data": {
    "subject": "...",
    "body": "...",
    "raw": "SUBJECT: ...\nBODY:\n...",
    "sentiment": {
      "label": "NEGATIVE",
      "confidence": 0.98,
      "tone_warning": "This email reads as quite negative in tone (98% confidence). You may want to review the wording before sending.",
      "truncated": false
    },
    "task_id": 1
  },
  "message": "Email draft completed",
  "error": null
}
```

### 5) Optional send — `POST /api/v1/agents/email/send`
Set `SENDGRID_API_KEY` and `SENDGRID_FROM_EMAIL` in `.env`, then:
```bash
curl -s -X POST http://localhost:8000/api/v1/agents/email/send \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"to":"client@example.com","subject":"Follow-up","body":"Hi,\n\n..."}'
```

---

## Constraints respected

| Constraint | How |
|------------|-----|
| No Docker / no GPU | Local CPU DistilBERT + existing FastAPI stack |
| No training | HuggingFace pre-trained weights only |
| Sentiment never blocks core flow | try/except → `sentiment: null`; Send not gated |
| Match project style | `APIResponse`, Task rows, threadpool, JWT |
