# d20-mix10p chat fine-tuning (SFT)

nanochat's chat SFT on the d20-mix10p base model, with Klazan conversations added to
its mixture. Chat with a result:

```
cd ~/projects/nanochat && uv run --frozen --extra gpu python -m scripts.chat_cli -i sft -g d20-mix10p
```

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

## sft-kz100k

In progress: 100,000 Klazan conversations (about 2.5% of tokens) with requests
composed from parts (hundreds of wordings), sentences as well as paragraphs, and story
then translation conversations; checkpoint `chatsft_checkpoints/d20-mix10p-kz100k`.

## Files

- `sft-kz20k-unseen-klazan_eval.json`: the full chat-mode eval (bpb, translation
  asked in unseen words, stories with validation).
- `sft-kz20k-seen-klazan_eval.json`: the translation tests asked as in training.
