import unittest

from adds_sim.visualization import (
    MODE_TO_INDEX,
    available_dashboard_scenarios,
    build_dashboard_catalog_summary,
    build_dashboard_comparison,
    mode_durations_seconds,
)


class Phase7VisualizationTests(unittest.TestCase):
    def test_available_dashboard_scenarios_exposes_catalog_metadata(self) -> None:
        options = available_dashboard_scenarios()

        self.assertGreaterEqual(len(options), 5)
        self.assertEqual(options[0].scenario_id, "train_constant_speed_cruise")
        self.assertTrue(options[0].description)
        self.assertIn(options[0].split, {"train", "validation", "test", "stress"})

    def test_builds_rule_based_dashboard_comparison(self) -> None:
        comparison = build_dashboard_comparison("train_highway_lift_off")

        self.assertEqual(comparison.scenario.scenario_id, "train_highway_lift_off")
        self.assertEqual(comparison.adds_controller_kind, "rule_based")
        self.assertGreater(len(comparison.conventional_records), 0)
        self.assertGreater(len(comparison.adds_records), 0)
        self.assertEqual(comparison.conventional_records[0]["vehicle"], "Conventional")
        self.assertEqual(comparison.adds_records[0]["vehicle"], "ADDS")
        self.assertIn("relative_fuel_change", comparison.comparison.deltas)
        self.assertGreater(len(comparison.insights), 0)

    def test_records_include_dashboard_units_and_mode_indices(self) -> None:
        comparison = build_dashboard_comparison("test_mild_descent_lower_speed")
        first_adds_record = comparison.adds_records[0]

        self.assertIn("speed_kmh", first_adds_record)
        self.assertIn("engine_speed_rpm", first_adds_record)
        self.assertIn("fuel_used_ml", first_adds_record)
        self.assertIn("coupling_mode_index", first_adds_record)
        self.assertEqual(first_adds_record["coupling_mode_index"], MODE_TO_INDEX[first_adds_record["coupling_mode"]])

    def test_metric_cards_cover_primary_comparison_values(self) -> None:
        comparison = build_dashboard_comparison("validation_rolling_terrain")
        labels = {str(card["label"]) for card in comparison.metric_cards}

        self.assertIn("Fuel delta", labels)
        self.assertIn("Relative fuel change", labels)
        self.assertIn("RMS speed error delta", labels)
        self.assertIn("ADDS safety overrides", labels)

    def test_catalog_summary_contains_one_row_per_scenario(self) -> None:
        options = available_dashboard_scenarios()
        rows = build_dashboard_catalog_summary()

        self.assertEqual(len(rows), len(options))
        self.assertEqual(rows[0].adds_controller_kind, "rule_based")
        self.assertIn(rows[0].split, {"train", "validation", "test", "stress"})
        self.assertIsInstance(rows[0].fuel_delta_ml, float)
        self.assertIsInstance(rows[0].adds_transitions, int)

    def test_mode_durations_are_estimated_from_records(self) -> None:
        comparison = build_dashboard_comparison("train_highway_lift_off")
        durations = mode_durations_seconds(comparison.comparison.adds_result.records)

        self.assertGreater(durations["CONNECTED"], 0.0)
        self.assertGreater(durations["DECOUPLED"], 0.0)
        self.assertAlmostEqual(
            sum(durations.values()),
            float(comparison.comparison.adds_result.records[-1]["time"]),
            places=6,
        )

    def test_insights_classify_demonstration_scenario(self) -> None:
        comparison = build_dashboard_comparison("train_highway_lift_off")
        titles = {insight.title for insight in comparison.insights}

        self.assertIn("ADDS reduced simulated fuel use", titles)
        self.assertIn("ADDS changed drivetrain state", titles)

    def test_builds_learned_dashboard_comparison(self) -> None:
        comparison = build_dashboard_comparison("stress_low_speed_urban", "learned")

        self.assertEqual(comparison.adds_controller_kind, "learned")
        self.assertGreater(len(comparison.adds_records), 0)
        self.assertEqual(comparison.comparison.adds_result.controller_name, "learned_adds")

    def test_rejects_unknown_dashboard_scenario(self) -> None:
        with self.assertRaises(ValueError):
            build_dashboard_comparison("missing_scenario")


if __name__ == "__main__":
    unittest.main()
