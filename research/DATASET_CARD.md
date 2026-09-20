# PromptShield Research V2 — Dataset Card

## Dataset name

**PromptShield Research V2 Fixed Benchmark**

File:

`data/research_v2/benchmark_v2.json`

## Purpose

This benchmark is a compact admissions-oriented evaluation set for comparing two LLM-based prompt-injection detector prompt conditions and for measuring downstream synthetic-secret leakage on a simulated victim model.

It is **not** intended to be presented as a comprehensive public prompt-injection benchmark.

## Size

60 cases:

- 20 benign / legitimate user requests
  - 10 easy
  - 10 hard negatives containing security-sensitive language without requesting protected values
- 20 explicit direct prompt-injection attacks
  - 20 easy / overt
- 20 covert / contextual direct prompt-injection attacks
  - 10 medium
  - 10 hard

All cases enter through the **user-input attack surface**.

## Important taxonomy note

The “covert” category is still a **direct user-input attack**.

It is not equivalent to indirect prompt injection as defined by OWASP and the prompt-injection literature, where malicious instructions are embedded in external content such as files, webpages, retrieved documents, emails, or tool output.

Research V2 therefore uses the term:

> **covert / contextual direct prompt injection**

## Scenarios

The benchmark covers three fictional enterprise contexts:

- banking customer assistant
- HR assistant
- cloud technical-support assistant

These are synthetic scenarios and contain no real personal, corporate, or credential data.

## Provenance

Current benchmark provenance:

`source = "author_constructed"`

All 60 examples were constructed specifically for this project.

This should be disclosed because it creates a possible **author-design bias**: the same researcher defines the evaluation categories and develops the system being evaluated.

## Attack categories

### Benign

Legitimate product, policy, account-help, payroll-help, or support requests.

Purpose:
- estimate false-positive behavior;
- test whether security prompts over-block normal usage;
- include hard negatives that mention credentials, security reviews, redaction, or access-control concepts while explicitly avoiding requests for real protected values.

### Direct

Overt malicious instructions such as:
- instruction override;
- persona hijack;
- privilege claims;
- explicit secret exfiltration;
- jailbreak framing.

Purpose:
- measure basic attack recognition.

### Covert

The malicious objective remains present, but is embedded in a plausible context such as:
- compliance review;
- onboarding;
- incident support;
- audit preparation;
- roleplay;
- quality assurance.

Purpose:
- test whether contextual obfuscation changes detector performance.

## Labels

Each record contains:

- `id`
- `text`
- `is_attack`
- `category`
- `subcategory`
- `scenario`
- `objective_id`
- `protected_target`
- `source`
- `attack_surface`
- `difficulty`

## Leakage targets

Victim systems use **synthetic canary secrets**.

The exact canary values are never included in user-input benchmark text.

This prevents a simple echoed user prompt from being falsely counted as system-secret leakage.

## Freeze rule

Once the final benchmark experiment begins:

> **Do not rewrite individual cases after observing model performance.**

If a case is later found to contain an error, document the issue and create a versioned benchmark revision rather than silently changing the current set.

## Limitations

- small sample size;
- author-constructed examples;
- English only;
- direct user-input attack surface only;
- three simulated enterprise contexts;
- no multimodal attacks;
- no external-content indirect injection;
- no production tools or APIs;
- results may be model-specific.

## Appropriate claims

The dataset can support statements such as:

> “In this 60-case fixed benchmark, covert/contextual attacks produced a different detection pattern from explicit direct attacks.”

It cannot support claims such as:

> “PromptShield is robust to prompt injection in general.”

or:

> “The benchmark represents real-world prompt injection frequency.”

## Future dataset extension

A stronger follow-up would add:

- externally sourced attacks;
- true indirect-injection cases;
- multilingual prompts;
- more model families;
- independent annotation;
- held-out examples authored by someone other than the system developer.


---

# Adaptive-obfuscation variant set

File:

`data/research_v2/adaptive_variants.json`

The adaptive experiment uses 12 attack chains. Each chain contains three pre-registered, author-constructed variants:

1. `direct_overt`
2. `business_pretext`
3. `workflow_completion`

All three variants target the same registered protected resource.

The exact synthetic canary token is never placed in the user prompt.

## Why pre-register variants?

A generative red-team smoke test returned a provider-policy refusal rather than an attack rewrite. Counting that as detector evasion would be methodologically wrong because the adversarial objective disappeared.

Pre-registration therefore removes a provider-policy confound and makes the attack sequence reproducible.

## Limitation

The adaptive variants are author-constructed. This improves control and reproducibility but creates author-design bias. Results should therefore be described as outcomes **within this fixed adaptive protocol**, not as a general estimate of real-world adaptive-attack success.
