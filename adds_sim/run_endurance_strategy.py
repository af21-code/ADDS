"""Command-line endurance strategy report generation."""

from __future__ import annotations

import argparse
from pathlib import Path

from .endurance_strategy import (
    EnduranceStrategyConfig,
    run_endurance_strategy,
    write_endurance_strategy_report,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ADDS endurance strategy analysis.")
    parser.add_argument("output_dir", type=Path, help="Directory for endurance strategy artifacts.")
    parser.add_argument(
        "--controller",
        choices=("rule_based", "offline_optimized", "learned"),
        default="offline_optimized",
        help="ADDS controller variant to compare against the conventional baseline.",
    )
    parser.add_argument("--hours", type=float, default=24.0, help="Race duration in hours.")
    parser.add_argument(
        "--reference-stint-laps",
        type=int,
        default=30,
        help="Tank capacity expressed as conventional reference-lap fuel usage.",
    )
    parser.add_argument("--pit-loss", type=float, default=42.0, help="Pit stop time loss in seconds.")
    args = parser.parse_args()

    report = run_endurance_strategy(
        EnduranceStrategyConfig(
            race_duration_hours=args.hours,
            reference_stint_laps=args.reference_stint_laps,
            pit_stop_loss_seconds=args.pit_loss,
            adds_controller_kind=args.controller,
        )
    )
    json_path, csv_path = write_endurance_strategy_report(args.output_dir, report)

    print(f"json_report: {json_path}")
    print(f"csv_report: {csv_path}")
    print(f"verdict: {report.verdict}")
    print(
        "conventional: "
        f"laps={report.conventional.completed_laps}, "
        f"pits={report.conventional.pit_stops}, "
        f"stint_laps={report.conventional.stint_laps}"
    )
    print(
        "adds: "
        f"laps={report.adds.completed_laps}, "
        f"pits={report.adds.pit_stops}, "
        f"stint_laps={report.adds.stint_laps}"
    )
    print(f"delta_completed_laps: {report.deltas['delta_completed_laps']}")
    print(f"delta_pit_stops: {report.deltas['delta_pit_stops']}")
    print(f"relative_fuel_change: {report.deltas['relative_fuel_change']:.3f}%")
    print(
        "minimum_reference_stint_laps_for_one_extra_lap: "
        f"{report.thresholds.minimum_reference_stint_laps_for_one_extra_lap}"
    )
    for message in report.interpretation:
        print(f"interpretation: {message}")


if __name__ == "__main__":
    main()
