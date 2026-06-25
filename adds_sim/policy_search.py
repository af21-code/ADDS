"""Leakage-resistant offline search for interpretable ADDS policy parameters."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .comparison import run_paired_comparison
from .controllers import ConventionalBaselineController, RuleBasedADDSController
from .defaults import default_simulation_config
from .robustness import (
    apply_perturbation_to_config,
    apply_perturbation_to_scenario,
    default_perturbations,
)
from .scenario_catalog import ScenarioCatalogEntry, entries_by_split, phase4_scenario_catalog
from .simulator import LongitudinalSimulator


@dataclass(frozen=True)
class PolicyCandidate:
    """One interpretable policy configuration in the fixed search grid."""

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
            name=f"offline_candidate_{self.candidate_id}",
        )


@dataclass(frozen=True)
class PolicySearchResult:
    """One candidate result for one scenario and perturbation."""

    candidate_id: str
    stage: str
    scenario_id: str
    perturbation: str
    relative_fuel_change: float
    delta_rms_speed_error_kmh: float
    mode_transition_count: int
    safety_override_count: int
    constraint_regression: bool
    relative_fuel_change_vs_rule_based: float
    passes_stage_gates: bool


@dataclass(frozen=True)
class PolicyCandidateSummary:
    """Train-stage aggregate used to rank one candidate."""

    candidate: PolicyCandidate
    mean_relative_fuel_change: float
    worst_relative_fuel_change: float
    eligible: bool


@dataclass(frozen=True)
class PolicySearchReport:
    """Complete train, validation, and frozen-test policy-search audit."""

    candidates: tuple[PolicyCandidate, ...]
    train_ranking: tuple[PolicyCandidateSummary, ...]
    validation_results: tuple[PolicySearchResult, ...]
    test_results: tuple[PolicySearchResult, ...]
    stress_results: tuple[PolicySearchResult, ...]
    selected_candidate: PolicyCandidate | None
    promotion_passed: bool
    promotion_reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "protocol": {
                "train": "Rank on train scenarios across the default perturbation envelope.",
                "validation": "Select the first ranked candidate that passes validation gates.",
                "test": "Audit the selected candidate once on the frozen test split.",
            },
            "candidates": [asdict(candidate) for candidate in self.candidates],
            "train_ranking": [asdict(summary) for summary in self.train_ranking],
            "validation_results": [asdict(result) for result in self.validation_results],
            "test_results": [asdict(result) for result in self.test_results],
            "stress_results": [asdict(result) for result in self.stress_results],
            "selected_candidate": asdict(self.selected_candidate) if self.selected_candidate else None,
            "promotion_passed": self.promotion_passed,
            "promotion_reasons": list(self.promotion_reasons),
        }


def default_policy_candidates() -> tuple[PolicyCandidate, ...]:
    """Return the small predeclared search grid in deterministic order."""

    candidates: list[PolicyCandidate] = []
    index = 1
    for coast_speed_margin in (0.4, 0.5, 0.6):
        for minimum_target_speed_drop in (0.25, 0.35):
            candidates.append(
                PolicyCandidate(
                    candidate_id=f"C{index:02d}",
                    coast_speed_margin=coast_speed_margin,
                    reconnect_speed_margin=0.1,
                    minimum_target_speed_drop=minimum_target_speed_drop,
                    maximum_coast_grade=0.005,
                )
            )
            index += 1
    return tuple(candidates)


def run_offline_policy_search(
    entries: tuple[ScenarioCatalogEntry, ...] | None = None,
    candidates: tuple[PolicyCandidate, ...] | None = None,
) -> PolicySearchReport:
    """Run train ranking, validation selection, and a frozen-test promotion audit."""

    catalog = entries or phase4_scenario_catalog()
    grouped = entries_by_split(catalog)
    candidate_grid = candidates or default_policy_candidates()
    train_results: dict[str, tuple[PolicySearchResult, ...]] = {}
    summaries: list[PolicyCandidateSummary] = []

    for candidate in candidate_grid:
        results = _evaluate_train_candidate(candidate, grouped["train"])
        train_results[candidate.candidate_id] = results
        summaries.append(
            PolicyCandidateSummary(
                candidate=candidate,
                mean_relative_fuel_change=sum(result.relative_fuel_change for result in results)
                / len(results),
                worst_relative_fuel_change=max(result.relative_fuel_change for result in results),
                eligible=all(result.passes_stage_gates for result in results),
            )
        )

    ranking = tuple(
        sorted(
            summaries,
            key=lambda summary: (
                not summary.eligible,
                summary.mean_relative_fuel_change,
                summary.candidate.candidate_id,
            ),
        )
    )

    validation_results: list[PolicySearchResult] = []
    selected_candidate: PolicyCandidate | None = None
    for summary in ranking:
        if not summary.eligible:
            continue
        results = _evaluate_nominal_candidate(
            summary.candidate,
            grouped["validation"],
            stage="validation",
        )
        validation_results.extend(results)
        has_validated_benefit = any(
            result.relative_fuel_change <= -1.0 for result in results
        )
        if all(result.passes_stage_gates for result in results) and has_validated_benefit:
            selected_candidate = summary.candidate
            break

    if selected_candidate is None:
        return PolicySearchReport(
            candidates=candidate_grid,
            train_ranking=ranking,
            validation_results=tuple(validation_results),
            test_results=(),
            stress_results=(),
            selected_candidate=None,
            promotion_passed=False,
            promotion_reasons=("No train-ranked candidate passed the validation promotion gates.",),
        )

    test_results = _evaluate_nominal_candidate(
        selected_candidate,
        grouped["test"],
        stage="test",
    )
    stress_results = _evaluate_nominal_candidate(
        selected_candidate,
        grouped["stress"],
        stage="stress",
    )
    reasons: list[str] = []
    if not all(result.passes_stage_gates for result in test_results):
        reasons.append("The selected candidate violated at least one frozen-test gate.")
    if not all(result.passes_stage_gates for result in stress_results):
        reasons.append("The selected candidate violated at least one stress-audit gate.")
    minimum_improvement_percentage_points = 0.5
    if not any(
        result.relative_fuel_change_vs_rule_based <= -minimum_improvement_percentage_points
        for result in test_results
    ):
        reasons.append(
            "The selected candidate did not improve fuel use over the rule-based "
            f"baseline by at least {minimum_improvement_percentage_points:.1f} percentage points."
        )
    promotion_passed = not reasons
    if promotion_passed:
        reasons.append("The selected candidate passed every frozen-test promotion criterion.")

    return PolicySearchReport(
        candidates=candidate_grid,
        train_ranking=ranking,
        validation_results=tuple(validation_results),
        test_results=test_results,
        stress_results=stress_results,
        selected_candidate=selected_candidate,
        promotion_passed=promotion_passed,
        promotion_reasons=tuple(reasons),
    )


def write_policy_search_report(path: Path, report: PolicySearchReport) -> Path:
    """Write one reproducible policy-search report."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _evaluate_train_candidate(
    candidate: PolicyCandidate,
    entries: tuple[ScenarioCatalogEntry, ...],
) -> tuple[PolicySearchResult, ...]:
    base_config = default_simulation_config()
    results: list[PolicySearchResult] = []
    for perturbation in default_perturbations():
        config = apply_perturbation_to_config(base_config, perturbation)
        simulator = LongitudinalSimulator(config)
        for entry in entries:
            scenario = apply_perturbation_to_scenario(entry.scenario, perturbation)
            results.append(
                _evaluate_candidate(
                    simulator,
                    entry,
                    scenario,
                    candidate,
                    stage="train",
                    perturbation=perturbation.name,
                )
            )
    return tuple(results)


