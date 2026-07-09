"""Command-line track-lap sector analysis report generation."""

from __future__ import annotations

import argparse
from pathlib import Path

from .track_lap_analysis import (
    build_track_lap_sector_analysis,
    write_track_lap_sector_analysis,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ADDS track-lap sector diagnostics.")
    parser.add_argument("output_dir", type=Path, help="Directory for sector-analysis artifacts.")
    parser.add_argument(
        "--controller",
        choices=("rule_based", "offline_optimized", "track_lap_balanced", "learned"),
        default="offline_optimized",
        help="ADDS controller variant to diagnose.",
    )
    args = parser.parse_args()

    analysis = build_track_lap_sector_analysis(adds_controller_kind=args.controller)
    json_path, csv_path = write_track_lap_sector_analysis(args.output_dir, analysis)

    print(f"json_report: {json_path}")
    print(f"csv_report: {csv_path}")
    print(f"controller: {analysis.adds_controller_kind}")
    if analysis.worst_time_loss_sector is not None:
        sector = analysis.worst_time_loss_sector
        print(
            "worst_time_loss_sector: "
            f"{sector.sector.index} {sector.sector.name}, "
            f"delta_time={sector.delta_time:.3f}s, "
            f"delta_fuel={sector.delta_fuel_kg * 1_000.0:.2f}g, "
            f"verdict={sector.verdict}"
        )
    if analysis.best_fuel_saving_sector is not None:
        sector = analysis.best_fuel_saving_sector
        print(
            "best_fuel_saving_sector: "
            f"{sector.sector.index} {sector.sector.name}, "
            f"delta_time={sector.delta_time:.3f}s, "
            f"delta_fuel={sector.delta_fuel_kg * 1_000.0:.2f}g, "
            f"verdict={sector.verdict}"
        )
    for recommendation in analysis.recommendations:
        print(f"recommendation: {recommendation}")


if __name__ == "__main__":
    main()
