"""Summarize adaptive results after objective-preservation coding.

Workflow:
1. Run run_adaptive_experiment.py.
2. Copy adaptive_raw.jsonl to adaptive_coded.jsonl.
3. For every row, replace objective_preserved=null with true/false using the
   pre-defined rubric.
4. Run this script.

Usage:
    python -m research_v2.summarize_adaptive
"""

import csv
import json
from collections import defaultdict
from pathlib import Path

from research_v2.metrics import adaptive_security_metrics, detection_leakage_matrix

IN_PATH = Path("results/research_v2/adaptive_coded.jsonl")
OUT_DIR = Path("results/research_v2")


def write_csv(path: Path, rows):
    if not rows:
        raise ValueError(f"No rows available for {path}")
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main():
    if not IN_PATH.exists():
        raise FileNotFoundError(
            f"{IN_PATH} not found. Copy adaptive_raw.jsonl to adaptive_coded.jsonl "
            "and code objective_preserved first."
        )

    rows = []
    parse_error_count = 0

    with IN_PATH.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)

            if row.get("objective_preserved") is None:
                raise ValueError(
                    "Uncoded objective_preserved in "
                    f"seed={row.get('seed_id')} round={row.get('round')}."
                )

            # A detector parse error is missing data, not successful evasion.
            if row.get("detected") is None:
                parse_error_count += 1
                continue

            row["is_attack_seed"] = True
            rows.append(row)

    if not rows:
        raise ValueError("No usable adaptive rows after excluding parse errors.")

    overall = adaptive_security_metrics(rows)
    overall["parse_errors_excluded"] = parse_error_count

    matrix = detection_leakage_matrix(rows)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    write_csv(
        OUT_DIR / "adaptive_summary.csv",
        [overall],
    )

    write_csv(
        OUT_DIR / "adaptive_detection_leakage_matrix.csv",
        [matrix],
    )

    # Per-round outcomes make the adaptation trajectory visible.
    by_round = defaultdict(list)
    for row in rows:
        by_round[int(row["round"])].append(row)

    round_rows = []
    for round_id in sorted(by_round):
        metrics = adaptive_security_metrics(by_round[round_id])
        round_rows.append({
            "round": round_id,
            **metrics,
        })

    write_csv(
        OUT_DIR / "adaptive_round_summary.csv",
        round_rows,
    )

    # Per-seed summary is useful for failure-case selection in the portfolio.
    by_seed = defaultdict(list)
    for row in rows:
        by_seed[row["seed_id"]].append(row)

    seed_rows = []
    for seed_id in sorted(by_seed):
        seed_group = sorted(by_seed[seed_id], key=lambda r: int(r["round"]))
        metrics = adaptive_security_metrics(seed_group)
        seed_rows.append({
            "seed_id": seed_id,
            "scenario": seed_group[0]["scenario"],
            "objective_id": seed_group[0]["objective_id"],
            **metrics,
        })

    write_csv(
        OUT_DIR / "adaptive_seed_summary.csv",
        seed_rows,
    )

    print("Adaptive security metrics:")
    print(json.dumps(overall, indent=2))
    print("Detection x leakage matrix:")
    print(json.dumps(matrix, indent=2))
    print("Per-round and per-seed summaries were also saved.")


if __name__ == "__main__":
    main()
