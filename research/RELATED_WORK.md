# Related Work Notes — PromptShield Research V2

This is intentionally a **short positioning note**, not a full literature review.

Its purpose is to keep the admissions research brief technically accurate and to identify the minimum literature needed to explain the study.

## 1. Prompt-injection taxonomy

### OWASP LLM01:2025 — Prompt Injection

OWASP distinguishes:

- **Direct prompt injection**: malicious instructions are supplied directly through the user-facing prompt/input.
- **Indirect prompt injection**: malicious instructions are embedded in external content such as webpages, files, retrieved documents, or other data later processed by the LLM.

Reference:

OWASP GenAI Security Project, **LLM01:2025 Prompt Injection**  
https://genai.owasp.org/llmrisk/llm01-prompt-injection/

### Important correction for PromptShield

The current Research V2 benchmark uses **user-input attacks only**.

Therefore, the 20 “covert” cases should be described as:

> **covert / contextual direct prompt injections**

They should **not** be presented as true indirect prompt injections merely because the malicious intent is hidden inside a plausible business narrative.

A future extension could introduce actual indirect injection through retrieved files, webpages, emails, or tool output.

---

## 2. Indirect prompt injection as a system-level threat

Kai Greshake et al., **“Not what you've signed up for: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection”** (2023).

The paper emphasizes that LLM-integrated applications blur the boundary between instructions and data. It demonstrates attacks in which malicious instructions are placed into externally retrieved content rather than directly entered by the end user.

Preprint:  
https://arxiv.org/abs/2302.12173

### Relevance to PromptShield

This supports two decisions:

1. avoid conflating contextual direct attacks with true indirect injection;
2. treat prompt injection as a property of the **whole information system**, not only a text-classification problem.

---

## 3. Benchmark design for indirect prompt injection

Jingwei Yi et al., **“Benchmarking and Defending Against Indirect Prompt Injection Attacks on Large Language Models”** (BIPIA, 2023).

BIPIA was introduced specifically to evaluate indirect prompt injection and studies the distinction between informational context and actionable instructions.

Preprint:  
https://arxiv.org/abs/2312.14197

### Relevance to PromptShield

Research V2 is deliberately smaller and focused on direct user-input attacks, but BIPIA is useful as a benchmark-design reference:

- define the attack channel clearly;
- separate task/context from adversarial instruction;
- use explicit outcome measures rather than only qualitative examples.

---

## 4. Dynamic and adaptive evaluation

Edoardo Debenedetti et al., **“AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents”**, NeurIPS 2024 Datasets and Benchmarks Track.

AgentDojo evaluates tool-using agents with realistic tasks, security test cases, attacks, defenses, and adaptive evaluation.

Official proceedings:  
https://proceedings.nips.cc/paper_files/paper/2024/hash/97091a5177d8dc64b1da8bf3e1f6fb54-Abstract-Datasets_and_Benchmarks_Track.html

### Relevance to PromptShield

The strongest conceptual connection is that **security evaluation should measure whether the attacker goal is actually achieved**, not merely whether a detector assigns a label.

This motivates PromptShield Research V2's separation of:

- detection evasion;
- adversarial-objective preservation;
- downstream victim outcome.

---

## 5. Moving beyond prompt-only defenses

Sizhe Chen, Julien Piet, Chawin Sitawarin, David Wagner, **“StruQ: Defending Against Prompt Injection with Structured Queries”**, USENIX Security 2025.

StruQ separates prompt/instruction content from user data through a structured interface and a specially trained model.

Official publication:  
https://www.usenix.org/conference/usenixsecurity25/presentation/chen-sizhe

### Relevance to PromptShield

PromptShield's original project focused heavily on prompt engineering and detector prompting.

StruQ supports a more mature Research V2 conclusion:

> Prompt-level detection can be useful for evaluation, but robust deployment may require architectural separation and system-level controls.

This aligns with the original project report's own future-work direction toward least privilege and system-level defenses.

---

## 6. Practical security guidance

OWASP's current prevention guidance recommends multiple layers rather than relying on a single prompt-level defense, including:

- constrained model behavior;
- deterministic output validation;
- input/output filtering;
- least-privilege access;
- human approval for high-risk actions;
- clear separation of untrusted external content;
- adversarial testing.

Reference:

OWASP, **LLM Prompt Injection Prevention Cheat Sheet**  
https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html

### Relevance to PromptShield

This is useful for the final “Future Work” section.

Research V2 should avoid claiming that a better detector prompt solves prompt injection. A more defensible conclusion is that detector evaluation is one layer in a broader trustworthy information-system architecture.

---

# Minimal literature set for the 3-page admissions brief

The Canva brief does not need a full literature-review section.

A small footer or references box can cite only:

1. OWASP LLM01:2025
2. Greshake et al. (2023)
3. Yi et al. / BIPIA (2023)
4. Debenedetti et al. / AgentDojo (NeurIPS 2024)
5. Chen et al. / StruQ (USENIX Security 2025)

This is enough to establish:

- attack taxonomy;
- why indirect injection matters;
- why benchmark design matters;
- why adaptive/outcome-based evaluation matters;
- why system-level defenses are relevant.

## Research gap language for PromptShield

Do **not** claim:

> “Existing research only evaluates binary detection.”

That statement is too broad and is not supported by the literature above.

A safer positioning is:

> “PromptShield Research V2 uses a compact, reproducible evaluation that places detector classification and victim-model leakage side by side, while separately checking whether adaptive evasions preserve the original adversarial objective.”

This describes what the project actually does without overstating novelty.
