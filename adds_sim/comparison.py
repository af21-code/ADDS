"""Paired conventional-vs-ADDS comparison helpers."""

from __future__ import annotations

from dataclasses import dataclass

from .benchmarks import with_adds_enabled
from .controllers import Controller
from .metrics import summarize_run
from .simulator import LongitudinalSimulator, Scenario, SimulationResult


@dataclass(frozen=True)
class PairedComparisonResult:
    """Results from one paired conventional and ADDS scenario run."""

    scenario_id: str
    conventional_result: SimulationResult
    adds_result: SimulationResult
    conventional_summary: dict[str, float | int | bool | str]
    adds_summary: dict[str, float | int | bool | str]
    deltas: dict[str, float | bool]


def run_paired_comparison(
    simulator: LongitudinalSimulator,
    scenario: Scenario,
    conventional_controller: Controller,
    adds_controller: Controller,
) -> PairedComparisonResult:
    """Run one fair paired comparison with identical scenario inputs."""

    conventional_scenario = with_adds_enabled(scenario, False)
    adds_scenario = with_adds_enabled(scenario, True)

    conventional_result = simulator.run(conventional_scenario, conventional_controller)
    adds_result = simulator.run(adds_scenario, adds_controller)
    conventional_summary = summarize_run(conventional_result)
    adds_summary = summarize_run(adds_result)

    deltas = {
        "delta_fuel_used": float(adds_summary["fuel_used"]) - float(conventional_summary["fuel_used"]),
        "relative_fuel_change": _relative_change(float(conventional_summary["fuel_used"]), float(adds_summary["fuel_used"])),
        "delta_travel_time": float(adds_summary["travel_time"]) - float(conventional_summary["travel_time"]),
        "delta_rms_speed_error": float(adds_summary["rms_speed_error"]) - float(conventional_summary["rms_speed_error"]),
        "delta_brake_energy": float(adds_summary["brake_energy"]) - float(conventional_summary["brake_energy"]),
        "delta_coupling_slip_energy": float(adds_summary["coupling_slip_energy"]) - float(conventional_summary["coupling_slip_energy"]),
        "constraint_regression": bool(adds_summary["hard_constraint_violation_count"])
        and not bool(conventional_summary["hard_constraint_violation_count"]),
    }

    return PairedComparisonResult(
        scenario_id=scenario.scenario_id,
        conventional_result=conventional_result,
        adds_result=adds_result,
        conventional_summary=conventional_summary,
        adds_summary=adds_summary,
        deltas=deltas,
    )


def _relative_change(baseline: float, candidate: float) -> float:
    if baseline == 0.0:
        return 0.0 if candidate == 0.0 else float("inf")
    return 100.0 * (candidate - baseline) / baseline
