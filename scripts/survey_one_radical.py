"""Dump every entry for radical KhZD, grouped by broad-POS, to inform the
canonical-form picking rules for the headword consolidator.
"""

from __future__ import annotations

import io
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DATA = Path(__file__).resolve().parent.parent / "data" / "dictionary.json"

# Mapping from regex-on-tag → broad POS category.
# Order matters: first match wins.
POS_RULES: list[tuple[str, str]] = [
    (r"^NOUN TYPE", "NOUN"),
    (r"^Infinitive\b", "VERB-INFINITIVE"),
    (r"\bImperfect\b", "VERB-IMPERFECT"),
    (r"\bPerfect\b", "VERB-PERFECT"),
    (r"\bCausative\b", "VERB-CAUSATIVE"),
    (r"\bPassive\b", "VERB-PASSIVE"),
    (r"\bEnergetic\b", "VERB-ENERGETIC"),
    (r"\bJussive\b", "VERB-JUSSIVE"),
    (r"\bInteractive\b", "VERB-INTERACTIVE"),
    (r"\bImperative\b", "VERB-IMPERATIVE"),
    (r"\bGerund\b", "VERB-GERUND"),
    (r"\bParticiple\b", "VERB-PARTICIPLE"),
    (r"\bContinual\b", "VERB-CONTINUAL"),
    (r"\bIntimate\b", "DIMINUTIVE"),
    (r"\bDERIVED\b|\bDEFINED\b", "DERIVED"),
    (r"\bFragmental\b|\bElemental\b", "NOUN-FRAGMENTAL"),
    (r"^ADJECTIVE\b|\bComp(e|a)rative\b|\bSuperlative\b", "ADJECTIVE"),
    (r"^Adverb\b", "ADVERB"),
    (r"^Interjection\b|^INTERJECTION", "INTERJECTION"),
    (r"^Conjunction\b", "CONJUNCTION"),
    (r"^Preposition\b|^Article\b", "FUNCTION"),
    (r"^Pronoun\b", "PRONOUN"),
    (r"^Number\b|^Numeral\b", "NUMERAL"),
    (r"^Inflection:", "INFLECTION-MARKER"),
    (r"^Compound\b", "COMPOUND"),
]
COMPILED_POS_RULES = [(re.compile(p, re.IGNORECASE), label) for p, label in POS_RULES]


def classify(tag: str) -> str:
    for rx, label in COMPILED_POS_RULES:
        if rx.search(tag):
            return label
    return "OTHER"


def main() -> None:
    entries = json.loads(DATA.read_text(encoding="utf-8"))
    target = "KhZD"
    rows = [e for e in entries if e.get("radical") == target]
    print(f"radical {target}: {len(rows)} entries")

    by_pos = defaultdict(list)
    for e in rows:
        by_pos[classify(e.get("tag") or "")].append(e)

    print(f"\nBreakdown by broad POS:")
    for pos in sorted(by_pos, key=lambda p: -len(by_pos[p])):
        n = len(by_pos[pos])
        print(f"  {pos:25s} {n:4d}")

    for pos, group in by_pos.items():
        print(f"\n=== {pos} ({len(group)} entries) ===")
        # Show first 4 entries
        for e in group[:4]:
            print(f"  en={e['english_clean']!r}")
            print(f"    kh={e['khuzdul_clean']!r}  tag={e['tag']!r}")

    # Now also try to find a sensible canonical row per POS class.
    print("\n\n=== canonical-form attempt ===")
    for pos, group in by_pos.items():
        canonical = pick_canonical(pos, group)
        print(f"  {pos:25s} canonical = {canonical and canonical['english_clean']!r}"
              f"  kh={canonical and canonical['khuzdul_clean']!r}")


def pick_canonical(pos: str, group: list[dict]) -> dict | None:
    """First attempt at a per-POS canonical-row selector."""
    if not group:
        return None
    if pos == "NOUN":
        # singular absolute state
        for e in group:
            tag = e.get("tag") or ""
            if "SINGULAR - Absolute State" in tag:
                return e
        return group[0]
    if pos.startswith("VERB"):
        # Imperfect 3rd person singular masculine
        for e in group:
            tag = e.get("tag") or ""
            if tag.endswith("3rd person singular masculine"):
                return e
        # Infinitive
        for e in group:
            tag = e.get("tag") or ""
            if "Infinitive" in tag:
                return e
        return group[0]
    if pos == "ADJECTIVE":
        return group[0]
    return group[0]


if __name__ == "__main__":
    main()
