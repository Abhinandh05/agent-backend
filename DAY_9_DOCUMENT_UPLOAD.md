
# Day 9 — Document Upload + Parsing → Vector Store

What was built for Day 9 of the AI Multi-Agent Business Operating System.

## Overview
Authenticated file upload → parse by type → chunk → embed (MiniLM) → store in
local Chroma. Ready for Day 10 RAG queries. No Docker, no OCR, no paid storage.

---

## Files created / updated

### Model + migration
| File | Purpose |
|------|---------|
| `models/document.py` | SQLAlchemy `Document` (status, chunk_count, paths, …) |
| `models/user.py` | `documents` relationship |
| `models/__init__.py` | Export `Document` |
| `alembic/versions/c3d9e8f1a2b0_add_documents_table.py` | Creates `documents` table |
| `alembic/env.py` | Imports `Document` for metadata |

### Service + storage
| File | Purpose |
|------|---------|
| `services/document_service.py` | `extract_text()`, `process_document()`, background job |
| `uploads/` | Local file storage (gitignored except `.gitkeep`) |

Parsers: `.pdf` (pdfplumber), `.docx` (python-docx), `.xlsx`/`.csv` (pandas,
one line per row for chunk-friendly text), `.txt` (plain read).  
OCR/scanned PDFs noted as future (needs Tesseract).

### Vector store
| File | Purpose |
|------|---------|
| `vectorstore/client.py` | Added `delete_by_document_id()` |

Reuses Day 8: `split_text()`, `embed_batch()`, `add_chunks()`.

### API
| Endpoint | Purpose |
|----------|---------|
| `POST /api/v1/documents/upload` | Auth + type/size checks; save file; background index |
| `GET /api/v1/documents` | List current user's docs (newest first) |
| `GET /api/v1/documents/{id}` | Detail (owner only) |
| `DELETE /api/v1/documents/{id}` | Disk + DB + Chroma chunks |

Router: `routers/documents.py`, registered in `main.py`.  
Upload limit: **10MB**. Background indexing via FastAPI `BackgroundTasks`.

### Tests / deps / docs
| File | Purpose |
|------|---------|
| `tests/test_documents_router.py` | 401 / 400 / 200 upload + user isolation |
| `requirements.txt` | `pdfplumber`, `python-docx`, `openpyxl` (`python-multipart` already present) |
| `.gitignore` | `uploads/*` |
| `DAY_9_DOCUMENT_UPLOAD.md` | This summary |

**Frontend:** not in Day 9 (fits Day 10 with RAG UI).

---

## Status flow
`uploaded` → (background) `processing` → `indexed`  
On failure: `failed` + `error_message` set (request itself still returns 200 on upload).

---

## Your steps

### 1) Install deps
```bash
source venv/bin/activate
pip install pdfplumber python-docx openpyxl
# or: pip install -r requirements.txt
```

### 2) Migrate DB
```bash
# If alembic.ini is present / configured with DATABASE_URL:
alembic upgrade head
```
Revision: `c3d9e8f1a2b0` — creates `documents`.

### 3) Run API
```bash
uvicorn main:app --reload --port 8000
```

### 4) Manual curl

```bash
# Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"YOUR_EMAIL","password":"YOUR_PASSWORD"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Upload a small text file
echo "Q3 revenue grew 12 percent driven by enterprise renewals." > /tmp/day9_test.txt
curl -s -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/day9_test.txt"

# Immediate response shape (status still "uploaded"):
# {
#   "success": true,
#   "data": { "document_id": 1, "filename": "day9_test.txt", "status": "uploaded" },
#   "message": "File uploaded; processing started in the background.",
#   "error": null
# }

# Wait a few seconds for MiniLM + Chroma, then list:
curl -s http://localhost:8000/api/v1/documents \
  -H "Authorization: Bearer $TOKEN"

# After indexing, expect status "indexed" and chunk_count > 0:
# {
#   "success": true,
#   "data": {
#     "documents": [
#       {
#         "id": 1,
#         "filename": "day9_test.txt",
#         "status": "indexed",
#         "chunk_count": 1,
#         ...
#       }
#     ]
#   },
#   "message": "Documents retrieved",
#   "error": null
# }

# Single doc
curl -s http://localhost:8000/api/v1/documents/1 \
  -H "Authorization: Bearer $TOKEN"
```

### 5) Pytest
```bash
pytest tests/test_documents_router.py -q
```

---

## Not today (Day 10+)
- RAG query endpoint / agent tool over uploaded docs  
- Frontend upload UI  
- OCR for scanned PDFs (`pytesseract`)
