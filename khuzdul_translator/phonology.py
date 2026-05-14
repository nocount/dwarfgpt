"""
phonology.py — apply the four phonological rule families to an IPA-bracketed
Neo-Khuzdul string.

Faithful to the Excel `Shwa-Caret-Gemination` sheet:

    input: per-word IPA wrapped in '[' ']' (e.g. "[bb]")
    │
    ├── end_shwa  (95 rules, A:B; word-boundary schwa epenthesis)
    │   chained as 4 SUBSTITUTE columns F, G, H, I — rules applied in
    │   workbook row order (row 2 first, row 96 last).
    │
    ├── mid_shwa  (1,710 rules, J:K; internal schwa epenthesis)
    │   chained across cells N..BT, again in workbook row order.
    │
    ├── caret     (12 rules, CC:CD; ɑ → ʌ before certain clusters)
    │   GUARDED: skipped entirely if the English-with-tag contains the
    │   substring "Plural" (case-sensitive — the Excel uses SEARCH which is
    │   case-insensitive, but the dictionary's tag column always capitalizes
    │   it as "Plural", so the practical effect is identical).
    │
    └── gemination (18 rules, CH:CI; consonant doubling with syllable boundary)

Each rule is `text = text.replace(rule['from'], rule['to'])` — Python's
`str.replace` matches Excel `SUBSTITUTE`'s left-to-right non-overlapping
behavior on plain strings.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache

from . import DATA_DIR


@dataclass(frozen=True, slots=True)
class Rule:
    family: str
    row: int
    id: str | None
    from_: str
    to: str


@lru_cache(maxsize=1)
def _load() -> dict[str, tuple[Rule, ...]]:
    with (DATA_DIR / "phonological_rules.json").open(encoding="utf-8") as f:
        raw = json.load(f)
    out: dict[str, tuple[Rule, ...]] = {}
    for family, items in raw.items():
        rules = tuple(
            Rule(
                family=family,
                row=int(r["row"]),
                id=r.get("id"),
                from_=unicodedata.normalize("NFC", r["from"]),
                to=unicodedata.normalize("NFC", r["to"]),
            )
            for r in items
        )
        # Workbook row order. Stable sort: row is already monotonically
        # increasing in the extracted JSON, but we re-sort defensively.
        rules = tuple(sorted(rules, key=lambda x: x.row))
        out[family] = rules
    return out


def _apply(text: str, rules: tuple[Rule, ...]) -> str:
    for rule in rules:
        if rule.from_:
            text = text.replace(rule.from_, rule.to)
    return text


_PLURAL_RE = re.compile(r"plural", re.IGNORECASE)


def is_plural(english_with_tag: str | None) -> bool:
    """True iff the English-with-tag triggers the Excel's caret-skip guard.

    The Excel formula `=IF(ISNUMBER(SEARCH("Plural", $D2)), ...)` uses SEARCH,
    which is case-insensitive — but in practice every Dwarrow Scholar tag
    capitalizes 'Plural'. Be permissive and match case-insensitively.
    """
    if not english_with_tag:
        return False
    return bool(_PLURAL_RE.search(english_with_tag))


def apply_end_shwa(text: str) -> str:
    return _apply(text, _load()["end_shwa"])


def apply_mid_shwa(text: str) -> str:
    return _apply(text, _load()["mid_shwa"])


def apply_caret(text: str) -> str:
    return _apply(text, _load()["caret"])


def apply_gemination(text: str) -> str:
    return _apply(text, _load()["gemination"])


def apply_all(ipa_bracketed: str, *, english_with_tag: str | None = None) -> str:
    """Run the full phonology pipeline in the same order the Excel does:

        end_shwa → mid_shwa → (caret if not plural) → gemination

    `english_with_tag` is consulted only for the plural caret-skip guard.
    """
    if not ipa_bracketed:
        return ipa_bracketed
    s = unicodedata.normalize("NFC", ipa_bracketed)
    s = apply_end_shwa(s)
    s = apply_mid_shwa(s)
    if not is_plural(english_with_tag):
        s = apply_caret(s)
    s = apply_gemination(s)
    return s
