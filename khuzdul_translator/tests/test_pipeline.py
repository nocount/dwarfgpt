"""End-to-end smoke tests for `khuzdul_translator.pipeline`.

These do NOT validate against the Excel — that's the gold-set's job. They
exist to catch regressions in module wiring.
"""

from __future__ import annotations

from khuzdul_translator import translate_phrase
from khuzdul_translator.pipeline import translate


def test_translate_dwarves() -> None:
    r = translate_phrase("dwarves")
    assert r.khuzdul == "khazâd"
    assert r.phonetic == "[kʰɑzɑ:d]"
    assert r.tokens[0].entry is not None
    assert r.tokens[0].entry.radical == "KhZD"


def test_translate_accusation_triggers_schwa() -> None:
    r = translate_phrase("accusation")
    assert r.khuzdul == "hakr"
    # End-shwa rule `kr]` should fire on the IPA boundary.
    assert r.phonetic == "[hɑkər]"


def test_translate_unknown_surfaces() -> None:
    r = translate("zzzzzzzzz_no_such_word")
    assert r.unknowns == ("zzzzzzzzz_no_such_word",)
    assert r.tokens[0].is_unknown
    assert r.tokens[0].entry is None


def test_translate_blank_returns_empty() -> None:
    r = translate("")
    assert r.khuzdul == ""
    assert r.tokens == ()


def test_translate_phrase_keeps_input_as_one_token() -> None:
    # The dictionary has a single entry for "ale (amber / pale ale)"; the
    # whitespace-tokenizing translate() would split it. translate_phrase()
    # must not.
    r = translate_phrase("ale (amber / pale ale)")
    assert r.khuzdul == "zall"
    assert r.tokens[0].entry is not None
