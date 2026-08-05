"""FastAPI application: RAG API + static frontend."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import ingest as ingest_service
from .config import settings
from .openrouter import OpenRouterError
from .rag import answer_question
from .vector_store import VectorStore, VectorStoreError

app = FastAPI(title="PDF RAG Assistant", version="1.0.0")

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class AskRequest(BaseModel):
    question: str


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health() -> dict:
    qdrant_ok = False
    try:
        VectorStore().list_documents()
        qdrant_ok = True
    except VectorStoreError:
        pass
    return {"status": "ok", "qdrant_configured": qdrant_ok}


@app.get("/api/documents")
def list_documents() -> dict:
    try:
        documents = VectorStore().list_documents()
    except VectorStoreError as exc:
        return {"documents": [], "error": str(exc)}
    return {
        "documents": documents,
        "total_chunks": sum(d["chunks"] for d in documents),
    }


@app.post("/api/ingest")
async def ingest_pdf(upload: UploadFile = File(...)) -> dict:
    if not upload.filename or not upload.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")
    pdf_bytes = await upload.read()
    try:
        return ingest_service.ingest_pdf(pdf_bytes, upload.filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (OpenRouterError, VectorStoreError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/api/ask")
def ask(body: AskRequest) -> dict:
    question = body.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    try:
        result = answer_question(question)
    except (OpenRouterError, VectorStoreError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {
        "question": question,
        "answer": result.answer,
        "available": result.available,
        "sources": [
            {"document": h.document, "page": h.page, "text": h.text, "score": round(h.score, 4)}
            for h in result.sources
        ],
    }


@app.get("/api/openrouter/models")
def configured_models() -> dict:
    """Expose which embedding/generation models the app uses."""
    return {
        "embedding_provider": settings.embedding_provider,
        "embedding_model": settings.embedding_model,
        "embedding_dim": settings.embedding_dim,
        "llm_model": settings.llm_model,
        "llm_fallbacks": settings.llm_fallback_models,
    }
