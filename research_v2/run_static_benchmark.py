"""Run the fixed PromptShield Research V2 benchmark.

Design:
- 60 frozen cases
- 2 detector prompt conditions
- configurable repetitions (default 3)
- one victim call per case/repetition, shared across detector conditions
- raw JSONL output + CSV summaries
- parse errors are reported separately rather than silently treated as benign

Usage:
    python -m research_v2.run_static_benchmark --repetitions 3
"""

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

from research_v2.common import (
    DEFAULT_MODEL,
    DETECTOR_TEMPERATURE,
    VICTIM_TEMPERATURE,
    ResearchDetector,
    ResearchVictim,
    append_jsonl,
    load_json,
    utc_now,
)
from research_v2.metrics import binary_metrics, detection_leakage_matrix


BENCHMARK_PATH = "data/research_v2/benchmark_v2.json"
OUT_DIR = Path("results/research_v2")


def summarize(rows):
    parsed_rows = [r for r in rows if not r["parse_error"]]
    metric_rows = [
        {
            "actual_attack": r["actual_attack"],
            "predicted_attack": r["predicted_attack"],
        }
        for r in parsed_rows
    ]
    result = binary_metrics(metric_rows)
    result["parse_errors"] = sum(1 for r in rows if r["parse_error"])
    result["attempted_predictions"] = len(rows)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional small smoke-test limit.",
    )
    args = parser.parse_args()

    if args.repetitions < 1:
        raise ValueError("--repetitions must be >= 1")

    cases = load_json(BENCHMARK_PATH)
    if args.limit:
        cases = cases[: args.limit]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = str(OUT_DIR / "benchmark_raw.jsonl")
    summary_path = OUT_DIR / "benchmark_summary.csv"
    category_path = OUT_DIR / "benchmark_category_summary.csv"
    matrix_path = OUT_DIR / "detection_leakage_matrix.csv"
    metadata_path = OUT_DIR / "experiment_metadata.json"

    Path(raw_path).write_text("", encoding="utf-8")

    detector = ResearchDetector(model=args.model)
    victim = ResearchVictim(model=args.model)
    rows = []

    for rep in range(1, args.repetitions + 1):
        for case in cases:
            victim_result = victim.respond(case["scenario"], case["text"])

            for condition in ("baseline", "structured"):
                detection = detector.analyze(case["text"], condition)
                parsed = detection["parsed"]

                row = {
                    "timestamp": utc_now(),
                    "repetition": rep,
                    "case_id": case["id"],
                    "text": case["text"],
                    "actual_attack": case["is_attack"],
                    "category": case["category"],
                    "subcategory": case["subcategory"],
                    "scenario": case["scenario"],
                    "objective_id": case["objective_id"],
                    "protected_target": case["protected_target"],
                    "source": case["source"],
                    "attack_surface": case["attack_surface"],
                    "detector_condition": condition,
                    "parse_error": detection["parse_error"],
                    "detector_raw": detection["raw_text"],
                    "predicted_attack": None if parsed is None else bool(parsed.get("is_attack")),
                    "predicted_type": None if parsed is None else parsed.get("attack_type"),
                    "reported_confidence": None if parsed is None else parsed.get("confidence"),
                    "victim_leaked": victim_result["leaked"],
                    "leaked_canaries": victim_result["leaked_canaries"],
                    "victim_response": victim_result["response"],
                }
                append_jsonl(raw_path, row)
                rows.append(row)

    overall = []
    for condition in ("baseline", "structured"):
        group = [r for r in rows if r["detector_condition"] == condition]
        overall.append({"detector_condition": condition, **summarize(group)})

    with open(summary_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(overall[0].keys()))
        writer.writeheader()
        writer.writerows(overall)

    category_rows = []
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["detector_condition"], row["category"])].append(row)

    for (condition, category), group in sorted(grouped.items()):
        category_rows.append({
            "detector_condition": condition,
            "category": category,
            **summarize(group),
        })

    with open(category_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(category_rows[0].keys()))
        writer.writeheader()
        writer.writerows(category_rows)

    matrix_rows = []
    for condition in ("baseline", "structured"):
        usable = [
            {
                "detected": r["predicted_attack"],
                "leaked": r["victim_leaked"],
            }
            for r in rows
            if r["detector_condition"] == condition
            and r["actual_attack"]
            and not r["parse_error"]
        ]
        matrix_rows.append({
            "detector_condition": condition,
            **detection_leakage_matrix(usable),
        })

    with open(matrix_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(matrix_rows[0].keys()))
        writer.writeheader()
        writer.writerows(matrix_rows)

    metadata = {
        "generated_at": utc_now(),
        "benchmark_path": BENCHMARK_PATH,
        "case_count": len(cases),
        "repetitions": args.repetitions,
        "detector_conditions": ["baseline", "structured"],
        "model": args.model,
        "detector_temperature": DETECTOR_TEMPERATURE,
        "victim_temperature": VICTIM_TEMPERATURE,
        "victim_calls": len(cases) * args.repetitions,
        "detector_calls": len(cases) * args.repetitions * 2,
        "important_note": (
            "Model-reported confidence is stored for inspection but is not a primary metric."
        ),
    }
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Saved raw results to {raw_path}")
    print(f"Saved overall summary to {summary_path}")
    print(f"Saved category summary to {category_path}")
    print(f"Saved detection/leakage matrix to {matrix_path}")
    print(f"Saved metadata to {metadata_path}")


if __name__ == "__main__":
    main()
