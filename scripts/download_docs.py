"""Download the assignment PDFs from the shared Google Drive folder.

Usage:
    python -m scripts.download_docs
"""
from __future__ import annotations

import sys
from pathlib import Path

FOLDER_ID = "1VN7E4YfANr4Zde4sias_JZw6piyLHvu2"
DEST = Path(__file__).resolve().parent.parent / "data" / "pdfs"


def main() -> int:
    try:
        import gdown  # optional dependency
    except ImportError:
        print("gdown is not installed. Run: .venv/bin/pip install gdown")
        return 1

    DEST.mkdir(parents=True, exist_ok=True)
    url = f"https://drive.google.com/drive/folders/{FOLDER_ID}"
    print(f"Downloading folder {url} into {DEST} ...")
    gdown.download_folder(url=url, output=str(DEST), quiet=False, use_cookies=False)
    print(f"Done. PDFs are in {DEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
