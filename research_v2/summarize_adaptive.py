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
from pathlib import Path

from research_v2.metrics import adaptive_security_metrics, detection_leakage_matrix

IN_PATH = Path("results/research_v2/adaptive_coded.jsonl")
OUT_DIR = Path("results/research_v2")


def main():
    if not IN_PATH.exists():
        raise FileNotFoundError(
            f"{IN_PATH} not found. Copy adaptive_raw.jsonl to adaptive_coded.jsonl "
            "and code objective_preserved first."
        )

    rows = []
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
                continue

            row["is_attack_seed"] = True
            rows.append(row)

    metrics = adaptive_security_metrics(rows)
    matrix = detection_leakage_matrix(rows)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with (OUT_DIR / "adaptive_summary.csv").open(
        "w", newline="", encoding="utf-8"
    ) as f:
        writer = csv.DictWriter(f, fieldnames=list(metrics.keys()))
        writer.writeheader()
        writer.writerow(metrics)

    with (OUT_DIR / "adaptive_detection_leakage_matrix.csv").open(
        "w", newline="", encoding="utf-8"
    ) as f:
        writer = csv.DictWriter(f, fieldnames=list(matrix.keys()))
        writer.writeheader()
        writer.writerow(matrix)

    print("Adaptive security metrics:")
    print(json.dumps(metrics, indent=2))
    print("Detection x leakage matrix:")
    print(json.dumps(matrix, indent=2))


if __name__ == "__main__":
    main()
