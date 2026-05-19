"""Show pdfplumber's table-detection output for the given PDF."""

from __future__ import annotations

import io
import sys
from pathlib import Path

import pdfplumber

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DEFAULT = Path(__file__).resolve().parent.parent / "corpus" / "pdfs" / (
    "The Dwarrow Scholar - Neo-Khuzdul Support Documents N-04 - Noun Types.pdf"
)


def main(path: Path) -> None:
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages):
            print(f"\n========== PAGE {i+1} ==========")
            text = page.extract_text() or ""
            print(f"FULL TEXT ({len(text)} chars):")
            print(text)
            tables = page.extract_tables()
            print(f"\nDETECTED {len(tables)} TABLES:")
            for j, t in enumerate(tables):
                print(f"\n-- TABLE {j+1} ({len(t)} rows) --")
                for row in t:
                    print("  | ".join((c or "")[:50] for c in row))


if __name__ == "__main__":
    target = DEFAULT if len(sys.argv) < 2 else Path(sys.argv[1])
    main(target)
