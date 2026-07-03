import json
import tempfile
import unittest
from pathlib import Path

from adds_sim import (
    TrackLapSection,
    build_reference_track_lap_scenario,
    reference_track_lap_sections,
    run_track_lap_comparison,
    write_track_lap_report,
)


class Phase8TrackLapTests(unittest.TestCase):
    def test_builds_distance_limited_reference_track_lap(self) -> None:
        scenario = build_reference_track_lap_scenario()
        sections = reference_track_lap_sections()

        self.assertEqual(scenario.scenario_id, "adds_reference_circuit_v1")
        self.assertEqual(scenario.distance_limit, 3_000.0)
        self.assertGreater(scenario.time_limit, sum(section.duration for section in sections))
        self.assertAlmostEqual(scenario.target_speed_profile.value_at(0.0), scenario.initial_speed)
        self.assertGreater(scenario.target_speed_profile.value_at(35.0), scenario.target_speed_profile.value_at(20.0))

    def test_rejects_invalid_track_lap_sections(self) -> None:
        with self.assertRaises(ValueError):
            build_reference_track_lap_scenario(
                sections=(TrackLapSection("invalid", duration=0.0, target_speed_end=30.0),)
            )

    def test_runs_offline_optimized_track_lap_comparison(self) -> None:
        report = run_track_lap_comparison("offline_optimized")
        comparison = report.comparison

        self.assertEqual(report.schema_version, "1.0")
        self.assertEqual(report.adds_controller_kind, "offline_optimized")
        self.assertEqual(comparison.conventional_result.termination_reason, "distance_limit")
        self.assertEqual(comparison.adds_result.termination_reason, "distance_limit")
        self.assertLessEqual(comparison.deltas["relative_fuel_change"], -1.0)
        self.assertLessEqual(comparison.deltas["delta_rms_speed_error"] * 3.6, 1.0)
        self.assertGreater(comparison.adds_summary["mode_transition_count"], 0)
        self.assertEqual(comparison.adds_summary["safety_override_count"], 0)
        self.assertGreater(
            next(stat for stat in report.stats if stat.label == "Decoupled duration").adds_value,
            0.0,
        )

    def test_writes_track_lap_report_and_trajectories(self) -> None:
        report = run_track_lap_comparison("rule_based")

        with tempfile.TemporaryDirectory() as tmp:
            json_path, stats_path, conventional_path, adds_path = write_track_lap_report(Path(tmp), report)

            self.assertTrue(json_path.exists())
            self.assertTrue(stats_path.exists())
            self.assertTrue(conventional_path.exists())
            self.assertTrue(adds_path.exists())

            data = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(data["schema_version"], "1.0")
            self.assertEqual(data["scenario"]["distance_limit"], 3_000.0)
            self.assertEqual(data["adds_controller_kind"], "rule_based")
            self.assertGreater(len(data["sections"]), 0)
            self.assertIn("relative_fuel_change", data["deltas"])
            self.assertGreater(len(stats_path.read_text(encoding="utf-8").splitlines()), 1)
            self.assertGreater(len(conventional_path.read_text(encoding="utf-8").splitlines()), 1)
            self.assertGreater(len(adds_path.read_text(encoding="utf-8").splitlines()), 1)


if __name__ == "__main__":
    unittest.main()
