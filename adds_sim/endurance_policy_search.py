"""Endurance-oriented policy search for race-useful ADDS behavior."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .controllers import RuleBasedADDSController
from .endurance_strategy import (
    EnduranceStrategyConfig,
    EnduranceStrategyReport,
    build_endurance_strategy_report,
)
from .track_lap import run_custom_track_lap_comparison


@dataclass(frozen=True)
class EndurancePolicyCandidate:
    """One interpretable ADDS candidate for endurance strategy search."""

    candidate_id: str
    coast_speed_margin: float
    reconnect_speed_margin: float
    minimum_target_speed_drop: float
    maximum_coast_grade: float

    def controller(self, gear: int) -> RuleBasedADDSController:
        return RuleBasedADDSController(
            gear=gear,
            coast_speed_margin=self.coast_speed_margin,
            reconnect_speed_margin=self.reconnect_speed_margin,
            minimum_target_speed_drop=self.minimum_target_speed_drop,
            maximum_coast_grade=self.maximum_coast_grade,
            name=f"endurance_candidate_{self.candidate_id}",
        )


@dataclass(frozen=True)
class EndurancePolicySearchRow:
    """One candidate's track-lap and endurance-strategy result."""

    candidate: EndurancePolicyCandidate
    verdict: str
    relative_fuel_change: float
    delta_lap_time: float
    delta_completed_laps: int
    delta_pit_stops: int
    lap_equivalent_advantage_seconds: float
    adds_transitions: int
    adds_safety_overrides: int
    adds_stint_laps: int
    minimum_reference_stint_laps_for_one_extra_lap: int | None
    promotion_eligible: bool


@dataclass(frozen=True)
class EndurancePolicySearchReport:
    """Complete endurance policy-search audit."""

    schema_version: str
    config: EnduranceStrategyConfig
    candidates: tuple[EndurancePolicyCandidate, ...]
    rows: tuple[EndurancePolicySearchRow, ...]
    best_candidate: EndurancePolicyCandidate | None
    promotion_passed: bool
    promotion_reasons: tuple[str, ...]
    recommended_next_actions: tuple[str, ...]


def default_endurance_policy_candidates() -> tuple[EndurancePolicyCandidate, ...]:
    """Return a deterministic grid around conservative-to-aggressive ADDS behavior."""

    candidates: list[EndurancePolicyCandidate] = []
    index = 1
    for coast_speed_margin in (0.20, 0.30, 0.40, 0.50, 0.60):
        for minimum_target_speed_drop in (0.25, 0.30, 0.35, 0.45):
            candidates.append(
                EndurancePolicyCandidate(
                    candidate_id=f"E{index:02d}",
                    coast_speed_margin=coast_speed_margin,
                    reconnect_speed_margin=0.1,
                    minimum_target_speed_drop=minimum_target_speed_drop,
                    maximum_coast_grade=0.005,
                )
            )
            index += 1
    return tuple(candidates)


def run_endurance_policy_search(
    config: EnduranceStrategyConfig | None = None,
    candidates: tuple[EndurancePolicyCandidate, ...] | None = None,
) -> EndurancePolicySearchReport:
    """Search for a policy that turns fuel saving into endurance value."""

    strategy_config = config or EnduranceStrategyConfig()
    candidate_grid = candidates or default_endurance_policy_candidates()
    rows = tuple(_evaluate_candidate(strategy_config, candidate) for candidate in candidate_grid)
    ranked_rows = tuple(sorted(rows, key=_ranking_key))
    eligible_rows = tuple(row for row in ranked_rows if row.promotion_eligible)
    best_candidate = eligible_rows[0].candidate if eligible_rows else None
    promotion_passed = best_candidate is not None
    promotion_reasons = _promotion_reasons(ranked_rows, promotion_passed)
    return EndurancePolicySearchReport(
        schema_version="1.0",
        config=strategy_config,
        candidates=candidate_grid,
        rows=ranked_rows,
        best_candidate=best_candidate,
        promotion_passed=promotion_passed,
        promotion_reasons=promotion_reasons,
        recommended_next_actions=_recommended_next_actions(ranked_rows, promotion_passed),
    )


