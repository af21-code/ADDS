"""Reproducible controller-portfolio reporting."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .scenario_catalog import ScenarioCatalogEntry, phase4_scenario_catalog
from .visualization import (
    DASHBOARD_CONTROLLER_LABELS,
    SUPPORTED_DASHBOARD_CONTROLLER_KINDS,
    DashboardControllerPortfolioRow,
    build_dashboard_controller_portfolio,
    build_dashboard_sensitivity,
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
class ControllerPortfolioInsight:
    """Human-readable interpretation of one controller portfolio report."""

    severity: str
    title: str
    message: str


@dataclass(frozen=True)
class ControllerPortfolioReport:
    """Machine-readable controller comparison across all catalog scenarios."""

    controller_kinds: tuple[str, ...]
    scenario_count: int
    rows: tuple[DashboardControllerPortfolioRow, ...]
    aggregates: tuple[ControllerPortfolioAggregate, ...]
    insights: tuple[ControllerPortfolioInsight, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "controller_kinds": list(self.controller_kinds),
            "scenario_count": self.scenario_count,
            "row_count": len(self.rows),
            "aggregates": [asdict(aggregate) for aggregate in self.aggregates],
            "insights": [asdict(insight) for insight in self.insights],
            "rows": [asdict(row) for row in self.rows],
        }


@dataclass(frozen=True)
class ControllerRobustnessPortfolioRow:
    """One scenario-controller-perturbation result for robustness comparison."""

    perturbation: str
    scenario_id: str
    split: str
    description: str
    adds_controller_kind: str
    controller_label: str
    mass_scale: float
    drag_scale: float
    rolling_resistance_scale: float
    tire_friction_scale: float
    grade_offset_percent: float
    relative_fuel_change: float
    rms_speed_error_delta_kmh: float
    adds_transitions: int
    adds_safety_overrides: int
    constraint_regression: bool
    verdict_code: str
    efficiency_claim_accepted: bool


@dataclass(frozen=True)
class ControllerRobustnessPortfolioAggregate:
    """Aggregate robustness result for one ADDS controller."""

    adds_controller_kind: str
    controller_label: str
    run_count: int
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
class ControllerRobustnessFailureSummary:
    """Rejected-run summary for one scenario and ADDS controller."""

    scenario_id: str
    split: str
    adds_controller_kind: str
    controller_label: str
    rejected_runs: int
    total_runs: int
    rejection_rate_percent: float
    worst_relative_fuel_change: float
    maximum_rms_speed_error_delta_kmh: float
    verdict_codes: tuple[str, ...]
    rejected_perturbations: tuple[str, ...]


@dataclass(frozen=True)
class ControllerRobustnessRejectionBreakdown:
    """Rejected-run counts grouped by ADDS controller and verdict code."""

    adds_controller_kind: str
    controller_label: str
    verdict_code: str
    rejected_runs: int
    controller_rejected_runs: int
    rejection_share_percent: float
    affected_scenarios: tuple[str, ...]
    affected_perturbations: tuple[str, ...]


@dataclass(frozen=True)
class ControllerRobustnessPortfolioReport:
    """Machine-readable cross-controller robustness report."""

    controller_kinds: tuple[str, ...]
    scenario_count: int
    perturbation_count: int
    rows: tuple[ControllerRobustnessPortfolioRow, ...]
    aggregates: tuple[ControllerRobustnessPortfolioAggregate, ...]
    insights: tuple[ControllerPortfolioInsight, ...]
    failure_summaries: tuple[ControllerRobustnessFailureSummary, ...]
    rejection_breakdown: tuple[ControllerRobustnessRejectionBreakdown, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "controller_kinds": list(self.controller_kinds),
            "scenario_count": self.scenario_count,
            "perturbation_count": self.perturbation_count,
            "row_count": len(self.rows),
            "aggregates": [asdict(aggregate) for aggregate in self.aggregates],
            "insights": [asdict(insight) for insight in self.insights],
            "failure_summaries": [asdict(summary) for summary in self.failure_summaries],
            "rejection_breakdown": [asdict(item) for item in self.rejection_breakdown],
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
        insights=_portfolio_insights(aggregates, scope_label="catalog"),
    )


def build_controller_robustness_portfolio_report(
    entries: tuple[ScenarioCatalogEntry, ...] | None = None,
    adds_controller_kinds: tuple[str, ...] = SUPPORTED_DASHBOARD_CONTROLLER_KINDS,
) -> ControllerRobustnessPortfolioReport:
    """Build a cross-controller robustness report across the default perturbations."""

    catalog = entries or phase4_scenario_catalog()
    rows: list[ControllerRobustnessPortfolioRow] = []
    for controller_kind in adds_controller_kinds:
        for entry in catalog:
            sensitivity = build_dashboard_sensitivity(
                entry.scenario.scenario_id,
                controller_kind,
                catalog,
            )
            for sensitivity_row in sensitivity.rows:
                rows.append(
                    ControllerRobustnessPortfolioRow(
                        perturbation=sensitivity_row.perturbation,
                        scenario_id=entry.scenario.scenario_id,
                        split=entry.split,
                        description=entry.description,
                        adds_controller_kind=controller_kind,
                        controller_label=_controller_label(controller_kind),
                        mass_scale=sensitivity_row.mass_scale,
                        drag_scale=sensitivity_row.drag_scale,
                        rolling_resistance_scale=sensitivity_row.rolling_resistance_scale,
                        tire_friction_scale=sensitivity_row.tire_friction_scale,
                        grade_offset_percent=sensitivity_row.grade_offset_percent,
                        relative_fuel_change=sensitivity_row.relative_fuel_change,
                        rms_speed_error_delta_kmh=sensitivity_row.rms_speed_error_delta_kmh,
                        adds_transitions=sensitivity_row.adds_transitions,
                        adds_safety_overrides=sensitivity_row.adds_safety_overrides,
                        constraint_regression=sensitivity_row.constraint_regression,
                        verdict_code=sensitivity_row.verdict_code,
                        efficiency_claim_accepted=sensitivity_row.efficiency_claim_accepted,
                    )
                )

    perturbations = {row.perturbation for row in rows}
    aggregates = tuple(
        _aggregate_robustness_rows(controller_kind, tuple(rows))
        for controller_kind in adds_controller_kinds
    )
    return ControllerRobustnessPortfolioReport(
        controller_kinds=adds_controller_kinds,
        scenario_count=len(catalog),
        perturbation_count=len(perturbations),
        rows=tuple(rows),
        aggregates=aggregates,
        insights=_portfolio_insights(aggregates, scope_label="robustness envelope"),
        failure_summaries=_robustness_failure_summaries(tuple(rows)),
        rejection_breakdown=_robustness_rejection_breakdown(tuple(rows)),
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


def write_controller_robustness_portfolio_report(
    output_dir: Path,
    report: ControllerRobustnessPortfolioReport,
) -> tuple[Path, Path]:
    """Write JSON and CSV controller-robustness portfolio artifacts."""

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "controller_robustness_portfolio_report.json"
    csv_path = output_dir / "controller_robustness_portfolio_rows.csv"
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


def _aggregate_robustness_rows(
    controller_kind: str,
    rows: tuple[ControllerRobustnessPortfolioRow, ...],
) -> ControllerRobustnessPortfolioAggregate:
    controller_rows = tuple(row for row in rows if row.adds_controller_kind == controller_kind)
    if not controller_rows:
        return ControllerRobustnessPortfolioAggregate(
            adds_controller_kind=controller_kind,
            controller_label=_controller_label(controller_kind),
            run_count=0,
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
    return ControllerRobustnessPortfolioAggregate(
        adds_controller_kind=controller_kind,
        controller_label=controller_rows[0].controller_label,
        run_count=len(controller_rows),
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


def _controller_label(controller_kind: str) -> str:
    return DASHBOARD_CONTROLLER_LABELS.get(controller_kind, controller_kind)


def _robustness_failure_summaries(
    rows: tuple[ControllerRobustnessPortfolioRow, ...],
) -> tuple[ControllerRobustnessFailureSummary, ...]:
    grouped: dict[tuple[str, str], list[ControllerRobustnessPortfolioRow]] = {}
    for row in rows:
        grouped.setdefault((row.scenario_id, row.adds_controller_kind), []).append(row)

    summaries: list[ControllerRobustnessFailureSummary] = []
    for group_rows in grouped.values():
        rejected_rows = tuple(row for row in group_rows if not row.efficiency_claim_accepted)
        if not rejected_rows:
            continue
        total_runs = len(group_rows)
        first = group_rows[0]
        summaries.append(
            ControllerRobustnessFailureSummary(
                scenario_id=first.scenario_id,
                split=first.split,
                adds_controller_kind=first.adds_controller_kind,
                controller_label=first.controller_label,
                rejected_runs=len(rejected_rows),
                total_runs=total_runs,
                rejection_rate_percent=100.0 * len(rejected_rows) / total_runs,
                worst_relative_fuel_change=max(row.relative_fuel_change for row in group_rows),
                maximum_rms_speed_error_delta_kmh=max(
                    row.rms_speed_error_delta_kmh for row in group_rows
                ),
                verdict_codes=tuple(sorted({row.verdict_code for row in rejected_rows})),
                rejected_perturbations=tuple(sorted(row.perturbation for row in rejected_rows)),
            )
        )

    return tuple(
        sorted(
            summaries,
            key=lambda summary: (
                -summary.rejection_rate_percent,
                -summary.rejected_runs,
                -summary.worst_relative_fuel_change,
                -summary.maximum_rms_speed_error_delta_kmh,
                summary.scenario_id,
                summary.adds_controller_kind,
            ),
        )
    )


def _robustness_rejection_breakdown(
    rows: tuple[ControllerRobustnessPortfolioRow, ...],
) -> tuple[ControllerRobustnessRejectionBreakdown, ...]:
    rejected_rows = tuple(row for row in rows if not row.efficiency_claim_accepted)
    controller_rejection_counts: dict[str, int] = {}
    grouped: dict[tuple[str, str], list[ControllerRobustnessPortfolioRow]] = {}
    for row in rejected_rows:
        controller_rejection_counts[row.adds_controller_kind] = (
            controller_rejection_counts.get(row.adds_controller_kind, 0) + 1
        )
        grouped.setdefault((row.adds_controller_kind, row.verdict_code), []).append(row)

    breakdown: list[ControllerRobustnessRejectionBreakdown] = []
    for (controller_kind, verdict_code), group_rows in grouped.items():
        controller_rejected_runs = controller_rejection_counts[controller_kind]
        breakdown.append(
            ControllerRobustnessRejectionBreakdown(
                adds_controller_kind=controller_kind,
                controller_label=group_rows[0].controller_label,
                verdict_code=verdict_code,
                rejected_runs=len(group_rows),
                controller_rejected_runs=controller_rejected_runs,
                rejection_share_percent=(
                    100.0 * len(group_rows) / controller_rejected_runs
                    if controller_rejected_runs
                    else 0.0
                ),
                affected_scenarios=tuple(sorted({row.scenario_id for row in group_rows})),
                affected_perturbations=tuple(sorted({row.perturbation for row in group_rows})),
            )
        )

    return tuple(
        sorted(
            breakdown,
            key=lambda item: (
                item.adds_controller_kind,
                -item.rejected_runs,
                item.verdict_code,
            ),
        )
    )


def _portfolio_insights(
    aggregates: tuple[ControllerPortfolioAggregate | ControllerRobustnessPortfolioAggregate, ...],
    scope_label: str,
) -> tuple[ControllerPortfolioInsight, ...]:
    if not aggregates:
        return (
            ControllerPortfolioInsight(
                severity="neutral",
                title="No controller results",
                message=f"No controller results were available for the {scope_label}.",
            ),
        )

    ranked = sorted(
        aggregates,
        key=lambda aggregate: (
            -aggregate.acceptance_rate_percent,
            aggregate.mean_relative_fuel_change,
            aggregate.maximum_safety_overrides,
            aggregate.constraint_regression_count,
            aggregate.adds_controller_kind,
        ),
    )
    leader = ranked[0]
    total_runs = _aggregate_run_count(leader)
    insights = [
        ControllerPortfolioInsight(
            severity="positive" if leader.accepted_efficiency_claims else "neutral",
            title="Best current controller",
            message=(
                f"{leader.controller_label} leads the {scope_label} with "
                f"{leader.accepted_efficiency_claims}/{total_runs} accepted efficiency "
                f"claims and {leader.mean_relative_fuel_change:.3f}% mean relative "
                "fuel change."
            ),
        )
    ]

    if len(ranked) > 1:
        runner_up = ranked[1]
        acceptance_gap = leader.acceptance_rate_percent - runner_up.acceptance_rate_percent
        fuel_gap = leader.mean_relative_fuel_change - runner_up.mean_relative_fuel_change
        insights.append(
            ControllerPortfolioInsight(
                severity="neutral",
                title="Margin over next controller",
                message=(
                    f"Compared with {runner_up.controller_label}, the leader changes "
                    f"acceptance rate by {acceptance_gap:.1f} percentage points and "
                    f"mean fuel change by {fuel_gap:.3f} percentage points."
                ),
            )
        )

    if leader.acceptance_rate_percent < 50.0:
        insights.append(
            ControllerPortfolioInsight(
                severity="caution",
                title="Benefit remains condition-dependent",
                message=(
                    f"The leading controller accepts only {leader.acceptance_rate_percent:.1f}% "
                    f"of {scope_label} runs, so the result is not yet broadly robust."
                ),
            )
        )

    if all(
        aggregate.maximum_safety_overrides == 0 and aggregate.constraint_regression_count == 0
        for aggregate in aggregates
    ):
        insights.append(
            ControllerPortfolioInsight(
                severity="positive",
                title="No safety or constraint regression",
                message=(
                    "All compared controllers completed this portfolio without safety "
                    "overrides or hard-constraint regressions."
                ),
            )
        )

    return tuple(insights)


def _aggregate_run_count(
    aggregate: ControllerPortfolioAggregate | ControllerRobustnessPortfolioAggregate,
) -> int:
    if isinstance(aggregate, ControllerRobustnessPortfolioAggregate):
        return aggregate.run_count
    return aggregate.scenario_count
