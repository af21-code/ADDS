import csv
import json
import tempfile
import unittest
from pathlib import Path

from adds_sim import (
    ParameterPerturbation,
    apply_perturbation_to_config,
    apply_perturbation_to_scenario,
    default_perturbations,
    default_simulation_config,
    phase4_scenario_catalog,
    run_robustness_evaluation,
    write_robustness_report,
)


class Phase6RobustnessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = default_simulation_config()
        self.entries = phase4_scenario_catalog()

    def test_perturbation_modifies_config_and_scenario(self) -> None:
        perturbation = ParameterPerturbation(
            name="test_shift",
            mass_scale=1.10,
            drag_scale=1.20,
            rolling_resistance_scale=1.30,
            tire_friction_scale=0.80,
            grade_offset=0.01,
        )

        config = apply_perturbation_to_config(self.config, perturbation)
        scenario = apply_perturbation_to_scenario(self.entries[0].scenario, perturbation)

        self.assertAlmostEqual(config.vehicle.mass, self.config.vehicle.mass * 1.10)
        self.assertAlmostEqual(config.vehicle.drag_coefficient, self.config.vehicle.drag_coefficient * 1.20)
        self.assertAlmostEqual(
            config.vehicle.rolling_resistance_coefficient,
            self.config.vehicle.rolling_resistance_coefficient * 1.30,
        )
        self.assertAlmostEqual(
            config.environment.tire_friction_coefficient,
            self.config.environment.tire_friction_coefficient * 0.80,
        )
        self.assertAlmostEqual(scenario.grade_profile.value_at(0.0), self.entries[0].scenario.grade_profile.value_at(0.0) + 0.01)

    def test_robustness_evaluation_completes_expected_runs(self) -> None:
        perturbations = default_perturbations()[:3]
        report = run_robustness_evaluation(entries=self.entries[:2], perturbations=perturbations)

        self.assertEqual(len(report.runs), 6)
        self.assertTrue(report.completed_successfully)
        self.assertEqual(report.constraint_regression_count, 0)
        self.assertGreaterEqual(report.max_relative_fuel_change, report.min_relative_fuel_change)

    def test_writes_json_and_csv_report(self) -> None:
        report = run_robustness_evaluation(entries=self.entries[:1], perturbations=default_perturbations()[:2])

        with tempfile.TemporaryDirectory() as tmp:
            json_path, csv_path = write_robustness_report(Path(tmp), report)

            self.assertTrue(json_path.exists())
            self.assertTrue(csv_path.exists())

            data = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(data["schema_version"], "1.0")
            self.assertEqual(len(data["runs"]), 2)

            with csv_path.open(newline="", encoding="utf-8") as file:
                rows = list(csv.DictReader(file))
            self.assertEqual(len(rows), 2)
            self.assertIn("relative_fuel_change", rows[0])


if __name__ == "__main__":
    unittest.main()
