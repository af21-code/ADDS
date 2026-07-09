import json
import tempfile
import unittest
from pathlib import Path

from adds_sim import (
    build_track_lap_sector_analysis,
    reference_track_lap_sections,
    reference_track_lap_sectors,
    write_track_lap_sector_analysis,
)


class Phase11TrackLapSectorAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.analysis = build_track_lap_sector_analysis(adds_controller_kind="offline_optimized")

    def test_reference_sectors_cover_the_full_lap_distance(self) -> None:
        sectors = reference_track_lap_sectors()
        sections = reference_track_lap_sections()

        self.assertEqual(len(sectors), len(sections))
        self.assertAlmostEqual(sectors[0].start_distance, 0.0)
        self.assertAlmostEqual(sectors[-1].end_distance, 3_000.0)
        for previous, current in zip(sectors[:-1], sectors[1:]):
            self.assertAlmostEqual(previous.end_distance, current.start_distance)
            self.assertLess(previous.start_distance, previous.end_distance)

    def test_analysis_identifies_time_loss_and_fuel_saving_regions(self) -> None:
        analysis = self.analysis

        self.assertEqual(analysis.schema_version, "1.0")
        self.assertEqual(analysis.adds_controller_kind, "offline_optimized")
        self.assertGreater(len(analysis.sectors), 0)
        self.assertIsNotNone(analysis.worst_time_loss_sector)
        self.assertIsNotNone(analysis.best_fuel_saving_sector)
        self.assertTrue(any(row.delta_fuel_kg < 0.0 for row in analysis.sectors))
        self.assertTrue(any(row.delta_time > 0.0 for row in analysis.sectors))
        self.assertGreater(len(analysis.recommendations), 0)

    def test_sector_totals_are_consistent_with_lap_trade_offs(self) -> None:
        delta_time = sum(row.delta_time for row in self.analysis.sectors)
        delta_fuel_kg = sum(row.delta_fuel_kg for row in self.analysis.sectors)

        self.assertGreater(delta_time, 0.0)
        self.assertLess(delta_fuel_kg, 0.0)

    def test_writes_track_lap_sector_analysis_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            json_path, csv_path = write_track_lap_sector_analysis(Path(tmp), self.analysis)

            self.assertTrue(json_path.exists())
            self.assertTrue(csv_path.exists())
            data = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(data["schema_version"], "1.0")
            self.assertEqual(data["adds_controller_kind"], "offline_optimized")
            self.assertEqual(len(data["sectors"]), len(self.analysis.sectors))
            self.assertIsNotNone(data["worst_time_loss_sector"])
            self.assertIsNotNone(data["best_fuel_saving_sector"])
            self.assertGreater(len(csv_path.read_text(encoding="utf-8").splitlines()), 1)


if __name__ == "__main__":
    unittest.main()
