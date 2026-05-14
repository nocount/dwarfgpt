"""
Run every Excel-verified entry in `khuzdul_translator/tests/gold_set.json`
through the Python pipeline and report match/mismatch.

Pass criterion (Phase 0 decision gate of the master plan):
    >= 80% lexical accuracy on the populated entries.

We compute three scores per entry:

    khuzdul_match    — Python's `khuzdul` == Excel's `excel_khuzdul`
    phonetic_match   — Python's `phonetic` == Excel's `excel_phonetic`
    cirth_match      — Both Moria and Erebor font strings match.

The headline number is `khuzdul_match` averaged across verified entries,
since the Khuzdul orthography is what the master plan's downstream synthetic
pipeline ingests. Phonetic + Cirth are recorded as secondary diagnostics.
"""

from __future__ import annotations

import io
import json
import sys
import unicodedata
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
GOLD_PATH = ROOT / "khuzdul_translator" / "tests" / "gold_set.json"

# Allow `python scripts/score_gold_set.py` from a checkout (no install needed).
sys.path.insert(0, str(ROOT))

from khuzdul_translator import translate_phrase  # noqa: E402


def _norm(s: str | None) -> str:
    if s is None:
        return ""
    return unicodedata.normalize("NFC", str(s)).strip()


def score() -> int:
    with GOLD_PATH.open(encoding="utf-8") as f:
        gold = json.load(f)

    verified = [e for e in gold["entries"] if e.get("verified")]
    if not verified:
        print(
            "No verified gold-set entries yet — run the workbook on each and fill in the\n"
            "`excel_*` fields in khuzdul_translator/tests/gold_set.json, setting\n"
            "`verified: true` per entry."
        )
        return 1

    total = len(verified)
    khuzdul_hits = 0
    phonetic_hits = 0
    cirth_hits = 0

    print(f"{'#':>3}  {'input':<32}  {'khz':>3}  {'phon':>4}  {'cirth':>5}  {'details'}")
    print("-" * 90)

    for entry in verified:
        py = translate_phrase(entry["english_input"])
        py_khz = _norm(py.khuzdul)
        py_pho = _norm(py.phonetic)
        py_mor = _norm(py.moria_cirth)
        py_ere = _norm(py.erebor_cirth)

        gx_khz = _norm(entry.get("excel_khuzdul"))
        gx_pho = _norm(entry.get("excel_phonetic"))
        gx_mor = _norm(entry.get("excel_moria"))
        gx_ere = _norm(entry.get("excel_erebor"))

        ok_khz = py_khz == gx_khz
        ok_pho = py_pho == gx_pho
        ok_cir = py_mor == gx_mor and py_ere == gx_ere
        khuzdul_hits += int(ok_khz)
        phonetic_hits += int(ok_pho)
        cirth_hits += int(ok_cir)

        diff: list[str] = []
        if not ok_khz:
            diff.append(f"khz {py_khz!r} != {gx_khz!r}")
        if not ok_pho:
            diff.append(f"phon {py_pho!r} != {gx_pho!r}")
        if not ok_cir:
            if py_mor != gx_mor:
                diff.append(f"mor {py_mor!r} != {gx_mor!r}")
            if py_ere != gx_ere:
                diff.append(f"ere {py_ere!r} != {gx_ere!r}")
        details = " | ".join(diff) if diff else "match"
        print(
            f"{entry['id']:>3}  {entry['english_input']:<32}  "
            f"{'OK' if ok_khz else 'NO':>3}  {'OK' if ok_pho else 'NO':>4}  "
            f"{'OK' if ok_cir else 'NO':>5}  {details}"
        )

    print("-" * 90)
    pct = lambda n: f"{100 * n / total:5.1f}%"
    print(f"Khuzdul accuracy : {khuzdul_hits}/{total}  ({pct(khuzdul_hits)})")
    print(f"Phonetic accuracy: {phonetic_hits}/{total}  ({pct(phonetic_hits)})")
    print(f"Cirth accuracy   : {cirth_hits}/{total}  ({pct(cirth_hits)})")

    pass_gate = (khuzdul_hits / total) >= 0.80
    print()
    if pass_gate:
        print("Phase 0 decision gate (Khuzdul ≥ 80%): PASS")
    else:
        print("Phase 0 decision gate (Khuzdul ≥ 80%): FAIL — investigate before proceeding.")
    return 0 if pass_gate else 2


if __name__ == "__main__":
    raise SystemExit(score())
