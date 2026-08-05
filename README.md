# PDF RAG Assistant

A full-stack RAG application that answers questions from PDF documents, with citations (document name, page number, retrieved text). Built with FastAPI, Qdrant, and OpenRouter free models.

## Architecture

```
PDFs ──▶ pypdf (per-page text) ──▶ word chunks w/ page metadata
                                      │
                                      ▼
                 NVIDIA Nemotron 3 Embed 1B (2048-dim, free API)
                                      │
                                      ▼
                          Qdrant (local Docker or Cloud free tier)
                                      │
   Browser ──▶ FastAPI ──▶ query embed ──▶ top-k retrieval ──▶ score gate
        ◀── answer + sources ──◀─ LLM (OpenRouter :free) ◀───────┘
```

## Libraries

- `fastapi` + `uvicorn` — web app / API
- `pypdf` — PDF parsing (page numbers)
- `qdrant-client` — vector storage & search
- `httpx` — OpenRouter API calls
- `python-dotenv` — configuration

## Models (all free)

- **Embedding (default):** NVIDIA `nvidia/nemotron-3-embed-1b` (2048-dim) via build.nvidia.com — free trial key, 40 RPM. Also supports **Groq** (`nomic-embed-text-v1_5`, 768-dim) and **OpenRouter** (`nvidia/nemotron-3-embed-1b:free`) by setting `EMBEDDING_PROVIDER` (nvidia | groq | openrouter).
- **Generation:** OpenRouter `openai/gpt-oss-20b:free`, with automatic fallbacks (`google/gemma-4-31b-it:free`, `nvidia/nemotron-3-super-120b-a12b:free`) — all configurable via `.env`

## How to run

1. `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
2. Create a free OpenRouter key (https://openrouter.ai/keys), a free embedding key (NVIDIA: https://build.nvidia.com or Groq: https://console.groq.com/keys), and a free Qdrant cluster (https://cloud.qdrant.io), then:
   `cp .env.example .env` and fill in `OPENROUTER_API_KEY`, `EMBEDDING_API_KEY`, `QDRANT_URL`, `QDRANT_API_KEY`
3. Download the PDFs (`python -m scripts.download_docs` needs `pip install gdown`, or put PDFs in `data/pdfs/` manually)
4. Index: `python -m scripts.ingest data/pdfs`
5. Run: `.venv/bin/uvicorn app.main:app --reload` → http://localhost:8000 (upload more PDFs via the UI)

## Assumptions

- PDFs are text-based (no OCR). Pages with no extractable text are skipped.
- Cited page numbers refer to the page as displayed in a PDF viewer (1-based), not the printed book pagination (the filenames' `p0683-p0794` ranges are the original report pagination).
- Out-of-document questions are rejected via an LLM instruction plus a retrieval score threshold (`RETRIEVAL_SCORE_THRESHOLD`); tune it per your corpus.
- Re-ingesting a document overwrites its chunks (deterministic point IDs).
- OpenRouter free tier has rate limits (~20 req/min, ~50 req/day without credits); embeddings are batched to stay within limits. The default NVIDIA embedding provider has no request-day cap (40 RPM).

## Deploy (Render free tier)

1. Push this repo to GitHub, create a new **Web Service** on https://render.com (free, no credit card).
2. Build: `pip install -r requirements.txt` · Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Add the same `.env` variables (OpenRouter + Qdrant) in Render → Environment.
4. After deploy, upload your PDFs through the web UI — data lives in Qdrant Cloud, so it persists.

API docs at `/docs`. Health check at `/health`.
