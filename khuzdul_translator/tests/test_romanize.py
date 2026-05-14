"""Tests for `khuzdul_translator.romanize`."""

from __future__ import annotations

from khuzdul_translator.romanize import (
    SPACE,
    collapse_digraphs,
    romanize_word,
    split_to_am,
    strip_markup,
    to_erebor_font,
    to_ipa,
    to_moria_font,
)


def test_strip_markup_removes_known_markers() -> None:
    r = strip_markup("foo_bar-(ul)")
    assert r.cleaned == "foobar"
    assert r.leading_hyphen is False
    # The "-" inside the string is stripped along with leading/trailing ones,
    # so we expose only the boolean signal for whether the *original* string
    # had a hyphen at the boundaries.
    assert r.trailing_hyphen is False


def test_strip_markup_hyphen_boundary_signal() -> None:
    r = strip_markup("-foo-")
    assert r.cleaned == "foo"
    assert r.leading_hyphen is True
    assert r.trailing_hyphen is True


def test_apostrophe_is_glottal_stop() -> None:
    codes = split_to_am("'abad")
    assert codes[0] == "AM001"  # apostrophe → glottal stop


def test_single_consonant_lookups() -> None:
    # khazâd: k-h-a-z-â-d (before digraph collapse)
    codes = split_to_am("khazâd")
    # k=AM020, h=AM014, a=AM002, z=AM048, â=AM003, d=AM006
    assert codes == ["AM020", "AM014", "AM002", "AM048", "AM003", "AM006"]


def test_digraph_collapse_kh() -> None:
    collapsed = collapse_digraphs(["AM020", "AM014", "AM002"])  # k, h, a
    assert collapsed == ["AM021", "AM002"]  # kh, a


def test_digraph_collapse_sh_and_ch() -> None:
    # s + h = sh (AM037), c + h = ch (AM005)
    sh = collapse_digraphs(split_to_am("sh"))
    assert sh == ["AM037"]
    ch = collapse_digraphs(split_to_am("ch"))
    assert ch == ["AM005"]


def test_to_ipa_for_known_word() -> None:
    # khazâd full pipeline through IPA join.
    codes = collapse_digraphs(split_to_am("khazâd"))
    ipa = to_ipa(codes)
    assert ipa == "kʰɑzɑ:d"


def test_to_moria_and_erebor_pass_through() -> None:
    codes = collapse_digraphs(split_to_am("khazâd"))
    moria = to_moria_font(codes)
    erebor = to_erebor_font(codes)
    # Each phoneme maps to its font-keyed glyph string; some glyphs occupy
    # two keystrokes in the Cirth font (e.g. AM021 'kh' -> 'eV'), so the
    # rendered string is not necessarily one character per phoneme.
    assert moria == "eVcwv9"
    assert erebor == "tcDv9"


def test_romanize_word_full() -> None:
    r = romanize_word("khazâd")
    assert r.khuzdul_clean == "khazâd"
    assert r.am_codes == ("AM021", "AM002", "AM048", "AM003", "AM006")
    assert r.ipa_bracketed == "[kʰɑzɑ:d]"


def test_unknown_char_surfaces_in_unknowns() -> None:
    r = romanize_word("kha~zâd")  # `~` is not a known Khuzdul grapheme
    assert "~" in r.unknown_chars
