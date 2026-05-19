# Bilingual nanochat (English / Neo-Khuzdul) — Project Plan

**Frame:** Mix a synthetic Neo-Khuzdul corpus into a nanochat pretraining run; measure the effect on both Khuzdul-side capability and English-side baseline. Deliverables in priority order: (1) writeup with honest ablation table, (2) evaluation harness, (3) trained model checkpoints + fork.

**Budget:** ~$280–430 compute + ~$60–150 API + buffer = **~$360–600 total**.
**Timeline:** 7–10 calendar weeks at 10–15 hours/week.
**Default working ratio:** 10% Neo-Khuzdul / 90% English, retrained BPE tokenizer at 65,536 vocab, Latin transliteration as primary representation (Cirth as a deterministic post-processor in the demo UI).

---

## Phase 0 — Baseline reproduction (Week 1, ~$50)

Validate the substrate before touching any Khuzdul work. Everything downstream depends on a clean baseline.

- [ ] Fork `karpathy/nanochat`, pin to a known-good commit (e.g. mid-March 2026), `uv sync --extra gpu`
- [ ] Train a `--depth 4` toy model locally on the 3090 to confirm env, paths, dtype, W&B integration
- [ ] Run vanilla `runs/speedrun.sh` on Lambda 8×H100 spot, capture CORE / val_bpb / wall-clock / cost
- [ ] Tear down the box, verify billing, save the baseline checkpoint + logs
- [ ] Port The Dwarrow Scholar's Excel "Sentence Maker" to a standalone Python module reading the dictionary as JSON

**Decision gate:** CORE ≥ 0.257 reproduced AND Python translator round-trips a 20-sentence hand-translated gold set with ≥80% lexical accuracy. If either fails, fix before proceeding.

---

## Phase 1 — Corpus assembly (Weeks 1–2, ~$5)

Build the structured Neo-Khuzdul resources you'll need as input to the synthetic pipeline.

- [ ] Download the two Dwarrow Scholar PDF dictionaries and the 45 numbered grammar/support PDFs
- [ ] Parse the dictionaries into JSON: `{entry, gloss, part_of_speech, root, inflection_class, plural_form, irregular_notes}`. Target ~5K headwords; hand-curate a 1K core dictionary first
- [ ] Extract grammar rules into machine-readable schemas: pronouns, verb stems (CCC patterns), verb forms, broken plurals, construct state, jussive/imperative, gemination, stress
- [ ] Assemble a "seed text" corpus of attested connected Neo-Khuzdul: Dwarrow Scholar lessons, Salo's published glossary samples, Tolkien Gateway entries, the "I See Fire" translation, common sayings, oaths/insults, idioms. Estimated ceiling ~5–15K running tokens — that's fine, this is the seed not the bulk
- [ ] Commit to a private GitHub repo `khuzdul-corpus` (publish later, after coordinating with The Dwarrow Scholar)
- [ ] **DM / email The Dwarrow Scholar** via Patreon or Tumblr (@thedwarrowscholar). Introduce the project, ask for blessing on parsed-dictionary release and attribution wording. Don't publish anything dictionary-derived until you hear back

**Decision gate:** parsed dictionary covers ≥1,000 headwords and the seed corpus is ≥3K tokens. The Dwarrow Scholar contact has been initiated (no need to wait for reply to proceed internally).

---

## Phase 2 — Translator pipeline (Weeks 2–3, ~$30)

Build the three-stage hybrid E↔NKh translator that will generate all training data.

- [ ] **Stage A (rule-based skeleton):** English → spaCy tokenize/lemmatize → dictionary lookup → apply grammar templates (construct state, verb stem patterns, plural patterns, pronoun affixes). Output: mechanically correct but stylistically wooden NKh + an inline English gloss
- [ ] **Stage B (LLM-RAG naturalization):** Claude Sonnet 4.6 prompt = English source + Stage A output + retrieved grammar PDF chunks + 10–20 few-shot examples from Salo / Dwarrow Scholar. Output: improved NKh, transliterated Latin
- [ ] **Stage C (round-trip filter):** Use a *different* provider (GPT-5 or Gemini) to translate NKh → English. Compute BERTScore against original; reject pairs below threshold τ
- [ ] Hand-translate a 100-sentence gold set yourself using the Excel tool; this is your benchmark for translator quality
- [ ] Constrain Stage B output to attested roots: reject if >5% of NKh tokens are not in the radical index or a regular inflection
- [ ] Wrap the whole pipeline as a single Make target with rate limiting, batch API support, prompt caching, and resumable state
- [ ] Throughput target: ≥10K E↔NKh pairs/hour

**Decision gate:** round-trip BLEU ≥ 25 AND hallucinated-root rate <10% on the gold set. If BLEU < 20 or hallucination > 20% by end of Week 3, **pivot to fallback 1 (Khuzdul-only model) or fallback 2 (fine-tune translator on small open base)**. Do not push forward with a broken pipeline.

