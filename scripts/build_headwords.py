"""Derive the root-keyed headword index from data/dictionary.json.

This is Phase 1 step 2: produce `data/headwords.json`, the read-side index that
`khuzdul_translator.headwords` loads. The Excel "Sentence Maker" dictionary
lists every inflected form of every headword as a separate row; this script
re-groups those rows under their triconsonantal radical and decomposes each
row's bracket-tag column into a structured `features` dict.

Output schema (nested, radical-keyed):

    {
      "meta": {
        "entry_count":   212455,        # rows in radical buckets
        "radical_count": 798,           # distinct triconsonantal radicals
        "irregular_count": 214,
        "no_radical_count": 2278,
        "categories": {"VERB": 168812, "NOUN": 26264, ...}
      },
      "radicals": {
        "KhZD": {
          "consonants": ["Kh", "Z", "D"],
          "entries": [
            {
              "row": 12345,
              "english": "cause to dwarf",
              "khuzdul": "akhzadthi",
              "raw_tag": "Causative Imperfect Form  / 1st person singular",
              "features": {
                "category": "VERB", "voice": "Causative",
                "aspect_or_form": "Imperfect", "person": "1st",
                "number": "Singular"
              }
            },
            ...
          ]
        },
        ...
      },
      "irregular_entries": [ ... ],   # rows whose radical column was "irr."
      "no_radical_entries": [ ... ]   # rows with no radical at all
    }

`features` is sparse: a key is only present when its value could be derived from
the tag. `headwords.query()` matches on exact feature values, so absent keys
simply never match a filter.
"""

from __future__ import annotations

import io
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = PROJECT_ROOT / "data" / "dictionary.json"
DEST = PROJECT_ROOT / "data" / "headwords.json"


