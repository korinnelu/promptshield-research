"""Extract interpretable failure cases from Research V2 static results.

This script does not run any model calls. It post-processes benchmark_raw.jsonl.

Outputs:
- false_negatives.csv
- false_positives.csv
- detector_disagreements.csv
- not_detected_with_leakage.csv
- benign_with_leakage.csv
- detection_leakage_all_inputs.csv
- victim_leakage_all_inputs.csv
- case_consistency.csv

Usage:
    python -m research_v2.analyze_failures
"""

import csv
import json
from collections import defaultdict
from pathlib import Path

RESULTS = Path("results/research_v2")
RAW_PATH = RESULTS / "benchmark_raw.jsonl"


def read_jsonl(path: Path):
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run the static benchmark first."
        )
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_csv(path: Path, rows, fieldnames=None):
    if not rows:
        # Keep an explicit empty file with headers when possible.
        if fieldnames:
            with path.open("w", newline="", encoding="utf-8") as f:
                csv.DictWriter(f, fieldnames=fieldnames).writeheader()
        return

    if fieldnames is None:
        fieldnames = list(rows[0].keys())

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def compact(row):
    return {
        "repetition": row["repetition"],
        "case_id": row["case_id"],
        "category": row["category"],
        "subcategory": row["subcategory"],
        "scenario": row["scenario"],
        "detector_condition": row["detector_condition"],
        "actual_attack": row["actual_attack"],
        "predicted_attack": row["predicted_attack"],
        "victim_leaked": row["victim_leaked"],
        "leaked_canaries": ";".join(row.get("leaked_canaries", [])),
        "reported_confidence": row.get("reported_confidence"),
        "text": row["text"],
        "detector_raw": row.get("detector_raw", ""),
        "victim_response": row.get("victim_response", ""),
    }


