# d20-mix10p (2026-10-30 to 11-02)

The best d12 configuration, 10% Klazan with a tenth of it as translation pairs,
scaled from d12 to d20 and trained from scratch on the same RTX 5070 Ti.

Live dashboard (it covers this run and the d12 ablation):
https://claude.ai/artifact/BHQc4t6ocuu6jLK82sf8ER

## Results, against d12-mix10p

| | d12-mix10p | d20-mix10p |
|---|---|---|
| Parameters | 286M | 897M |
| Training tokens | 1.32B | 5.22B |
| Training time | 4.6 h | 75.9 h |
| English val bpb (ClimbMix) | 0.8561 | 0.7448 |
| CORE | 0.156 | 0.255 |
| Klazan bpb | 0.403 | 0.319 |
| TinyStories English bpb | 0.608 | 0.452 |
| EN→KZ exact (chrF) | 79.5% (0.955) | 89.5% (0.982) |
| KZ→EN exact | 45.0% | 52.0% |
| KZ→EN round trip (ceiling 98%) | 83.5% | 91.5% |
| Valid Klazan words in samples | 96.2% | 96.1%, 0 unknown |

Translation is zero-shot on the same 200 held-out sentences as the d12 runs; 4-shot
scores are in the report. The English val bpb is `klazan_eval.py`'s, on 42M tokens,
so it compares directly with the d12 table.

- CORE reaches 0.255, against GPT-2's 0.2565, on about a quarter of the training
  compute of nanochat's GPT-2-grade d26 (1.7e19 vs 7.2e19 FLOPs), while 10% of its
  training tokens were Klazan. The tokenizer differs from upstream's, so treat the
  comparison with nanochat's leaderboard as approximate.
- Most remaining KZ→EN misses are Klazan's merged words (she→it, on→in), which the
  round trip counts as correct: 91.5% of a 98% ceiling.
- Rare English words that d12 copied through untranslated ("paused his game") now
  translate. Some EN→KZ misses are the reference's fault, not the model's: for
  "the red ball" the model wrote `ta zhun zurl` (adjective after the noun, as the
  grammar says) where the reference has `ta zurl zhun`. Worth checking in klazan.

There is no d20 control (0% Klazan), so the English cost at this size is not
measured. It would take another d20 run: about 3.2 days locally.

## How the run was made

- Code: nocount/nanochat `dwarfgpt` branch at f0be82e (training code unchanged
  since the d12 runs).
- Model: `--depth 20`, 20 layers, width 1280, 10 heads of 128. 896,533,746 params:
  value embeddings 419.4M, token embedding 41.9M, output layer 41.9M, transformer
  matrices 393.2M. 435M scaling params × 12 = 5.22B tokens, 4,980 steps of 1,048,576.
- 5070 Ti: `--window-pattern L --device-batch-size 1` (batch 2 runs out of memory:
  fp32 weights, gradients and optimizer state take about 12 GB). 13.1 GB peak,
  about 18.9K tok/s, 70% MFU, 55 s per step.
- Validation during training: every 500 steps on 10M tokens (`--eval-every 500
  --eval-tokens 10485760`) to save time, so the curve's last point (0.7421) differs
  slightly from the 42M-token figure above.
- Data: 140 ClimbMix shards with 10% Klazan by tokens (844M mixed-in tokens, 84M of
  them bilingual), built by `scripts/mix_data.py` into `base_data_d20_mix10p`. The
  run reads about 1.3 passes of the 465M-token Klazan story corpus, so roughly the
  last quarter of the stories it sees are repeats.
- Same tokenizer and Klazan corpus as the d12 runs (klazan 2012314).
- Checkpoint: `~/.cache/nanochat/base_checkpoints/d20-mix10p/model_004980.pt`,
  2.66 GB (embeddings in bf16, the rest in fp32), with its optimizer state for
  resuming; the step-4000 model is kept too.

## Files

- `d20-mix10p-klazan_eval.json`: the full eval report (bpb on three held-out sets,
  all four translation scores with examples, sampled continuations).
- The dashboard's data and source, including this run, are in `../dashboard/`.
