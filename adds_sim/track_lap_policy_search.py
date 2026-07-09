"""Track-lap focused search for reducing ADDS sector time penalties."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .controllers import OfflineOptimizedADDSController, RuleBasedADDSController
from .track_lap import run_custom_track_lap_comparison
from .track_lap_analysis import TrackLapSectorAnalysis, build_track_lap_sector_analysis


@dataclass(frozen=True)
class TrackLapPolicyCandidate:
    """One interpretable controller candidate for track-lap penalty reduction."""

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
            name=f"track_lap_candidate_{self.candidate_id}",
        )


@dataclass(frozen=True)
class TrackLapPolicySearchRow:
    """One candidate result against the track-lap sector baseline."""

    candidate: TrackLapPolicyCandidate
    relative_fuel_change: float
    delta_lap_time: float
    adds_transitions: int
    adds_safety_overrides: int
    worst_time_loss_sector_name: str
    worst_time_loss_delta: float
    best_fuel_saving_sector_name: str
    best_fuel_saving_delta_kg: float
    lap_time_improvement_vs_baseline: float
    worst_sector_improvement_vs_baseline: float
    promotion_eligible: bool


@dataclass(frozen=True)
class TrackLapPolicySearchReport:
    """Complete track-lap policy-search diagnostic report."""

    schema_version: str
    baseline_controller_kind: str
    baseline_relative_fuel_change: float
    baseline_delta_lap_time: float
    baseline_worst_sector_name: str
    baseline_worst_sector_delta: float
    candidates: tuple[TrackLapPolicyCandidate, ...]
    rows: tuple[TrackLapPolicySearchRow, ...]
    best_candidate: TrackLapPolicyCandidate | None
    promotion_passed: bool
    promotion_reasons: tuple[str, ...]
    recommended_next_actions: tuple[str, ...]


def default_track_lap_policy_candidates() -> tuple[TrackLapPolicyCandidate, ...]:
    """Return a deterministic grid around the current track-lap controller."""

    candidates: list[TrackLapPolicyCandidate] = []
    index = 1
    for coast_speed_margin in (0.30, 0.40, 0.50, 0.60):
        for reconnect_speed_margin in (0.05, 0.10, 0.20):
            for minimum_target_speed_drop in (0.25, 0.35, 0.45):
                candidates.append(
                    TrackLapPolicyCandidate(
                        candidate_id=f"T{index:02d}",
                        coast_speed_margin=coast_speed_margin,
                        reconnect_speed_margin=reconnect_speed_margin,
                        minimum_target_speed_drop=minimum_target_speed_drop,
                        maximum_coast_grade=0.005,
                    )
                )
                index += 1
    return tuple(candidates)


def run_track_lap_policy_search(
    candidates: tuple[TrackLapPolicyCandidate, ...] | None = None,
) -> TrackLapPolicySearchReport:
    """Search for a track-lap policy that reduces time penalty without losing fuel value."""

    candidate_grid = candidates or default_track_lap_policy_candidates()
    baseline = run_custom_track_lap_comparison(
        adds_controller=OfflineOptimizedADDSController(gear=5),
        adds_controller_kind="offline_optimized",
    )
    baseline_analysis = build_track_lap_sector_analysis(baseline)
    baseline_worst = _require_worst_sector(baseline_analysis)
    baseline_relative_fuel_change = float(baseline.comparison.deltas["relative_fuel_change"])
    baseline_delta_lap_time = float(baseline.comparison.deltas["delta_travel_time"])

    rows = tuple(
        _evaluate_candidate(
            candidate,
            baseline_delta_lap_time=baseline_delta_lap_time,
            baseline_worst_sector_delta=baseline_worst.delta_time,
        )
        for candidate in candidate_grid
    )
    ranked_rows = tuple(sorted(rows, key=_ranking_key))
    eligible_rows = tuple(row for row in ranked_rows if row.promotion_eligible)
    best_candidate = eligible_rows[0].candidate if eligible_rows else None
    promotion_passed = best_candidate is not None
    return TrackLapPolicySearchReport(
        schema_version="1.0",
        baseline_controller_kind="offline_optimized",
        baseline_relative_fuel_change=baseline_relative_fuel_change,
        baseline_delta_lap_time=baseline_delta_lap_time,
        baseline_worst_sector_name=baseline_worst.sector.name,
        baseline_worst_sector_delta=baseline_worst.delta_time,
        candidates=candidate_grid,
        rows=ranked_rows,
        best_candidate=best_candidate,
        promotion_passed=promotion_passed,
        promotion_reasons=_promotion_reasons(ranked_rows, promotion_passed),
        recommended_next_actions=_recommended_next_actions(ranked_rows, promotion_passed),
    )


def write_track_lap_policy_search_report(
    output_dir: Path,
    report: TrackLapPolicySearchReport,
) -> tuple[Path, Path]:
    """Write track-lap policy-search JSON and CSV artifacts."""

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "track_lap_policy_search_report.json"
    csv_path = output_dir / "track_lap_policy_search_rows.csv"

    with json_path.open("w", encoding="utf-8") as file:
        json.dump(_report_payload(report), file, indent=2)

    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=(
                "candidate_id",
                "coast_speed_margin",
                "reconnect_speed_margin",
                "minimum_target_speed_drop",
                "relative_fuel_change",
                "delta_lap_time",
                "adds_transitions",
                "adds_safety_overrides",
                "worst_time_loss_sector_name",
                "worst_time_loss_delta",
                "best_fuel_saving_sector_name",
                "best_fuel_saving_delta_kg",
                "lap_time_improvement_vs_baseline",
                "worst_sector_improvement_vs_baseline",
                "promotion_eligible",
            ),
        )
        writer.writeheader()
        for row in report.rows:
            writer.writerow(_row_payload(row))
    return json_path, csv_path


def _evaluate_candidate(
    candidate: TrackLapPolicyCandidate,
    baseline_delta_lap_time: float,
    baseline_worst_sector_delta: float,
) -> TrackLapPolicySearchRow:
    track_lap = run_custom_track_lap_comparison(
        adds_controller=candidate.controller(gear=5),
        adds_controller_kind=f"track_lap_candidate_{candidate.candidate_id}",
    )
    analysis = build_track_lap_sector_analysis(track_lap)
    worst = analysis.worst_time_loss_sector
    best_fuel = analysis.best_fuel_saving_sector
    relative_fuel_change = float(track_lap.comparison.deltas["relative_fuel_change"])
    delta_lap_time = float(track_lap.comparison.deltas["delta_travel_time"])
    lap_time_improvement = baseline_delta_lap_time - delta_lap_time
    worst_sector_delta = worst.delta_time if worst else 0.0
    worst_sector_improvement = baseline_worst_sector_delta - worst_sector_delta
    promotion_eligible = (
        relative_fuel_change <= -1.0
        and lap_time_improvement >= 0.04
        and worst_sector_improvement >= 0.015
        and int(track_lap.comparison.adds_summary["safety_override_count"]) == 0
        and not bool(track_lap.comparison.deltas["constraint_regression"])
    )
    return TrackLapPolicySearchRow(
        candidate=candidate,
        relative_fuel_change=relative_fuel_change,
        delta_lap_time=delta_lap_time,
        adds_transitions=int(track_lap.comparison.adds_summary["mode_transition_count"]),
        adds_safety_overrides=int(track_lap.comparison.adds_summary["safety_override_count"]),
        worst_time_loss_sector_name=worst.sector.name if worst else "",
        worst_time_loss_delta=worst_sector_delta,
        best_fuel_saving_sector_name=best_fuel.sector.name if best_fuel else "",
        best_fuel_saving_delta_kg=best_fuel.delta_fuel_kg if best_fuel else 0.0,
        lap_time_improvement_vs_baseline=lap_time_improvement,
        worst_sector_improvement_vs_baseline=worst_sector_improvement,
        promotion_eligible=promotion_eligible,
    )


def _ranking_key(row: TrackLapPolicySearchRow) -> tuple[object, ...]:
    return (
        not row.promotion_eligible,
        row.worst_time_loss_delta,
        row.delta_lap_time,
        row.candidate.coast_speed_margin,
        row.candidate.minimum_target_speed_drop,
        row.relative_fuel_change,
        row.candidate.candidate_id,
    )


def _promotion_reasons(
    rows: tuple[TrackLapPolicySearchRow, ...],
    promotion_passed: bool,
) -> tuple[str, ...]:
    best = rows[0]
    if promotion_passed:
        return (
            f"Candidate {best.candidate.candidate_id} reduced the worst sector penalty "
            f"by {best.worst_sector_improvement_vs_baseline:.3f} s while keeping "
            f"{abs(best.relative_fuel_change):.3f}% simulated fuel saving.",
            f"Lap-time penalty improved by {best.lap_time_improvement_vs_baseline:.3f} s versus the offline baseline.",
        )
    return (
        "No candidate met the track-lap promotion gates.",
        f"Best-ranked candidate {best.candidate.candidate_id} still missed at least one gate.",
    )


def _recommended_next_actions(
    rows: tuple[TrackLapPolicySearchRow, ...],
    promotion_passed: bool,
) -> tuple[str, ...]:
    best = rows[0]
    if promotion_passed:
        return (
            f"Promote candidate {best.candidate.candidate_id} as the track-lap balanced controller variant.",
            f"Use {best.worst_time_loss_sector_name} as the regression sector for future controller changes.",
            "Re-run endurance policy search with the track-lap balanced variant before making race-strategy claims.",
        )
    return (
        "Keep the offline optimized controller as the active track-lap baseline.",
        "Expand the candidate grid only after adding a richer preview model.",
    )


def _require_worst_sector(analysis: TrackLapSectorAnalysis):
    if analysis.worst_time_loss_sector is None:
        raise ValueError("track-lap sector analysis did not produce a worst time-loss sector")
    return analysis.worst_time_loss_sector


def _report_payload(report: TrackLapPolicySearchReport) -> dict[str, object]:
    return {
        "schema_version": report.schema_version,
        "baseline_controller_kind": report.baseline_controller_kind,
        "baseline_relative_fuel_change": report.baseline_relative_fuel_change,
        "baseline_delta_lap_time": report.baseline_delta_lap_time,
        "baseline_worst_sector_name": report.baseline_worst_sector_name,
        "baseline_worst_sector_delta": report.baseline_worst_sector_delta,
        "candidates": [asdict(candidate) for candidate in report.candidates],
        "rows": [_row_payload(row) for row in report.rows],
        "best_candidate": asdict(report.best_candidate) if report.best_candidate else None,
        "promotion_passed": report.promotion_passed,
        "promotion_reasons": list(report.promotion_reasons),
        "recommended_next_actions": list(report.recommended_next_actions),
    }


def _row_payload(row: TrackLapPolicySearchRow) -> dict[str, object]:
    return {
        "candidate_id": row.candidate.candidate_id,
        "coast_speed_margin": row.candidate.coast_speed_margin,
        "reconnect_speed_margin": row.candidate.reconnect_speed_margin,
        "minimum_target_speed_drop": row.candidate.minimum_target_speed_drop,
        "relative_fuel_change": row.relative_fuel_change,
        "delta_lap_time": row.delta_lap_time,
        "adds_transitions": row.adds_transitions,
        "adds_safety_overrides": row.adds_safety_overrides,
        "worst_time_loss_sector_name": row.worst_time_loss_sector_name,
        "worst_time_loss_delta": row.worst_time_loss_delta,
        "best_fuel_saving_sector_name": row.best_fuel_saving_sector_name,
        "best_fuel_saving_delta_kg": row.best_fuel_saving_delta_kg,
        "lap_time_improvement_vs_baseline": row.lap_time_improvement_vs_baseline,
        "worst_sector_improvement_vs_baseline": row.worst_sector_improvement_vs_baseline,
        "promotion_eligible": row.promotion_eligible,
    }
