"""Command-line reference track-lap report generation."""

from __future__ import annotations

import argparse
from pathlib import Path

from .track_lap import run_track_lap_comparison, write_track_lap_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the ADDS reference track-lap prototype.")
    parser.add_argument("output_dir", type=Path, help="Directory for track-lap artifacts.")
    parser.add_argument(
        "--controller",
        choices=("rule_based", "offline_optimized", "track_lap_balanced", "learned"),
        default="offline_optimized",
        help="ADDS controller variant to compare against the conventional baseline.",
    )
    args = parser.parse_args()

    report = run_track_lap_comparison(args.controller)
    json_path, stats_path, conventional_path, adds_path = write_track_lap_report(args.output_dir, report)

    print(f"json_report: {json_path}")
    print(f"stats_csv: {stats_path}")
    print(f"conventional_trajectory: {conventional_path}")
    print(f"adds_trajectory: {adds_path}")
    print(f"track_name: {report.track_name}")
    print(f"controller: {report.adds_controller_kind}")
    print(f"scenario_id: {report.scenario.scenario_id}")
    print(f"termination_conventional: {report.comparison.conventional_result.termination_reason}")
    print(f"termination_adds: {report.comparison.adds_result.termination_reason}")
    for stat in report.stats:
        print(
            f"{stat.label}: conventional={stat.conventional_value:.3f} {stat.unit}, "
            f"adds={stat.adds_value:.3f} {stat.unit}, delta={stat.delta:.3f} {stat.unit}"
        )


if __name__ == "__main__":
    main()
