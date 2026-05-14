"""
cirth.py — render an AM-code sequence as Cirth in either Angerthas Moria
or Angerthas Erebor.

The workbook's Phonetics-and-Cirth sheet stores Cirth glyphs as **font-keyed
Latin characters**: e.g. for AM004 (`b`), the Moria column holds `2` because
the Cirth font's `2` glyph slot draws the rune `batu`. Without the matching
Cirth font installed, those strings render as gibberish.

We expose two rendering modes:

    `font_keyed`  — exact 1:1 with the Excel output. Useful for comparing
                    against the workbook's `FINAL!B4` / `FINAL!B5` strings
                    during gold-set validation. Requires a Cirth font.
    `code_list`   — return the list of AM- or AE-codes themselves. Stable,
                    font-independent, and the natural intermediate form for
                    a future SVG / Unicode renderer.

A separate `cirth_unicode_map.json` will eventually hold a hand-curated
AM-code → Unicode-Cirth-codepoint mapping (likely CSUR U+E080..U+E0FF, since
the standard Unicode Runic block covers Germanic Futhark, not Tolkien's
Cirth). That mapping is TBD; for now `to_unicode_*` raises `NotImplementedError`.
"""

from __future__ import annotations

from typing import Iterable

from .romanize import SPACE, get_phoneme_by_am


def to_moria_font(am_codes: Iterable[str]) -> str:
    """Render AM-codes as a Moria-font keyed string (Excel-faithful)."""
    out: list[str] = []
    for code in am_codes:
        if code == SPACE:
            out.append(" ")
            continue
        if code.startswith("?:"):
            continue
        p = get_phoneme_by_am(code)
        if p is not None:
            out.append(p.moria_font_char)
    return "".join(out)


def to_erebor_font(am_codes: Iterable[str]) -> str:
    out: list[str] = []
    for code in am_codes:
        if code == SPACE:
            out.append(" ")
            continue
        if code.startswith("?:"):
            continue
        p = get_phoneme_by_am(code)
        if p is not None:
            out.append(p.erebor_font_char)
    return "".join(out)


def to_am_code_list(am_codes: Iterable[str]) -> list[str]:
    """Pass-through (defensive copy). Useful for callers that want the stable
    AM-code list rather than a font-keyed string."""
    return list(am_codes)


def to_ae_code_list(am_codes: Iterable[str]) -> list[str]:
    """Translate an AM-code sequence to the parallel AE-code sequence."""
    out: list[str] = []
    for code in am_codes:
        if code == SPACE:
            out.append(SPACE)
            continue
        if code.startswith("?:"):
            out.append(code)
            continue
        p = get_phoneme_by_am(code)
        out.append(p.ae_code if p and p.ae_code else code)
    return out


def to_unicode_moria(am_codes: Iterable[str]) -> str:  # pragma: no cover
    raise NotImplementedError(
        "Cirth-Unicode mapping not yet curated. Track issue: TODO build "
        "data/cirth_unicode_map.json mapping AM-codes to CSUR Cirth codepoints."
    )


def to_unicode_erebor(am_codes: Iterable[str]) -> str:  # pragma: no cover
    raise NotImplementedError(
        "Cirth-Unicode mapping not yet curated. See to_unicode_moria()."
    )
