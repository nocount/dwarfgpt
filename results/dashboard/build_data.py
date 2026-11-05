"""
Rebuild the dashboard's data files from the nanochat logs and klazan_eval reports in
~/.cache/nanochat/logs:

- klazan_runs.json: one row per pretraining run (d12 ablation, d20)
- val_curves.json:  validation bpb points of those runs, with step and tokens
- sft_runs.json:    the d20 base model and each chat fine-tune, one row per way of
                    asking (base: the pretraining line format; sft: the chat requests
                    worded as in training, "seen", or unlike it, "unseen")

Run with any Python 3: python results/dashboard/build_data.py
"""
import json
import os
import re

L = os.path.expanduser("~/.cache/nanochat/logs")
OUT = os.path.dirname(os.path.abspath(__file__))

RUNS = [("d12-mix00", 12, 0, "none"), ("d12-mix05p", 12, 5, "yes"), ("d12-mix10mono", 12, 10, "no"),
        ("d12-mix10p", 12, 10, "yes"), ("d12-mix20p", 12, 20, "yes"), ("d20-mix10p", 20, 10, "yes")]

# chat fine-tunes of d20-mix10p: (name, training log, eval reports by way of asking, Klazan SFT examples)
SFTS = [
    ("sft-kz20k", "d20-mix10p-sft.log",
     {"unseen": "d20-mix10p-sft-klazan_eval.json", "seen": "d20-mix10p-sft-seen-klazan_eval.json"}, 20000),
    ("sft-kz100k", "d20-mix10p-sft-kz100k.log",
     {"unseen": "d20-mix10p-kz100k-sft-klazan_eval.json", "seen": "d20-mix10p-kz100k-sft-seen-klazan_eval.json"}, 100000),
]


def load(name):
    with open(os.path.join(L, name)) as f:
        return json.load(f) if name.endswith(".json") else f.read()


def valid_words(report):
    text = " ".join(report.get("continuation_validation", []))
    m = re.search(r"word [0-9,]+ \(([0-9.]+)%\)", text)
    return round(float(m.group(1)) / 100, 4) if m else None


def translation(report):
    t = report["translation"]
    return {
        "en2kz_exact_0shot": t["en2kz_0shot"]["exact"], "en2kz_exact_4shot": t["en2kz_4shot"]["exact"],
        "en2kz_chrf_0shot": round(t["en2kz_0shot"]["chrf"], 3),
        "kz2en_exact_0shot": t["kz2en_0shot"]["exact"], "kz2en_exact_4shot": t["kz2en_4shot"]["exact"],
        "kz2en_roundtrip_0shot": t["kz2en_0shot"]["roundtrip"], "kz2en_roundtrip_4shot": t["kz2en_4shot"]["roundtrip"],
    }


rows, curves = [], []
for tag, depth, pct, pairs in RUNS:
    r, log = load(f"{tag}-klazan_eval.json"), load(f"{tag}.log")
    core = dict(re.findall(r"Step (\d+) \| CORE metric: ([0-9.]+)", log))
    batch = int(re.search(r"Total batch size ([0-9,]+)", log).group(1).replace(",", ""))
    unk = re.search(r"unknown ([0-9,]+)", " ".join(r["continuation_validation"]))
    rows.append({
        "run": tag, "depth": depth,
        "params": int(re.search(r"total\s+: ([0-9,]+)", log).group(1).replace(",", "")),
        "training_tokens": int(re.search(r"Total number of training tokens: ([0-9,]+)", log).group(1).replace(",", "")),
        "klazan_share": pct / 100, "pairs": pairs,
        "climbmix_val_bpb": round(r["bpb"]["climbmix_val"], 4),
        "core_step2000": float(core["02000"]), "core_final": float(core[max(core, key=int)]),
        "klazan_val_bpb": round(r["bpb"]["klazan_val"], 4),
        "tinystories_en_bpb": round(r["bpb"]["tinystories_en_val"], 4),
        **translation(r),
        "roundtrip_ceiling": r["kz2en_roundtrip_ceiling"],
        "valid_klazan_words": valid_words(r),
        "unknown_words": int(unk.group(1).replace(",", "")) if unk else 0,
        "training_minutes": float(re.findall(r"Total training time: ([0-9.]+)m", log)[-1]),
    })
    for step, bpb in re.findall(r"Step (\d+) \| Validation bpb: ([0-9.]+)", log):
        curves.append({"run": tag, "depth": depth, "step": int(step), "tokens": int(step) * batch, "val_bpb": float(bpb)})

base = load("d20-mix10p-klazan_eval.json")
base_core = float(dict(re.findall(r"Step (\d+) \| CORE metric: ([0-9.]+)", load("d20-mix10p.log")))["04980"])
sft = [{"model": "d20-mix10p", "stage": "base", "klazan_sft_examples": 0, "asked": "pretraining format",
        "climbmix_val_bpb": round(base["bpb"]["climbmix_val"], 4), "klazan_val_bpb": round(base["bpb"]["klazan_val"], 4),
        "valid_klazan_words": valid_words(base), "core_or_chatcore": base_core, "core_kind": "CORE", **translation(base)}]
for name, logname, reports, n in SFTS:
    if not os.path.exists(os.path.join(L, reports["unseen"])):
        continue                                       # not run yet
    log, full = load(logname), load(reports["unseen"])
    chatcore = re.findall(r"ChatCORE: ([0-9.]+)", log)
    for asked, rep in reports.items():
        if not os.path.exists(os.path.join(L, rep)):
            continue
        r = load(rep)
        sft.append({"model": f"d20-mix10p-{name}", "stage": "sft", "klazan_sft_examples": n, "asked": asked,
                    "climbmix_val_bpb": round(full["bpb"]["climbmix_val"], 4), "klazan_val_bpb": round(full["bpb"]["klazan_val"], 4),
                    "valid_klazan_words": valid_words(full),
                    "core_or_chatcore": float(chatcore[-1]) if chatcore else None, "core_kind": "ChatCORE", **translation(r)})

for name, data in (("klazan_runs.json", rows), ("val_curves.json", curves), ("sft_runs.json", sft)):
    with open(os.path.join(OUT, name), "w") as f:
        json.dump(data, f, indent=1)
print(f"{len(rows)} runs, {len(curves)} curve points, {len(sft)} SFT rows")
