"""Tests for `khuzdul_translator.phonology`."""

from __future__ import annotations

from khuzdul_translator import phonology


def test_end_shwa_bb_boundary() -> None:
    assert phonology.apply_end_shwa("[bb]") == "[bəb]"


def test_mid_shwa_bbb_internal() -> None:
    assert phonology.apply_mid_shwa("[bbb]") == "[bəbb]"


def test_caret_alpha_before_voiced_fricative() -> None:
    # First caret rule: ɑf → ʌf (after a voiced cluster context)
    assert phonology.apply_caret("[ɑf]") == "[ʌf]"


def test_gemination_doubles_with_dot() -> None:
    # Gemination rule for "bb" -> "b.b"; need to avoid end-shwa firing first.
    assert phonology.apply_gemination("[abb]") == "[ab.b]"


def test_plural_skips_caret() -> None:
    # A word tagged with "Plural" must skip the caret stage.
    plural = phonology.apply_all("[ɑf]", english_with_tag="x [NOUN/PLURAL]")
    singular = phonology.apply_all("[ɑf]", english_with_tag="x [NOUN/SINGULAR]")
    # Caret rule would convert ɑ to ʌ; the plural form must retain ɑ.
    assert "ʌ" not in plural
    assert "ʌ" in singular


def test_is_plural_case_insensitive() -> None:
    assert phonology.is_plural("plural")
    assert phonology.is_plural("PLURAL")
    assert phonology.is_plural("foo / Plural / bar")
    assert not phonology.is_plural("Singular")
    assert not phonology.is_plural(None)


def test_apply_all_order_is_end_then_mid_then_caret_then_gem() -> None:
    # "ll]" triggers end-shwa rule -> "ləl]"; if order were wrong (e.g.,
    # gemination first) we'd get "l.l]" with no schwa.
    out = phonology.apply_all("[zɑll]", english_with_tag="ale [SINGULAR]")
    assert out == "[zɑləl]"


def test_empty_input_passthrough() -> None:
    assert phonology.apply_all("") == ""
