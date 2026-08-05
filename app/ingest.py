"""PDF ingestion: parse -> chunk -> embed -> store in Qdrant."""
from __future__ import annotations

from qdrant_client import models

from .chunker import chunk_pdf
from .config import settings
from .openrouter import build_embedder
from .vector_store import VectorStore, _point_id


def ingest_pdf(pdf_bytes: bytes, document_name: str) -> dict:
    """Parse, chunk, embed and index a single PDF. Returns a summary."""
    chunks = chunk_pdf(pdf_bytes, document_name)
    if not chunks:
        raise ValueError(f"No extractable text found in {document_name!r}")

    texts = [c.text for c in chunks]
    with build_embedder() as embedder:
        vectors = embedder.embed(texts, input_type="passage")

    if len(vectors) != len(chunks):
        raise RuntimeError(
            f"Embedding count mismatch: expected {len(chunks)} vectors, got {len(vectors)}"
        )

    points = [
        models.PointStruct(
            id=_point_id(f"{chunk.document}::{chunk.page}::{chunk.index}"),
            vector=vector,
            payload={
                "text": chunk.text,
                "document": chunk.document,
                "page": chunk.page,
                "chunk_index": chunk.index,
            },
        )
        for chunk, vector in zip(chunks, vectors)
    ]

    store = VectorStore()
    stored = store.upsert(points)
    return {
        "document": document_name,
        "chunks_indexed": stored,
        "pages": len(set(c.page for c in chunks)),
        "embedding_provider": settings.embedding_provider,
        "embedding_model": settings.embedding_model,
    }