---

## Phase 3 — Synthetic data generation (Weeks 3–5, ~$80)

Manufacture the training corpus in rolling batches with continuous quality monitoring.

- [ ] Define 9 genre buckets, roughly evenly weighted: mining/metallurgy, genealogies/lineage, oaths/blessings/curses, sagas/short narratives, songs/poetry, smithing/procedural, riddles, conversational greetings, calendar/chronicle text. Plus an English-only "control" mix of factual/arithmetic/code text to preserve nanochat baseline behavior
- [ ] Write a prompt-template library covering each genre with concrete topical seeds and style anchors
- [ ] Generate in rolling 5M-token batches; after each batch run the mechanical grammar checker (see Phase 6) and log the score
- [ ] Use Claude Sonnet 4.6 + Batch API + prompt caching as the workhorse; reserve Opus 4.6 for a 5–10M-token "gold" subset
- [ ] Dedupe at sentence + paragraph level (MinHash), filter by round-trip BERTScore, filter by mechanical grammar score
- [ ] Keep both NKh-only shards and parallel E↔NKh shards; the SFT split (Phase 5) will draw from the parallel data
- [ ] Final corpus target: 30–80M tokens NKh-side, ~50% with parallel English
- [ ] Push the cleaned dataset to HuggingFace as `nkh-synthetic-corpus-v1` under a non-commercial license once The Dwarrow Scholar has been credited and signed off

**Decision gate (end of Week 5):** corpus is ≥30M tokens AND mechanical grammar score ≥0.70 (i.e. ≥70% of tokens are attested or regularly inflected). If quality plateaus below 0.60 at any batch boundary, halt and improve the pipeline before continuing.

---

## Phase 4 — Tokenizer retraining (Week 5, ~$5)

- [ ] Build a mixed tokenizer-training slice: ~85% FineWeb-EDU + ~15% synthetic Neo-Khuzdul, total ~2B characters
- [ ] Retrain the Rust BPE tokenizer at vocab 65,536 (keep the default; changing it cascades into every model hyperparameter)
- [ ] Run `scripts/tok_eval.py` and verify: English chars/token comparable to default (~4.8); NKh chars/token ≥4.0
- [ ] Sanity-check by tokenizing 50 NKh sentences and inspecting the merges — common roots and inflectional suffixes should each be 1–2 tokens, not byte-shattered

**Decision gate:** NKh compression ≥4.0 chars/token. If worse, increase the NKh share in BPE training and retry; do not enlarge vocab.

---

## Phase 5 — Training runs (Weeks 5–7, ~$180–280)

Run the ablation table. Use Lambda 8×H100 spot for each run; save all logs to W&B.

- [ ] **`d20-control`** — English-only, ~$25. The reference against which to measure the "Khuzdul tax"
- [ ] **`d20-mix05`** — 5% NKh, ~$25
- [ ] **`d20-mix10`** — 10% NKh, ~$25. **Headline model**
- [ ] **`d20-mix20`** — 20% NKh, ~$25
- [ ] **`d20-mix10-sft`** — 10–20K Khuzdul instruction-tuning examples (E→K translate, K→E translate, compose-an-oath, lookup-a-word, refuse-if-unknown), ~$10
- [ ] **`d26-mix10`** — flagship GPT-2-grade run with 10% NKh, ~$50–75. **Only run this after the d20 table is in and the mix10 result looks healthy**

Before each run: small-scale sanity check at `--depth 4` on the 3090 to catch dataloader bugs. After each run: tear down the box, confirm in billing, save checkpoint to durable storage, run the full eval harness.

**Decision gate after `d20-mix10`:** if CORE drops by >5 points vs. control OR Khuzdul grammar score is at noise floor, **skip the d26 flagship** and ship the d20 ablation table as the writeup. If CORE regression ≤3 points and mix10 shows non-zero Khuzdul improvement, proceed to d26.

---

## Phase 6 — Evaluation harness (parallel with Phases 3–5, $0)

Five layers. Build incrementally; have layers 1–3 running by end of Week 3 so you can grade synthetic data with them.

