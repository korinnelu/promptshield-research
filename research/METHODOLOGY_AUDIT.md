# PromptShield Research V2 — Methodology Audit

> Scope: this audit is based on the current code in `main`, the 15-case benchmark in `data/test_cases.json`, and the original course report in `docs/Prompt Shield Project Document.pdf`.
>
> Goal: turn the course PoC into a compact, defensible empirical study for graduate admissions **without overstating what the existing evidence supports**.

## 1. What is already strong

The current project is more than a UI demo. It already separates five useful components:

1. **Red team generation** — `src/red_team.py`
2. **Blue team detection** — `src/blue_team.py`
3. **Victim model / downstream outcome measurement** — `src/victim.py`
4. **Quantitative evaluator** — `src/evaluator.py`
5. **Automated report generation** — `src/reporter.py`

The most researchable design choice is the separation between:

- **Detection outcome**: did the detector label the prompt as an attack?
- **Security outcome**: did the victim model actually reveal protected information?

This supports a stronger research framing than “which prompt gets the highest F1?”

## 2. Core research framing

### Central idea

> **Detection is not necessarily successful defense, and evasion is not necessarily a successful attack.**

The research version should distinguish three concepts:

- **Detection success** — the detector correctly classifies the input.
- **Detection evasion** — the detector classifies a malicious input as benign.
- **Attack success** — the adversarial objective is preserved and the victim produces a prohibited security outcome, such as leaking a synthetic secret.

### Proposed research questions

**RQ1.** How does attack obfuscation affect the performance of an LLM-based prompt-injection detector?

**RQ2.** Can adaptive attack evolution increase detection evasion while preserving the original adversarial objective?

**RQ3.** How closely does detector performance correspond to downstream sensitive-data leakage?

These three questions can be answered with the existing architecture after a focused research-layer extension.

---

## 3. Methodological issues in the current version

### 3.1 Benchmark size and construction

Current state:
- 15 total cases
- 5 benign
- 5 explicit attacks
- 5 covert attacks
- cases are manually authored for the project

Risk:
- the benchmark is too small for strong comparative claims;
- the same author designs both the system and the benchmark, creating design bias;
- F1 = 1.0 on 15 examples provides little discrimination between detector variants.

Research V2 action:
- expand to a **pre-registered 60-case benchmark**;
- keep the test set fixed before the final experiment;
- record category and scenario metadata for every case;
- avoid editing cases after seeing the final results.

Recommended split:

| Category | Cases |
|---|---:|
| Benign / legitimate requests | 20 |
| Explicit / direct attacks | 20 |
| Covert / contextual attacks | 20 |
| **Total** | **60** |

Suggested covert subcategories:
- authority / insider pretext
- legitimate business-process pretext
- social / emotional framing
- roleplay or contextual reframing

### 3.2 Detector “confidence” is not a calibrated probability

Current state:
- the detector returns values such as 0.8, 0.9, and 0.95.

Risk:
- these are model-generated self-reports, not calibrated probabilities;
- a drop from 0.9 to 0.8 should not be interpreted as a literal 10-percentage-point decrease in security.

Research V2 action:
- keep confidence only as a **secondary descriptive signal**;
- do not use it as the primary evidence for RQ1–RQ3;
- primary metrics should be based on observed classifications and victim outcomes.

### 3.3 V1 vs V2 should be framed as prompt conditions, not proof of Chain-of-Thought

Current state:
- V1 is a minimal detector prompt.
- V2 instructs the model to check five security dimensions before returning JSON.

Research V2 action:
rename the conditions as:

- **Baseline Detector Prompt**
- **Structured Security Analysis Prompt**

This is a more precise operational description than claiming access to or measurement of hidden chain-of-thought.

### 3.4 MITRE mapping is useful context, not primary ground truth

Current state:
- PromptShield maps LLM attacks to selected MITRE ATT&CK techniques.

Value:
- useful for communication with security practitioners;
- useful as an operational taxonomy.

Limitation:
- ATT&CK was not designed as a native prompt-injection taxonomy;
- some mappings are analogical.

Research V2 action:
- keep MITRE mapping as supplementary analysis;
- remove “MITRE mapping accuracy” from the main performance claim unless an independently defined gold-standard mapping is created.