def write_endurance_policy_search_report(
    output_dir: Path,
    report: EndurancePolicySearchReport,
) -> tuple[Path, Path]:
    """Write endurance policy-search JSON and CSV artifacts."""

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "endurance_policy_search_report.json"
    csv_path = output_dir / "endurance_policy_search_rows.csv"

    with json_path.open("w", encoding="utf-8") as file:
        json.dump(_report_payload(report), file, indent=2)

    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=(
                "candidate_id",
                "coast_speed_margin",
                "minimum_target_speed_drop",
                "verdict",
                "relative_fuel_change",
                "delta_lap_time",
                "delta_completed_laps",
                "delta_pit_stops",
                "lap_equivalent_advantage_seconds",
                "adds_transitions",
                "adds_safety_overrides",
                "adds_stint_laps",
                "minimum_reference_stint_laps_for_one_extra_lap",
                "promotion_eligible",
            ),
        )
        writer.writeheader()
        for row in report.rows:
            writer.writerow(_row_payload(row))
    return json_path, csv_path


def _evaluate_candidate(
    config: EnduranceStrategyConfig,
    candidate: EndurancePolicyCandidate,
) -> EndurancePolicySearchRow:
    provisional_track_lap = run_custom_track_lap_comparison(
        adds_controller=candidate.controller(gear=5),
        adds_controller_kind=f"endurance_candidate_{candidate.candidate_id}",
    )
    report = build_endurance_strategy_report(
        provisional_track_lap,
        EnduranceStrategyConfig(
            race_name=config.race_name,
            race_duration_hours=config.race_duration_hours,
            reference_stint_laps=config.reference_stint_laps,
            pit_stop_loss_seconds=config.pit_stop_loss_seconds,
            adds_controller_kind="rule_based",
        ),
    )
    return _row_from_report(candidate, report)


def _row_from_report(
    candidate: EndurancePolicyCandidate,
    report: EnduranceStrategyReport,
) -> EndurancePolicySearchRow:
    comparison = report.track_lap.comparison
    relative_fuel_change = float(comparison.deltas["relative_fuel_change"])
    delta_lap_time = float(comparison.deltas["delta_travel_time"])
    delta_completed_laps = int(report.deltas["delta_completed_laps"])
    lap_equivalent_advantage = float(report.deltas["lap_equivalent_advantage_seconds"])
    promotion_eligible = (
        report.verdict in {"STRATEGIC_ADVANTAGE", "DISTANCE_ADVANTAGE", "TIME_ADVANTAGE"}
        and relative_fuel_change < -0.1
        and delta_completed_laps >= 0
        and int(comparison.adds_summary["safety_override_count"]) == 0
        and not bool(comparison.deltas["constraint_regression"])
    )
    return EndurancePolicySearchRow(
        candidate=candidate,
        verdict=report.verdict,
        relative_fuel_change=relative_fuel_change,
        delta_lap_time=delta_lap_time,
        delta_completed_laps=delta_completed_laps,
        delta_pit_stops=int(report.deltas["delta_pit_stops"]),
        lap_equivalent_advantage_seconds=lap_equivalent_advantage,
        adds_transitions=int(comparison.adds_summary["mode_transition_count"]),
        adds_safety_overrides=int(comparison.adds_summary["safety_override_count"]),
        adds_stint_laps=report.adds.stint_laps,
        minimum_reference_stint_laps_for_one_extra_lap=(
            report.thresholds.minimum_reference_stint_laps_for_one_extra_lap
        ),
        promotion_eligible=promotion_eligible,
    )


