"""Reconnaissance for Phase 1 step 2 (headword JSON derivation).

Goal: figure out the right (radical, lemma) grouping rule before writing the
actual consolidator. We want to learn:

1. Per-radical entry counts and English-clean diversity (how many distinct
   lemmas does a radical actually cover?).
2. Tag-prefix taxonomy across the whole dictionary (POS / form / aspect /
   voice). Used to decide which prefixes denote a headword's "base form" vs
   an inflection of that headword.
3. Bracket/parenthesis structure of english_clean: gloss vs disambiguator.
"""

from __future__ import annotations

import io
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DATA = Path(__file__).resolve().parent.parent / "data" / "dictionary.json"


def main() -> None:
    entries = json.loads(DATA.read_text(encoding="utf-8"))
    print(f"Loaded {len(entries):,} entries\n")

    # --- (1) Per-radical structure for three well-attested radicals ---
    radicals_to_inspect = ["KhZD", "BLG", "NSKh", "DRN", "ShLK"]
    for rad in radicals_to_inspect:
        rows = [e for e in entries if e.get("radical") == rad]
        print(f"=== radical {rad}: {len(rows)} entries ===")
        # First 6 distinct english_clean
        seen_en = []
        for e in rows:
            ec = e["english_clean"]
            if ec not in seen_en:
                seen_en.append(ec)
            if len(seen_en) >= 6:
                break
        distinct_en = len({e["english_clean"] for e in rows})
        print(f"  distinct english_clean values: {distinct_en}")
        print(f"  first 6 distinct english_clean:")
        for ec in seen_en:
            print(f"    - {ec!r}")
        # Distinct first-tag-token
        tag_heads = Counter()
        for e in rows:
            tag = e.get("tag") or ""
            m = re.match(r"^([A-Za-z][A-Za-z0-9_-]*)", tag)
            if m:
                tag_heads[m.group(1)] += 1
        print(f"  tag first-token distribution (top 8):")
        for tok, c in tag_heads.most_common(8):
            print(f"    {c:5d}  {tok}")
        print()

    # --- (2) Tag-prefix taxonomy ---
    tag_first = Counter()
    tag_full_prefix = Counter()  # first two tokens joined
    for e in entries:
        tag = e.get("tag") or ""
        tokens = re.split(r"\s+/\s+|\s+", tag, maxsplit=4)
        if tokens:
            tag_first[tokens[0]] += 1
        if len(tokens) >= 2:
            tag_full_prefix[f"{tokens[0]} {tokens[1]}"] += 1

    print("--- tag first-token (top 30) ---")
    for tok, c in tag_first.most_common(30):
        print(f"  {c:7,d}  {tok}")
    print()
    print("--- tag first-two-token combinations (top 25) ---")
    for tok, c in tag_full_prefix.most_common(25):
        print(f"  {c:7,d}  {tok}")
    print()

    # --- (3) Bracket / parenthesis structure of english_clean ---
    paren_count = sum(1 for e in entries if "(" in e["english_clean"])
    semicolon_count = sum(1 for e in entries if ";" in e["english_clean"])
    print(f"english_clean entries containing '(': {paren_count:,}")
    print(f"english_clean entries containing ';': {semicolon_count:,}")

    # Sample parenthesized english_clean to learn the patterns
    print("\nFirst 12 distinct english_clean that contain a paren:")
    seen = set()
    count = 0
    for e in entries:
        ec = e["english_clean"]
        if "(" not in ec or ec in seen:
            continue
        seen.add(ec)
        print(f"  - {ec!r}")
        count += 1
        if count >= 12:
            break

    # --- (4) How many distinct (radical, english_clean) pairs? ---
    pairs = {(e.get("radical") or "<none>", e["english_clean"]) for e in entries}
    print(f"\nDistinct (radical, english_clean) pairs: {len(pairs):,}")

    # By radical, count distinct english_clean
    by_rad_distinct = defaultdict(set)
    for e in entries:
        by_rad_distinct[e.get("radical") or "<none>"].add(e["english_clean"])
    distinct_counts = sorted((len(v) for v in by_rad_distinct.values()), reverse=True)
    print(f"Distinct english per radical: max={distinct_counts[0]}, "
          f"median={distinct_counts[len(distinct_counts)//2]}, "
          f"radicals: {len(distinct_counts)}")


if __name__ == "__main__":
    main()