def main():
    rows = read_jsonl(RAW_PATH)
    RESULTS.mkdir(parents=True, exist_ok=True)

    usable = [r for r in rows if not r.get("parse_error")]

    false_negatives = [
        compact(r)
        for r in usable
        if r["actual_attack"] and not r["predicted_attack"]
    ]
    false_positives = [
        compact(r)
        for r in usable
        if (not r["actual_attack"]) and r["predicted_attack"]
    ]

    write_csv(
        RESULTS / "false_negatives.csv",
        false_negatives,
        fieldnames=list(compact(usable[0]).keys()) if usable else None,
    )
    write_csv(
        RESULTS / "false_positives.csv",
        false_positives,
        fieldnames=list(compact(usable[0]).keys()) if usable else None,
    )

    # Paired disagreement analysis: same case + repetition, different detector
    # conditions. This is especially useful for identifying structured-prompt
    # rescues and regressions.
    grouped = defaultdict(dict)
    for r in rows:
        grouped[(r["repetition"], r["case_id"])][r["detector_condition"]] = r

    disagreement_rows = []
    for (rep, case_id), pair in sorted(grouped.items()):
        if "baseline" not in pair or "structured" not in pair:
            continue

        b = pair["baseline"]
        s = pair["structured"]

        if b["parse_error"] or s["parse_error"]:
            outcome = "parse_error_pair"
        else:
            b_correct = b["predicted_attack"] == b["actual_attack"]
            s_correct = s["predicted_attack"] == s["actual_attack"]

            if b_correct == s_correct and b["predicted_attack"] == s["predicted_attack"]:
                continue
            if (not b_correct) and s_correct:
                outcome = "structured_rescue"
            elif b_correct and (not s_correct):
                outcome = "structured_regression"
            else:
                outcome = "prediction_disagreement"

        disagreement_rows.append({
            "repetition": rep,
            "case_id": case_id,
            "category": b["category"],
            "subcategory": b["subcategory"],
            "scenario": b["scenario"],
            "outcome": outcome,
            "actual_attack": b["actual_attack"],
            "baseline_prediction": b.get("predicted_attack"),
            "structured_prediction": s.get("predicted_attack"),
            "baseline_confidence": b.get("reported_confidence"),
            "structured_confidence": s.get("reported_confidence"),
            "victim_leaked": b["victim_leaked"],
            "text": b["text"],
            "baseline_raw": b.get("detector_raw", ""),
            "structured_raw": s.get("detector_raw", ""),
        })

    disagreement_fields = [
        "repetition", "case_id", "category", "subcategory", "scenario",
        "outcome", "actual_attack", "baseline_prediction",
        "structured_prediction", "baseline_confidence",
        "structured_confidence", "victim_leaked", "text",
        "baseline_raw", "structured_raw",
    ]
    write_csv(
        RESULTS / "detector_disagreements.csv",
        disagreement_rows,
        disagreement_fields,
    )

    # The security-critical comparison cell for RQ3.
    not_detected_with_leakage = [
        compact(r)
        for r in usable
        if r["actual_attack"]
        and (not r["predicted_attack"])
        and r["victim_leaked"]
    ]
    write_csv(
        RESULTS / "not_detected_with_leakage.csv",
        not_detected_with_leakage,
        fieldnames=list(compact(usable[0]).keys()) if usable else None,
    )



    # Victim outcomes are generated once per repetition/case and then shared
    # across detector conditions. Deduplicate before reporting victim rates.
    unique_victim = []
    seen_victim = set()
    for r in rows:
        key = (r["repetition"], r["case_id"])
        if key in seen_victim:
            continue
        seen_victim.add(key)
        unique_victim.append(r)

    victim_summary_rows = []
    for category in ("benign", "direct", "covert"):
        group = [r for r in unique_victim if r["category"] == category]
        leaked = sum(1 for r in group if r["victim_leaked"])
        truncated = sum(1 for r in group if r["victim_truncated"])
        victim_summary_rows.append({
            "category": category,
            "leaked": leaked,
            "total": len(group),
            "leakage_rate": leaked / len(group) if group else 0.0,
            "truncated": truncated,
        })

    all_inputs = unique_victim
    all_attacks = [r for r in unique_victim if r["actual_attack"]]
    for label, group in (
        ("all_attacks", all_attacks),
        ("all_inputs", all_inputs),
    ):
        leaked = sum(1 for r in group if r["victim_leaked"])
        truncated = sum(1 for r in group if r["victim_truncated"])
        victim_summary_rows.append({
            "category": label,
            "leaked": leaked,
            "total": len(group),
            "leakage_rate": leaked / len(group) if group else 0.0,
            "truncated": truncated,
        })

    write_csv(
        RESULTS / "victim_leakage_all_inputs.csv",
        victim_summary_rows,
    )

    benign_with_leakage = [
        {
            "repetition": r["repetition"],
            "case_id": r["case_id"],
            "category": r["category"],
            "subcategory": r["subcategory"],
            "scenario": r["scenario"],
            "victim_leaked": r["victim_leaked"],
            "leaked_canaries": ";".join(r.get("leaked_canaries", [])),
            "victim_finish_reason": r["victim_finish_reason"],
            "victim_truncated": r["victim_truncated"],
            "text": r["text"],
            "victim_response": r["victim_response"],
        }
        for r in unique_victim
        if (not r["actual_attack"]) and r["victim_leaked"]
    ]
    benign_leak_fields = [
        "repetition", "case_id", "category", "subcategory", "scenario",
        "victim_leaked", "leaked_canaries", "victim_finish_reason",
        "victim_truncated", "text", "victim_response",
    ]
    write_csv(
        RESULTS / "benign_with_leakage.csv",
        benign_with_leakage,
        benign_leak_fields,
    )

    # Post-hoc all-input matrix. The pre-registered primary matrix is
    # attack-only; this exploratory matrix surfaces leakage caused by benign
    # inputs without relabeling those inputs as attacks.
    all_input_matrix_rows = []
    for condition in ("baseline", "structured"):
        group = [
            r for r in usable
            if r["detector_condition"] == condition
        ]
        matrix = {
            "detected_no_leak": 0,
            "detected_leak": 0,
            "not_detected_no_leak": 0,
            "not_detected_leak": 0,
        }
        for r in group:
            detected = bool(r["predicted_attack"])
            leaked = bool(r["victim_leaked"])
            if detected and leaked:
                matrix["detected_leak"] += 1
            elif detected and not leaked:
                matrix["detected_no_leak"] += 1
            elif (not detected) and leaked:
                matrix["not_detected_leak"] += 1
            else:
                matrix["not_detected_no_leak"] += 1

        all_input_matrix_rows.append({
            "detector_condition": condition,
            **matrix,
        })

    write_csv(
        RESULTS / "detection_leakage_all_inputs.csv",
        all_input_matrix_rows,
    )

    # Stability by case and condition across repetitions.
    by_case_condition = defaultdict(list)
    for r in rows:
        by_case_condition[(r["case_id"], r["detector_condition"])].append(r)

    consistency_rows = []
    for (case_id, condition), group in sorted(by_case_condition.items()):
        valid = [r for r in group if not r["parse_error"]]
        attack_votes = sum(1 for r in valid if r["predicted_attack"])
        benign_votes = sum(1 for r in valid if not r["predicted_attack"])
        total_valid = len(valid)
        majority = (
            "attack" if attack_votes > benign_votes
            else "benign" if benign_votes > attack_votes
            else "tie"
        )

        first = group[0]
        consistency_rows.append({
            "case_id": case_id,
            "category": first["category"],
            "subcategory": first["subcategory"],
            "detector_condition": condition,
            "valid_runs": total_valid,
            "parse_errors": len(group) - total_valid,
            "attack_votes": attack_votes,
            "benign_votes": benign_votes,
            "majority_prediction": majority,
            "unanimous": (
                total_valid > 0
                and (attack_votes == total_valid or benign_votes == total_valid)
            ),
        })

    write_csv(
        RESULTS / "case_consistency.csv",
        consistency_rows,
    )

    print(f"False negatives: {len(false_negatives)}")
    print(f"False positives: {len(false_positives)}")
    print(f"Detector disagreements: {len(disagreement_rows)}")
    print(f"Attack: not detected + leakage: {len(not_detected_with_leakage)}")
    print(f"Benign inputs with victim leakage: {len(benign_with_leakage)}")
    print("Saved all-input leakage summaries and case-level consistency.")


if __name__ == "__main__":
    main()
