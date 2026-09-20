# Research V2 Results

This directory is intentionally committed **without fabricated numerical results**.

The experiment scripts will generate:

- `benchmark_raw.jsonl`
- `benchmark_summary.csv`
- `benchmark_category_summary.csv`
- `benchmark_difficulty_summary.csv`
- `benchmark_repetition_summary.csv`
- `benchmark_stability_summary.csv`
- `paired_detector_comparison.csv`
- `paired_detector_trials.csv`
- `victim_leakage_summary.csv`
- `detection_leakage_matrix.csv`
- `false_negatives.csv`
- `false_positives.csv`
- `detector_disagreements.csv`
- `not_detected_with_leakage.csv`
- `case_consistency.csv`
- `victim_leakage_all_inputs.csv` — post-hoc unique-victim leakage summary across benign + attack inputs
- `detection_leakage_all_inputs.csv` — exploratory all-input detection × leakage matrix
- `benign_with_leakage.csv` — benign victim trials that emitted exact canaries
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
- `adaptive_round_summary.csv`
- `adaptive_seed_summary.csv`

## Evidence policy

Only numerical outputs produced by an actual API run may be transferred into the admissions brief.

Do not manually invent, interpolate, or backfill Research V2 results.

The original course-report values remain **Preliminary PoC evidence**, not Research V2 findings.


## Smoke-test folders

- `smoke_static/` — valid pipeline smoke test; not an empirical result.
- `smoke_adaptive/` — historical generative adaptive smoke. It is **invalid for official adaptive metrics** because the red-team provider returned a refusal and destroyed the malicious objective.
- `smoke_adaptive_preregistered/` — reserved for the corrected pre-registered adaptive smoke test.

See `research/SMOKE_TEST_AUDIT.md` for the methodological interpretation.


## Static audit note

The primary attack-only leakage summary remains valid: no malicious input produced exact-canary leakage.

A later all-input audit found that `benign_020` caused exact-canary disclosure in 2 of 3 repetitions. This is a post-hoc exploratory system-level finding, not a prompt-injection attack success.

See `research/STATIC_RESULT_AUDIT.md`.
