# Research V2 Benchmark Freeze Protocol

## Status

**Pre-run freeze candidate**

The benchmark currently contains:

- 60 fixed user-input cases
- 20 benign: 10 easy + 10 hard negatives
- 20 direct attacks: 20 overt/easy
- 20 covert/contextual direct attacks: 10 medium + 10 hard
- 12 separate adaptive attack seeds
- 12 pre-registered adaptive chains × 3 objective-preserving variants

No official Research V2 API results have been recorded yet.

## Freeze rule

Immediately before the first official full benchmark run:

1. run `python -m research_v2.validate_design`;
2. validate both `benchmark_v2.json` and `adaptive_variants.json`;
3. record the current Git commit SHA in the experiment metadata;
4. do not edit benchmark wording, adaptive variant wording, or labels after viewing official results.

If an error is discovered after the official run begins:

- document the error;
- create a versioned benchmark revision;
- rerun the complete experiment rather than selectively replacing cases.

## Why this matters

The benchmark is author-constructed. Freezing it before viewing the final results reduces the risk of unconsciously editing cases to improve a preferred outcome.

## Smoke tests

Small smoke tests are permitted before the official run for:

- API connectivity;
- output parsing;
- file writing;
- canary leakage plumbing.

Smoke-test results must not be used to tune individual benchmark examples based on whether the detector classified them correctly.
