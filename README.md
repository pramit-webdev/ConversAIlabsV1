# PDF RAG Assistant

A full-stack RAG application that answers questions from PDF documents, with citations (document name, page number, retrieved text). Built with FastAPI, Qdrant, and NVIDIA free models — with a DeepSeek-style chat UI (threads, streaming answers, markdown rendering).

**Live demo:** https://pdf-rag-assistant-pxpa.onrender.com

## Features

- **Chat UI** — DeepSeek-style: dark sidebar with chat history, no-bubble message rows, markdown rendering (headings, tables, code blocks with copy button, lists, quotes), suggestion chips, streaming answers.
- **Streaming with early evidence** — retrieved sources appear under the answer within seconds of asking; when the answer completes, only the sources it actually cited stay (uncited cards fade out).
- **Citations** — `[1]`, `[2]` markers in the answer link to the exact page + text snippet.
- **Relevant-question gating** — out-of-document questions are refused (retrieval score threshold + LLM instruction).
- **Persistent threads** — chats saved in localStorage, uploads indexed into Qdrant Cloud (survives redeploys).

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
        ◀── answer + sources ◀─ LLM (NVIDIA free chat) ◀────────┘
```

## Libraries

- `fastapi` + `uvicorn` — web app / API (SSE streaming)
- `pypdf` — PDF parsing (page numbers)
- `qdrant-client` — vector storage & search
- `httpx` — OpenAI-compatible API calls (embeddings + chat)
- `python-dotenv` — configuration
- Vanilla JS frontend (no frameworks, no CDN) — streaming via fetch + ReadableStream

## Models (all free, NVIDIA build.nvidia.com)

- **Embedding:** `nvidia/nemotron-3-embed-1b` (2048-dim) — 40 RPM free tier, no daily cap. Also supports **Groq** (`nomic-embed-text-v1_5`) and **OpenRouter** (`nvidia/nemotron-3-embed-1b:free`) via `EMBEDDING_PROVIDER`.
- **Generation:** `nvidia/nemotron-nano-3-30b-a3b` (NVIDIA free chat), with automatic fallback chain: `nvidia/nemotron-3-nano-30b-a3b` → `meta/llama-3.1-8b-instruct`. All configurable via `.env`. An OpenRouter key is *not* required, but setting `LLM_BASE_URL`/`LLM_API_KEY` to OpenRouter works too.

## How to run

1. `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
2. Create a free NVIDIA key (https://build.nvidia.com — one key works for both embedding and chat) and a free Qdrant cluster (https://cloud.qdrant.io), then:
   `cp .env.example .env` and fill in `EMBEDDING_API_KEY`, `QDRANT_URL`, `QDRANT_API_KEY` (LLM vars default to NVIDIA with the embedding key).
3. Download the PDFs (`python -m scripts.download_docs` needs `pip install gdown`, or put PDFs in `data/pdfs/` manually)
4. Index: `python -m scripts.ingest data/pdfs`
5. Run: `.venv/bin/uvicorn app.main:app --reload` → http://localhost:8000 (upload more PDFs via the UI)

## Assumptions

- PDFs are text-based (no OCR). Pages with no extractable text are skipped.
- Cited page numbers refer to the page as displayed in a PDF viewer (1-based).
- Out-of-document questions are rejected via a retrieval score threshold (`RETRIEVAL_SCORE_THRESHOLD`) plus an LLM instruction; tune it per your corpus.
- Re-ingesting a document overwrites its chunks (deterministic point IDs).
- NVIDIA free tier: embeddings ~40 RPM (batched + paced); chat is generous, though slower under load.

## Deploy (Render free tier)

1. Push this repo to GitHub, create a new **Web Service** on https://render.com (free, no credit card).
2. Build: `pip install -r requirements.txt` · Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Add the same `.env` variables in Render → Environment (`EMBEDDING_API_KEY`, `QDRANT_URL`, `QDRANT_API_KEY`; optional `LLM_BASE_URL`/`LLM_API_KEY`/`LLM_MODEL`).
4. After deploy, upload your PDFs through the web UI — data lives in Qdrant Cloud, so it persists.

API docs at `/docs`. Health check at `/health`.
