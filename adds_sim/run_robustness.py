"""Command-line robustness evaluation."""

from __future__ import annotations

import argparse
from pathlib import Path

from .robustness import run_robustness_evaluation, write_robustness_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ADDS robustness and sensitivity evaluation.")
    parser.add_argument("output_dir", type=Path, help="Directory for robustness report artifacts.")
    args = parser.parse_args()
    report = run_robustness_evaluation()
    json_path, csv_path = write_robustness_report(args.output_dir, report)
    print(f"json_report: {json_path}")
    print(f"csv_report: {csv_path}")
    print(f"runs: {len(report.runs)}")
    print(f"completed_successfully: {report.completed_successfully}")
    print(f"constraint_regression_count: {report.constraint_regression_count}")
    print(f"max_adds_safety_overrides: {report.max_adds_safety_overrides}")


if __name__ == "__main__":
    main()