def _evaluate_nominal_candidate(
    candidate: PolicyCandidate,
    entries: tuple[ScenarioCatalogEntry, ...],
    stage: str,
) -> tuple[PolicySearchResult, ...]:
    simulator = LongitudinalSimulator(default_simulation_config())
    return tuple(
        _evaluate_candidate(
            simulator,
            entry,
            entry.scenario,
            candidate,
            stage=stage,
            perturbation="nominal",
        )
        for entry in entries
    )


def _evaluate_candidate(
    simulator: LongitudinalSimulator,
    entry: ScenarioCatalogEntry,
    scenario,
    candidate: PolicyCandidate,
    stage: str,
    perturbation: str,
) -> PolicySearchResult:
    conventional = ConventionalBaselineController(scenario.initial_gear)
    candidate_comparison = run_paired_comparison(
        simulator,
        scenario,
        conventional,
        candidate.controller(scenario.initial_gear),
    )
    rule_comparison = run_paired_comparison(
        simulator,
        scenario,
        ConventionalBaselineController(scenario.initial_gear),
        RuleBasedADDSController(scenario.initial_gear),
    )
    relative_fuel_change = float(candidate_comparison.deltas["relative_fuel_change"])
    rms_delta_kmh = float(candidate_comparison.deltas["delta_rms_speed_error"]) * 3.6
    transitions = int(candidate_comparison.adds_summary["mode_transition_count"])
    safety_overrides = int(candidate_comparison.adds_summary["safety_override_count"])
    constraint_regression = bool(candidate_comparison.deltas["constraint_regression"])
    passes = (
        relative_fuel_change <= 0.0
        and rms_delta_kmh <= 1.0
        and transitions <= 5
        and safety_overrides == 0
        and not constraint_regression
    )
    return PolicySearchResult(
        candidate_id=candidate.candidate_id,
        stage=stage,
        scenario_id=entry.scenario.scenario_id,
        perturbation=perturbation,
        relative_fuel_change=relative_fuel_change,
        delta_rms_speed_error_kmh=rms_delta_kmh,
        mode_transition_count=transitions,
        safety_override_count=safety_overrides,
        constraint_regression=constraint_regression,
        relative_fuel_change_vs_rule_based=(
            relative_fuel_change - float(rule_comparison.deltas["relative_fuel_change"])
        ),
        passes_stage_gates=passes,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the ADDS offline policy-search audit.")
    parser.add_argument("output_path", type=Path, help="JSON report output path.")
    args = parser.parse_args()
    report = run_offline_policy_search()
    path = write_policy_search_report(args.output_path, report)
    print(f"report: {path}")
    print(f"selected_candidate: {report.selected_candidate.candidate_id if report.selected_candidate else 'none'}")
    print(f"promotion_passed: {report.promotion_passed}")


if __name__ == "__main__":
    main()
