import json
import tempfile
import unittest
from pathlib import Path

from adds_sim import (
    TrackLapBalancedADDSController,
    build_track_lap_sector_analysis,
    default_track_lap_policy_candidates,
    run_track_lap_comparison,
    run_track_lap_policy_search,
    write_track_lap_policy_search_report,
)


class Phase12TrackLapPolicySearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = run_track_lap_policy_search()

    def test_search_uses_deterministic_candidate_grid(self) -> None:
        candidates = default_track_lap_policy_candidates()

        self.assertEqual(len(candidates), 36)
        self.assertEqual(candidates[0].candidate_id, "T01")
        self.assertEqual(candidates[-1].candidate_id, "T36")
        self.assertEqual(len(self.report.rows), len(candidates))

    def test_promotes_track_lap_balanced_candidate(self) -> None:
        report = self.report

        self.assertTrue(report.promotion_passed)
        self.assertIsNotNone(report.best_candidate)
        self.assertEqual(report.best_candidate.candidate_id, "T10")
        self.assertAlmostEqual(report.best_candidate.coast_speed_margin, 0.40)
        self.assertAlmostEqual(report.best_candidate.reconnect_speed_margin, 0.05)
        self.assertAlmostEqual(report.best_candidate.minimum_target_speed_drop, 0.25)
        self.assertTrue(report.rows[0].promotion_eligible)
        self.assertLess(report.rows[0].delta_lap_time, report.baseline_delta_lap_time)
        self.assertLess(report.rows[0].worst_time_loss_delta, report.baseline_worst_sector_delta)
        self.assertLessEqual(report.rows[0].relative_fuel_change, -1.0)

    def test_track_lap_balanced_controller_matches_promoted_candidate(self) -> None:
        controller = TrackLapBalancedADDSController(gear=5)
        self.assertAlmostEqual(controller.coast_speed_margin, self.report.best_candidate.coast_speed_margin)
        self.assertAlmostEqual(controller.reconnect_speed_margin, self.report.best_candidate.reconnect_speed_margin)
        self.assertAlmostEqual(controller.minimum_target_speed_drop, self.report.best_candidate.minimum_target_speed_drop)

    def test_track_lap_balanced_variant_reduces_sector_penalty(self) -> None:
        offline = run_track_lap_comparison("offline_optimized")
        balanced = run_track_lap_comparison("track_lap_balanced")
        offline_analysis = build_track_lap_sector_analysis(offline)
        balanced_analysis = build_track_lap_sector_analysis(balanced)

        self.assertLess(
            balanced.comparison.deltas["delta_travel_time"],
            offline.comparison.deltas["delta_travel_time"],
        )
        self.assertLessEqual(balanced.comparison.deltas["relative_fuel_change"], -1.0)
        self.assertLess(
            balanced_analysis.worst_time_loss_sector.delta_time,
            offline_analysis.worst_time_loss_sector.delta_time,
        )

    def test_writes_track_lap_policy_search_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            json_path, csv_path = write_track_lap_policy_search_report(Path(tmp), self.report)

            self.assertTrue(json_path.exists())
            self.assertTrue(csv_path.exists())
            data = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(data["schema_version"], "1.0")
            self.assertTrue(data["promotion_passed"])
            self.assertEqual(data["best_candidate"]["candidate_id"], "T10")
            self.assertEqual(len(data["rows"]), len(self.report.rows))
            self.assertGreater(len(csv_path.read_text(encoding="utf-8").splitlines()), 1)


if __name__ == "__main__":
    unittest.main()
