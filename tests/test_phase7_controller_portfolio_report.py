import csv
import json
import tempfile
import unittest
from pathlib import Path

from adds_sim import (
    build_controller_portfolio_report,
    build_controller_robustness_portfolio_report,
    phase4_scenario_catalog,
    write_controller_robustness_portfolio_report,
    write_controller_portfolio_report,
)


class Phase7ControllerPortfolioReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.entries = phase4_scenario_catalog()

    def test_builds_controller_portfolio_report_with_aggregates(self) -> None:
        report = build_controller_portfolio_report(entries=self.entries)

        self.assertEqual(report.scenario_count, len(self.entries))
        self.assertEqual(len(report.rows), len(self.entries) * 3)
        self.assertEqual(len(report.aggregates), 3)
        self.assertEqual(
            {aggregate.adds_controller_kind for aggregate in report.aggregates},
            {"rule_based", "offline_optimized", "learned"},
        )
        self.assertTrue(
            all(aggregate.scenario_count == len(self.entries) for aggregate in report.aggregates)
        )

    def test_report_preserves_optimized_frozen_test_result(self) -> None:
        report = build_controller_portfolio_report(entries=self.entries)
        high_speed_rows = {
            row.adds_controller_kind: row
            for row in report.rows
            if row.scenario_id == "test_high_speed_coast"
        }

        self.assertLess(
            high_speed_rows["offline_optimized"].relative_fuel_change,
            high_speed_rows["rule_based"].relative_fuel_change - 0.5,
        )
        self.assertEqual(high_speed_rows["offline_optimized"].adds_safety_overrides, 0)
        self.assertEqual(high_speed_rows["offline_optimized"].adds_transitions, 5)

    def test_writes_json_and_csv_controller_portfolio_report(self) -> None:
        report = build_controller_portfolio_report(entries=self.entries[:2])

        with tempfile.TemporaryDirectory() as tmp:
            json_path, csv_path = write_controller_portfolio_report(Path(tmp), report)

            self.assertTrue(json_path.exists())
            self.assertTrue(csv_path.exists())

            data = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(data["schema_version"], "1.0")
            self.assertEqual(data["scenario_count"], 2)
            self.assertEqual(data["row_count"], 6)
            self.assertEqual(len(data["aggregates"]), 3)

            with csv_path.open(newline="", encoding="utf-8") as file:
                rows = list(csv.DictReader(file))

        self.assertEqual(len(rows), 6)
        self.assertIn("controller_label", rows[0])
        self.assertIn("relative_fuel_change", rows[0])

    def test_builds_controller_robustness_portfolio_report(self) -> None:
        report = build_controller_robustness_portfolio_report(entries=self.entries[:2])

        self.assertEqual(report.scenario_count, 2)
        self.assertEqual(report.perturbation_count, 8)
        self.assertEqual(len(report.rows), 2 * 3 * 8)
        self.assertEqual(len(report.aggregates), 3)
        self.assertTrue(all(aggregate.run_count == 16 for aggregate in report.aggregates))

    def test_robustness_report_preserves_nominal_optimized_gain(self) -> None:
        report = build_controller_robustness_portfolio_report(entries=self.entries)
        high_speed_nominal = {
            row.adds_controller_kind: row
            for row in report.rows
            if row.scenario_id == "test_high_speed_coast"
            and row.perturbation == "nominal"
        }

        self.assertLess(
            high_speed_nominal["offline_optimized"].relative_fuel_change,
            high_speed_nominal["rule_based"].relative_fuel_change - 0.5,
        )
        self.assertEqual(high_speed_nominal["offline_optimized"].adds_safety_overrides, 0)

    def test_writes_json_and_csv_controller_robustness_portfolio_report(self) -> None:
        report = build_controller_robustness_portfolio_report(entries=self.entries[:1])

        with tempfile.TemporaryDirectory() as tmp:
            json_path, csv_path = write_controller_robustness_portfolio_report(Path(tmp), report)

            self.assertTrue(json_path.exists())
            self.assertTrue(csv_path.exists())

            data = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(data["schema_version"], "1.0")
            self.assertEqual(data["scenario_count"], 1)
            self.assertEqual(data["perturbation_count"], 8)
            self.assertEqual(data["row_count"], 24)

            with csv_path.open(newline="", encoding="utf-8") as file:
                rows = list(csv.DictReader(file))

        self.assertEqual(len(rows), 24)
        self.assertIn("perturbation", rows[0])
        self.assertIn("controller_label", rows[0])


if __name__ == "__main__":
    unittest.main()
