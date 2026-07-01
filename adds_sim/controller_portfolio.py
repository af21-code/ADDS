"""Reproducible controller-portfolio reporting."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .scenario_catalog import ScenarioCatalogEntry, phase4_scenario_catalog
from .visualization import (
    SUPPORTED_DASHBOARD_CONTROLLER_KINDS,
    DashboardControllerPortfolioRow,
    build_dashboard_controller_portfolio,
)


@dataclass(frozen=True)
class ControllerPortfolioAggregate:
    """Aggregate result for one ADDS controller across the scenario catalog."""

    adds_controller_kind: str
    controller_label: str
    scenario_count: int
    accepted_efficiency_claims: int
    acceptance_rate_percent: float
    mean_relative_fuel_change: float
    best_relative_fuel_change: float
    worst_relative_fuel_change: float
    maximum_rms_speed_error_delta_kmh: float
    total_mode_transitions: int
    maximum_safety_overrides: int
    constraint_regression_count: int


@dataclass(frozen=True)
class ControllerPortfolioReport:
    """Machine-readable controller comparison across all catalog scenarios."""

    controller_kinds: tuple[str, ...]
    scenario_count: int
    rows: tuple[DashboardControllerPortfolioRow, ...]
    aggregates: tuple[ControllerPortfolioAggregate, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "controller_kinds": list(self.controller_kinds),
            "scenario_count": self.scenario_count,
            "row_count": len(self.rows),
            "aggregates": [asdict(aggregate) for aggregate in self.aggregates],
            "rows": [asdict(row) for row in self.rows],
        }


def build_controller_portfolio_report(
    entries: tuple[ScenarioCatalogEntry, ...] | None = None,
    adds_controller_kinds: tuple[str, ...] = SUPPORTED_DASHBOARD_CONTROLLER_KINDS,
) -> ControllerPortfolioReport:
    """Build the reproducible report used by the dashboard portfolio view."""

    catalog = entries or phase4_scenario_catalog()
    rows = build_dashboard_controller_portfolio(adds_controller_kinds, catalog)
    aggregates = tuple(
        _aggregate_controller_rows(controller_kind, rows)
        for controller_kind in adds_controller_kinds
    )
    return ControllerPortfolioReport(
        controller_kinds=adds_controller_kinds,
        scenario_count=len(catalog),
        rows=rows,
        aggregates=aggregates,
    )


def write_controller_portfolio_report(
    output_dir: Path,
    report: ControllerPortfolioReport,
) -> tuple[Path, Path]:
    """Write JSON and CSV controller-portfolio report artifacts."""

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "controller_portfolio_report.json"
    csv_path = output_dir / "controller_portfolio_rows.csv"
    json_path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with csv_path.open("w", newline="", encoding="utf-8") as file:
        fieldnames = tuple(asdict(report.rows[0]).keys()) if report.rows else ()
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in report.rows:
            writer.writerow(asdict(row))
    return json_path, csv_path


def _aggregate_controller_rows(
    controller_kind: str,
    rows: tuple[DashboardControllerPortfolioRow, ...],
) -> ControllerPortfolioAggregate:
    controller_rows = tuple(row for row in rows if row.adds_controller_kind == controller_kind)
    if not controller_rows:
        return ControllerPortfolioAggregate(
            adds_controller_kind=controller_kind,
            controller_label=controller_kind,
            scenario_count=0,
            accepted_efficiency_claims=0,
            acceptance_rate_percent=0.0,
            mean_relative_fuel_change=0.0,
            best_relative_fuel_change=0.0,
            worst_relative_fuel_change=0.0,
            maximum_rms_speed_error_delta_kmh=0.0,
            total_mode_transitions=0,
            maximum_safety_overrides=0,
            constraint_regression_count=0,
        )

    accepted = sum(1 for row in controller_rows if row.efficiency_claim_accepted)
    return ControllerPortfolioAggregate(
        adds_controller_kind=controller_kind,
        controller_label=controller_rows[0].controller_label,
        scenario_count=len(controller_rows),
        accepted_efficiency_claims=accepted,
        acceptance_rate_percent=100.0 * accepted / len(controller_rows),
        mean_relative_fuel_change=sum(row.relative_fuel_change for row in controller_rows)
        / len(controller_rows),
        best_relative_fuel_change=min(row.relative_fuel_change for row in controller_rows),
        worst_relative_fuel_change=max(row.relative_fuel_change for row in controller_rows),
        maximum_rms_speed_error_delta_kmh=max(
            row.rms_speed_error_delta_kmh for row in controller_rows
        ),
        total_mode_transitions=sum(row.adds_transitions for row in controller_rows),
        maximum_safety_overrides=max(row.adds_safety_overrides for row in controller_rows),
        constraint_regression_count=sum(1 for row in controller_rows if row.constraint_regression),
    )
