import tempfile
import unittest
from pathlib import Path

from adds_sim import (
    BehavioralCloningModel,
    LearnedADDSController,
    LongitudinalSimulator,
    default_simulation_config,
    entries_by_split,
    phase4_scenario_catalog,
    collect_imitation_examples,
    summarize_run,
    train_behavioral_cloning_model,
)
from adds_sim.benchmarks import with_adds_enabled
from adds_sim.train_imitation import train_and_evaluate_imitation


class Phase5ImitationLearningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = default_simulation_config()
        self.simulator = LongitudinalSimulator(self.config)
        self.catalog = phase4_scenario_catalog()
        self.grouped = entries_by_split(self.catalog)

    def test_collects_training_examples_from_train_split(self) -> None:
        examples = collect_imitation_examples(self.simulator, self.grouped["train"])

        self.assertGreater(len(examples), 0)
        self.assertEqual({example.split for example in examples}, {"train"})
        self.assertIn("DECOUPLING", {example.requested_mode for example in examples})

    def test_trains_and_round_trips_checkpoint(self) -> None:
        examples = collect_imitation_examples(self.simulator, self.grouped["train"])
        report = train_behavioral_cloning_model(examples)

        self.assertEqual(report.model.model_type, "threshold_behavioral_cloning")
        self.assertEqual(report.model.schema_version, "2.0")
        self.assertGreater(report.model.training_examples, 0)
        self.assertGreaterEqual(report.model.coast_speed_margin, 0.0)
        self.assertGreaterEqual(report.model.reconnect_speed_margin, 0.0)
        self.assertIn("CONNECTED", report.label_counts)

        with tempfile.TemporaryDirectory() as tmp:
            checkpoint_path = Path(tmp) / "learned_adds_thresholds.json"
            report.model.save(checkpoint_path)
            loaded = BehavioralCloningModel.load(checkpoint_path)

        self.assertEqual(report.model, loaded)

    def test_learned_controller_completes_held_out_splits(self) -> None:
        examples = collect_imitation_examples(self.simulator, self.grouped["train"])
        model = train_behavioral_cloning_model(examples).model

        for split in ("validation", "test", "stress"):
            for entry in self.grouped[split]:
                with self.subTest(split=split, scenario=entry.scenario.scenario_id):
                    scenario = with_adds_enabled(entry.scenario, True)
                    controller = LearnedADDSController(gear=scenario.initial_gear, model=model)
                    result = self.simulator.run(scenario, controller)
                    summary = summarize_run(result)

                    self.assertTrue(summary["completed_successfully"])
                    self.assertFalse(summary["numerical_failure"])
                    self.assertEqual(summary["hard_constraint_violation_count"], 0)
                    self.assertLessEqual(
                        summary["safety_override_count"],
                        self.config.safety.max_supervisor_overrides_per_km * max(summary["distance_traveled"] / 1000.0, 1.0),
                    )

    def test_training_entrypoint_writes_checkpoint_and_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifacts = train_and_evaluate_imitation(Path(tmp))

            self.assertTrue(artifacts.checkpoint_path.exists())
            self.assertTrue(artifacts.training_report_path.exists())
            self.assertTrue(artifacts.evaluation_report_path.exists())


if __name__ == "__main__":
    unittest.main()
