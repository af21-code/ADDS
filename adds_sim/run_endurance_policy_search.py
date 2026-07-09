"""Command-line endurance policy-search report generation."""

from __future__ import annotations

import argparse
from pathlib import Path

from .endurance_policy_search import (
    run_endurance_policy_search,
    write_endurance_policy_search_report,
)
from .endurance_strategy import EnduranceStrategyConfig


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ADDS endurance-oriented policy search.")
    parser.add_argument("output_dir", type=Path, help="Directory for endurance policy-search artifacts.")
    parser.add_argument("--hours", type=float, default=24.0, help="Race duration in hours.")
    parser.add_argument(
        "--reference-stint-laps",
        type=int,
        default=30,
        help="Tank capacity expressed as conventional reference-lap fuel usage.",
    )
    parser.add_argument("--pit-loss", type=float, default=42.0, help="Pit stop time loss in seconds.")
    args = parser.parse_args()

    report = run_endurance_policy_search(
        EnduranceStrategyConfig(
            race_duration_hours=args.hours,
            reference_stint_laps=args.reference_stint_laps,
            pit_stop_loss_seconds=args.pit_loss,
        )
    )
    json_path, csv_path = write_endurance_policy_search_report(args.output_dir, report)

    print(f"json_report: {json_path}")
    print(f"csv_report: {csv_path}")
    print(f"candidates: {len(report.candidates)}")
    print(f"promotion_passed: {report.promotion_passed}")
    print(f"best_candidate: {report.best_candidate.candidate_id if report.best_candidate else 'none'}")
    for reason in report.promotion_reasons:
        print(f"reason: {reason}")
    for row in report.rows[:5]:
        print(
            "candidate: "
            f"{row.candidate.candidate_id}, "
            f"coast_margin={row.candidate.coast_speed_margin:.2f}, "
            f"reconnect_margin={row.candidate.reconnect_speed_margin:.2f}, "
            f"min_drop={row.candidate.minimum_target_speed_drop:.2f}, "
            f"verdict={row.verdict}, "
            f"fuel={row.relative_fuel_change:.3f}%, "
            f"lap_time_delta={row.delta_lap_time:.3f}s, "
            f"delta_laps={row.delta_completed_laps}, "
            f"eligible={row.promotion_eligible}"
        )
    for action in report.recommended_next_actions:
        print(f"next_action: {action}")


if __name__ == "__main__":
    main()
