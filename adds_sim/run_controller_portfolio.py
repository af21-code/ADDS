"""Command-line controller-portfolio report generation."""

from __future__ import annotations

import argparse
from pathlib import Path

from .controller_portfolio import (
    build_controller_portfolio_report,
    write_controller_portfolio_report,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ADDS controller-portfolio reporting.")
    parser.add_argument("output_dir", type=Path, help="Directory for controller portfolio artifacts.")
    args = parser.parse_args()
    report = build_controller_portfolio_report()
    json_path, csv_path = write_controller_portfolio_report(args.output_dir, report)
    print(f"json_report: {json_path}")
    print(f"csv_report: {csv_path}")
    print(f"controllers: {len(report.controller_kinds)}")
    print(f"scenarios: {report.scenario_count}")
    print(f"rows: {len(report.rows)}")
    for aggregate in report.aggregates:
        print(
            f"{aggregate.adds_controller_kind}: "
            f"accepted={aggregate.accepted_efficiency_claims}/{aggregate.scenario_count}, "
            f"mean_relative_fuel_change={aggregate.mean_relative_fuel_change:.3f}%"
        )


if __name__ == "__main__":
    main()
