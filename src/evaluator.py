"""
Evaluator — records results and computes F1, Precision, Recall, Accuracy.
"""

import json
import pandas as pd
from datetime import datetime


class Evaluator:
    def __init__(self):
        self.results = []

    def add_result(self, attack_text: str, prediction: dict, ground_truth: bool = True):
        self.results.append({
            "timestamp":            datetime.now().isoformat(),
            "input":                attack_text,
            "predicted_attack":     prediction.get("is_attack", False),
            "actual_attack":        ground_truth,
            "attack_type":          prediction.get("attack_type", "unknown"),
            "confidence":           prediction.get("confidence", 0.0),
            "severity":             prediction.get("severity", "none"),
            "explanation":          prediction.get("explanation", ""),
            "mitre_technique_id":   prediction.get("mitre_technique_id", "none"),
            "mitre_technique_name": prediction.get("mitre_technique_name", "none"),
            "indicators":           prediction.get("indicators", [])
        })

    def calculate_metrics(self) -> dict:
        if not self.results:
            return {}

        y_true = [r["actual_attack"] for r in self.results]
        y_pred = [r["predicted_attack"] for r in self.results]

        tp = sum(1 for t, p in zip(y_true, y_pred) if t and p)
        fp = sum(1 for t, p in zip(y_true, y_pred) if not t and p)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t and not p)
        tn = sum(1 for t, p in zip(y_true, y_pred) if not t and not p)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1        = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        accuracy  = (tp + tn) / len(y_true) if y_true else 0.0

        return {
            "accuracy":  round(accuracy, 4),
            "precision": round(precision, 4),
            "recall":    round(recall, 4),
            "f1_score":  round(f1, 4),
            "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "total": len(self.results)
        }

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self.results)

    def save(self, path: str = "data/results/results.json"):
        import os
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "metrics": self.calculate_metrics(),
                "results": self.results
            }, f, ensure_ascii=False, indent=2)
        print(f"Results saved to {path}")