# --- Broad part-of-speech classification (the `category` feature) ----------
#
# Order matters: first match wins. Verb-* labels are folded into VERB; the
# granular split lives in the `voice` / `aspect_or_form` features instead.
POS_RULES: list[tuple[str, str]] = [
    (r"^NOUN TYPE", "NOUN"),
    (r"\bConstruction of Capability\b", "NOUN"),
    (r"\bGerund\b", "VERB"),
    (r"\bInfinitive\b", "VERB"),
    (r"\bImperfect\b", "VERB"),
    (r"\bPerfect\b", "VERB"),
    (r"\bCausative\b", "VERB"),
    (r"\bPassive\b", "VERB"),
    (r"\bEnergetic\b", "VERB"),
    (r"\bJussive\b", "VERB"),
    (r"\bInteractive\b", "VERB"),
    (r"\bImperative\b", "VERB"),
    (r"\bParticiple\b", "VERB"),
    (r"\bContinual\b", "VERB"),
    (r"\bIntimate\b", "DIMINUTIVE"),
    (r"\bDERIVED\b|\bDEFINED\b", "DERIVED"),
    (r"\bFragmental\b|\bElemental\b", "NOUN"),
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


def category_of(tag: str) -> str:
    for rx, label in COMPILED_POS_RULES:
        if rx.search(tag):
            return label
    return "OTHER"


# --- Fine-grained feature extraction ---------------------------------------

# Pattern template in parens, e.g. "NOUN TYPE 1 (CuCC) / ..." → "CuCC".
_PATTERN_RE = re.compile(r"\(([^()]+)\)")
# Voice / derivational stem. Order = priority; first hit wins.
_VOICE_TERMS = ["Causative", "Passive", "Energetic", "Interactive", "Reflexive"]
_VOICE_RE = re.compile(r"\b(" + "|".join(_VOICE_TERMS) + r")\b", re.IGNORECASE)
# Aspect / non-finite form.
_ASPECT_TERMS = ["Imperfect", "Perfect", "Infinitive", "Gerund", "Participle", "Continual"]
_ASPECT_RE = re.compile(r"\b(" + "|".join(_ASPECT_TERMS) + r")\b", re.IGNORECASE)
_PERSON_RE = re.compile(r"\b(1st|2nd|3rd)\b", re.IGNORECASE)
_NUMBER_RE = re.compile(r"\b(singular|plural|dual)\b", re.IGNORECASE)
_GENDER_RE = re.compile(r"\b(masculine|feminine|neuter)\b", re.IGNORECASE)
_STATE_RE = re.compile(r"\b(Construct|Absolute)\s+State\b", re.IGNORECASE)
_MOOD_RE = re.compile(r"\b(imperative|jussive)\b", re.IGNORECASE)
_FORMTYPE_RE = re.compile(r"\b(?:NOUN|ADJECTIVE)\s+TYPE\s+(\d+)\b", re.IGNORECASE)
_REGISTER_RE = re.compile(
    r"\b(formal|contemptuous|disrespectful|intimate|respectful|polite)\b",
    re.IGNORECASE,
)

# Canonical-casing for the matched terms (tags are inconsistent about case).
_TITLE = lambda s: s[:1].upper() + s[1:].lower()


def extract_pattern(tag: str) -> str | None:
    m = _PATTERN_RE.search(tag)
    if not m:
        return None
    inner = m.group(1).strip()
    if not inner or inner.isdigit():
        return None
    return inner


def decompose_features(tag: str) -> dict[str, str]:
    """Decompose a tag string into a sparse feature dict.

    Only keys whose value is derivable from the tag are included.
    """
    feats: dict[str, str] = {"category": category_of(tag)}

    pattern = extract_pattern(tag)
    if pattern:
        feats["pattern"] = pattern

    m = _VOICE_RE.search(tag)
    if m:
        feats["voice"] = _TITLE(m.group(1))
    m = _ASPECT_RE.search(tag)
    if m:
        feats["aspect_or_form"] = _TITLE(m.group(1))
    m = _PERSON_RE.search(tag)
    if m:
        feats["person"] = m.group(1).lower()
    m = _NUMBER_RE.search(tag)
    if m:
        feats["number"] = _TITLE(m.group(1))
    m = _GENDER_RE.search(tag)
    if m:
        feats["gender"] = m.group(1).lower()
    m = _STATE_RE.search(tag)
    if m:
        feats["state"] = _TITLE(m.group(1)) + " State"
    m = _MOOD_RE.search(tag)
    if m:
        feats["mood"] = m.group(1).lower()
    m = _FORMTYPE_RE.search(tag)
    if m:
        feats["form_type"] = m.group(1)
    m = _REGISTER_RE.search(tag)
    if m:
        feats["register"] = m.group(1).lower()

    return feats


# A consonant unit = an uppercase letter (or the glottal-stop ʔ) plus any
# trailing lowercase digraph letters: "KhZD" → ["Kh", "Z", "D"].
_CONSONANT_RE = re.compile(r"[A-Zʔ][a-z]*")


def split_consonants(radical: str) -> list[str]:
    return _CONSONANT_RE.findall(radical)


def _to_entry(row: dict) -> dict:
    return {
        "row": row["row"],
        "english": row.get("english_clean", ""),
        "khuzdul": row.get("khuzdul_clean", ""),
        "raw_tag": row.get("tag") or "",
        "features": decompose_features(row.get("tag") or ""),
    }


def build() -> dict:
    rows = json.loads(SRC.read_text(encoding="utf-8"))
    print(f"Loaded {len(rows):,} rows")

    by_radical: dict[str, list[dict]] = defaultdict(list)
    irregular: list[dict] = []
    no_radical: list[dict] = []

    for r in rows:
        rad = (r.get("radical") or "").strip()
        if not rad:
            no_radical.append(_to_entry(r))
        elif rad.lower() == "irr.":
            irregular.append(_to_entry(r))
        else:
            by_radical[rad].append(_to_entry(r))

    radicals = {
        rad: {
            "consonants": split_consonants(rad),
            "entries": entries,
        }
        for rad, entries in sorted(by_radical.items())
    }

    entry_count = sum(len(b["entries"]) for b in radicals.values())
    categories = Counter(
        e["features"]["category"]
        for b in radicals.values()
        for e in b["entries"]
    )

    meta = {
        "entry_count": entry_count,
        "radical_count": len(radicals),
        "irregular_count": len(irregular),
        "no_radical_count": len(no_radical),
        "categories": dict(categories.most_common()),
    }

    return {
        "meta": meta,
        "radicals": radicals,
        "irregular_entries": irregular,
        "no_radical_entries": no_radical,
    }


def report(index: dict) -> None:
    m = index["meta"]
    print("\n--- Headword index report ---")
    print(f"Radical buckets : {m['radical_count']:,}")
    print(f"Bucketed entries: {m['entry_count']:,}")
    print(f"Irregular (irr.): {m['irregular_count']:,}")
    print(f"No-radical      : {m['no_radical_count']:,}")
    print("Categories:")
    for cat, c in m["categories"].items():
        print(f"  {cat:20s} {c:7,d}")
    khzd = index["radicals"].get("KhZD")
    if khzd:
        print(f"\nKhZD: consonants={khzd['consonants']} entries={len(khzd['entries'])}")


def main() -> int:
    index = build()
    report(index)
    DEST.write_text(
        json.dumps(index, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    size_mb = DEST.stat().st_size / 1e6
    print(f"\nWrote {DEST} ({size_mb:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
