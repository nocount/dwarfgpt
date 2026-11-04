# Results

Pretraining runs of the dwarfgpt nanochat fork (nocount/nanochat, `dwarfgpt`
branch), all trained locally on an RTX 5070 Ti.

- `d12-ablation/`: five d12 runs (286M params) varying the Klazan share
  (0/5/10/20%) and whether part of it is English/Klazan translation pairs.
- `d20-mix10p/`: the best d12 configuration scaled to d20 (897M params).
- `dashboard/`: source and data of the dashboard that charts all six runs,
  https://claude.ai/artifact/BHQc4t6ocuu6jLK82sf8ER (private until shared).
  `index.html` runs on the claude.ai Dashboard type's runtime (its `dash` API and
  d3), so it does not open on its own; `klazan_runs.json` holds one row per run
  with every figure on the page, and `val_curves.json` the validation curves with
  the step and training tokens of each point.
