"""First-pass peek at one Dwarrow Scholar PDF: page count, font-size
distribution, and per-page text dump. Used to design the extractor for
similar PDFs.
"""

from __future__ import annotations

import io
import sys
from collections import Counter
from pathlib import Path

import pdfplumber

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DEFAULT = Path(__file__).resolve().parent.parent / "corpus" / "pdfs" / (
    "The Dwarrow Scholar - Neo-Khuzdul Support Documents N-04 - Noun Types.pdf"
)


def main(path: Path = DEFAULT) -> None:
    print(f"Peeking: {path.name}")
    with pdfplumber.open(path) as pdf:
        print(f"Pages: {len(pdf.pages)}")
        # Font/size distribution
        sizes = Counter()
        fonts = Counter()
        for page in pdf.pages:
            for c in page.chars:
                sizes[round(c["size"], 1)] += 1
                fonts[c.get("fontname", "?")] += 1
        print("\nTop font sizes (rounded):")
        for s, c in sizes.most_common(8):
            print(f"  size={s:5}  count={c:,}")
        print("\nTop fonts:")
        for f, c in fonts.most_common(8):
            print(f"  {f}  count={c:,}")

        # First 2 pages of text, raw
        for i, page in enumerate(pdf.pages[:3]):
            text = page.extract_text() or ""
            print(f"\n----- PAGE {i+1} ({len(text)} chars) -----")
            print(text[:2500])


if __name__ == "__main__":
    target = DEFAULT if len(sys.argv) < 2 else Path(sys.argv[1])
    main(target)
