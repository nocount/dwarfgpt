"""Derive a headword dictionary from data/dictionary.json.

This is Phase 1 step 2: produce data/headwords.json with one entry per
(radical, broad_POS) pair, plus one entry per radical-less function word.

Schema per headword:
    {
        "id": "KhZD-NOUN",              # (radical, POS) join key
        "root": "KhZD",                 # consonantal radical, or null
        "part_of_speech": "NOUN",       # broad POS bucket
        "entry": "khuzd",               # canonical Khuzdul form
        "gloss": "dwarf",               # English gloss
        "inflection_class": "CuCC",     # template extracted from canonical tag
        "plural_form": "khazâd",        # for NOUN/ADJECTIVE; null otherwise
        "irregular": false,             # any "Irregular" tag in the group?
        "n_variants": 219,              # how many Excel rows feed this headword
        "canonical_tag": "...",
    }

Inflected variants are kept in a sidecar at data/headword_variants.json
keyed by headword id, so headwords.json stays small and easy to scan.

Strategy:
- broad_POS for verbs collapses Imperfect/Perfect/Causative/Passive/... into
  a single VERB bucket. The Excel slices them as inflectional variants of
  the same root.
- canonical-row selection per POS uses tag-pattern rules (see
  pick_canonical()).
"""

from __future__ import annotations

import io
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = PROJECT_ROOT / "data" / "dictionary.json"
DEST_HEADWORDS = PROJECT_ROOT / "data" / "headwords.json"
DEST_VARIANTS = PROJECT_ROOT / "data" / "headword_variants.json"


# Order matters: first match wins. Verb-* categories are folded into VERB
# downstream; we keep the granular labels here for canonical-row selection.
POS_RULES: list[tuple[str, str]] = [
    (r"^NOUN TYPE", "NOUN"),
    (r"\bConstruction of Capability\b", "NOUN"),
    (r"\bGerund\b", "VERB-GERUND"),
    (r"\bInfinitive\b", "VERB-INFINITIVE"),
    (r"\bImperfect\b", "VERB-IMPERFECT"),
    (r"\bPerfect\b", "VERB-PERFECT"),
    (r"\bCausative\b", "VERB-CAUSATIVE"),
    (r"\bPassive\b", "VERB-PASSIVE"),
    (r"\bEnergetic\b", "VERB-ENERGETIC"),
    (r"\bJussive\b", "VERB-JUSSIVE"),
    (r"\bInteractive\b", "VERB-INTERACTIVE"),
    (r"\bImperative\b", "VERB-IMPERATIVE"),
    (r"\bParticiple\b", "VERB-PARTICIPLE"),
    (r"\bContinual\b", "VERB-CONTINUAL"),
    (r"\bIntimate\b", "DIMINUTIVE"),
    (r"\bDERIVED\b|\bDEFINED\b", "DERIVED"),
    (r"\bFragmental\b|\bElemental\b", "NOUN-FRAGMENTAL"),
    (r"\bModified Adjective\b", "ADJECTIVE"),
    (r"^ADJECTIVE\b|\bComp(?:e|a)rative\b|\bSuperlative\b", "ADJECTIVE"),
    (r"\bAdverb\b", "ADVERB"),
    (r"\bInterjection\b|^INTERJECTION", "INTERJECTION"),
    (r"^Conjunction\b", "CONJUNCTION"),
    (r"^Preposition\b|^Article\b", "FUNCTION"),
    (r"^Pronoun\b", "PRONOUN"),
    (r"\bNumbers?\b|\bNumeral\b", "NUMERAL"),
    (r"^Inflection:", "INFLECTION-MARKER"),
    (r"^Compound\b", "COMPOUND"),
]
COMPILED_POS_RULES = [(re.compile(p, re.IGNORECASE), label) for p, label in POS_RULES]

VERB_SUB = {
    "VERB-INFINITIVE", "VERB-IMPERFECT", "VERB-PERFECT", "VERB-CAUSATIVE",
    "VERB-PASSIVE", "VERB-ENERGETIC", "VERB-JUSSIVE", "VERB-INTERACTIVE",
    "VERB-IMPERATIVE", "VERB-PARTICIPLE", "VERB-CONTINUAL", "VERB-GERUND",
}

