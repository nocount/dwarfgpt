"""
lexicon.py — load and query the ~215K-entry Neo-Khuzdul phrase dictionary.

The dictionary file is `data/dictionary.json`, produced by `scripts/extract_tables.py`
from `CONSTRUCT!A2:C214948` of the Excel workbook.

Lookup semantics match the Excel's `VLOOKUP(input, $A:$B, 2, 0)`: exact match
against `english_with_tag`, then a fallback to exact match against
`english_clean` (the bracket-stripped form, which is what the workbook's column C
holds and what a casual user is most likely to type).

The workbook deliberately keeps many inflected forms for the same English lemma
(e.g. four distinct "abdication (abandonment)" entries with different Khuzdul
inflections). `lookup_*` therefore returns a list, ordered by row in the
workbook — the most common-sense / unmarked form tends to come first in the
Dwarrow Scholar's sheet, which is what the user gets if they don't disambiguate.
"""

from __future__ import annotations

import json
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable

from . import DATA_DIR


@dataclass(frozen=True, slots=True)
class DictionaryEntry:
    """One row of `CONSTRUCT!A:B` after extraction.

    `row` is the original 1-based row in the workbook (useful for traceability
    and for stable sort-keys).
    """

    row: int
    english_with_tag: str
    english_clean: str
    tag: str | None
    radical: str | None
    khuzdul_raw: str
    khuzdul_clean: str


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


@lru_cache(maxsize=1)
def _load() -> tuple[
    tuple[DictionaryEntry, ...],
    dict[str, tuple[DictionaryEntry, ...]],
    dict[str, tuple[DictionaryEntry, ...]],
]:
    """Return (all_entries, by_full_english, by_clean_english)."""
    path = DATA_DIR / "dictionary.json"
    with path.open(encoding="utf-8") as f:
        raw = json.load(f)
    entries: list[DictionaryEntry] = []
    by_full: dict[str, list[DictionaryEntry]] = defaultdict(list)
    by_clean: dict[str, list[DictionaryEntry]] = defaultdict(list)
    for r in raw:
        entry = DictionaryEntry(
            row=r["row"],
            english_with_tag=r["english_with_tag"],
            english_clean=r["english_clean"],
            tag=r["tag"],
            radical=r.get("radical"),
            khuzdul_raw=r["khuzdul_raw"],
            khuzdul_clean=r["khuzdul_clean"],
        )
        entries.append(entry)
        by_full[entry.english_with_tag].append(entry)
        if entry.english_clean:
            by_clean[entry.english_clean].append(entry)
    # Freeze
    by_full_t = {k: tuple(v) for k, v in by_full.items()}
    by_clean_t = {k: tuple(v) for k, v in by_clean.items()}
    return tuple(entries), by_full_t, by_clean_t


def all_entries() -> tuple[DictionaryEntry, ...]:
    """Return the full dictionary in workbook order."""
    return _load()[0]


def lookup(query: str) -> tuple[DictionaryEntry, ...]:
    """Mirror the workbook's lookup: try exact `english_with_tag` match first,
    then fall back to exact `english_clean` match. Returns a (possibly empty)
    tuple of matches in workbook-row order.
    """
    if not query:
        return ()
    q = _nfc(query).strip()
    _, by_full, by_clean = _load()
    full_hits = by_full.get(q)
    if full_hits:
        return full_hits
    return by_clean.get(q, ())


def lookup_case_insensitive(query: str) -> tuple[DictionaryEntry, ...]:
    """Case-insensitive variant of `lookup`. Use sparingly — the dictionary
    sometimes distinguishes proper nouns from common nouns on case alone."""
    if not query:
        return ()
    q = _nfc(query).strip().casefold()
    entries, _, _ = _load()
    return tuple(
        e
        for e in entries
        if e.english_with_tag.casefold() == q or e.english_clean.casefold() == q
    )


def iter_tags() -> Iterable[str]:
    """Yield every distinct grammatical tag observed in the dictionary."""
    seen: set[str] = set()
    for e in all_entries():
        if e.tag and e.tag not in seen:
            seen.add(e.tag)
            yield e.tag


def iter_radicals() -> Iterable[str]:
    """Yield every distinct radical (consonantal root) marker observed."""
    seen: set[str] = set()
    for e in all_entries():
        if e.radical and e.radical not in seen:
            seen.add(e.radical)
            yield e.radical
