"""Validate PromptShield Research V2 benchmark and adaptive seed design.

This script checks structural issues before any paid API experiment is run.

Usage:
    python -m research_v2.validate_design
"""

import json
from collections import Counter
from pathlib import Path

from research_v2.canary_victim import SCENARIOS

BENCHMARK_PATH = Path("data/research_v2/benchmark_v2.json")
SEEDS_PATH = Path("data/research_v2/adaptive_seeds.json")
VARIANTS_PATH = Path("data/research_v2/adaptive_variants.json")


def load(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def fail(message: str):
    raise AssertionError(message)


def validate_benchmark(cases):
    if len(cases) != 60:
        fail(f"Expected 60 benchmark cases, found {len(cases)}.")

    ids = [c["id"] for c in cases]
    if len(ids) != len(set(ids)):
        fail("Benchmark case IDs are not unique.")

    category_counts = Counter(c["category"] for c in cases)
    expected = {"benign": 20, "direct": 20, "covert": 20}
    if dict(category_counts) != expected:
        fail(f"Unexpected category counts: {dict(category_counts)}")

    difficulty_counts = Counter(
        (c["category"], c.get("difficulty")) for c in cases
    )
    expected_difficulty = {
        ("benign", "easy"): 10,
        ("benign", "hard"): 10,
        ("direct", "easy"): 20,
        ("covert", "medium"): 10,
        ("covert", "hard"): 10,
    }
    if dict(difficulty_counts) != expected_difficulty:
        fail(f"Unexpected difficulty counts: {dict(difficulty_counts)}")

    valid_scenarios = set(SCENARIOS)
    for case in cases:
        missing = [
            key for key in (
                "id",
                "text",
                "is_attack",
                "category",
                "subcategory",
                "scenario",
                "objective_id",
                "protected_target",
                "source",
                "attack_surface",
                "difficulty",
            )
            if key not in case
        ]
        if missing:
            fail(f"{case.get('id', '<unknown>')} missing fields: {missing}")

        if case["attack_surface"] != "user_input":
            fail(f"{case['id']} uses unexpected attack surface {case['attack_surface']}.")

        valid_difficulty = {
            "benign": {"easy", "hard"},
            "direct": {"easy"},
            "covert": {"medium", "hard"},
        }
        if case["difficulty"] not in valid_difficulty[case["category"]]:
            fail(
                f"{case['id']} has invalid difficulty {case['difficulty']} "
                f"for category {case['category']}."
            )

        if case["scenario"] not in valid_scenarios:
            fail(f"{case['id']} uses unknown scenario {case['scenario']}.")

        if case["category"] == "benign" and case["is_attack"]:
            fail(f"{case['id']} is benign but labeled attack.")

        if case["category"] in {"direct", "covert"} and not case["is_attack"]:
            fail(f"{case['id']} is an attack category but labeled benign.")

        if case["category"] == "benign":
            if case["objective_id"] is not None or case["protected_target"] is not None:
                fail(f"{case['id']} benign case must not define attack objectives.")
        else:
            if not case["objective_id"]:
                fail(f"{case['id']} attack case is missing objective_id.")

        # Canary contamination check:
        # a test input must never literally contain a victim canary token, because
        # an echoed input could then be falsely counted as system-secret leakage.
        for scenario in SCENARIOS.values():
            for canary in scenario.canaries:
                if canary in case["text"]:
                    fail(
                        f"{case['id']} contains canary token {canary} in user input."
                    )


def validate_seeds(seeds):
    if len(seeds) != 12:
        fail(f"Expected 12 adaptive seeds, found {len(seeds)}.")

    ids = [s["id"] for s in seeds]
    if len(ids) != len(set(ids)):
        fail("Adaptive seed IDs are not unique.")

    scenario_counts = Counter(s["scenario"] for s in seeds)
    expected = {"banking_chatbot": 4, "hr_system": 4, "support_bot": 4}
    if dict(scenario_counts) != expected:
        fail(f"Unexpected adaptive scenario counts: {dict(scenario_counts)}")

    for seed in seeds:
        if seed["scenario"] not in SCENARIOS:
            fail(f"{seed['id']} uses unknown scenario {seed['scenario']}.")

        if not seed.get("objective_id"):
            fail(f"{seed['id']} is missing objective_id.")

        if not seed.get("protected_target"):
            fail(f"{seed['id']} is missing protected_target.")

        if seed["protected_target"] not in SCENARIOS[seed["scenario"]].canaries:
            fail(
                f"{seed['id']} target does not belong to scenario "
                f"{seed['scenario']}."
            )

        for scenario in SCENARIOS.values():
            for canary in scenario.canaries:
                if canary in seed["seed_prompt"]:
                    fail(
                        f"{seed['id']} contains canary token {canary} in seed prompt."
                    )



def validate_variants(chains):
    if len(chains) != 12:
        fail(f"Expected 12 adaptive variant chains, found {len(chains)}.")

    ids = [c["id"] for c in chains]
    if len(ids) != len(set(ids)):
        fail("Adaptive variant chain IDs are not unique.")

    scenario_counts = Counter(c["scenario"] for c in chains)
    expected = {"banking_chatbot": 4, "hr_system": 4, "support_bot": 4}
    if dict(scenario_counts) != expected:
        fail(
            "Unexpected adaptive variant scenario counts: "
            f"{dict(scenario_counts)}"
        )

    valid_strategies = {
        0: "direct_overt",
        1: "business_pretext",
        2: "workflow_completion",
    }

    for chain in chains:
        if chain["scenario"] not in SCENARIOS:
            fail(
                f"{chain['id']} uses unknown scenario "
                f"{chain['scenario']}."
            )

        if not chain.get("objective_id"):
            fail(f"{chain['id']} is missing objective_id.")

        target = chain.get("protected_target")
        if not target:
            fail(f"{chain['id']} is missing protected_target.")

        if target not in SCENARIOS[chain["scenario"]].canaries:
            fail(
                f"{chain['id']} target does not belong to scenario "
                f"{chain['scenario']}."
            )

        variants = chain.get("variants", [])
        if len(variants) != 3:
            fail(
                f"{chain['id']} must contain exactly 3 pre-registered "
                f"variants, found {len(variants)}."
            )

        rounds = [int(v["round"]) for v in variants]
        if rounds != [0, 1, 2]:
            fail(
                f"{chain['id']} rounds must be exactly [0, 1, 2], "
                f"found {rounds}."
            )

        for variant in variants:
            rnd = int(variant["round"])
            if variant.get("strategy") != valid_strategies[rnd]:
                fail(
                    f"{chain['id']} round {rnd} has unexpected strategy "
                    f"{variant.get('strategy')}."
                )

            if variant.get("intended_objective_preserved") is not True:
                fail(
                    f"{chain['id']} round {rnd} must be pre-registered "
                    "as intended objective-preserving."
                )

            text = variant.get("text", "").strip()
            if not text:
                fail(f"{chain['id']} round {rnd} has empty attack text.")

            for scenario in SCENARIOS.values():
                for canary in scenario.canaries:
                    if canary in text:
                        fail(
                            f"{chain['id']} round {rnd} contains exact "
                            f"canary token {canary}."
                        )


def main():
    benchmark = load(BENCHMARK_PATH)
    seeds = load(SEEDS_PATH)
    variants = load(VARIANTS_PATH)

    validate_benchmark(benchmark)
    validate_seeds(seeds)
    validate_variants(variants)

    print("Research V2 design validation passed.")
    print("Benchmark: 60 cases = 20 benign + 20 direct + 20 covert.")
    print("Adaptive seeds: 12 = 4 banking + 4 HR + 4 cloud support.")
    print("Adaptive variants: 12 chains x 3 pre-registered rounds.")
    print("Difficulty split validated: benign 10/10, direct 20 easy, covert 10/10.")
    print("No benchmark or adaptive prompt contains an exact synthetic canary token.")


if __name__ == "__main__":
    main()
