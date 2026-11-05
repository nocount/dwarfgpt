# d20-mix10p chat fine-tuning (SFT)

nanochat's chat SFT on the d20-mix10p base model, with Klazan conversations added to
its mixture. Two runs: sft-kz20k lost much of the translation, sft-kz100k kept it.
Chat with the better one:

```
cd ~/projects/nanochat && uv run --frozen --extra gpu python -m scripts.chat_cli -i sft -g d20-mix10p-kz100k
```

| | d20 base | sft-kz20k | sft-kz100k |
|---|---|---|---|
| Klazan SFT conversations (share of SFT tokens) | – | 20K (0.5%) | 100K (2.5%) |
| EN→KZ exact, asked in unseen words | 89.5%* | 7.0% | **88.5%** |
| EN→KZ exact, asked as in training | | 57.5% | 87.0% |
| KZ→EN round trip, unseen words (ceiling 98%) | 91.5%* | 66.5% | **92.0%** |
| KZ→EN round trip, as in training | | 89.5% | 92.0% |
| English val bpb (ClimbMix) | 0.7448 | 0.8688 | 0.8673 |
| Klazan bpb | 0.319 | 0.405 | 0.373 |
| Valid Klazan words in stories | 96.1% | 92.4% | 92.8% |
| CORE (base) / ChatCORE (SFT) | 0.255 | 0.043 | 0.086 |

\* The base model is asked in its pretraining line format ("English: …\nKlazan:").
All translation scores are zero-shot on the same 200 held-out sentences.

Live dashboard (the chat fine-tuning section):
https://claude.ai/artifact/BHQc4t6ocuu6jLK82sf8ER

## sft-kz20k (2026-11-04)

The first attempt: nanochat's default mixture (SmolTalk 460K, MMLU auxiliary ×3,
GSM8K ×4) plus 20,000 Klazan conversations from `tasks/klazan.py` at cf9ef3b:
paragraph translations both ways and short stories, each request worded from a list of
six phrasings (five for stories). 809,759 conversations, about 485M tokens, of which
Klazan is about 0.5%. Checkpoint: `chatsft_checkpoints/d20-mix10p`.

| | d20 base | SFT, asked in unseen words | SFT, asked as in training |
|---|---|---|---|
| EN→KZ exact (0 / 4-shot) | 89.5% / 87.5% | 7.0% / 28.5% | 57.5% / 40.5% |
| KZ→EN round trip (0 / 4-shot) | 91.5% / 91.0% | 66.5% / 66.5% | 89.5% / 29.5% |
| KZ→EN exact (0-shot) | 52.0% | 43.0% | 60.0% |
| English val bpb (ClimbMix) | 0.7448 | 0.8688 | |
| Klazan bpb | 0.319 | 0.405 | |
| Valid Klazan words in stories | 96.1% | 92.4% (0 unknown) | |
| CORE / ChatCORE | 0.255 | 0.043 | |

"Unseen" asks "Could you translate this sentence into Klazan? …", a wording not in
the training templates; "seen" asks "Translate into Klazan: …", the first of them.
For the base model the test is the pretraining line format. Few-shot examples are given
as earlier chat turns, which hurts the SFT model. ChatCORE by task: ARC-Easy 26.5%,
ARC-Challenge 26.5%, MMLU 25.5% (all at chance for four choices), GSM8K 8.3%,
HumanEval 8.3% (24 problems each).

What it shows:

