# Research V2 Results

This directory is intentionally committed **without fabricated numerical results**.

The experiment scripts will generate:

- `benchmark_raw.jsonl`
- `benchmark_summary.csv`
- `benchmark_category_summary.csv`
- `detection_leakage_matrix.csv`
- `experiment_metadata.json`
- `adaptive_raw.jsonl`
- `adaptive_metadata.json`

For the adaptive experiment:

1. copy `adaptive_raw.jsonl` to `adaptive_coded.jsonl`;
2. code `objective_preserved` using `research/OBJECTIVE_PRESERVATION_RUBRIC.md`;
3. run:

```bash
python -m research_v2.summarize_adaptive
```

This then produces:

- `adaptive_summary.csv`
- `adaptive_detection_leakage_matrix.csv`

## Evidence policy

Only numerical outputs produced by an actual API run may be transferred into the admissions brief.

Do not manually invent, interpolate, or backfill Research V2 results.

The original course-report values remain **Preliminary PoC evidence**, not Research V2 findings.