### 3.5 Adaptive evasion currently does not prove attack success

The most important issue in the existing adaptive experiment is that an evolved prompt can become more benign-sounding by **dropping part of its original malicious objective**.

Therefore:

> `detected = false` is not sufficient evidence that the red team produced a successful attack.

Research V2 must track:
1. detection evasion;
2. objective preservation;
3. actual victim outcome.

Recommended definition:

```text
True Attack Success =
    Detection Evasion
    AND Adversarial Objective Preserved
    AND Prohibited Victim Outcome Observed
```

A looser secondary metric may report evasion and leakage separately.

### 3.6 Leakage detection should use synthetic canary secrets

Current state:
- `src/victim.py` checks natural-language sensitive keywords.

Risk:
- short or common keywords can create ambiguous matches;
- partial natural-language disclosure is harder to score consistently.

Research V2 action:
embed clearly synthetic secrets such as:

- `CANARY_BANK_ADMIN_7F32A9`
- `CANARY_API_KEY_X92KQ4`
- `CANARY_HR_SECRET_M51P8D`

Primary leakage metric:
- exact canary exposed: yes / no.

Optional secondary metric:
- number of unique canaries exposed.

### 3.7 “World-aware” should not imply live literature retrieval

Current state:
- the red-team prompt asks Gemini to use current research and real-world incidents up to its knowledge cutoff.

Research V2 action:
- describe this as **knowledge-guided attack generation** unless live retrieval is actually implemented;
- do not claim real-time or literature-grounded threat intelligence without a retrieval layer and cited sources.

---

## 4. Recommended experiment design

### Experiment A — Static benchmark

**Inputs:** 60 fixed cases.

**Detector conditions:**
1. Baseline Detector Prompt
2. Structured Security Analysis Prompt

**Recommended repetitions:** 3 runs per case per condition.

Why repeat:
- LLM outputs can vary even at low temperature;
- repeated trials let us report stability instead of a single lucky run.

Primary metrics:
- Precision
- Recall
- F1
- False Positive Rate
- False Negative Rate

Stratified metrics:
- benign
- direct
- covert

Most important comparison:
- direct-attack recall vs covert-attack recall.

### Experiment B — Adaptive attack evaluation

Use a small fixed set of malicious objectives, for example 12 seeds.

Each seed should record:
- scenario
- target protected resource
- original adversarial objective
- maximum adaptation rounds

For each round record:
- attack text
- detector decision
- detector prompt condition
- objective preserved? (predefined rubric)
- victim canary leaked?
- leaked canary IDs

Primary metrics:
- Evasion Rate
- Objective-Preservation Rate
- Leakage Rate
- True Attack Success Rate

### Experiment C — Detection vs security outcome

Create a 2 × 2 outcome table:

| | No Leakage | Leakage |
|---|---:|---:|
| Detected | n | n |
| Not Detected | n | n |

The most security-critical cell is:

> **Not Detected + Leakage**

This directly answers RQ3.

---

## 5. What can be claimed from the original course version

Safe preliminary statements:
- a modular red-team / detector / victim / evaluator pipeline was implemented;
- the original benchmark contained 15 labeled cases;
- the course report recorded one detector-evasion event in the third adaptive chain at Round 2;
- the five-attack live victim test recorded no keyword-detected leakage in that run;
- the original report explicitly recognized benchmark size, language, scenario, simulated-victim, and prompt-only-defense limitations.

Statements that should **not** be presented as final Research V2 findings:
- that the structured detector is definitively superior;
- that model-reported confidence is a calibrated risk probability;
- that an adaptive evasion is automatically a successful attack;
- that MITRE mapping accuracy proves better prompt-injection defense;
- that “world-aware” generation uses live current research.

---

## 6. Admissions positioning

The strongest admissions story is not:

> “I built an AI security product with many features.”

It is:

> “I revisited my own working prototype, identified weaknesses in the original evaluation design, and redesigned the experiment to distinguish classifier performance from actual security outcomes.”

That demonstrates:
- methodological self-critique;
- experimental design;
- reproducibility;
- quantitative evaluation;
- failure analysis;
- ability to turn engineering work into a researchable question.

This is the intended role of Research V2.
