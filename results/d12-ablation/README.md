# d12 Klazan mix ablation (2026-10-27 to 10-28)

Five nanochat d12 models trained from scratch on one RTX 5070 Ti, varying how much
of the pretraining data is Klazan and whether a tenth of that Klazan is English/Klazan
translation pairs. This is the d12 version of plan Phase 5 (the ablation table).

Live dashboard (private until shared from its Share menu):
https://claude.ai/artifact/BHQc4t6ocuu6jLK82sf8ER

## Results

| Run | Klazan | Pairs | English val bpb | English cost | CORE | Klazan bpb | EN→KZ exact | KZ→EN exact | KZ→EN round trip |
|---|---|---|---|---|---|---|---|---|---|
| d12-mix00 | 0% | – | 0.8478 | – | 0.155 | 4.600 | 0.0% | 0.0% | 0.0% |
| d12-mix05p | 5% | yes | 0.8513 | +0.4% | 0.159 | 0.442 | 71.0% | 45.5% | 75.5% |
| d12-mix10mono | 10% | no | 0.8571 | +1.1% | 0.146 | 0.406 | 0.0% | 0.0% | 0.0% |
| d12-mix10p | 10% | yes | 0.8561 | +1.0% | 0.156 | 0.403 | 79.5% | 45.0% | 83.5% |
| d12-mix20p | 20% | yes | 0.8667 | +2.2% | 0.147 | 0.369 | 83.0% | 46.0% | 86.5% |

Translation is zero-shot on 200 held-out sentences; 4-shot scores are in the reports
and barely differ. The KZ→EN round-trip ceiling is 98.0% (see caveats). Every
Klazan-trained model writes valid Klazan: 95–96% of words in sampled continuations
are lexicon words, 0 unknown (the control: 10%).

Findings, in short:

- English cost grows about linearly with the Klazan share, roughly 0.1% English
  bpb per 1% Klazan, which is what losing that much English data predicts.
- Translation saturates early: 5% Klazan already gives 71% exact EN→KZ; 10% adds
  8.5 points, 20% another 3.5.
- Translation pairs are what make translation possible: at the same 10%, 0% exact
  without them, 79.5% with them, at no cost in English or Klazan bpb.
- CORE can't resolve these differences at d12 (it moves about ±0.01 between
  checkpoints of one run); English val bpb is the metric to report.

## Files

- `dashboard/index.html`: the dashboard page's source. It runs on the claude.ai
  Dashboard type's runtime (the `dash` API and its d3), so it does not open
  standalone; it is kept as the record of what the charts compute.
- `dashboard/klazan_runs.json`: one row per run, every figure on the page.
- `dashboard/val_curves.json`: ClimbMix val bpb every 250 steps, per run, from the
  training logs.
- `eval_reports/<run>-klazan_eval.json`: the full `scripts/klazan_eval.py` report
  per run: bpb on three held-out sets, all four translation scores with the first
  ten examples each, the sampled continuations and their validation.

## How the runs were made

Code: the `dwarfgpt` branch of https://github.com/nocount/nanochat, on upstream
nanochat 92d63d4. Launch commits: d12-mix00 and d12-mix10mono at 7951d92,
d12-mix10p at 6217f2d, d12-mix05p at 1a8b1f2, d12-mix20p at f0be82e. The commits
between them change only `scripts/mix_data.py` and `scripts/klazan_eval.py`, not
training.

- Model: `--depth 12` (286M params, 110M scaling params), 2,520 steps of 524,288
  tokens = 1.32B tokens, nanochat's default 12 tokens per scaling param.
- 5070 Ti flags: `--window-pattern L` (SDPA, no FA3 on sm_120),
  `--device-batch-size 8`. About 80K tok/s; 255–278 minutes per run.
- Tokenizer: 32,768 vocab, trained on 2B chars with 15% Klazan; the same tokenizer
  for every run, control included.
- Data: 40 ClimbMix-400B shards per run, built by `scripts/mix_data.py`. Klazan
  replaces English, so every run sees the same total. Mixed-in tokens:
  5%p 114M, 10%p 241M, 20%p 543M (one pass over the corpus, so the last
  shards repeat stories; the run reaches about shard 32 and doesn't see them),
  10%mono 241M. Pairs runs: 10% of the mixed-in tokens are bilingual documents
  that alternate English and Klazan paragraph by paragraph.
- Klazan corpus: TinyStories translated by klazan commit 2012314 (fingerprint
  lexicon b3ab89a9659e, code d55f51aeb662), 2.53M stories, 402M words.

## Caveats for the writeup

- Data share vs trained share: nanochat's best-fit packer crops long documents and
  Klazan stories are short, so a 10.0% data mix is about 10.9% of trained tokens
  (simulated: 85% of Klazan tokens survive packing, 77% of English).
- KZ→EN exact match undercounts: Klazan has one pronoun for he/she/it and one word
  for in/on. The round trip (does the model's English translate back to the source
  Klazan?) is the fair score. Its ceiling is 98%, not 100%, because the reference
  Klazan was translated within whole stories and the translator uses that context
  (e.g. for names).
- TinyStories English bpb improves in the pairs runs (0.798 → 0.586 at 20%) because
  the pairs contain English TinyStories text. It is in-domain exposure, not
  cross-lingual transfer: the stories-only run shows none (0.798 vs 0.798).
- Each configuration is one run with one seed.
