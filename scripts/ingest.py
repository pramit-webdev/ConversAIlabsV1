"""CLI: index one or more PDFs into Qdrant.

Usage:
    python -m scripts.ingest data/pdfs/employee_handbook.pdf
    python -m scripts.ingest data/pdfs/            # whole folder
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.chunker import chunk_pdf  # noqa: E402
from app.ingest import ingest_pdf  # noqa: E402
from app.vector_store import VectorStore  # noqa: E402


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2

    target = Path(sys.argv[1])
    pdfs = sorted(target.glob("*.pdf")) if target.is_dir() else [target]
    pdfs = [p for p in pdfs if p.is_file() and p.suffix.lower() == ".pdf"]
    if not pdfs:
        print(f"No PDF files found at {target}")
        return 1

    indexed = {d["document"]: d["chunks"] for d in VectorStore().list_documents()}

    for path in pdfs:
        expected = len(chunk_pdf(path.read_bytes(), path.name))
        if indexed.get(path.name) == expected:
            print(f"Skipping {path.name} (already indexed: {expected} chunks)")
            continue
        print(f"Ingesting {path.name} ...", flush=True)
        summary = ingest_pdf(path.read_bytes(), path.name)
        print(
            f"  done: {summary['chunks_indexed']} chunks across "
            f"{summary['pages']} pages (model: {summary['embedding_model']})"
        )
    print("All documents indexed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
