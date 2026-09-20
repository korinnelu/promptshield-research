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
import random
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
DEFAULT_OUT_DIR = Path("results/research_v2")


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




def select_limited_cases(cases, limit):
    """Select a deterministic, category-balanced subset for smoke tests."""
    if limit is None or limit >= len(cases):
        return list(cases)
    if limit < 1:
        raise ValueError("--limit must be >= 1")

    by_category = {
        category: [c for c in cases if c["category"] == category]
        for category in ("benign", "direct", "covert")
    }

    selected = []
    index = 0
    while len(selected) < limit:
        added = False
        for category in ("benign", "direct", "covert"):
            bucket = by_category[category]
            if index < len(bucket) and len(selected) < limit:
                selected.append(bucket[index])
                added = True
        if not added:
            break
        index += 1

    return selected


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Detector model.")
    parser.add_argument("--victim-model", default=DEFAULT_MODEL)
    parser.add_argument("--shuffle-seed", type=int, default=20260920)
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional output directory. Limited smoke tests default to a separate folder.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional small smoke-test limit.",
    )
    args = parser.parse_args()

    if args.repetitions < 1:
        raise ValueError("--repetitions must be >= 1")

    cases = select_limited_cases(load_json(BENCHMARK_PATH), args.limit)

    out_dir = (
        Path(args.output_dir)
        if args.output_dir
        else DEFAULT_OUT_DIR / "smoke_static"
        if args.limit is not None
        else DEFAULT_OUT_DIR
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    raw_path = str(out_dir / "benchmark_raw.jsonl")
    summary_path = out_dir / "benchmark_summary.csv"
    category_path = out_dir / "benchmark_category_summary.csv"
    difficulty_path = out_dir / "benchmark_difficulty_summary.csv"
    repetition_path = out_dir / "benchmark_repetition_summary.csv"
    stability_path = out_dir / "benchmark_stability_summary.csv"
    matrix_path = out_dir / "detection_leakage_matrix.csv"
    paired_path = out_dir / "paired_detector_comparison.csv"
    paired_trials_path = out_dir / "paired_detector_trials.csv"
    leakage_path = out_dir / "victim_leakage_summary.csv"
    metadata_path = out_dir / "experiment_metadata.json"

    Path(raw_path).write_text("", encoding="utf-8")

    detector = ResearchDetector(model=args.model)
    victim = ResearchVictim(model=args.victim_model)
    rows = []

    for rep in range(1, args.repetitions + 1):
        rep_cases = list(cases)
        random.Random(args.shuffle_seed + rep).shuffle(rep_cases)

        for case_index, case in enumerate(rep_cases):
            # The victim is evaluated independently of detector condition.
            # Sharing the same victim outcome across the two detector conditions
            # makes the detector comparison paired rather than confounded by a
            # different victim sample.
            victim_result = victim.respond(case["scenario"], case["text"])

            condition_order = (
                ("baseline", "structured")
                if (rep + case_index) % 2 == 0
                else ("structured", "baseline")
            )
            for condition in condition_order:
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
                    "difficulty": case["difficulty"],
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

    # Difficulty-stratified metrics. Category is retained because "hard"
    # benign cases and "hard" covert attacks serve different purposes.
    difficulty_rows = []
    difficulty_groups = defaultdict(list)
    for row in rows:
        difficulty_groups[
            (row["detector_condition"], row["category"], row["difficulty"])
        ].append(row)

    for (condition, category, difficulty), group in sorted(
        difficulty_groups.items()
    ):
        difficulty_rows.append({
            "detector_condition": condition,
            "category": category,
            "difficulty": difficulty,
            **summarize(group),
        })
    write_csv(difficulty_path, difficulty_rows)

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

    # Paired baseline-vs-structured correctness comparison on identical trials.
    pair_groups = defaultdict(dict)
    for row in rows:
        pair_groups[(row["repetition"], row["case_id"])][
            row["detector_condition"]
        ] = row

    paired_records = []
    paired_by_category = defaultdict(lambda: {
        "both_correct": 0,
        "baseline_only_correct": 0,
        "structured_only_correct": 0,
        "both_wrong": 0,
        "parse_error_pairs": 0,
        "n_pairs": 0,
    })

    for (_, _), pair in pair_groups.items():
        if "baseline" not in pair or "structured" not in pair:
            continue

        b = pair["baseline"]
        s = pair["structured"]
        category = b["category"]
        bucket = paired_by_category[category]
        bucket["n_pairs"] += 1

        if b["parse_error"] or s["parse_error"]:
            bucket["parse_error_pairs"] += 1
            outcome = "parse_error_pair"
        else:
            b_correct = b["predicted_attack"] == b["actual_attack"]
            s_correct = s["predicted_attack"] == s["actual_attack"]

            if b_correct and s_correct:
                bucket["both_correct"] += 1
                outcome = "both_correct"
            elif b_correct and not s_correct:
                bucket["baseline_only_correct"] += 1
                outcome = "baseline_only_correct"
            elif not b_correct and s_correct:
                bucket["structured_only_correct"] += 1
                outcome = "structured_only_correct"
            else:
                bucket["both_wrong"] += 1
                outcome = "both_wrong"

        paired_records.append({
            "repetition": b["repetition"],
            "case_id": b["case_id"],
            "category": category,
            "outcome": outcome,
        })

    paired_summary = []
    for category in ("benign", "direct", "covert"):
        paired_summary.append({
            "category": category,
            **paired_by_category[category],
        })

    # Add an overall row.
    overall_pair = {
        "category": "overall",
        "both_correct": sum(r["both_correct"] for r in paired_summary),
        "baseline_only_correct": sum(r["baseline_only_correct"] for r in paired_summary),
        "structured_only_correct": sum(r["structured_only_correct"] for r in paired_summary),
        "both_wrong": sum(r["both_wrong"] for r in paired_summary),
        "parse_error_pairs": sum(r["parse_error_pairs"] for r in paired_summary),
        "n_pairs": sum(r["n_pairs"] for r in paired_summary),
    }
    paired_summary.append(overall_pair)
    write_csv(paired_path, paired_summary)
    write_csv(paired_trials_path, paired_records)

    # Victim leakage is independent of detector condition. Use one copy of each
    # paired trial to avoid double-counting the same victim response.
    victim_rows = [
        r for r in rows
        if r["detector_condition"] == "baseline"
    ]
    leakage_summary = []
    for category in ("direct", "covert"):
        group = [r for r in victim_rows if r["category"] == category]
        leaked = sum(1 for r in group if r["victim_leaked"])
        leakage_summary.append({
            "category": category,
            "leaked": leaked,
            "total": len(group),
            "leakage_rate": leaked / len(group) if group else 0.0,
        })

    attack_group = [r for r in victim_rows if r["actual_attack"]]
    attack_leaked = sum(1 for r in attack_group if r["victim_leaked"])
    leakage_summary.append({
        "category": "all_attacks",
        "leaked": attack_leaked,
        "total": len(attack_group),
        "leakage_rate": attack_leaked / len(attack_group) if attack_group else 0.0,
    })
    write_csv(leakage_path, leakage_summary)

    metadata = {
        "generated_at": utc_now(),
        "git_commit_sha": get_git_sha(),
        "benchmark_path": BENCHMARK_PATH,
        "output_dir": str(out_dir),
        "is_smoke_test": args.limit is not None,
        "case_count": len(cases),
        "repetitions": args.repetitions,
        "detector_conditions": ["baseline", "structured"],
        "detector_model": args.model,
        "victim_model": args.victim_model,
        "shuffle_seed": args.shuffle_seed,
        "condition_order": "alternated by repetition and case index",
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
    print(f"Saved difficulty summary to {difficulty_path}")
    print(f"Saved repetition summary to {repetition_path}")
    print(f"Saved stability summary to {stability_path}")
    print(f"Saved detection/leakage matrix to {matrix_path}")
    print(f"Saved paired detector comparison to {paired_path}")
    print(f"Saved paired detector trials to {paired_trials_path}")
    print(f"Saved victim leakage summary to {leakage_path}")
    print(f"Saved metadata to {metadata_path}")


if __name__ == "__main__":
    main()
