import json
import tempfile
import unittest
from pathlib import Path

from adds_sim.policy_search import (
    default_policy_candidates,
    run_offline_policy_search,
    write_policy_search_report,
)


class Phase5PolicySearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = run_offline_policy_search()

    def test_search_uses_fixed_grid_and_selects_after_validation(self) -> None:
        self.assertEqual(len(default_policy_candidates()), 6)
        self.assertEqual(len(self.report.train_ranking), 6)
        self.assertIsNotNone(self.report.selected_candidate)
        self.assertEqual(self.report.selected_candidate.candidate_id, "C03")
        self.assertTrue(self.report.validation_results)

    def test_frozen_test_promotes_only_meaningful_constrained_improvement(self) -> None:
        self.assertTrue(self.report.promotion_passed)
        self.assertTrue(all(result.passes_stage_gates for result in self.report.test_results))
        self.assertTrue(all(result.passes_stage_gates for result in self.report.stress_results))
        self.assertTrue(
            any(
                result.relative_fuel_change_vs_rule_based <= -0.5
                for result in self.report.test_results
            )
        )

    def test_writes_reproducible_policy_search_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = write_policy_search_report(
                Path(tmp) / "policy_search_report.json",
                self.report,
            )
            data = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(data["schema_version"], "1.0")
        self.assertEqual(data["selected_candidate"]["candidate_id"], "C03")
        self.assertTrue(data["promotion_passed"])
        self.assertTrue(data["test_results"])
        self.assertTrue(data["stress_results"])


if __name__ == "__main__":
    unittest.main()
