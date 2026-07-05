import json
import tempfile
import unittest
from pathlib import Path

from adds_sim import (
    EnduranceStrategyConfig,
    run_endurance_strategy,
    write_endurance_strategy_report,
)


class Phase9EnduranceStrategyTests(unittest.TestCase):
    def test_default_endurance_strategy_reports_fuel_saving_with_lap_loss(self) -> None:
        report = run_endurance_strategy()

        self.assertEqual(report.schema_version, "1.0")
        self.assertEqual(report.config.race_duration_hours, 24.0)
        self.assertGreater(report.conventional.completed_laps, 0)
        self.assertGreater(report.adds.completed_laps, 0)
        self.assertLess(report.deltas["relative_fuel_change"], 0.0)
        self.assertEqual(report.verdict, "FUEL_SAVING_WITH_LAP_LOSS")
        self.assertLess(report.deltas["delta_completed_laps"], 0)
        self.assertIsNotNone(report.thresholds.minimum_reference_stint_laps_for_one_extra_lap)

    def test_threshold_identifies_when_adds_gets_extra_stint_lap(self) -> None:
        report = run_endurance_strategy(
            EnduranceStrategyConfig(reference_stint_laps=94)
        )

        self.assertTrue(report.thresholds.adds_gains_stint_lap_at_current_tank)
        self.assertGreater(report.adds.stint_laps, report.conventional.stint_laps)
        self.assertEqual(report.verdict, "FUEL_SAVING_WITH_LAP_LOSS")

    def test_rejects_invalid_strategy_configuration(self) -> None:
        with self.assertRaises(ValueError):
            run_endurance_strategy(EnduranceStrategyConfig(race_duration_hours=0.0))
        with self.assertRaises(ValueError):
            run_endurance_strategy(EnduranceStrategyConfig(reference_stint_laps=0))
        with self.assertRaises(ValueError):
            run_endurance_strategy(EnduranceStrategyConfig(pit_stop_loss_seconds=-1.0))

    def test_writes_endurance_strategy_artifacts(self) -> None:
        report = run_endurance_strategy(EnduranceStrategyConfig(race_duration_hours=1.0))

        with tempfile.TemporaryDirectory() as tmp:
            json_path, csv_path = write_endurance_strategy_report(Path(tmp), report)

            self.assertTrue(json_path.exists())
            self.assertTrue(csv_path.exists())
            data = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(data["schema_version"], "1.0")
            self.assertEqual(data["verdict"], report.verdict)
            self.assertIn("thresholds", data)
            self.assertGreater(len(csv_path.read_text(encoding="utf-8").splitlines()), 1)


if __name__ == "__main__":
    unittest.main()
