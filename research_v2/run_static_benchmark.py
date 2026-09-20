"""Run the fixed PromptShield Research V2 benchmark.

Design:
- 60 frozen cases
- 2 detector prompt conditions
- configurable repetitions (default 3)
- one victim call per case/repetition, shared across detector conditions
- raw JSONL output + pooled, category, repetition, and stability summaries
- parse errors are reported separately rather than silently treated as benign

Usage:
    python -m research_v2.run_static_benchmark --repetitions 3
"""

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean, pstdev

from research_v2.common import (
    DEFAULT_MODEL,
    DETECTOR_TEMPERATURE,
    VICTIM_TEMPERATURE,
    ResearchDetector,
    ResearchVictim,
    append_jsonl,
    get_git_sha,
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


def write_csv(path: Path, rows):
    if not rows:
        raise ValueError(f"No rows available for {path}")
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


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
    repetition_path = OUT_DIR / "benchmark_repetition_summary.csv"
    stability_path = OUT_DIR / "benchmark_stability_summary.csv"
    matrix_path = OUT_DIR / "detection_leakage_matrix.csv"
    metadata_path = OUT_DIR / "experiment_metadata.json"

    Path(raw_path).write_text("", encoding="utf-8")

    detector = ResearchDetector(model=args.model)
    victim = ResearchVictim(model=args.model)
    rows = []

    for rep in range(1, args.repetitions + 1):
        for case in cases:
            # The victim is evaluated independently of detector condition.
            # Sharing the same victim outcome across the two detector conditions
            # makes the detector comparison paired rather than confounded by a
            # different victim sample.
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
                    "predicted_attack": (
                        None if parsed is None else bool(parsed.get("is_attack"))
                    ),
                    "predicted_type": (
                        None if parsed is None else parsed.get("attack_type")
                    ),
                    "reported_confidence": (
                        None if parsed is None else parsed.get("confidence")
                    ),
                    "victim_leaked": victim_result["leaked"],
                    "leaked_canaries": victim_result["leaked_canaries"],
                    "victim_response": victim_result["response"],
                }
                append_jsonl(raw_path, row)
                rows.append(row)

    # Pooled metrics by detector condition.
    overall = []
    for condition in ("baseline", "structured"):
        group = [r for r in rows if r["detector_condition"] == condition]
        overall.append({"detector_condition": condition, **summarize(group)})
    write_csv(summary_path, overall)

    # Category-level pooled metrics.
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
    write_csv(category_path, category_rows)

    # Per-repetition metrics, so run-to-run stability is visible.
    repetition_rows = []
    for rep in range(1, args.repetitions + 1):
        for condition in ("baseline", "structured"):
            group = [
                r for r in rows
                if r["repetition"] == rep
                and r["detector_condition"] == condition
            ]
            repetition_rows.append({
                "repetition": rep,
                "detector_condition": condition,
                **summarize(group),
            })
    write_csv(repetition_path, repetition_rows)

    # Mean and population SD across repetitions.
    stability_rows = []
    metric_names = [
        "accuracy",
        "precision",
        "recall",
        "f1",
        "false_positive_rate",
        "false_negative_rate",
    ]
    for condition in ("baseline", "structured"):
        subset = [
            r for r in repetition_rows
            if r["detector_condition"] == condition
        ]
        record = {"detector_condition": condition}
        for metric in metric_names:
            values = [float(r[metric]) for r in subset]
            record[f"{metric}_mean"] = mean(values)
            record[f"{metric}_sd"] = pstdev(values)
        record["parse_errors_total"] = sum(int(r["parse_errors"]) for r in subset)
        stability_rows.append(record)
    write_csv(stability_path, stability_rows)

    # Detector classification x independently measured victim leakage.
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
    write_csv(matrix_path, matrix_rows)

    metadata = {
        "generated_at": utc_now(),
        "git_commit_sha": get_git_sha(),
        "benchmark_path": BENCHMARK_PATH,
        "case_count": len(cases),
        "repetitions": args.repetitions,
        "detector_conditions": ["baseline", "structured"],
        "model": args.model,
        "detector_temperature": DETECTOR_TEMPERATURE,
        "victim_temperature": VICTIM_TEMPERATURE,
        "victim_calls": len(cases) * args.repetitions,
        "detector_calls": len(cases) * args.repetitions * 2,
        "design_note": (
            "Detector and victim are evaluated in parallel. "
            "The detector is not assumed to be a blocking production gateway."
        ),
        "important_note": (
            "Model-reported confidence is stored for inspection but is not a "
            "primary metric or calibrated probability."
        ),
    }
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Saved raw results to {raw_path}")
    print(f"Saved pooled summary to {summary_path}")
    print(f"Saved category summary to {category_path}")
    print(f"Saved repetition summary to {repetition_path}")
    print(f"Saved stability summary to {stability_path}")
    print(f"Saved detection/leakage matrix to {matrix_path}")
    print(f"Saved metadata to {metadata_path}")


if __name__ == "__main__":
    main()
