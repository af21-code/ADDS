"""Command-line track-lap policy-search report generation."""

from __future__ import annotations

import argparse
from pathlib import Path

from .track_lap_policy_search import (
    run_track_lap_policy_search,
    write_track_lap_policy_search_report,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ADDS track-lap policy search.")
    parser.add_argument("output_dir", type=Path, help="Directory for track-lap policy-search artifacts.")
    args = parser.parse_args()

    report = run_track_lap_policy_search()
    json_path, csv_path = write_track_lap_policy_search_report(args.output_dir, report)

    print(f"json_report: {json_path}")
    print(f"csv_report: {csv_path}")
    print(f"candidates: {len(report.candidates)}")
    print(f"promotion_passed: {report.promotion_passed}")
    print(f"best_candidate: {report.best_candidate.candidate_id if report.best_candidate else 'none'}")
    print(
        "baseline: "
        f"fuel={report.baseline_relative_fuel_change:.3f}%, "
        f"lap_time_delta={report.baseline_delta_lap_time:.3f}s, "
        f"worst_sector={report.baseline_worst_sector_name}, "
        f"worst_sector_delta={report.baseline_worst_sector_delta:.3f}s"
    )
    for reason in report.promotion_reasons:
        print(f"reason: {reason}")
    for row in report.rows[:5]:
        print(
            "candidate: "
            f"{row.candidate.candidate_id}, "
            f"fuel={row.relative_fuel_change:.3f}%, "
            f"lap_time_delta={row.delta_lap_time:.3f}s, "
            f"worst_sector_delta={row.worst_time_loss_delta:.3f}s, "
            f"eligible={row.promotion_eligible}"
        )
    for action in report.recommended_next_actions:
        print(f"next_action: {action}")


if __name__ == "__main__":
    main()
