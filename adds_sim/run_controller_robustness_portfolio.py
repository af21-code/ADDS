"""Command-line controller-robustness portfolio report generation."""

from __future__ import annotations

import argparse
from pathlib import Path

from .controller_portfolio import (
    build_controller_robustness_portfolio_report,
    write_controller_robustness_portfolio_report,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ADDS controller robustness portfolio reporting.")
    parser.add_argument("output_dir", type=Path, help="Directory for controller robustness artifacts.")
    args = parser.parse_args()
    report = build_controller_robustness_portfolio_report()
    json_path, csv_path = write_controller_robustness_portfolio_report(args.output_dir, report)
    print(f"json_report: {json_path}")
    print(f"csv_report: {csv_path}")
    print(f"controllers: {len(report.controller_kinds)}")
    print(f"scenarios: {report.scenario_count}")
    print(f"perturbations: {report.perturbation_count}")
    print(f"rows: {len(report.rows)}")
    for aggregate in report.aggregates:
        print(
            f"{aggregate.adds_controller_kind}: "
            f"accepted={aggregate.accepted_efficiency_claims}/{aggregate.run_count}, "
            f"acceptance_rate={aggregate.acceptance_rate_percent:.1f}%, "
            f"mean_relative_fuel_change={aggregate.mean_relative_fuel_change:.3f}%"
        )


if __name__ == "__main__":
    main()
