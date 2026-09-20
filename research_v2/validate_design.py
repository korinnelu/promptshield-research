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
            )
            if key not in case
        ]
        if missing:
            fail(f"{case.get('id', '<unknown>')} missing fields: {missing}")

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


def main():
    benchmark = load(BENCHMARK_PATH)
    seeds = load(SEEDS_PATH)

    validate_benchmark(benchmark)
    validate_seeds(seeds)

    print("Research V2 design validation passed.")
    print("Benchmark: 60 cases = 20 benign + 20 direct + 20 covert.")
    print("Adaptive seeds: 12 = 4 banking + 4 HR + 4 cloud support.")
    print("No user prompt contains an exact synthetic canary token.")


if __name__ == "__main__":
    main()
