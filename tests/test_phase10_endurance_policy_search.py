import json
import tempfile
import unittest
from pathlib import Path

from adds_sim import (
    default_endurance_policy_candidates,
    run_endurance_policy_search,
    write_endurance_policy_search_report,
)


class Phase10EndurancePolicySearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = run_endurance_policy_search()

    def test_search_uses_deterministic_candidate_grid(self) -> None:
        candidates = default_endurance_policy_candidates()

        self.assertEqual(len(candidates), 60)
        self.assertEqual(candidates[0].candidate_id, "E01")
        self.assertEqual(candidates[-1].candidate_id, "E60")
        self.assertEqual(len(self.report.rows), len(candidates))

    def test_current_grid_does_not_promote_fuel_saving_with_lap_loss(self) -> None:
        self.assertFalse(self.report.promotion_passed)
        self.assertIsNone(self.report.best_candidate)
        self.assertTrue(
            any(row.verdict == "FUEL_SAVING_WITH_LAP_LOSS" for row in self.report.rows)
        )
        self.assertTrue(
            any(row.verdict == "NEUTRAL_NO_BENEFIT" for row in self.report.rows)
        )
        self.assertFalse(any(row.promotion_eligible for row in self.report.rows))
        self.assertIn("No searched candidate", self.report.promotion_reasons[0])

    def test_recommendations_identify_best_saving_and_non_losing_guardrail(self) -> None:
        actions = " ".join(self.report.recommended_next_actions)

        self.assertIn("Do not promote", actions)
        self.assertIn("best fuel-saving candidate", actions)
        self.assertIn("least damaging fuel-saving candidate", actions)
        self.assertIn("best non-losing candidate", actions)

    def test_writes_endurance_policy_search_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            json_path, csv_path = write_endurance_policy_search_report(
                Path(tmp),
                self.report,
            )

            self.assertTrue(json_path.exists())
            self.assertTrue(csv_path.exists())
            data = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(data["schema_version"], "1.0")
            self.assertFalse(data["promotion_passed"])
            self.assertEqual(len(data["rows"]), 60)
            self.assertGreater(len(csv_path.read_text(encoding="utf-8").splitlines()), 1)


if __name__ == "__main__":
    unittest.main()
