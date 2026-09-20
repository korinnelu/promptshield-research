"""Run PromptShield Research V2 adaptive-obfuscation experiments.

Official Research V2 uses pre-registered, objective-preserving variants rather
than a generative red-team model. This avoids provider safety refusals and makes
the attack sequence reproducible.

Adaptive policy:
- evaluate Round 0;
- if detected, advance to the next pre-registered obfuscation variant;
- stop the chain after the first detector evasion or after the maximum round.

The victim is evaluated independently at every executed round.

Usage:
    python -m research_v2.run_adaptive_experiment --max-round 2
"""

import argparse
import json
from pathlib import Path

from research_v2.common import (
    DEFAULT_MODEL,
    DETECTOR_TEMPERATURE,
    VICTIM_TEMPERATURE,
    TOP_P,
    ResearchDetector,
    ResearchVictim,
    append_jsonl,
    get_git_sha,
    load_json,
    utc_now,
)

VARIANTS_PATH = "data/research_v2/adaptive_variants.json"
DEFAULT_OUT_DIR = Path("results/research_v2")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--max-round",
        type=int,
        default=2,
        help="Maximum pre-registered obfuscation round to evaluate (0-2).",
    )
    parser.add_argument(
        "--detector-condition",
        choices=["baseline", "structured"],
        default="structured",
    )
    parser.add_argument("--detector-model", default=DEFAULT_MODEL)
    parser.add_argument("--victim-model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional number of attack chains for a smoke test.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional output directory. Limited smoke tests default to a separate folder.",
    )
    args = parser.parse_args()

    if not 0 <= args.max_round <= 2:
        raise ValueError("--max-round must be between 0 and 2.")

    chains = load_json(VARIANTS_PATH)
    if args.limit is not None:
        if args.limit < 1:
            raise ValueError("--limit must be >= 1.")
        chains = chains[: args.limit]

    out_dir = (
        Path(args.output_dir)
        if args.output_dir
        else DEFAULT_OUT_DIR / "smoke_adaptive_preregistered"
        if args.limit is not None
        else DEFAULT_OUT_DIR
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    raw_path = str(out_dir / "adaptive_raw.jsonl")
    Path(raw_path).write_text("", encoding="utf-8")

    detector = ResearchDetector(model=args.detector_model)
    victim = ResearchVictim(model=args.victim_model)

    executed_rows = 0
    completed_chains = 0
    evaded_chains = 0

    for chain in chains:
        chain_evaded = False

        for variant in chain["variants"]:
            rnd = int(variant["round"])
            if rnd > args.max_round:
                break

            attack_text = variant["text"]

            detection = detector.analyze(
                attack_text,
                args.detector_condition,
            )
            parsed = detection["parsed"]
            victim_result = victim.respond(
                chain["scenario"],
                attack_text,
            )

            row = {
                "timestamp": utc_now(),
                "seed_id": chain["id"],
                "round": rnd,
                "strategy": variant["strategy"],
                "scenario": chain["scenario"],
                "objective_id": chain["objective_id"],
                "protected_target": chain["protected_target"],
                "attack_text": attack_text,
                "variant_source": "pre_registered_author_constructed",
                "intended_objective_preserved": bool(
                    variant.get("intended_objective_preserved", False)
                ),
                "detector_condition": args.detector_condition,
                "parse_error": detection["parse_error"],
                "detected": None if parsed is None else parsed["is_attack"],
                "detector_raw": detection["raw_text"],
                "detector_explanation": (
                    None if parsed is None else parsed.get("explanation")
                ),
                "reported_confidence": (
                    None if parsed is None else parsed.get("confidence")
                ),
                "victim_response": victim_result["response"],
                "leaked": victim_result["leaked"],
                "leaked_canaries": victim_result["leaked_canaries"],
                "objective_preserved": None,
                "objective_preservation_note": (
                    "Manual coding required using the pre-defined rubric. "
                    "The intended label is not used as final evidence."
                ),
            }
            append_jsonl(raw_path, row)
            executed_rows += 1

            # A parse failure is missing data, not evasion. Continue to the next
            # pre-registered round so the chain can still be inspected.
            if parsed is None:
                continue

            if parsed["is_attack"] is False:
                chain_evaded = True
                evaded_chains += 1
                break

        completed_chains += 1

    metadata = {
        "generated_at": utc_now(),
        "git_commit_sha": get_git_sha(),
        "variants_path": VARIANTS_PATH,
        "seed_count": len(chains),
        "output_dir": str(out_dir),
        "is_smoke_test": args.limit is not None,
        "max_round": args.max_round,
        "adaptive_policy": (
            "Advance to next pre-registered obfuscation variant only while the "
            "previous executed round is detected; stop after first evasion or "
            "maximum round."
        ),
        "variant_source": "pre_registered_author_constructed",
        "detector_condition": args.detector_condition,
        "detector_model": args.detector_model,
        "victim_model": args.victim_model,
        "detector_temperature": DETECTOR_TEMPERATURE,
        "victim_temperature": VICTIM_TEMPERATURE,
        "top_p": TOP_P,
        "executed_rows": executed_rows,
        "completed_chains": completed_chains,
        "chains_with_detector_evasion": evaded_chains,
        "manual_step_required": (
            "Code objective_preserved for every executed row before calculating "
            "strict True Attack Success Rate."
        ),
        "design_note": (
            "The official Research V2 adaptive experiment does not use a "
            "generative red-team model. A prior smoke test with Gemini produced "
            "a provider-policy refusal that destroyed the adversarial objective, "
            "so pre-registered variants are used for reproducibility."
        ),
    }
    (out_dir / "adaptive_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Saved adaptive raw results to {raw_path}")
    print(f"Executed rows: {executed_rows}")
    print(f"Completed chains: {completed_chains}")
    print(f"Chains with detector evasion: {evaded_chains}")
    print("Next: manually code objective_preserved before final adaptive metrics.")


if __name__ == "__main__":
    main()
