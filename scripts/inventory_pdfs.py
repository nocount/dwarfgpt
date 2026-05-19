"""Walk `corpus/pdfs/` and print a one-line summary per file.

This is a Phase 1 step 3 prep tool — it sniffs each PDF so we know what topic
each file covers before writing dedicated extractors per topic.

Output per file:
    <filename>   <page_count>p   <byte_size>   <heuristic_topic>   <first_header>

The heuristic_topic is a best-effort label derived from filename + first
page's text. Trust it for sorting; don't trust it for routing.
"""

from __future__ import annotations

import io
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PDF_DIR = PROJECT_ROOT / "corpus" / "pdfs"

# Heuristic topic keywords. Order matters — first match wins.
TOPIC_KEYWORDS: list[tuple[str, list[str]]] = [
    ("dictionary",          ["dictionary", "lexicon", "glossary"]),
    ("verb-stems",          ["verb stem", "verbal stem", "CCC", "trilateral"]),
    ("verb-conjugation",    ["conjugation", "imperfect", "perfect", "jussive"]),
    ("pronouns",            ["pronoun"]),
    ("plurals",             ["broken plural", "plural form", "broken-plural"]),
    ("construct-state",     ["construct state", "construct-state", "iḍāfa", "izafe"]),
    ("noun-patterns",       ["noun pattern", "noun type", "CaCC", "nominal"]),
    ("adjectives",          ["adjective", "adjectival"]),
    ("phonology",           ["phonology", "phoneme", "gemination", "stress",
                              "schwa", "shwa", "epenthesis"]),
    ("orthography",         ["orthography", "cirth", "tengwar", "transcription"]),
    ("syntax",              ["syntax", "word order", "clause"]),
    ("particles",           ["particle", "preposition", "conjunction"]),
    ("imperative",          ["imperative", "jussive"]),
    ("derivation",          ["derivation", "derived form"]),
    ("numerals",            ["numeral", "cardinal", "ordinal"]),
    ("phrasebook",          ["phrasebook", "phrase book", "sentences", "examples"]),
    ("lessons",             ["lesson", "tutorial", "course"]),
]


def guess_topic(filename: str, head_text: str) -> str:
    bag = (filename + " " + head_text).lower()
    for topic, kws in TOPIC_KEYWORDS:
        for kw in kws:
            if kw.lower() in bag:
                return topic
    return "?"


def head_lines(text: str, n: int = 3) -> str:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return " | ".join(lines[:n])[:120]


def main() -> None:
    if not PDF_DIR.exists():
        print(f"corpus/pdfs/ does not exist. Create it and drop PDFs there.")
        sys.exit(1)

    pdfs = sorted(PDF_DIR.glob("*.pdf"))
    if not pdfs:
        print(f"No PDFs in {PDF_DIR.relative_to(PROJECT_ROOT)}/.")
        print(f"Drop The Dwarrow Scholar's dictionary + grammar PDFs in that directory")
        print(f"and re-run this script. See corpus/README.md for naming guidance.")
        return

    try:
        from pypdf import PdfReader
    except ImportError:
        print("pypdf is not installed. Add it with:")
        print("  uv add pypdf")
        sys.exit(1)

    print(f"{'filename':<55} {'pp':>4} {'size':>9}  {'topic':<18}  first lines")
    print("-" * 140)
    for p in pdfs:
        try:
            reader = PdfReader(str(p))
            pages = len(reader.pages)
            first_text = reader.pages[0].extract_text() or "" if pages else ""
        except Exception as exc:
            print(f"{p.name:<55} {'?':>4} {p.stat().st_size:>9}  <error: {exc!s}>")
            continue
        topic = guess_topic(p.name, first_text)
        size_kb = p.stat().st_size // 1024
        size_str = f"{size_kb} KB" if size_kb < 1024 else f"{size_kb // 1024} MB"
        head = re.sub(r"\s+", " ", first_text)[:120]
        print(f"{p.name:<55} {pages:>4} {size_str:>9}  {topic:<18}  {head}")


if __name__ == "__main__":
    main()
