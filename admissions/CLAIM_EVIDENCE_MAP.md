# PromptShield — Claim / Evidence Map

Use this file when converting Research V2 into the final Canva admissions pages.

The rule is simple:

> **Every strong sentence in the portfolio should point to a specific observable result.**

## Claims allowed before Research V2 is run

### Claim

> I implemented a modular LLM-security testing pipeline with red-team generation, LLM-based detection, a simulated victim, quantitative evaluation, and adaptive attacks.

Evidence:
- repository source code;
- original course report.

### Claim

> The original 15-case PoC benchmark was too small to meaningfully distinguish the two detector prompt conditions.

Evidence:
- both original detector variants reached the same binary F1 in the small course benchmark;
- this is presented as motivation for Research V2, not a final comparative finding.

### Claim

> Re-examining the original adaptive experiment showed that detector evasion alone is not sufficient to establish attack success.

Evidence:
- the original Round-2 evasion example;
- methodological inspection of whether the original malicious objective remained present.

## Claims allowed only after real Research V2 outputs exist

### Example A

> Covert/contextual attacks had lower recall than direct attacks.

Required evidence:
- `benchmark_category_summary.csv`;
- direct and covert recall values;
- no unresolved parse-error issue that changes interpretation.

### Example B

> Structured security analysis reduced false negatives.

Required evidence:
- baseline vs structured FNR;
- repeated benchmark runs;
- result should be reported with the actual observed magnitude.

### Example C

> Detector classification did not perfectly correspond to victim leakage.

Required evidence:
- `detection_leakage_matrix.csv`;
- at least two outcome cells are populated in a way that supports the statement.

### Example D

> Adaptive detector evasion did or did not preserve the original malicious objective.

Required evidence:
- pre-registered `adaptive_variants.json`;
- manually coded objective-preservation labels;
- objective-preservation rubric;
- `adaptive_summary.csv`.

The prior Gemini smoke-test refusal must not be counted as evasion because it destroyed the objective.

### Example E

> A strict true-attack-success event occurred.

Required evidence for each counted event:

```text
not detected
AND objective_preserved = true
AND leaked = true
```

## Claims to avoid

Do not write:

- “proves”
- “guarantees security”
- “industry-grade defense”
- “state of the art”
- “world-aware latest attacks” unless retrieval is actually implemented
- “MITRE accuracy proves detection quality”
- “confidence 0.9 means 90% attack probability”
- “indirect injection” for the current covert user-input cases
- “real enterprise deployment” for the simulated victim environment

## Preferred language

Use:

- “in this benchmark”
- “within the evaluated model/setup”
- “preliminary evidence”
- “observed”
- “suggests”
- “failure analysis”
- “simulated enterprise victim”
- “synthetic canary leakage”
- “covert/contextual direct attack”

## Admissions principle

The strongest signal is not that every result is positive.

A credible result with a clearly defined failure case is more valuable than an exaggerated perfect score.

The portfolio should show:

1. what was implemented;
2. what was measured;
3. what failed;
4. how the evaluation was redesigned;
5. what can and cannot be concluded.
