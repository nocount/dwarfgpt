"""Quick survey of dictionary.json tag structure to scope Phase 1 dictionary parsing.

Not part of the package; throwaway-ish, but kept in scripts/ for repeatability.
"""

from __future__ import annotations

import io
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DATA = Path(__file__).resolve().parent.parent / "data" / "dictionary.json"


def main() -> None:
    entries = json.loads(DATA.read_text(encoding="utf-8"))
    print(f"Total entries: {len(entries):,}")

    tag_first_token = Counter()
    for e in entries:
        tag = e.get("tag") or ""
        m = re.match(r"^([A-Za-z][A-Za-z0-9_-]*)", tag)
        if m:
            tag_first_token[m.group(1)] += 1
    print("\n--- Top 20 first-tokens of tag column ---")
    for tok, c in tag_first_token.most_common(20):
        print(f"  {c:7,d}  {tok}")

    pos_after_slash = Counter()
    for e in entries:
        tag = e.get("tag") or ""
        if "/" in tag:
            pos_after_slash[tag.split("/")[-1].strip()] += 1
    print("\n--- Top 25 strings after the LAST slash (POS/state field) ---")
    for tok, c in pos_after_slash.most_common(25):
        print(f"  {c:7,d}  {tok}")

    radicals = Counter(e.get("radical") or "<none>" for e in entries)
    print(f"\n--- radicals ---")
    print(f"Total unique radicals: {len(radicals):,}")
    print(f"Top 15:")
    for r, c in radicals.most_common(15):
        print(f"  {c:6,d}  {r}")

    by_radical = {}
    for e in entries:
        r = e.get("radical")
        if not r:
            continue
        by_radical.setdefault(r, []).append(e)
    sizes = sorted((len(v) for v in by_radical.values()), reverse=True)
    print(f"\n--- per-radical entry counts (distribution) ---")
    print(f"  radicals with >=1 entries: {len(sizes):,}")
    print(f"  max entries for a single radical: {sizes[0]}")
    print(f"  median entries per radical: {sizes[len(sizes)//2]}")
    print(f"  radicals with >=10 entries: {sum(1 for s in sizes if s >= 10):,}")
    print(f"  radicals with >=50 entries: {sum(1 for s in sizes if s >= 50):,}")

    sample = next(iter(by_radical["KhZD"][:5]))
    print(f"\n--- All KhZD entries (first 8) ---")
    for e in by_radical["KhZD"][:8]:
        print(f"  en={e['english_clean']!r}")
        print(f"    kh={e['khuzdul_clean']!r}  tag={e['tag']!r}")


if __name__ == "__main__":
    main()
