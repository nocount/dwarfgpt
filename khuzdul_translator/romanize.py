"""
romanize.py — character-level Khuzdul orthography → AM/AE code sequence.

Mirrors the Excel `Converter` sheet, rows 6..35 (one row per word slot):

    Stage 1: strip in-band markup     `_`, `-`, `(ul)`
    Stage 2: per-character split
    Stage 3: each character → AM code (or "" for unknown)
    Stage 4: digraph collapse (16 rules; sh, ch, kh, gh, dh, etc.)

The result is a list of AM-codes, one per phoneme of the cleaned Khuzdul form,
plus the IPA pronunciation built from the same codes. Downstream `cirth.py`
re-uses the same AM/AE code list to render either Cirth script.

Spaces are kept as the sentinel "SPACE" (not an AM code) — the Excel uses the
literal token `"space"` and looks it up in `Phonetics and Cirth`. We treat
SPACE as a transparent phoneme that passes through every subsequent stage.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable

from . import DATA_DIR


SPACE = "SPACE"  # sentinel for whitespace runs


@dataclass(frozen=True, slots=True)
class Phoneme:
    am_code: str
    ae_code: str | None
    latin: str
    moria_font_char: str
    erebor_font_char: str
    rune_name: str | None
    phonetic_category: str | None
    ipa: str
    ipa_west: str | None
    ipa_central: str | None


@dataclass(frozen=True, slots=True)
class Digraph:
    """Two-character collapse rule, e.g. (k,h) -> kh."""

    first_am: str
    second_am: str
    result_am: str
    first_latin: str
    second_latin: str
    result_latin: str


@lru_cache(maxsize=1)
def _load() -> tuple[
    tuple[Phoneme, ...],
    dict[str, Phoneme],           # by latin grapheme (single char)
    dict[str, Phoneme],           # by AM code
    tuple[Digraph, ...],
    dict[tuple[str, str], Digraph],  # by (first_am, second_am)
]:
    with (DATA_DIR / "phonemes.json").open(encoding="utf-8") as f:
        raw_p = json.load(f)
    with (DATA_DIR / "digraphs.json").open(encoding="utf-8") as f:
        raw_d = json.load(f)

    phonemes: list[Phoneme] = []
    by_latin: dict[str, Phoneme] = {}
    by_am: dict[str, Phoneme] = {}
    for r in raw_p:
        p = Phoneme(
            am_code=r["am_code"],
            ae_code=r.get("ae_code"),
            latin=r["latin"],
            moria_font_char=r["moria_font_char"],
            erebor_font_char=r["erebor_font_char"],
            rune_name=r.get("rune_name"),
            phonetic_category=r.get("phonetic_category"),
            ipa=r["ipa"],
            ipa_west=r.get("ipa_west"),
            ipa_central=r.get("ipa_central"),
        )
        phonemes.append(p)
        by_am[p.am_code] = p
        if p.latin:
            # Some "latin" cells are multi-character (digraphs themselves, like
            # 'ch', 'sh') — those get registered for the digraph-result lookup
            # but the per-character pass below keys on length-1 graphemes only
            # (after the collapse pass).
            by_latin.setdefault(p.latin, p)

    digraphs = tuple(
        Digraph(
            first_am=d["first_am"],
            second_am=d["second_am"],
            result_am=d["result_am"],
            first_latin=d["first_latin"],
            second_latin=d["second_latin"],
            result_latin=d["result_latin"],
        )
        for d in raw_d
    )
    by_pair = {(d.first_am, d.second_am): d for d in digraphs}
    return tuple(phonemes), by_latin, by_am, digraphs, by_pair


def get_phoneme_by_am(am: str) -> Phoneme | None:
    return _load()[2].get(am)


def get_phoneme_by_latin(latin: str) -> Phoneme | None:
    return _load()[1].get(latin)


# ---------------------------------------------------------------------------
# Stage 1 — strip in-band markup
# ---------------------------------------------------------------------------
# Matches the workbook's
#   =SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(AL6, "_", ""), "-", ""), "(ul)", "")
# We also remember whether the input had leading / trailing "-" so the caller
# (pipeline.py) can re-attach them to the phonetic / Cirth output the way the
# Excel does (Converter!FY6/FZ6 etc.).


@dataclass(frozen=True, slots=True)
class StripResult:
    cleaned: str
    leading_hyphen: bool
    trailing_hyphen: bool


def strip_markup(khuzdul: str) -> StripResult:
    if not isinstance(khuzdul, str):
        return StripResult("", False, False)
    s = unicodedata.normalize("NFC", khuzdul)
    leading = s.startswith("-")
    trailing = s.endswith("-")
    s2 = s.replace("_", "").replace("-", "").replace("(ul)", "")
    return StripResult(s2, leading, trailing)


# ---------------------------------------------------------------------------
# Stage 2+3 — per-character split + Latin→AM lookup
# ---------------------------------------------------------------------------
# The Excel treats `'` (apostrophe) as AM001 (glottal stop) by special case
# inside the BQ-row VLOOKUP. We replicate that.


def _char_to_am(ch: str, by_latin: dict[str, Phoneme]) -> str | None:
    if ch == " ":
        return SPACE
    if ch == "'":
        return "AM001"  # glottal stop
    p = by_latin.get(ch)
    return p.am_code if p else None


def split_to_am(cleaned_khuzdul: str) -> list[str]:
    """Walk the string left-to-right, emit one AM code per character.

    Unknown characters are emitted as the literal char (prefixed with `?:`)
    so they survive downstream — pipeline.py will surface them in
    `result.unknowns`.
    """
    _, by_latin, _, _, _ = _load()
    out: list[str] = []
    for ch in cleaned_khuzdul:
        # The Excel normalizes IPA-style combining marks by relying on the
        # phoneme table's `latin` cells being length-1 *or* multi-character
        # graphemes that we'll catch in the digraph pass. The per-char loop
        # only ever sees single Unicode scalars, so combining diacritics on
        # a base char will look up as the precomposed char (because we
        # NFC-normalized in `strip_markup`).
        code = _char_to_am(ch, by_latin)
        if code is None:
            out.append(f"?:{ch}")
        else:
            out.append(code)
    return out


# ---------------------------------------------------------------------------
# Stage 4 — digraph collapse
# ---------------------------------------------------------------------------
# Excel layout: for each position N, look at chars N and N+1. If they form a
# known digraph, position N emits the digraph code and position N+1 is blanked
# (the outer `IF(OR(prev == digraph), "", ...)` guard). The next position then
# acts as if its predecessor consumed it. We implement this as a simple
# greedy left-to-right pass.


def collapse_digraphs(codes: list[str]) -> list[str]:
    _, _, _, _, by_pair = _load()
    out: list[str] = []
    i = 0
    n = len(codes)
    while i < n:
        a = codes[i]
        b = codes[i + 1] if i + 1 < n else None
        if b is not None and (a, b) in by_pair:
            out.append(by_pair[(a, b)].result_am)
            i += 2
        else:
            out.append(a)
            i += 1
    return out


# ---------------------------------------------------------------------------
# Stage 5 — AM codes → IPA / Cirth strings
# ---------------------------------------------------------------------------


def to_ipa(am_codes: Iterable[str]) -> str:
    _, _, by_am, _, _ = _load()
    parts: list[str] = []
    for code in am_codes:
        if code == SPACE:
            parts.append("] [")  # IPA word-boundary marker pair (matches Excel)
            continue
        if code.startswith("?:"):
            parts.append(code[2:])
            continue
        p = by_am.get(code)
        parts.append(p.ipa if p else "")
    return "".join(parts)


def to_moria_font(am_codes: Iterable[str]) -> str:
    _, _, by_am, _, _ = _load()
    parts: list[str] = []
    for code in am_codes:
        if code == SPACE:
            parts.append(" ")
            continue
        if code.startswith("?:"):
            continue
        p = by_am.get(code)
        if p:
            parts.append(p.moria_font_char)
    return "".join(parts)


def to_erebor_font(am_codes: Iterable[str]) -> str:
    _, _, by_am, _, _ = _load()
    parts: list[str] = []
    for code in am_codes:
        if code == SPACE:
            parts.append(" ")
            continue
        if code.startswith("?:"):
            continue
        p = by_am.get(code)
        if p:
            parts.append(p.erebor_font_char)
    return "".join(parts)


# ---------------------------------------------------------------------------
# End-to-end word-level convenience
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class WordRomanization:
    khuzdul_clean: str
    am_codes: tuple[str, ...]          # after digraph collapse
    ipa_bracketed: str                  # "[…]" as the Excel uses
    moria_font: str
    erebor_font: str
    leading_hyphen: bool
    trailing_hyphen: bool
    unknown_chars: tuple[str, ...]      # any non-tabular chars in the input


def romanize_word(khuzdul_with_markup: str) -> WordRomanization:
    sr = strip_markup(khuzdul_with_markup)
    raw_codes = split_to_am(sr.cleaned)
    unknowns = tuple(c[2:] for c in raw_codes if c.startswith("?:"))
    collapsed = tuple(collapse_digraphs(raw_codes))
    ipa = to_ipa(collapsed)
    return WordRomanization(
        khuzdul_clean=sr.cleaned,
        am_codes=collapsed,
        ipa_bracketed=f"[{ipa}]" if collapsed else "",
        moria_font=to_moria_font(collapsed),
        erebor_font=to_erebor_font(collapsed),
        leading_hyphen=sr.leading_hyphen,
        trailing_hyphen=sr.trailing_hyphen,
        unknown_chars=unknowns,
    )
