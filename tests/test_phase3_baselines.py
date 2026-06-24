import unittest

from adds_sim import (
    ConventionalBaselineController,
    LongitudinalSimulator,
    RuleBasedADDSController,
    benchmark_scenarios,
    default_simulation_config,
    run_paired_comparison,
    summarize_run,
)
from adds_sim.benchmarks import with_adds_enabled


class Phase3BaselineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = default_simulation_config()
        self.simulator = LongitudinalSimulator(self.config)

    def test_conventional_baseline_completes_catalog(self) -> None:
        for scenario in benchmark_scenarios():
            with self.subTest(scenario=scenario.scenario_id):
                result = self.simulator.run(
                    with_adds_enabled(scenario, False),
                    ConventionalBaselineController(gear=scenario.initial_gear),
                )
                summary = summarize_run(result)

                self.assertTrue(summary["completed_successfully"])
                self.assertFalse(summary["numerical_failure"])
                self.assertEqual(summary["hard_constraint_violation_count"], 0)

    def test_rule_based_adds_baseline_completes_catalog(self) -> None:
        transitions = 0
        for scenario in benchmark_scenarios():
            with self.subTest(scenario=scenario.scenario_id):
                result = self.simulator.run(
                    with_adds_enabled(scenario, True),
                    RuleBasedADDSController(gear=scenario.initial_gear),
                )
                summary = summarize_run(result)
                transitions += int(summary["mode_transition_count"])

                self.assertTrue(summary["completed_successfully"])
                self.assertFalse(summary["numerical_failure"])
                self.assertEqual(summary["hard_constraint_violation_count"], 0)
                self.assertLessEqual(
                    summary["safety_override_count"],
                    self.config.safety.max_supervisor_overrides_per_km * max(summary["distance_traveled"] / 1000.0, 1.0),
                )

        self.assertGreater(transitions, 0)

    def test_paired_comparison_uses_matching_scenario_inputs(self) -> None:
        scenario = benchmark_scenarios()[1]

        comparison = run_paired_comparison(
            self.simulator,
            scenario,
            ConventionalBaselineController(gear=scenario.initial_gear),
            RuleBasedADDSController(gear=scenario.initial_gear),
        )

        self.assertEqual(comparison.scenario_id, scenario.scenario_id)
        self.assertEqual(comparison.conventional_result.scenario_id, scenario.scenario_id)
        self.assertEqual(comparison.adds_result.scenario_id, scenario.scenario_id)
        self.assertFalse(comparison.deltas["constraint_regression"])
        self.assertIn("delta_fuel_used", comparison.deltas)
        self.assertIn("relative_fuel_change", comparison.deltas)
        self.assertGreater(comparison.adds_summary["mode_transition_count"], 0)

    def test_rule_based_adds_uses_same_speed_tracking_gain_as_baseline(self) -> None:
        conventional = ConventionalBaselineController(gear=5)
        adds = RuleBasedADDSController(gear=5)

        self.assertEqual(adds.proportional_gain, conventional.proportional_gain)

    def test_highway_coasting_benefit_passes_initial_research_gates(self) -> None:
        scenario = benchmark_scenarios()[1]
        comparison = run_paired_comparison(
            self.simulator,
            scenario,
            ConventionalBaselineController(gear=scenario.initial_gear),
            RuleBasedADDSController(gear=scenario.initial_gear),
        )

        self.assertLessEqual(comparison.deltas["relative_fuel_change"], -1.0)
        self.assertLessEqual(comparison.deltas["delta_rms_speed_error"] * 3.6, 1.0)
        self.assertEqual(comparison.adds_summary["mode_transition_count"], 5)
        self.assertEqual(comparison.adds_summary["safety_override_count"], 0)


if __name__ == "__main__":
    unittest.main()