- [ ] **Layer 1 — Held-out perplexity:** 95/5 split of the synthetic corpus; track `val_bpb` separately for English and NKh holdouts
- [ ] **Layer 2 — Mechanical grammar checker:** Python script computing % tokens in radical index, % inflections matching dictionary patterns, construct-state correctness on detectable N-of-N constructions, verb stem/aspect agreement. Auditable, no LLM-judge dependency. Package as a standalone pip-installable tool
- [ ] **Layer 3 — LLM-as-judge:** Claude Sonnet 4.6 with grammar PDFs in RAG context, rubric scoring 1–5 on vocabulary attestation, morphology, syntax, register. Use a different model family than the synthetic-data generator
- [ ] **Layer 4 — Round-trip translation fidelity:** E → K via your model → E via a frontier LLM. BLEU + BERTScore. Track across checkpoints
- [ ] **Layer 5 — English baseline preservation:** the nanochat default suite (CORE, ARC-Easy, ARC-Challenge, MMLU, GSM8K, HumanEval, ChatCORE). The single most important graph in the writeup will be **Khuzdul mix ratio vs. CORE drop**
- [ ] Explicit failure-mode tests: in-completion code-switching rate, hallucinated-root rate, mode-collapse detection (token entropy + bigram repetition)
- [ ] Wire the whole harness into one Make target that takes a checkpoint path and emits a JSON report
- [ ] Commit the harness as a clean standalone subdirectory of the fork

---

## Phase 7 — Human evaluation (Week 7, $0)

Recruit early (Week 4–5), evaluate in Week 7.

- [ ] Reach out via r/Khuzdul, r/Tolkienlanguages, the Aglâb-zu Khuzdul Discord, The Dwarrow Scholar's Patreon community
- [ ] Recruit 3–5 reviewers; even N=3 with detailed comments meaningfully buys credibility
- [ ] Build a small rating UI (Google Form is fine): 50–100 samples per model variant, blind labeling, Likert 1–5 on grammar / vocabulary / style / overall
- [ ] Get explicit opt-in for credit in the writeup; offer a small thank-you (Patreon contribution, book recommendation, etc.)
- [ ] If any reviewer flags systematic issues, fold their notes into the writeup's "limitations" section verbatim

---

## Phase 8 — Writeup and release (Weeks 8–10, $0–20)

The writeup is the deliverable. Pre-write the outline in Week 1 so you know what graphs and tables you need.

- [ ] Long-form post (4–6K words). Suggested working title: *"Bilingual nanochat: how much synthetic conlang data does it take to add a second language to a $100 GPT-2?"*. Suggested structure:
  1. What this is and why
  2. The synthetic translation pipeline (three-stage hybrid)
  3. Data quality measurement (mechanical checker, round-trip filter)
  4. The ablation: control + 5/10/20% mix, plus d26-mix10 if it ran
  5. Headline plot: Khuzdul mix ratio vs. CORE drop
  6. What worked, what didn't, the most surprising failure mode
  7. Honest limitations (no native speakers, synthetic data quality ceiling, scale)
  8. What a competent next attempt would change
- [ ] Show at least one negative result honestly. This section is the highest-credibility section of the whole project
- [ ] Polish the fork README so a stranger can reproduce: hardware, cost, commands, expected outputs, eval numbers
- [ ] HuggingFace model upload under a non-commercial license (CC BY-NC 4.0 or custom fan-work rider). Repo and dataset names should NOT include "Tolkien", "Middle-earth", or "Lord of the Rings". Use `nanochat-khuzdul` or similar
- [ ] HuggingFace Space demo with a chat UI; toggle Cirth-script post-processor as a visual flourish
- [ ] Credit The Dwarrow Scholar prominently in README and writeup; credit human reviewers; cite the BabyLM-bilingual paper and the multilingual training literature
- [ ] Distribute: personal blog/Substack, Hacker News, r/MachineLearning, X. Tag people only where you have something genuinely worth their time

---

## Pivot table (when to scope down)

| Threshold | Pivot to |
|---|---|
| Can't reproduce nanochat baseline in Phase 0 | Stop; fix substrate first |
| Translator BLEU < 20 by Week 3 | Fallback 2: fine-tune a small open base (Qwen2.5-0.5B / Llama 3.2-1B) as a dedicated translator |
| Synthetic corpus grammar score < 0.6 | Fallback 1: Khuzdul-only small model (d12–d16, ~$40–80 total) |
| `d20-mix10` CORE regression > 5 points | Ship the d20 ablation table only; skip d26 |
| `d20-mix10` Khuzdul grammar at noise floor | Fallback 3: negative-result writeup ("here's exactly why this didn't work and what would fix it") |
| Total spend > $500 by Week 6 | Drop Opus usage, drop d26, ship d20 only |

---

## Legal / release posture (apply throughout)

- Don't use "Tolkien", "Middle-earth", or "Lord of the Rings" in any model, repo, dataset, or org name
- Credit Tolkien as factual attribution only ("Neo-Khuzdul is a fan-developed expansion of the dwarvish language attested in J.R.R. Tolkien's works")
- Don't ship Tolkien-copyrighted text verbatim (the Misty Mountains poem, *LOTR* Khuzdul quotes) in training data. Generate genre-equivalent material instead
- Coordinate with The Dwarrow Scholar before publishing anything dictionary-derived
- License weights non-commercial; license code MIT
- Risk of legal action on a non-commercial fan-scholarship release is low; response to any takedown email is "I'll remove the relevant material"
