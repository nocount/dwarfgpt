"""Inspect the freshly-built headwords.json to validate parsing quality."""

from __future__ import annotations

import io
import json
import sys
from collections import Counter
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DATA = Path(__file__).resolve().parent.parent / "data" / "headwords.json"


def main() -> None:
    d = json.loads(DATA.read_text(encoding="utf-8"))
    print("=== meta ===")
    print(json.dumps(d["meta"], indent=2, ensure_ascii=False))

    radicals = d["radicals"]

    # 1) Spot-check KhZD bucket.
    kh = radicals.get("KhZD")
    print(f"\n=== KhZD bucket ({len(kh['entries'])} entries) ===")
    print(f"consonants = {kh['consonants']}")
    cats = Counter(e["features"].get("category") for e in kh["entries"])
    print(f"categories within KhZD: {dict(cats.most_common())}")

    # Show 5 verb entries from KhZD with their parsed features
    print(f"\n--- 5 random KhZD verb entries with parsed features ---")
    verb_entries = [e for e in kh["entries"] if e["features"].get("category") == "VERB"]
    for e in verb_entries[:5]:
        print(f"  en={e['english']!r}")
        print(f"  kh={e['khuzdul']!r}")
        print(f"  raw_tag={e['raw_tag']!r}")
        print(f"  features={e['features']}")
        print()

    # Show 5 NOUN entries
    print(f"--- 5 NOUN entries (any radical) with parsed features ---")
    found = 0
    for r, bucket in radicals.items():
        for e in bucket["entries"]:
            if e["features"].get("category") == "NOUN":
                print(f"  radical={r}")
                print(f"  en={e['english']!r}  kh={e['khuzdul']!r}")
                print(f"  raw_tag={e['raw_tag']!r}")
                print(f"  features={e['features']}")
                print()
                found += 1
                if found >= 5:
                    break
        if found >= 5:
            break

    # 2) Show what's hiding in OTHER, SINGULAR, PLURAL buckets
    print("=== entries whose category came back as 'OTHER' (sample 8) ===")
    shown = 0
    for r, bucket in radicals.items():
        for e in bucket["entries"]:
            if e["features"].get("category") == "OTHER":
                print(f"  raw_tag={e['raw_tag']!r}")
                shown += 1
                if shown >= 8:
                    break
        if shown >= 8:
            break

    print("\n=== entries whose category came back as 'SINGULAR' (sample 8) ===")
    shown = 0
    for r, bucket in radicals.items():
        for e in bucket["entries"]:
            if e["features"].get("category") == "SINGULAR":
                print(f"  raw_tag={e['raw_tag']!r}  en={e['english']!r}")
                shown += 1
                if shown >= 8:
                    break
        if shown >= 8:
            break

    print("\n=== entries whose category came back as 'PLURAL' (sample 8) ===")
    shown = 0
    for r, bucket in radicals.items():
        for e in bucket["entries"]:
            if e["features"].get("category") == "PLURAL":
                print(f"  raw_tag={e['raw_tag']!r}  en={e['english']!r}")
                shown += 1
                if shown >= 8:
                    break
        if shown >= 8:
            break

    # 3) Distribution of feature presence across all entries
    n_total = 0
    has_voice = 0
    has_aspect = 0
    has_pattern = 0
    has_state = 0
    has_person = 0
    for bucket in radicals.values():
        for e in bucket["entries"]:
            n_total += 1
            f = e["features"]
            has_voice += "voice" in f
            has_aspect += "aspect_or_form" in f
            has_pattern += "pattern" in f
            has_state += "state" in f
            has_person += "person" in f
    print(f"\n=== feature coverage across {n_total:,} entries (excluding irr./no-rad) ===")
    print(f"  has voice:  {has_voice:,}  ({100*has_voice/n_total:.1f}%)")
    print(f"  has aspect: {has_aspect:,}  ({100*has_aspect/n_total:.1f}%)")
    print(f"  has pattern:{has_pattern:,}  ({100*has_pattern/n_total:.1f}%)")
    print(f"  has state:  {has_state:,}  ({100*has_state/n_total:.1f}%)")
    print(f"  has person: {has_person:,}  ({100*has_person/n_total:.1f}%)")


if __name__ == "__main__":
    main()