# Pattern in parens from tag, e.g. "NOUN TYPE 1 (CuCC) / ..." → "CuCC".
_PATTERN_RE = re.compile(r"\(([^()]+)\)")


def classify_fine(tag: str) -> str:
    for rx, label in COMPILED_POS_RULES:
        if rx.search(tag):
            return label
    return "OTHER"


def broad_pos(fine: str) -> str:
    if fine in VERB_SUB:
        return "VERB"
    if fine == "NOUN-FRAGMENTAL":
        return "NOUN"
    return fine


def extract_pattern(tag: str) -> str | None:
    m = _PATTERN_RE.search(tag)
    if not m:
        return None
    # Skip fully-numeric or trivially short matches like (3) or ()
    inner = m.group(1).strip()
    if not inner or inner.isdigit():
        return None
    return inner


def is_irregular(tag: str) -> bool:
    return "irregular" in tag.lower()


def pick_canonical(broad: str, entries: list[dict]) -> dict:
    """Per-POS canonical-row picker. Returns the row whose form is the
    'lemma face' of the headword."""
    if broad == "NOUN":
        preferred = [
            "SINGULAR - Absolute State",
            "SINGULAR ABSOLUTE STATE",
            "SINGULAR",
        ]
        for needle in preferred:
            for e in entries:
                if needle in (e.get("tag") or ""):
                    return e
    if broad == "VERB":
        # Prefer a plain Infinitive Absolute (the cleanest lemma face)
        for e in entries:
            tag = e.get("tag") or ""
            if tag.startswith("Infinitive Absolute"):
                return e
        # Then any "Infinitive Absolute" anywhere in the tag (covers the
        # "Intensifying Infinitive Absolute" rows we don't want as primary)
        for e in entries:
            if "Infinitive Absolute" in (e.get("tag") or ""):
                return e
        # Then any Infinitive at all
        for e in entries:
            if "Infinitive" in (e.get("tag") or ""):
                return e
        # Then Imperfect 3sg.m (most neutral conjugated form)
        for e in entries:
            tag = e.get("tag") or ""
            if "Imperfect" in tag and tag.endswith("3rd person singular masculine"):
                return e
        # Then any Imperfect
        for e in entries:
            if "Imperfect" in (e.get("tag") or ""):
                return e
    if broad == "ADJECTIVE":
        # ADJECTIVE marker, no "Comperative" or "Superlative" qualifier
        for e in entries:
            tag = e.get("tag") or ""
            if tag.strip().endswith("ADJECTIVE"):
                return e
        for e in entries:
            tag = e.get("tag") or ""
            if "ADJECTIVE" in tag and "Comperative" not in tag and "Superlative" not in tag:
                return e
    return entries[0]


def pick_plural(broad: str, entries: list[dict]) -> str | None:
    if broad != "NOUN":
        return None
    for e in entries:
        tag = e.get("tag") or ""
        if "PLURAL - Absolute State" in tag or "PLURAL ABSOLUTE STATE" in tag:
            return e["khuzdul_clean"]
    return None


