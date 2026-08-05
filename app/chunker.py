"""PDF parsing and text chunking.

Each chunk remembers its document name and page number so answers can carry
accurate citations.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from io import BytesIO

from pypdf import PdfReader

from .config import settings

# Manupatra watermark lines (e.g. "Copyright @ Manupatra 2024-2025 Page 3530")
# add no content and pollute retrieval, so they are stripped from page text.
_WATERMARK_RE = re.compile(r"^\s*Copyright\s*@\s*Manupatra.*\bPage\s+\d+\s*\.?\s*$", re.IGNORECASE)


@dataclass(frozen=True)
class Chunk:
    text: str
    document: str
    page: int  # 1-based page number
    index: int  # chunk index within the document


def extract_page_text(pdf_bytes: bytes) -> list[str]:
    """Return one string per page of the PDF, watermark lines removed."""
    reader = PdfReader(BytesIO(pdf_bytes))
    pages: list[str] = []
    for page in reader.pages:
        raw = page.extract_text() or ""
        cleaned = "\n".join(line for line in raw.splitlines() if not _WATERMARK_RE.match(line))
        pages.append(cleaned.strip())
    return pages


def chunk_text(text: str, *, size: int | None = None, overlap: int | None = None) -> list[str]:
    """Split text into word-based chunks with overlap, on word boundaries."""
    size = size or settings.chunk_size
    overlap = overlap or settings.chunk_overlap
    if overlap >= size:
        overlap = size // 2

    words = text.split()
    if not words:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + size, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = max(start + size - overlap, start + 1)
    return chunks


def chunk_pdf(pdf_bytes: bytes, document_name: str) -> list[Chunk]:
    """Parse a PDF and return page-aware chunks."""
    chunks: list[Chunk] = []
    index = 0
    for page_no, page_text in enumerate(extract_page_text(pdf_bytes), start=1):
        for piece in chunk_text(page_text):
            if piece:
                chunks.append(Chunk(text=piece, document=document_name, page=page_no, index=index))
                index += 1
    return chunks
