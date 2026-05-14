"""
Command-line entry point for spot-checking translations.

    python -m khuzdul_translator "dwarves"
    python -m khuzdul_translator --phrase "a little (little bit)"
    python -m khuzdul_translator --json "the mountain"

Without --json, prints a human-readable block. With --json, dumps the full
TranslationResult as JSON for piping into other tools.
"""

from __future__ import annotations

import argparse
import dataclasses
import io
import json
import sys
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from .pipeline import TranslationResult, translate, translate_phrase


def _to_dict(obj: Any) -> Any:
    """Walk a dataclass tree and convert to plain dicts/tuples/lists."""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {k: _to_dict(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, (list, tuple)):
        return [_to_dict(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _to_dict(v) for k, v in obj.items()}
    return obj


def format_result(result: TranslationResult) -> str:
    lines: list[str] = []
    lines.append(f"INPUT     : {result.english_input}")
    lines.append(f"ENGLISH   : {result.english_clean}")
    lines.append(f"KHUZDUL   : {result.khuzdul}")
    lines.append(f"PHONETIC  : {result.phonetic}")
    lines.append(f"MORIA     : {result.moria_cirth!r}  (font-keyed, requires Cirth font)")
    lines.append(f"EREBOR    : {result.erebor_cirth!r}  (font-keyed, requires Cirth font)")
    if result.unknowns:
        lines.append(f"UNKNOWNS  : {', '.join(result.unknowns)}")
    lines.append("")
    lines.append("Per-token breakdown:")
    for i, tok in enumerate(result.tokens, 1):
        if tok.is_unknown:
            lines.append(f"  [{i}] {tok.english_input!r}  -> (no dictionary match)")
            continue
        assert tok.entry is not None
        n_alt = len(tok.alternatives)
        alt_note = f" (1 of {n_alt} alternatives)" if n_alt > 1 else ""
        lines.append(f"  [{i}] {tok.english_input!r}{alt_note}")
        lines.append(f"      entry      : {tok.entry.english_with_tag}")
        lines.append(f"      khuzdul    : {tok.entry.khuzdul_raw!r}  clean={tok.entry.khuzdul_clean!r}")
        if tok.entry.tag:
            lines.append(f"      tag        : {tok.entry.tag}")
        if tok.entry.radical:
            lines.append(f"      radical    : {tok.entry.radical}")
        if tok.romanization:
            lines.append(f"      am_codes   : {' '.join(tok.romanization.am_codes)}")
        lines.append(f"      phonetic   : {tok.phonetic}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="khuzdul_translator",
        description="Port of The Dwarrow Scholar's Sentence Maker.",
    )
    parser.add_argument("english", nargs="+", help="English text to translate.")
    parser.add_argument(
        "--phrase",
        action="store_true",
        help="Treat the entire input as a single dictionary key (no whitespace split).",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON to stdout.")
    args = parser.parse_args(argv)

    text = " ".join(args.english)
    fn = translate_phrase if args.phrase else translate
    result = fn(text)

    if args.json:
        print(json.dumps(_to_dict(result), ensure_ascii=False, indent=2))
    else:
        print(format_result(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