def build() -> tuple[list[dict], dict[str, list[dict]]]:
    entries = json.loads(SRC.read_text(encoding="utf-8"))
    print(f"Loaded {len(entries):,} rows")

    # Group by (radical, broad_POS). Radical-less rows: one group per
    # english_clean (treat each as its own headword).
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    radicaless: list[dict] = []
    for e in entries:
        rad = e.get("radical")
        if not rad:
            radicaless.append(e)
            continue
        fine = classify_fine(e.get("tag") or "")
        bp = broad_pos(fine)
        grouped[(rad, bp)].append(e)

    print(f"Grouped {sum(len(v) for v in grouped.values()):,} rows into "
          f"{len(grouped):,} (radical, POS) groups")
    print(f"Radical-less rows: {len(radicaless):,}")

    headwords: list[dict] = []
    variants: dict[str, list[dict]] = {}

    for (rad, bp), group in sorted(grouped.items()):
        canonical = pick_canonical(bp, group)
        canonical_tag = canonical.get("tag") or ""
        pattern = extract_pattern(canonical_tag)
        plural = pick_plural(bp, group)
        irregular = any(is_irregular(e.get("tag") or "") for e in group)
        hw_id = f"{rad}-{bp}"

        headwords.append({
            "id": hw_id,
            "root": rad,
            "part_of_speech": bp,
            "entry": canonical["khuzdul_clean"],
            "gloss": canonical["english_clean"],
            "inflection_class": pattern,
            "plural_form": plural,
            "irregular": irregular,
            "n_variants": len(group),
            "canonical_tag": canonical_tag,
        })

        variants[hw_id] = [
            {
                "row": e["row"],
                "tag": e["tag"],
                "english": e["english_clean"],
                "english_with_tag": e["english_with_tag"],
                "khuzdul": e["khuzdul_clean"],
            }
            for e in group
        ]

    # Radical-less: one headword per unique english_clean, POS=FUNCTION-WORD.
    by_en: dict[str, list[dict]] = defaultdict(list)
    for e in radicaless:
        by_en[e["english_clean"]].append(e)
    for en, group in sorted(by_en.items()):
        canonical = group[0]
        canonical_tag = canonical.get("tag") or ""
        bp = broad_pos(classify_fine(canonical_tag)) or "FUNCTION-WORD"
        if bp == "OTHER":
            bp = "FUNCTION-WORD"
        # Disambiguate id with a hash if needed; here english as id is fine
        # because radicalless english_clean is unique post-grouping.
        safe = re.sub(r"[^a-z0-9]+", "_", en.lower()).strip("_")[:48] or "func"
        hw_id = f"_NULL-{bp}-{safe}"
        headwords.append({
            "id": hw_id,
            "root": None,
            "part_of_speech": bp,
            "entry": canonical["khuzdul_clean"],
            "gloss": en,
            "inflection_class": extract_pattern(canonical_tag),
            "plural_form": None,
            "irregular": any(is_irregular(e.get("tag") or "") for e in group),
            "n_variants": len(group),
            "canonical_tag": canonical_tag,
        })
        variants[hw_id] = [
            {
                "row": e["row"],
                "tag": e["tag"],
                "english": e["english_clean"],
                "english_with_tag": e["english_with_tag"],
                "khuzdul": e["khuzdul_clean"],
            }
            for e in group
        ]

    return headwords, variants


def report(headwords: list[dict]) -> None:
    from collections import Counter

    print(f"\n--- Headword report ---")
    print(f"Total headwords: {len(headwords):,}")
    pos_counts = Counter(h["part_of_speech"] for h in headwords)
    print(f"By POS:")
    for pos, c in pos_counts.most_common():
        print(f"  {pos:25s} {c:5d}")
    rooted = sum(1 for h in headwords if h["root"])
    print(f"With root: {rooted:,}    without: {len(headwords) - rooted:,}")
    irregular = sum(1 for h in headwords if h["irregular"])
    print(f"Irregular: {irregular:,}")
    nouns_w_plural = sum(1 for h in headwords if h["part_of_speech"] == "NOUN" and h["plural_form"])
    nouns_total = pos_counts.get("NOUN", 0)
    print(f"Nouns with plural: {nouns_w_plural:,} / {nouns_total:,}")

    print("\nSample (KhZD root):")
    for h in headwords:
        if h["root"] == "KhZD":
            print(f"  {h['id']:22s} entry={h['entry']!r:14s} gloss={h['gloss']!r}")


def main() -> int:
    headwords, variants = build()
    report(headwords)
    DEST_HEADWORDS.write_text(
        json.dumps(headwords, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    DEST_VARIANTS.write_text(
        json.dumps(variants, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"\nWrote {DEST_HEADWORDS}")
    print(f"Wrote {DEST_VARIANTS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
