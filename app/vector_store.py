"""Qdrant vector store wrapper (Qdrant Cloud free tier or local Docker)."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass

from qdrant_client import QdrantClient, models

from .config import settings

_MAX_UPSERT_ATTEMPTS = 5


class VectorStoreError(Exception):
    """Raised when Qdrant is not configured or unreachable."""


@dataclass(frozen=True)
class Hit:
    text: str
    document: str
    page: int
    score: float


def _point_id(seed: str) -> str:
    """Deterministic UUID so re-ingesting a document never duplicates points."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, seed))


class VectorStore:
    def __init__(self) -> None:
        if not settings.qdrant_url:
            raise VectorStoreError(
                "QDRANT_URL is not set. Create a free cluster at https://cloud.qdrant.io "
                "(or run Qdrant locally via Docker and set QDRANT_URL=http://localhost:6333)."
            )
        self._client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key or None,
            timeout=180,  # free-tier clusters are slow; writes can take a while
        )
        self._collection = settings.qdrant_collection

    def ensure_collection(self) -> None:
        if not self._client.collection_exists(self._collection):
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config=models.VectorParams(
                    size=settings.embedding_dim,
                    distance=models.Distance.COSINE,
                ),
            )
            return
        info = self._client.get_collection(self._collection)
        actual = info.config.params.vectors.size
        if actual != settings.embedding_dim:
            raise VectorStoreError(
                f"Collection {self._collection!r} has {actual}-dim vectors but the current "
                f"embedding model produces {settings.embedding_dim} dims. Delete the collection "
                "or re-ingest with a matching model."
            )

    def upsert(self, points: list[models.PointStruct]) -> int:
        if not points:
            return 0
        self.ensure_collection()
        batch_size = 200  # keep each request well under Qdrant's 32MB payload cap
        total = 0
        for i in range(0, len(points), batch_size):
            batch = points[i : i + batch_size]
            for attempt in range(1, _MAX_UPSERT_ATTEMPTS + 1):
                try:
                    self._client.upsert(collection_name=self._collection, points=batch)
                    break
                except Exception:
                    if attempt == _MAX_UPSERT_ATTEMPTS:
                        raise
                    time.sleep(10 * attempt)
            total += len(batch)
        return total

    def search(self, vector: list[float], *, limit: int | None = None) -> list[Hit]:
        self.ensure_collection()
        limit = limit or settings.retrieval_top_k
        response = self._client.query_points(
            collection_name=self._collection,
            query=vector,
            limit=limit,
            with_payload=True,
        )
        hits: list[Hit] = []
        for res in response.points:
            payload = res.payload or {}
            hits.append(
                Hit(
                    text=payload.get("text", ""),
                    document=payload.get("document", "unknown"),
                    page=int(payload.get("page", 0)),
                    score=float(res.score),
                )
            )
        return hits

    def list_documents(self) -> list[dict]:
        """Return metadata about every indexed document."""
        if not self._client.collection_exists(self._collection):
            return []
        seen: dict[str, dict] = {}
        offset: str | None = None
        while True:
            points, next_offset = self._client.scroll(
                collection_name=self._collection,
                limit=200,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            for point in points:
                payload = point.payload or {}
                name = payload.get("document", "unknown")
                entry = seen.setdefault(name, {"document": name, "chunks": 0, "pages": set()})
                entry["chunks"] += 1
                entry["pages"].add(int(payload.get("page", 0)))
            if next_offset is None:
                break
            offset = next_offset
        result = [
            {"document": e["document"], "chunks": e["chunks"], "pages": sorted(e["pages"])}
            for e in seen.values()
        ]
        return sorted(result, key=lambda d: d["document"])
