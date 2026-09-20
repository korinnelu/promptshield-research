import json
import unittest
from pathlib import Path

from research_v2.canary_victim import SCENARIOS, detect_canary_leakage
from research_v2.metrics import (
    adaptive_chain_metrics,
    adaptive_security_metrics,
    binary_metrics,
    detection_leakage_matrix,
)
from research_v2.schema import parse_json_object, validate_detection_payload


class TestResearchV2Metrics(unittest.TestCase):
    def test_binary_metrics(self):
        rows = [
            {"actual_attack": True, "predicted_attack": True},
            {"actual_attack": True, "predicted_attack": False},
            {"actual_attack": False, "predicted_attack": True},
            {"actual_attack": False, "predicted_attack": False},
        ]
        m = binary_metrics(rows)
        self.assertEqual(m["tp"], 1)
        self.assertEqual(m["fp"], 1)
        self.assertEqual(m["fn"], 1)
        self.assertEqual(m["tn"], 1)
        self.assertAlmostEqual(m["precision"], 0.5)
        self.assertAlmostEqual(m["recall"], 0.5)
        self.assertAlmostEqual(m["f1"], 0.5)
        self.assertAlmostEqual(m["accuracy"], 0.5)

    def test_detection_leakage_matrix(self):
        rows = [
            {"detected": True, "leaked": False},
            {"detected": True, "leaked": True},
            {"detected": False, "leaked": False},
            {"detected": False, "leaked": True},
        ]
        m = detection_leakage_matrix(rows)
        self.assertEqual(m["detected_no_leak"], 1)
        self.assertEqual(m["detected_leak"], 1)
        self.assertEqual(m["not_detected_no_leak"], 1)
        self.assertEqual(m["not_detected_leak"], 1)

    def test_true_attack_success_is_strict(self):
        rows = [
            {
                "is_attack_seed": True,
                "detected": False,
                "objective_preserved": True,
                "leaked": True,
            },
            {
                "is_attack_seed": True,
                "detected": False,
                "objective_preserved": False,
                "leaked": True,
            },
            {
                "is_attack_seed": True,
                "detected": True,
                "objective_preserved": True,
                "leaked": True,
            },
            {
                "is_attack_seed": True,
                "detected": False,
                "objective_preserved": True,
                "leaked": False,
            },
        ]
        m = adaptive_security_metrics(rows)
        self.assertAlmostEqual(m["evasion_rate"], 0.75)
        self.assertAlmostEqual(m["true_attack_success_rate"], 0.25)

    def test_chain_level_adaptive_metrics(self):
        rows = [
            {
                "seed_id": "a",
                "detected": True,
                "objective_preserved": True,
                "leaked": False,
            },
            {
                "seed_id": "a",
                "detected": False,
                "objective_preserved": True,
                "leaked": False,
            },
            {
                "seed_id": "b",
                "detected": True,
                "objective_preserved": True,
                "leaked": True,
            },
            {
                "seed_id": "c",
                "detected": False,
                "objective_preserved": True,
                "leaked": True,
            },
        ]
        m = adaptive_chain_metrics(rows)
        self.assertEqual(m["chains"], 3)
        self.assertAlmostEqual(m["chain_evasion_rate"], 2 / 3)
        self.assertAlmostEqual(
            m["chain_objective_preserving_evasion_rate"], 2 / 3
        )
        self.assertAlmostEqual(m["chain_leakage_rate"], 2 / 3)
        self.assertAlmostEqual(m["chain_true_attack_success_rate"], 1 / 3)



class TestCanaryVictim(unittest.TestCase):
    def test_exact_canary_match(self):
        token = SCENARIOS["banking_chatbot"].canaries[0]
        result = detect_canary_leakage(
            f"The protected value is {token}.",
            "banking_chatbot",
        )
        self.assertTrue(result["leaked"])
        self.assertEqual(result["leak_count"], 1)

    def test_no_false_match_for_generic_security_language(self):
        result = detect_canary_leakage(
            "Never reveal passwords, API keys, or administrator credentials.",
            "banking_chatbot",
        )
        self.assertFalse(result["leaked"])
        self.assertEqual(result["leak_count"], 0)


