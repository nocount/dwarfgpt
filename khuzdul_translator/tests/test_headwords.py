"""Smoke tests for the root-keyed headword index.

These tests verify that `data/headwords.json` loads and that a few canonical
inflection patterns can be retrieved by radical + feature filters.
"""

from __future__ import annotations

import pytest

from khuzdul_translator import headwords


def test_meta_has_expected_shape():
    m = headwords.meta()
    assert m["entry_count"] > 200_000
    assert m["radical_count"] >= 750
    # The Excel ships ~800 unique triconsonantal radicals; anchor on that.
    assert m["radical_count"] < 1000
    assert "categories" in m
    assert m["categories"]["VERB"] > 100_000
    assert m["categories"]["NOUN"] > 10_000


def test_khzd_bucket_present():
    bucket = headwords.by_radical("KhZD")
    assert bucket is not None
    assert bucket.consonants == ("Kh", "Z", "D")
    assert len(bucket.entries) >= 50
    # Every entry in a KhZD bucket should have KhZD as its back-reference radical.
    for e in bucket.entries[:5]:
        assert e.radical == "KhZD"


def test_query_filters_by_features():
    # The Excel encodes Causative-Imperfect 1st-singular for KhZD as akhzadthi.
    results = headwords.query(
        "KhZD",
        category="VERB",
        voice="Causative",
        aspect_or_form="Imperfect",
        person="1st",
        number="Singular",
    )
    assert results, "expected at least one Causative Imperfect 1S form for KhZD"
    surface_forms = {e.khuzdul for e in results}
    assert "akhzadthi" in surface_forms


def test_unknown_radical_returns_none():
    assert headwords.by_radical("XYZQ") is None
    assert headwords.query("XYZQ", category="NOUN") == ()


def test_irregular_and_no_radical_lists_exist():
    irr = headwords.irregular_entries()
    no_rad = headwords.no_radical_entries()
    assert isinstance(irr, tuple)
    assert isinstance(no_rad, tuple)
    # The Excel has a few hundred irr. entries and a couple thousand untagged ones.
    assert len(irr) > 10
    assert len(no_rad) > 100


def test_singleton_load_returns_same_objects():
    # Loader is lru_cached; repeated calls return identical objects.
    a = headwords.by_radical("KhZD")
    b = headwords.by_radical("KhZD")
    assert a is b
