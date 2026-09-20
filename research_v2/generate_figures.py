"""Generate compact figures for the admissions research brief.

This script only works after real experiment outputs exist.

Usage:
    python -m research_v2.generate_figures

Outputs:
    results/research_v2/figures/
"""

import csv
from pathlib import Path

import matplotlib.pyplot as plt

RESULTS = Path("results/research_v2")
FIG_DIR = RESULTS / "figures"


def read_csv(path: Path):
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def require(path: Path):
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run the corresponding experiment first."
        )


def plot_recall_by_category():
    path = RESULTS / "benchmark_category_summary.csv"
    require(path)
    rows = read_csv(path)

    categories = ["direct", "covert"]
    conditions = ["baseline", "structured"]

    values = {
        cond: [
            float(next(
                r["recall"]
                for r in rows
                if r["detector_condition"] == cond and r["category"] == category
            ))
            for category in categories
        ]
        for cond in conditions
    }

    x = list(range(len(categories)))
    width = 0.36

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.bar([i - width / 2 for i in x], values["baseline"], width, label="Baseline")
    ax.bar([i + width / 2 for i in x], values["structured"], width, label="Structured")
    ax.set_xticks(x)
    ax.set_xticklabels(["Direct attacks", "Covert attacks"])
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Recall")
    ax.set_title("Detection Recall by Attack Category")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG_DIR / "recall_by_attack_category.png", dpi=220)
    plt.close(fig)


def plot_detection_leakage_matrix():
    path = RESULTS / "detection_leakage_matrix.csv"
    require(path)
    rows = read_csv(path)

    for row in rows:
        condition = row["detector_condition"]
        matrix = [
            [
                int(row["detected_no_leak"]),
                int(row["detected_leak"]),
            ],
            [
                int(row["not_detected_no_leak"]),
                int(row["not_detected_leak"]),
            ],
        ]

        fig, ax = plt.subplots(figsize=(5.5, 4.5))
        image = ax.imshow(matrix)
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["No leakage", "Leakage"])
        ax.set_yticks([0, 1])
        ax.set_yticklabels(["Detected", "Not detected"])
        ax.set_title(f"Detection × Leakage — {condition.title()}")

        for i in range(2):
            for j in range(2):
                ax.text(j, i, str(matrix[i][j]), ha="center", va="center")

        fig.colorbar(image, ax=ax)
        fig.tight_layout()
        fig.savefig(
            FIG_DIR / f"detection_leakage_{condition}.png",
            dpi=220,
        )
        plt.close(fig)


def plot_adaptive_funnel():
    path = RESULTS / "adaptive_summary.csv"
    if not path.exists():
        return

    row = read_csv(path)[0]
    labels = [
        "Evasion",
        "Objective\npreserved",
        "Leakage",
        "True attack\nsuccess",
    ]
    values = [
        float(row["evasion_rate"]),
        float(row["objective_preservation_rate"]),
        float(row["leakage_rate"]),
        float(row["true_attack_success_rate"]),
    ]

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.bar(labels, values)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Rate")
    ax.set_title("Adaptive Attack Outcome Rates")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "adaptive_outcomes.png", dpi=220)
    plt.close(fig)


def main():
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    plot_recall_by_category()
    plot_detection_leakage_matrix()
    plot_adaptive_funnel()
    print(f"Figures saved to {FIG_DIR}")


if __name__ == "__main__":
    main()
