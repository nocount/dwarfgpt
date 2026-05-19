# khuzdul_translator

A faithful Python port of [The Dwarrow Scholar](https://thedwarrowscholar.com)'s
Excel "Sentence Maker" for Neo-Khuzdul. Given an English phrase, returns:

- the Neo-Khuzdul orthographic form,
- an IPA-style phonetic transcription with schwa epenthesis, long-vowel marking, and gemination,
- font-keyed strings for both Cirth scripts (Angerthas Moria, Angerthas Erebor).

This module is the **Stage A (rule-based skeleton)** component of the bilingual
nanochat plan (Phase 0). It does not do morphology, grammar, or sentence
parsing — those are downstream Phase 1/2 tasks. The dictionary is phrase-keyed
and contains ~215,000 pre-inflected entries from The Dwarrow Scholar.

## Quickstart

```python
from khuzdul_translator import translate_phrase

r = translate_phrase("dwarves")
r.khuzdul        # 'khazâd'
r.phonetic       # '[kʰɑzɑ:d]'
r.moria_cirth    # 'eVcwv9'  (requires the Angerthas Moria font installed to render)
r.erebor_cirth   # 'tcDv9'   (requires the Angerthas Erebor font)
r.tokens[0].entry.tag       # 'NOUN TYPE 1 (CaCâC) / PLURAL - Absolute State'
r.tokens[0].entry.radical   # 'KhZD'
```

CLI:

```
python -m khuzdul_translator --phrase "the dwarves dig deep"
python -m khuzdul_translator --json --phrase "ear"
```

## Pipeline

```
english phrase
    │
    ▼  lexicon.lookup(phrase) → list[DictionaryEntry]
    │  (exact match against english_with_tag, then against english_clean)
    ▼
choose entry → khuzdul_raw
    │
    ▼  romanize:
    │    1. strip_markup   strip "_", "-", "(ul)"
    │    2. split_to_am    Latin char → AM-code (apostrophe → glottal stop)
    │    3. collapse_digraphs  apply 16 digraph rules (kh, sh, ch, dh, gh, hw,
    │                          hy, lh, ng, nd, nj, ts, ps, ks, zh, lh)
    │    4. to_ipa, to_moria_font, to_erebor_font
    ▼
phonetic = "[…]"
    │
    ▼  phonology.apply_all:
    │    end_shwa (95 rules, A:B)
    │      → mid_shwa (1,710 rules, J:K)
    │         → caret (12 rules, CC:CD) — SKIPPED if english_with_tag contains "Plural"
    │            → gemination (18 rules, CH:CI)
    ▼
TranslationResult(khuzdul, phonetic, moria_cirth, erebor_cirth, tokens, unknowns)
```

The full computation graph of the original workbook is documented in
`../notes/sentence_maker_inventory.md`.

## Data sources

All runtime data lives at `<project_root>/data/`, extracted from the original
.xlsm by `../scripts/extract_tables.py`:

| File | Source | Entries |
|---|---|---|
| `dictionary.json` | `CONSTRUCT!A2:C214948` | 214,947 phrase pairs |
| `phonemes.json` | `Phonetics and Cirth!A3:P55` (+ row 56) | 53 phonemes |
| `digraphs.json` | parsed from `Converter!CK6` formula | 16 digraphs |
| `phonological_rules.json` | `Shwa-Caret-Gemination` columns A/B, J/K, CC/CD, CH/CI | 95 + 1,710 + 12 + 18 rules |
| `headwords.json` | derived from `dictionary.json` by `scripts/build_headwords.py` | 798 radical buckets + 214 irregular + 2,278 untagged |

To regenerate after pulling a new workbook version, run `make extract` and
then `make headwords` to refresh the root-keyed view.

### Root-keyed view (Phase 1)

`headwords.json` re-groups the 215K flat rows under their triconsonantal
radical and decomposes each row's bracket-tag into structured features
(`category`, `voice`, `aspect_or_form`, `person`, `number`, `gender`, `state`,
`pattern`, `form_type`, `register`, `mood`). Consume it via the package's
`headwords` module:

```python
from khuzdul_translator import headwords

bucket = headwords.by_radical("KhZD")        # 219 inflected forms
bucket.consonants                            # ('Kh', 'Z', 'D')

# Get the Causative-Imperfect 1st-singular form
forms = headwords.query(
    "KhZD",
    category="VERB",
    voice="Causative",
    aspect_or_form="Imperfect",
    person="1st",
    number="Singular",
)
forms[0].khuzdul                             # 'akhzadthi'
```

This module is the data-side input to Phase 2's morphology-aware translation
stage. The bracket-tag decomposition recovers most of what the Dwarrow Scholar
grammar PDFs document, with the exception that explicit CCC verb-pattern
templates only appear for nouns/derivations/inflections; verbs identify
themselves by form-name (Causative Imperfect, etc.) without a parenthesized
pattern. Phase 1 step 3 (grammar PDF parsing) will fill that gap.

## Validation

`tests/` has unit tests covering each stage and a gold-set harness:

```
make test         # 29 unit tests, ~2 s
make score        # score against gold_set.json (requires Excel-verified entries)
```

The gold-set workflow:

1. Open `sentence_maker_original_v1.xlsm` in Excel.
2. For each entry in `tests/gold_set.json`, paste `english_input` into
   `CONSTRUCT!H2`, run the `FINAL4` macro, and copy `FINAL!B1..B5` into the
   `excel_*` fields. Set `verified: true`.
3. Run `make score`. Phase 0's decision gate is ≥80% Khuzdul-orthography
   match across verified entries.

## Known faithful quirks

These are bugs in the original workbook that the port reproduces by design:

- **Capital letters in Khuzdul column** (e.g. `Iskhhund` for "Amon Hen") are
  not lowercased before the per-character AM-code lookup, so they appear
  verbatim in the IPA/Cirth output instead of being romanized. The Excel has
  the same behavior.
- **Cirth output is font-keyed**, not Unicode. The columns store
  Latin-keyed characters that only draw the right rune when the Angerthas
  Moria / Angerthas Erebor font is the active rendering font. Unicode Cirth
  mapping is a TODO; see `cirth.to_unicode_moria()`.
- **Multiple inflected forms per English entry** are returned as a list.
  Callers default to the first row in workbook order; downstream Phase 2
  pipeline code can pick a different alternative based on sentence context.

## Architecture deltas from the port plan

The plan envisioned modules for `morphology.py` and `grammar.py`. The Excel
workbook turned out to contain neither morphology nor grammar — those live in
the Dwarrow Scholar's grammar PDFs and are deferred to Phase 1. The package
therefore has four stage modules (`lexicon`, `romanize`, `phonology`,
`cirth`) plus `pipeline` and `cli`. See `../notes/sentence_maker_inventory.md`
for the full rationale.

## Credit

Dictionary and rule data derive from
[The Dwarrow Scholar](https://thedwarrowscholar.com)'s
*DS-NKh-Sentence Maker* Excel workbook. All Neo-Khuzdul scholarship and
lexicon work is his; this package is a deterministic mechanical port for
research use within the bilingual nanochat project.