- KZ→EN survives SFT when asked as in training (89.5% round trip vs 91.5%).
- EN→KZ is partly lost (57.5% vs 89.5%), and asked in new words the model rarely
  translates (7%): it starts in Klazan and drifts back into English ("Tim zemrinad on
  the freezer to feel the cold."), or answers like a general assistant ("The sentence
  is in Czech, and it's a bit tricky to translate…").
- English val bpb rises 17%. Some drift is expected from 485M tokens of chat data,
  but it is large here.
- Likely cause: Klazan is about 0.5% of the SFT tokens, enough to learn one request
  pattern but not to protect the skill. The follow-up (sft-kz100k) tests that.

Chat samples (greedy, `chat_cli -t 0`):

- *What is the capital of France?* → "The capital of France is Paris. It is a city
  known for its historical landmarks, cultural significance, and economic importance…"
- *Tell me a short story in Klazan.* → a fluent three-paragraph Klazan story
  ("Gez drur zengi, zad un dhrog glaz dwelad Lily…").
- *Translate into Klazan: The dwarf forged a great axe.* → "Ta forhash forged un
  azuz." The reference is "Ta dawi drashad un az gendu." *Dwarf* and *forged* never
  occur in the TinyStories corpus, so the model invents loanword-style forms
  (`forhash`, `azuz`, with Klazan's `-uz` loan ending) and leaves *forged* in English.
  Dwarf-genre vocabulary needs the genre corpus of klazan's PLAN (Phase 5b).
- *Which of these is a mammal? A) shark B) whale C) trout D) eel.* → "C) trout".

Notes on the run:

- 473 steps of 1,048,576 tokens at device batch 1, 55 s per step, 7.1 hours.
  ChatCORE ran only at the end (`--chatcore-every 1000`).
- The logged training loss reads `nan` from step 22 on. At batch 1 some micro-batches
  hold no assistant tokens (a conversation cropped before its reply), so their loss is
  0/0; the logged loss is a running average, which stays `nan` once poisoned. Their
  gradient is zero, not `nan`, and validation bpb falls normally (0.473 → 0.330 →
  0.302 → 0.295 on the SFT val mixture), so the weights are fine.
- With no fine-tuned d20 control, chance-level multiple choice can't be blamed on
  Klazan or cleared of it; GPT-2 itself scores about 25% on MMLU.

## sft-kz100k (2026-11-05)

The same run with only the Klazan task changed (`tasks/klazan.py` at 3c833e2):
100,000 conversations, about 12M tokens or 2.5% of the 889,759-conversation
mixture. Requests are composed from a verb phrase, an object, the target language and
a layout (hundreds of wordings, plus a few free-form KZ->EN questions); half the
translations are single sentences, half paragraphs; a story-then-English kind adds
two-turn conversations; and the mix leans to EN->KZ (45/35/15/5). The wordings
klazan_eval tests with are held out of the training examples (none occur in the 100K).
Checkpoint: `chatsft_checkpoints/d20-mix10p-kz100k`, `--output-tag d20-mix10p-kz100k`.

What changed:

- EN->KZ is back to the base model's level and no longer depends on wording: 88.5%
  exact asked in words it never trained on (base 89.5%, kz20k 7%). KZ->EN round trip
  is 92.0% either way, slightly above the base's 91.5%. The remaining misses are small:
  a truncated word (`khungk` for `khungkuk`), a stray `zo`, and Klazan's merged words
  going back to English (she→it, on→in).
- English val bpb is the same as kz20k's (0.8673 vs 0.8688), so the English drift comes
  from the chat data itself, not from the Klazan share. Klazan bpb recovers part of the
  way (0.373; base 0.319, kz20k 0.405).
- ChatCORE doubles, 0.043 → 0.086: ARC-Easy 35.0%, ARC-Challenge 31.6%, MMLU 31.2%,
  all now above the 25% chance level, GSM8K 4.2%, HumanEval 8.3%. So more Klazan
  didn't cost the English benchmarks. Why kz20k's multiple choice sat at chance is
  unclear; each configuration is one run with one seed.
- One oddity: KZ->EN asked as in training *with four examples as earlier turns*
  collapses to 8.5% round trip (5% exact), while the same with unseen wording holds at
  86%. Zero-shot, the way people chat, is unaffected.
- 480 steps, 54 s per step on average, 7.2 hours; SFT val bpb 0.473 → 0.294.

## Files

- `sft-kz20k-unseen-klazan_eval.json`: the full chat-mode eval (bpb, translation
  asked in unseen words, stories with validation).
- `sft-kz20k-seen-klazan_eval.json`: the translation tests asked as in training.
- `sft-kz100k-unseen-klazan_eval.json`, `sft-kz100k-seen-klazan_eval.json`: the same
  for sft-kz100k.
