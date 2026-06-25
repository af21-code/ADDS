import csv
import json
import tempfile
import unittest
from pathlib import Path

from adds_sim import (
    LongitudinalSimulator,
    default_simulation_config,
    entries_by_split,
    phase4_scenario_catalog,
    run_batch_evaluation,
)


class Phase4DataInfrastructureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = default_simulation_config()
        self.simulator = LongitudinalSimulator(self.config)
        self.catalog = phase4_scenario_catalog()

    def test_catalog_has_unique_scenarios_and_required_splits(self) -> None:
        scenario_ids = [entry.scenario.scenario_id for entry in self.catalog]
        self.assertEqual(len(scenario_ids), len(set(scenario_ids)))

        grouped = entries_by_split(self.catalog)
        self.assertIn("train", grouped)
        self.assertIn("validation", grouped)
        self.assertIn("test", grouped)
        self.assertIn("stress", grouped)
        self.assertTrue(
            all("held-out" in entry.tags for entry in grouped["validation"] + grouped["test"] if "coast" in entry.tags)
        )
        train_ids = {entry.scenario.scenario_id for entry in grouped["train"]}
        held_out_ids = {
            entry.scenario.scenario_id
            for split in ("validation", "test")
            for entry in grouped[split]
        }
        self.assertTrue(train_ids.isdisjoint(held_out_ids))

    def test_batch_evaluation_writes_manifest_summary_and_trajectories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = run_batch_evaluation(self.simulator, self.catalog[:2], Path(tmp))

            self.assertTrue(output.manifest_path.exists())
            self.assertTrue(output.summary_path.exists())
            self.assertEqual(len(output.trajectory_paths), 4)
            self.assertTrue(all(path.exists() for path in output.trajectory_paths))

            manifest = json.loads(output.manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["schema_version"], "1.0")
            self.assertEqual(manifest["scenario_count"], 2)

            with output.summary_path.open(newline="", encoding="utf-8") as file:
                rows = list(csv.DictReader(file))
            self.assertEqual(len(rows), 4)
            self.assertTrue(all(row["completed_successfully"] == "True" for row in rows))

            with output.trajectory_paths[0].open(newline="", encoding="utf-8") as file:
                first_row = next(csv.DictReader(file))
            self.assertIn("time", first_row)
            self.assertIn("vehicle_speed", first_row)
            self.assertIn("coupling_mode", first_row)

    def test_batch_evaluation_is_reproducible(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_a, tempfile.TemporaryDirectory() as tmp_b:
            result_a = run_batch_evaluation(self.simulator, self.catalog, Path(tmp_a), write_trajectories=False)
            result_b = run_batch_evaluation(self.simulator, self.catalog, Path(tmp_b), write_trajectories=False)

            self.assertEqual(
                result_a.manifest_path.read_text(encoding="utf-8"),
                result_b.manifest_path.read_text(encoding="utf-8"),
            )
            self.assertEqual(
                result_a.summary_path.read_text(encoding="utf-8"),
                result_b.summary_path.read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
