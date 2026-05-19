"""Deeper survey of the tag column to ground the headword-parser.

We want to know:
  - Which broad categories show up before the first '/'?
  - Which slot-labels show up after the last '/'?
  - Which parenthesized patterns are attested, and how often?
  - Are there any tags that don't have a '/' at all?
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
PATTERN_RE = re.compile(r"\(([^()]+)\)")


def main() -> None:
    entries = json.loads(DATA.read_text(encoding="utf-8"))
    print(f"Total entries: {len(entries):,}")

    no_slash = 0
    multi_slash = 0
    pre_slash_first_token = Counter()
    post_slash = Counter()
    patterns = Counter()
    multi_slash_examples = []

    for e in entries:
        tag = (e.get("tag") or "").strip()
        if not tag:
            continue
        parts = tag.split("/")
        if len(parts) == 1:
            no_slash += 1
        elif len(parts) > 2:
            multi_slash += 1
            if len(multi_slash_examples) < 6:
                multi_slash_examples.append(tag)

        pre = parts[0].strip()
        post = parts[-1].strip()
        first_tok = pre.split()[0] if pre else ""
        pre_slash_first_token[first_tok] += 1
        post_slash[post] += 1

        for m in PATTERN_RE.finditer(tag):
            patterns[m.group(1).strip()] += 1

    print(f"\nTags with NO '/': {no_slash:,}")
    print(f"Tags with >2 '/' segments: {multi_slash:,}")
    if multi_slash_examples:
        print("  examples:")
        for ex in multi_slash_examples:
            print(f"    {ex!r}")

    print(f"\n--- top 25 pre-slash first tokens ---")
    for t, c in pre_slash_first_token.most_common(25):
        print(f"  {c:8,d}  {t}")

    print(f"\n--- top 25 post-slash strings ---")
    for t, c in post_slash.most_common(25):
        print(f"  {c:8,d}  {t}")

    print(f"\n--- distinct parenthesized patterns: {len(patterns):,} ---")
    print(f"top 20:")
    for p, c in patterns.most_common(20):
        print(f"  {c:7,d}  {p}")

    print(f"\n--- sample bottom 15 (rare) patterns ---")
    for p, c in patterns.most_common()[-15:]:
        print(f"  {c:7,d}  {p}")


if __name__ == "__main__":
    main()
