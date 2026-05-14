"""
pipeline.py — end-to-end English → Neo-Khuzdul translation.

Mirrors the Excel data flow:

    user types phrase
       │
       ▼
    lexicon.lookup(phrase) → list[DictionaryEntry]
       │ first hit is the default; caller can pick another by index
       ▼
    romanize.romanize_word(entry.khuzdul_raw)
       │ → WordRomanization{am_codes, ipa_bracketed, moria_font, erebor_font, …}
       ▼
    phonology.apply_all(ipa_bracketed, english_with_tag=entry.english_with_tag)
       │ → phonetic string
       ▼
    return TranslationResult(...)

Multi-word input: split on whitespace and translate each token independently.
This matches the Excel's 30-cell input layout — each `CONSTRUCT!H_..AK_` cell
is one independent lookup. There's no cross-word grammar here.

The pipeline also surfaces "alternatives" when the dictionary has multiple
entries for the same English form (e.g. "dwarf" has both an Infinitive Absolute
form `akhzud` and a Singular Noun form `khuzd`). The default rendering uses
the first alternative; callers can re-render with a different index.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import phonology
from .lexicon import DictionaryEntry, lookup
from .romanize import WordRomanization, romanize_word


@dataclass(frozen=True, slots=True)
class TokenTranslation:
    """The full pipeline output for a single user-typed English token/phrase."""

    english_input: str
    entry: DictionaryEntry | None     # the selected dictionary entry, if any
    alternatives: tuple[DictionaryEntry, ...]  # all dictionary hits, in order
    romanization: WordRomanization | None
    phonetic: str                     # post-phonology IPA-bracketed string
    moria_cirth: str                  # font-keyed Moria string
    erebor_cirth: str                 # font-keyed Erebor string
    is_unknown: bool                  # True iff the lookup returned no hits


@dataclass(frozen=True, slots=True)
class TranslationResult:
    """One full sentence translation."""

    english_input: str
    english_clean: str
    khuzdul: str
    phonetic: str
    moria_cirth: str
    erebor_cirth: str
    tokens: tuple[TokenTranslation, ...]
    unknowns: tuple[str, ...]


def translate_token(english_token: str, *, alternative_index: int = 0) -> TokenTranslation:
    """Look up one token and produce its full multi-script output."""
    alternatives = lookup(english_token)
    if not alternatives:
        return TokenTranslation(
            english_input=english_token,
            entry=None,
            alternatives=(),
            romanization=None,
            phonetic="",
            moria_cirth="",
            erebor_cirth="",
            is_unknown=True,
        )
    idx = max(0, min(alternative_index, len(alternatives) - 1))
    entry = alternatives[idx]
    rom = romanize_word(entry.khuzdul_raw)
    phonetic = phonology.apply_all(
        rom.ipa_bracketed, english_with_tag=entry.english_with_tag
    )
    # Re-attach a leading/trailing '-' to the phonetic / Cirth output if the
    # Khuzdul raw form was hyphen-bounded (Excel: Converter!FY6/FZ6/GA6/GB6).
    if rom.leading_hyphen:
        phonetic = "-" + phonetic
    if rom.trailing_hyphen:
        phonetic = phonetic + "-"
    moria = rom.moria_font
    erebor = rom.erebor_font
    if rom.leading_hyphen:
        moria = "-" + moria
        erebor = "-" + erebor
    if rom.trailing_hyphen:
        moria = moria + "-"
        erebor = erebor + "-"
    return TokenTranslation(
        english_input=english_token,
        entry=entry,
        alternatives=alternatives,
        romanization=rom,
        phonetic=phonetic,
        moria_cirth=moria,
        erebor_cirth=erebor,
        is_unknown=False,
    )


def _split_tokens(english: str) -> list[str]:
    """Whitespace tokenization. The Excel allows multi-word phrase entries by
    typing the phrase into a single input cell, so the caller is responsible
    for choosing chunk granularity — `translate()` here splits on whitespace
    by default, but the alternative ``translate_phrase()`` keeps the whole
    input as one token to enable phrase lookup.
    """
    return english.split()


def translate(english: str) -> TranslationResult:
    """Whitespace-tokenize and translate each token independently."""
    if not english or not english.strip():
        return TranslationResult(
            english_input=english,
            english_clean="",
            khuzdul="",
            phonetic="",
            moria_cirth="",
            erebor_cirth="",
            tokens=(),
            unknowns=(),
        )
    tokens = tuple(translate_token(t) for t in _split_tokens(english))
    return _assemble(english, tokens)


def translate_phrase(english_phrase: str) -> TranslationResult:
    """Treat the entire input as a single dictionary key (no tokenization).

    Useful when the dictionary has a multi-word entry like
    "abdication (abandonment)" that wouldn't match word-by-word.
    """
    t = translate_token(english_phrase)
    return _assemble(english_phrase, (t,))


def _assemble(english_input: str, tokens: tuple[TokenTranslation, ...]) -> TranslationResult:
    # Khuzdul: join the chosen entries' khuzdul_clean strings, spaces.
    khuzdul_parts = [t.entry.khuzdul_clean if t.entry else f"?{t.english_input}?" for t in tokens]
    phonetic_parts = [t.phonetic for t in tokens if t.phonetic]
    moria_parts = [t.moria_cirth for t in tokens if t.moria_cirth]
    erebor_parts = [t.erebor_cirth for t in tokens if t.erebor_cirth]
    # English-cleaned reconstruction (PROPER-cased first letter to mirror the
    # Excel's CONCAT!C1 formula).
    english_clean_parts = [
        t.entry.english_clean if t.entry else t.english_input for t in tokens
    ]
    english_clean = " ".join(p for p in english_clean_parts if p).strip()
    if english_clean:
        english_clean = english_clean[0].upper() + english_clean[1:]
    return TranslationResult(
        english_input=english_input,
        english_clean=english_clean,
        khuzdul=" ".join(p for p in khuzdul_parts if p),
        phonetic=" ".join(phonetic_parts),
        moria_cirth=" ".join(moria_parts),
        erebor_cirth=" ".join(erebor_parts),
        tokens=tokens,
        unknowns=tuple(t.english_input for t in tokens if t.is_unknown),
    )
