"""Robustness and sensitivity evaluation helpers."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from .comparison import run_paired_comparison
from .controllers import ConventionalBaselineController, RuleBasedADDSController
from .defaults import default_simulation_config
from .profiles import OffsetProfile
from .scenario_catalog import ScenarioCatalogEntry, phase4_scenario_catalog
from .simulator import LongitudinalSimulator, Scenario, SimulationConfig


@dataclass(frozen=True)
class ParameterPerturbation:
    """Multiplicative and additive uncertainty factors for one robust run."""

    name: str
    mass_scale: float = 1.0
    drag_scale: float = 1.0
    rolling_resistance_scale: float = 1.0
    tire_friction_scale: float = 1.0
    grade_offset: float = 0.0


@dataclass(frozen=True)
class RobustnessRun:
    """One scenario under one parameter perturbation."""

    perturbation: str
    scenario_id: str
    split: str
    completed_successfully: bool
    constraint_regression: bool
    delta_fuel_used: float
    relative_fuel_change: float
    delta_rms_speed_error: float
    adds_safety_override_count: int
    adds_mode_transition_count: int


@dataclass(frozen=True)
class RobustnessReport:
    """Aggregated robust evaluation report."""

    perturbations: tuple[ParameterPerturbation, ...]
    runs: tuple[RobustnessRun, ...]
    completed_successfully: bool
    constraint_regression_count: int
    max_adds_safety_overrides: int
    min_relative_fuel_change: float
    max_relative_fuel_change: float
    max_delta_rms_speed_error: float

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "perturbations": [asdict(perturbation) for perturbation in self.perturbations],
            "runs": [asdict(run) for run in self.runs],
            "completed_successfully": self.completed_successfully,
            "constraint_regression_count": self.constraint_regression_count,
            "max_adds_safety_overrides": self.max_adds_safety_overrides,
            "min_relative_fuel_change": self.min_relative_fuel_change,
            "max_relative_fuel_change": self.max_relative_fuel_change,
            "max_delta_rms_speed_error": self.max_delta_rms_speed_error,
        }


def default_perturbations() -> tuple[ParameterPerturbation, ...]:
    """Return a compact deterministic uncertainty envelope."""

    return (
        ParameterPerturbation(name="nominal"),
        ParameterPerturbation(name="heavy_payload", mass_scale=1.15),
        ParameterPerturbation(name="light_payload", mass_scale=0.90),
        ParameterPerturbation(name="high_drag", drag_scale=1.15),
        ParameterPerturbation(name="high_rolling_resistance", rolling_resistance_scale=1.20),
        ParameterPerturbation(name="low_grip", tire_friction_scale=0.75),
        ParameterPerturbation(name="grade_bias_uphill", grade_offset=0.01),
        ParameterPerturbation(
            name="combined_adverse",
            mass_scale=1.15,
            drag_scale=1.10,
            rolling_resistance_scale=1.15,
            tire_friction_scale=0.75,
            grade_offset=0.005,
        ),
    )


def apply_perturbation_to_config(config: SimulationConfig, perturbation: ParameterPerturbation) -> SimulationConfig:
    """Return a config copy modified by one perturbation."""

    return replace(
        config,
        vehicle=replace(
            config.vehicle,
            mass=config.vehicle.mass * perturbation.mass_scale,
            drag_coefficient=config.vehicle.drag_coefficient * perturbation.drag_scale,
            rolling_resistance_coefficient=config.vehicle.rolling_resistance_coefficient
            * perturbation.rolling_resistance_scale,
        ),
        environment=replace(
            config.environment,
            tire_friction_coefficient=config.environment.tire_friction_coefficient
            * perturbation.tire_friction_scale,
        ),
    )


def apply_perturbation_to_scenario(scenario: Scenario, perturbation: ParameterPerturbation) -> Scenario:
    """Return a scenario copy modified by one perturbation."""

    if perturbation.grade_offset == 0.0:
        return scenario
    return replace(scenario, grade_profile=OffsetProfile(scenario.grade_profile, perturbation.grade_offset))


def run_robustness_evaluation(
    entries: tuple[ScenarioCatalogEntry, ...] | None = None,
    perturbations: tuple[ParameterPerturbation, ...] | None = None,
    base_config: SimulationConfig | None = None,
) -> RobustnessReport:
    """Run paired comparisons across scenario and parameter perturbations."""

    entries = entries if entries is not None else phase4_scenario_catalog()
    perturbations = perturbations if perturbations is not None else default_perturbations()
    base_config = base_config if base_config is not None else default_simulation_config()

    runs: list[RobustnessRun] = []
    for perturbation in perturbations:
        config = apply_perturbation_to_config(base_config, perturbation)
        simulator = LongitudinalSimulator(config)
        for entry in entries:
            scenario = apply_perturbation_to_scenario(entry.scenario, perturbation)
            comparison = run_paired_comparison(
                simulator,
                scenario,
                ConventionalBaselineController(scenario.initial_gear),
                RuleBasedADDSController(scenario.initial_gear),
            )
            completed = bool(comparison.conventional_summary["completed_successfully"]) and bool(
                comparison.adds_summary["completed_successfully"]
            )
            runs.append(
                RobustnessRun(
                    perturbation=perturbation.name,
                    scenario_id=scenario.scenario_id,
                    split=entry.split,
                    completed_successfully=completed,
                    constraint_regression=bool(comparison.deltas["constraint_regression"]),
                    delta_fuel_used=float(comparison.deltas["delta_fuel_used"]),
                    relative_fuel_change=float(comparison.deltas["relative_fuel_change"]),
                    delta_rms_speed_error=float(comparison.deltas["delta_rms_speed_error"]),
                    adds_safety_override_count=int(comparison.adds_summary["safety_override_count"]),
                    adds_mode_transition_count=int(comparison.adds_summary["mode_transition_count"]),
                )
            )

    return _summarize_robustness(perturbations, tuple(runs))


def write_robustness_report(output_dir: Path, report: RobustnessReport) -> tuple[Path, Path]:
    """Write JSON and CSV robustness reports."""

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "robustness_report.json"
    csv_path = output_dir / "robustness_runs.csv"
    json_path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with csv_path.open("w", newline="", encoding="utf-8") as file:
        fieldnames = tuple(asdict(report.runs[0]).keys()) if report.runs else ()
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for run in report.runs:
            writer.writerow(asdict(run))
    return json_path, csv_path


def _summarize_robustness(
    perturbations: tuple[ParameterPerturbation, ...],
    runs: tuple[RobustnessRun, ...],
) -> RobustnessReport:
    if not runs:
        return RobustnessReport(
            perturbations=perturbations,
            runs=(),
            completed_successfully=False,
            constraint_regression_count=0,
            max_adds_safety_overrides=0,
            min_relative_fuel_change=0.0,
            max_relative_fuel_change=0.0,
            max_delta_rms_speed_error=0.0,
        )
    return RobustnessReport(
        perturbations=perturbations,
        runs=runs,
        completed_successfully=all(run.completed_successfully for run in runs),
        constraint_regression_count=sum(1 for run in runs if run.constraint_regression),
        max_adds_safety_overrides=max(run.adds_safety_override_count for run in runs),
        min_relative_fuel_change=min(run.relative_fuel_change for run in runs),
        max_relative_fuel_change=max(run.relative_fuel_change for run in runs),
        max_delta_rms_speed_error=max(run.delta_rms_speed_error for run in runs),
    )
