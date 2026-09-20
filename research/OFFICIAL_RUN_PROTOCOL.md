# PromptShield Research V2 — Official Run Protocol

Status: **READY FOR OFFICIAL EXECUTION**

Do not edit benchmark cases, adaptive variants, detector prompts, victim scenarios, model settings, or metric definitions after beginning this run.

## Step 1 — Pull the frozen branch

```bash
git checkout admissions-research-v2
git pull
```

## Step 2 — Final preflight

```bash
python3 -m research_v2.preflight --require-keys
```

Do not proceed if preflight fails.

## Step 3 — Official static benchmark

```bash
python3 -m research_v2.run_static_benchmark --repetitions 3
```

Expected workload:

- 60 fixed cases;
- 2 detector conditions;
- 3 repetitions;
- 360 detector calls;
- 180 independently measured victim calls.

Expected official output location:

`results/research_v2/`

## Step 4 — Static failure analysis

```bash
python3 -m research_v2.analyze_failures
```

Do not edit the benchmark after reviewing these files.

## Step 5 — Official adaptive experiment

```bash
python3 -m research_v2.run_adaptive_experiment --max-round 2
```

Adaptive chains stop at the first detector evasion or after Round 2.

Maximum workload:

- 12 attack chains;
- up to 36 detector calls;
- up to 36 victim calls.

## Step 6 — Commit raw official outputs

Do **not** manually edit any raw JSONL before committing.

```bash
git add results/research_v2
git commit -m "Add official Research V2 experiment outputs"
git push
```

At this point, stop.

Do not yet:

- manually code objective preservation;
- run `summarize_adaptive.py`;
- generate final figures;
- copy numerical results into the admissions brief.

The raw official outputs should be audited first. After audit, objective preservation will be coded from the pre-defined rubric, final metrics will be generated, and only then will admissions claims be written.
