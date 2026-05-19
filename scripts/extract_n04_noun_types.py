"""Extract Neo-Khuzdul noun-type taxonomy from N-04 Noun Types.pdf into
data/grammar/noun_types.json.

Schema (per noun type):
    {
        "type_id": "1" | "11b" | ...,
        "label": "Incarnates",
        "description": "related to ...",
        "tri_radical": {"pattern": "CuCC", "example": "khuzd"},
        "bi_radical":  {"pattern": "CaiC", "example": "daig"} | null,
        "source": {"pdf": "N-04 - Noun Types.pdf", "page": 1}
    }

The Phase 1 plan calls for one machine-readable schema per grammar phenomenon.
This script is the template — same pattern (peek → regex over plumbed text →
JSON) will work for the other 76 PDFs once their layouts are inspected.
"""

from __future__ import annotations

import io
import json
import re
import sys
from pathlib import Path

import pdfplumber

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PDF_PATH = PROJECT_ROOT / "corpus" / "pdfs" / (
    "The Dwarrow Scholar - Neo-Khuzdul Support Documents N-04 - Noun Types.pdf"
)
OUT_PATH = PROJECT_ROOT / "data" / "grammar" / "noun_types.json"

# Each row in the PDF text reads:
#   TYPE <id> <semantic description> <tri-pattern> <tri-example> (<bi-pattern> <bi-example> | does not exist)
#
# IDs are usually digits but include "11b". The semantic description is
# free-form text that may contain spaces, slashes, parens. The pattern is a
# Khuzdul template like CuCC, CaiC, CâCaC, iCCaC, aCCâC, CâCîC, etc — a
# mix of C's and lowercase vowel letters (including circumflexed vowels).
# Examples are lowercase Khuzdul transliteration tokens.
#
# Strategy: find the last two whitespace-delimited tokens of the line. If
# they are "does not exist" with no trailing example, the bi-radical row is
# absent. Otherwise they are (bi_pattern, bi_example). Then strip them off
# and repeat for the tri-radical pair. Whatever remains between "TYPE <id>"
# and the tri-radical pair is the description.

PATTERN_TOKEN = re.compile(r"^[CaeiouâêîôûüœCAEIOU]+\d*$")  # rough; just to spot patterns
EXAMPLE_TOKEN = re.compile(r"^['ʔa-zâêîôûA-ZÂÊÎÔÛ]+$")  # token of Khuzdul orthography

ROW_PREFIX = re.compile(r"^TYPE\s+(\S+)\s+(.*)$")


def parse_row(line: str) -> dict | None:
    line = line.strip()
    m = ROW_PREFIX.match(line)
    if not m:
        return None
    type_id, rest = m.group(1), m.group(2).strip()

    # Bi-radical pair detection
    bi_pattern: str | None = None
    bi_example: str | None = None
    if rest.endswith("does not exist"):
        rest = rest[: -len("does not exist")].rstrip()
    else:
        # The last two tokens should be (bi_pattern, bi_example)
        parts = rest.rsplit(None, 2)
        if len(parts) == 3:
            rest, bi_pattern, bi_example = parts
        elif len(parts) == 2:
            rest, bi_pattern = parts
            bi_example = None

    # Tri-radical pair: last two tokens of what remains
    parts = rest.rsplit(None, 2)
    if len(parts) < 3:
        # Some rows might be malformed; bail
        return None
    description, tri_pattern, tri_example = parts
    description = description.strip()

    return {
        "type_id": type_id,
        "label": extract_label(description),
        "description": description,
        "tri_radical": {"pattern": tri_pattern, "example": tri_example},
        "bi_radical": (
            None
            if bi_pattern is None
            else {"pattern": bi_pattern, "example": bi_example}
        ),
    }


# Heuristic: the first few rows of N-04 use short tags like "Incarnates",
# "Agent (person-form)", "MISC 1 (Ereborisms - Type 1)" as labels; longer
# rows use a "related to X" pattern where the label is X.
_RELATED_RE = re.compile(r"^related to\s+(.+)$", re.IGNORECASE)


def extract_label(description: str) -> str:
    m = _RELATED_RE.match(description)
    if m:
        return m.group(1).strip()
    return description


def extract() -> list[dict]:
    rows: list[dict] = []
    with pdfplumber.open(PDF_PATH) as pdf:
        page = pdf.pages[0]
        text = page.extract_text() or ""
    for line in text.splitlines():
        row = parse_row(line)
        if row is not None:
            row["source"] = {"pdf": PDF_PATH.name, "page": 1}
            rows.append(row)
    return rows


def main() -> int:
    rows = extract()
    print(f"Extracted {len(rows)} noun types")
    if not rows:
        print("WARNING: no rows extracted — layout drift?", file=sys.stderr)
        return 1

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(rows, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUT_PATH}")

    print("\nSample:")
    for r in rows[:5]:
        bi = r["bi_radical"]
        bi_str = f"{bi['pattern']}/{bi['example']}" if bi else "—"
        print(
            f"  TYPE {r['type_id']:>4s}  {r['tri_radical']['pattern']}/{r['tri_radical']['example']:<8s}"
            f"  bi={bi_str:<14s}  label={r['label']!r}"
        )

    # Sanity: count of "does not exist" vs bi-radical present
    have_bi = sum(1 for r in rows if r["bi_radical"])
    print(f"\nWith bi-radical form: {have_bi}/{len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
