"""End-to-end RAG pipeline: retrieve -> gate -> generate -> cite."""
from __future__ import annotations

from dataclasses import dataclass, field

from .config import settings
from .openrouter import OpenRouterError, build_embedder, build_llm
from .vector_store import Hit, VectorStore

NOT_FOUND_ANSWER = "The information is not available in the provided documents."

SYSTEM_PROMPT = (
    "You are a precise document assistant. You answer questions using ONLY the "
    "numbered sources provided in the user message, which were retrieved from a "
    "set of PDF documents. Rules:\n"
    "1. If the answer is not in the sources, reply with exactly: "
    f'"{NOT_FOUND_ANSWER}"\n'
    "2. Never invent facts, and never use outside knowledge.\n"
    "3. When you use a source, cite it inline as [n] where n is its number.\n"
    "4. Keep the answer concise and factual."
)


@dataclass
class RAGAnswer:
    answer: str
    available: bool
    sources: list[Hit] = field(default_factory=list)


def _build_context(hits: list[Hit]) -> str:
    blocks = []
    for i, hit in enumerate(hits, start=1):
        blocks.append(f"[{i}] Source: {hit.document} (page {hit.page})\n{hit.text}")
    return "\n\n".join(blocks)


def _parse_cited_markers(answer: str, num_sources: int) -> list[int]:
    """Extract citation markers ([1], 【1】) from the model's answer."""
    import re

    markers: set[int] = set()
    for match in re.findall(r"[\[【](\d+)[\]】]", answer):
        n = int(match)
        if 1 <= n <= num_sources:
            markers.add(n)
    return sorted(markers)


def answer_question(question: str, top_k: int | None = None) -> RAGAnswer:
    """Full pipeline. Raises VectorStoreError/OpenRouterError on failure."""
    top_k = top_k or settings.retrieval_top_k
    store = VectorStore()

    with build_embedder() as embedder, build_llm() as llm:
        # 1. Embed the question
        query_vector = embedder.embed([question], input_type="query")[0]

        # 2. Retrieve
        hits = store.search(query_vector, limit=top_k)

        # 3. Gate: nothing relevant retrieved -> do not answer
        if not hits or hits[0].score < settings.retrieval_score_threshold:
            return RAGAnswer(answer=NOT_FOUND_ANSWER, available=False)

        # 4. Generate with grounded context
        context = _build_context(hits)
        answer = llm.chat(
            system=SYSTEM_PROMPT,
            user=f"Question: {question}\n\nSources:\n{context}",
        )

        # 5. Citations: keep only sources actually cited; fall back to top-1
        if answer == NOT_FOUND_ANSWER or "not available in the provided documents" in answer.lower():
            return RAGAnswer(answer=NOT_FOUND_ANSWER, available=False, sources=[])

        cited = _parse_cited_markers(answer, len(hits))
        if cited:
            sources = [hits[i - 1] for i in cited]
        else:
            sources = hits[:1]  # model omitted markers; attribute to strongest source
        return RAGAnswer(answer=answer, available=True, sources=sources)
