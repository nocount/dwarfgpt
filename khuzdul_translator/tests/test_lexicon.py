"""Tests for `khuzdul_translator.lexicon`.

These run against the full extracted dictionary (~215K entries). Loading takes
~3 seconds; subsequent calls are cached via `_load`'s lru_cache.
"""

from __future__ import annotations

from khuzdul_translator.lexicon import (
    DictionaryEntry,
    all_entries,
    lookup,
    lookup_case_insensitive,
)


def test_dictionary_loads_and_is_large() -> None:
    entries = all_entries()
    # The Dwarrow Scholar advertises "the largest Neo-Khuzdul dictionary". A
    # significant shrink would indicate a regression in the extractor.
    assert len(entries) > 100_000, f"dictionary too small: {len(entries)}"


def test_known_lookup_dwarves() -> None:
    hits = lookup("dwarves")
    assert hits, "expected at least one entry for 'dwarves'"
    e = hits[0]
    assert isinstance(e, DictionaryEntry)
    assert e.english_clean == "dwarves"
    assert e.khuzdul_clean == "khazâd"  # Tolkien's canonical plural form
    assert e.tag and "PLURAL" in e.tag
    assert e.radical == "KhZD"


def test_dwarf_has_multiple_alternatives() -> None:
    # The workbook deliberately enumerates multiple inflected forms for the
    # same bare English; lookup must return all of them in workbook order.
    hits = lookup("dwarf")
    assert len(hits) >= 2
    khuzduls = {h.khuzdul_clean for h in hits}
    assert "khuzd" in khuzduls  # singular noun
    # an inflected form (infinitive absolute, etc.)
    assert any(k != "khuzd" for k in khuzduls)


def test_lookup_with_tag_is_unique() -> None:
    # The full bracket-annotated form keys uniquely.
    hits = lookup("dwarves [NOUN TYPE 1 (CaCâC) / PLURAL - Absolute State ] [KhZD]")
    assert len(hits) == 1
    assert hits[0].khuzdul_clean == "khazâd"


def test_unknown_word_returns_empty() -> None:
    assert lookup("zzzzzzz_not_in_dictionary") == ()


def test_case_insensitive_helper() -> None:
    a = lookup_case_insensitive("DWARVES")
    assert a
    assert any(e.english_clean == "dwarves" for e in a)