def _ranking_key(row: EndurancePolicySearchRow) -> tuple[object, ...]:
    return (
        not row.promotion_eligible,
        row.delta_completed_laps < 0,
        -row.delta_completed_laps,
        -row.lap_equivalent_advantage_seconds,
        row.relative_fuel_change >= -0.1,
        row.delta_lap_time,
        row.relative_fuel_change,
        row.candidate.candidate_id,
    )


def _promotion_reasons(
    rows: tuple[EndurancePolicySearchRow, ...],
    promotion_passed: bool,
) -> tuple[str, ...]:
    if promotion_passed:
        return ("At least one candidate turned ADDS fuel saving into a race-useful endurance result.",)

    best = rows[0]
    reasons = [
        "No searched candidate produced a race-useful endurance advantage.",
        f"Best-ranked candidate {best.candidate.candidate_id} verdict: {best.verdict}.",
    ]
    if best.relative_fuel_change >= -0.1:
        reasons.append("The best non-losing candidates are effectively neutral and do not save meaningful fuel.")
    if any(row.relative_fuel_change < -0.1 and row.delta_completed_laps < 0 for row in rows):
        reasons.append("Candidates that save fuel still lose completed laps in the 24h extrapolation.")
    return tuple(reasons)


def _recommended_next_actions(
    rows: tuple[EndurancePolicySearchRow, ...],
    promotion_passed: bool,
) -> tuple[str, ...]:
    if promotion_passed:
        return (
            "Promote the best candidate to dashboard review and robustness testing.",
            "Validate the result under longer tracks, pit-loss sweeps, and perturbations.",
        )
    best_saving = min(rows, key=lambda row: row.relative_fuel_change)
    best_non_losing = next((row for row in rows if row.delta_completed_laps >= 0), rows[0])
    return (
        "Do not promote a new ADDS race policy yet.",
        (
            "Reduce lap-time penalty before pursuing larger endurance claims; "
            f"best fuel-saving candidate {best_saving.candidate.candidate_id} saves "
            f"{abs(best_saving.relative_fuel_change):.3f}% but has "
            f"{best_saving.delta_completed_laps} completed laps."
        ),
        (
            "Use the best non-losing candidate as a guardrail; "
            f"{best_non_losing.candidate.candidate_id} has verdict {best_non_losing.verdict} "
            f"and {best_non_losing.relative_fuel_change:.3f}% fuel change."
        ),
    )


def _report_payload(report: EndurancePolicySearchReport) -> dict[str, object]:
    return {
        "schema_version": report.schema_version,
        "config": asdict(report.config),
        "candidates": [asdict(candidate) for candidate in report.candidates],
        "rows": [_row_payload(row) for row in report.rows],
        "best_candidate": asdict(report.best_candidate) if report.best_candidate else None,
        "promotion_passed": report.promotion_passed,
        "promotion_reasons": list(report.promotion_reasons),
        "recommended_next_actions": list(report.recommended_next_actions),
    }


def _row_payload(row: EndurancePolicySearchRow) -> dict[str, object]:
    return {
        "candidate_id": row.candidate.candidate_id,
        "coast_speed_margin": row.candidate.coast_speed_margin,
        "minimum_target_speed_drop": row.candidate.minimum_target_speed_drop,
        "verdict": row.verdict,
        "relative_fuel_change": row.relative_fuel_change,
        "delta_lap_time": row.delta_lap_time,
        "delta_completed_laps": row.delta_completed_laps,
        "delta_pit_stops": row.delta_pit_stops,
        "lap_equivalent_advantage_seconds": row.lap_equivalent_advantage_seconds,
        "adds_transitions": row.adds_transitions,
        "adds_safety_overrides": row.adds_safety_overrides,
        "adds_stint_laps": row.adds_stint_laps,
        "minimum_reference_stint_laps_for_one_extra_lap": (
            row.minimum_reference_stint_laps_for_one_extra_lap
        ),
        "promotion_eligible": row.promotion_eligible,
    }