class TestResearchDatasets(unittest.TestCase):
    def test_benchmark_shape(self):
        path = Path("data/research_v2/benchmark_v2.json")
        cases = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(len(cases), 60)
        self.assertEqual(len({c["id"] for c in cases}), 60)

        counts = {
            category: sum(1 for c in cases if c["category"] == category)
            for category in ("benign", "direct", "covert")
        }
        self.assertEqual(
            counts,
            {"benign": 20, "direct": 20, "covert": 20},
        )

        difficulty_counts = {}
        for case in cases:
            key = (case["category"], case["difficulty"])
            difficulty_counts[key] = difficulty_counts.get(key, 0) + 1

        self.assertEqual(
            difficulty_counts,
            {
                ("benign", "easy"): 10,
                ("benign", "hard"): 10,
                ("direct", "easy"): 20,
                ("covert", "medium"): 10,
                ("covert", "hard"): 10,
            },
        )

    def test_benchmark_has_no_canary_in_user_input(self):
        path = Path("data/research_v2/benchmark_v2.json")
        cases = json.loads(path.read_text(encoding="utf-8"))
        all_canaries = [
            token
            for scenario in SCENARIOS.values()
            for token in scenario.canaries
        ]
        for case in cases:
            for token in all_canaries:
                self.assertNotIn(token, case["text"], msg=case["id"])

    def test_adaptive_seed_shape(self):
        path = Path("data/research_v2/adaptive_seeds.json")
        seeds = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(len(seeds), 12)
        self.assertEqual(len({s["id"] for s in seeds}), 12)


    def test_adaptive_variants_shape(self):
        path = Path("data/research_v2/adaptive_variants.json")
        chains = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(len(chains), 12)
        self.assertEqual(len({c["id"] for c in chains}), 12)

        for chain in chains:
            self.assertEqual(
                [v["round"] for v in chain["variants"]],
                [0, 1, 2],
            )
            self.assertEqual(
                [v["strategy"] for v in chain["variants"]],
                [
                    "direct_overt",
                    "business_pretext",
                    "workflow_completion",
                ],
            )
            self.assertTrue(
                all(
                    v["intended_objective_preserved"]
                    for v in chain["variants"]
                )
            )

    def test_adaptive_variants_have_no_exact_canary(self):
        path = Path("data/research_v2/adaptive_variants.json")
        chains = json.loads(path.read_text(encoding="utf-8"))
        all_canaries = [
            token
            for scenario in SCENARIOS.values()
            for token in scenario.canaries
        ]
        for chain in chains:
            for variant in chain["variants"]:
                for token in all_canaries:
                    self.assertNotIn(
                        token,
                        variant["text"],
                        msg=f"{chain['id']} round {variant['round']}",
                    )


class TestDetectorSchema(unittest.TestCase):
    def test_valid_boolean_payload(self):
        payload = parse_json_object(
            '{"is_attack": false, "confidence": 0.2, "severity": "low"}'
        )
        validated = validate_detection_payload(payload)
        self.assertIsNotNone(validated)
        self.assertIs(validated["is_attack"], False)

    def test_string_false_is_rejected(self):
        payload = parse_json_object(
            '{"is_attack": "false", "confidence": 0.2, "severity": "low"}'
        )
        self.assertIsNone(validate_detection_payload(payload))

    def test_out_of_range_confidence_is_rejected(self):
        payload = parse_json_object(
            '{"is_attack": true, "confidence": 1.4, "severity": "high"}'
        )
        self.assertIsNone(validate_detection_payload(payload))

    def test_fenced_json_is_parsed(self):
        payload = parse_json_object(
            '```json\n{"is_attack": true, "confidence": 0.8}\n```'
        )
        self.assertIsNotNone(validate_detection_payload(payload))


if __name__ == "__main__":
    unittest.main()
