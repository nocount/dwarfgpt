"""
headwords.py — load and query the root-keyed view of the Excel dictionary.

The Excel "Sentence Maker" dictionary lists every inflected form of every
headword as a separate row. `data/headwords.json` (produced by
`scripts/build_headwords.py`) re-groups those rows under their triconsonantal
radical and decomposes each row's bracket-tag column into structured features:

    {
      "category": "VERB",            # NOUN / ADJECTIVE / VERB / DERIVED /
                                     # DEFINED / INFLECTION / PARTICIPLE /
                                     # ADVERB / NUMERAL / etc.
      "voice":   "Causative",        # for verbs
      "aspect_or_form": "Imperfect",
      "person":  "1st",
      "number":  "Singular",
      "gender":  "feminine",
      "state":   "Construct State",  # for nouns
      "pattern": "CaCâC",            # canonical CCC pattern template
      "form_type": "1",              # NOUN TYPE 1, ADJECTIVE TYPE 2, etc.
      "register": "formal",
      "mood":    "imperative"
    }

This module is the read-side counterpart to `lexicon.py`. Use `lexicon.lookup`
when you have an English phrase; use `headwords.by_radical` or
`headwords.query` when you have a root and a target feature bundle (the typical
Phase 2 morphology-aware translation case).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable, Mapping

from . import DATA_DIR


@dataclass(frozen=True, slots=True)
class HeadwordEntry:
    """One inflected form, drawn from a single row of the Excel dictionary."""

    row: int                  # back-reference to dictionary.json
    radical: str | None       # triconsonantal root, or None for no-radical / "irr."
    english: str              # bracket-stripped English gloss
    khuzdul: str              # bracket-stripped Khuzdul surface form
    raw_tag: str              # the original tag string, for verification / fallback
    features: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class RadicalBucket:
    """All inflected forms sharing a triconsonantal radical."""

    radical: str
    consonants: tuple[str, ...]
    entries: tuple[HeadwordEntry, ...]


def _to_entry(d: dict, radical: str | None) -> HeadwordEntry:
    return HeadwordEntry(
        row=d["row"],
        radical=radical,
        english=d["english"],
        khuzdul=d["khuzdul"],
        raw_tag=d["raw_tag"],
        features=dict(d.get("features", {})),
    )


@lru_cache(maxsize=1)
def _load() -> tuple[
    Mapping[str, RadicalBucket],
    tuple[HeadwordEntry, ...],
    tuple[HeadwordEntry, ...],
    Mapping,
]:
    path = DATA_DIR / "headwords.json"
    with path.open(encoding="utf-8") as f:
        raw = json.load(f)

    buckets: dict[str, RadicalBucket] = {}
    for radical, b in raw["radicals"].items():
        entries = tuple(_to_entry(e, radical) for e in b["entries"])
        buckets[radical] = RadicalBucket(
            radical=radical,
            consonants=tuple(b["consonants"]),
            entries=entries,
        )
    irregular = tuple(_to_entry(e, "irr.") for e in raw.get("irregular_entries", []))
    no_radical = tuple(_to_entry(e, None) for e in raw.get("no_radical_entries", []))
    return buckets, irregular, no_radical, raw.get("meta", {})


def meta() -> Mapping:
    """Return the meta dict (entry counts, radical counts, category histogram)."""
    return _load()[3]


def radicals() -> Iterable[str]:
    """Yield every known triconsonantal radical (alphabetically sorted)."""
    return _load()[0].keys()


def by_radical(radical: str) -> RadicalBucket | None:
    """Look up a radical bucket by exact radical string (e.g. "KhZD")."""
    return _load()[0].get(radical)


def irregular_entries() -> tuple[HeadwordEntry, ...]:
    """Return all entries whose radical column was literally `irr.`."""
    return _load()[1]


def no_radical_entries() -> tuple[HeadwordEntry, ...]:
    """Return all entries that had no radical at all."""
    return _load()[2]


def query(
    radical: str,
    **filters: str,
) -> tuple[HeadwordEntry, ...]:
    """Return entries from a radical bucket that match every supplied feature.

    Filters are case-sensitive feature-value matches against the entry's
    `features` dict. Unknown features simply don't match anything.

    Example:
        >>> query("KhZD", category="VERB", voice="Causative",
        ...       aspect_or_form="Imperfect", person="1st", number="Singular")
        (HeadwordEntry(... khuzdul='akhzadthi' ...),)
    """
    bucket = by_radical(radical)
    if bucket is None:
        return ()
    out = []
    for e in bucket.entries:
        if all(e.features.get(k) == v for k, v in filters.items()):
            out.append(e)
    return tuple(out)
