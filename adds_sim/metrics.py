"""Metric calculations from simulator logs."""

from __future__ import annotations

from math import sqrt

from .simulator import SimulationResult


def summarize_run(result: SimulationResult) -> dict[str, float | int | bool | str]:
    """Return a Phase 1 summary calculated from logged physical signals."""

    if not result.records:
        return {
            "scenario_id": result.scenario_id,
            "controller_name": result.controller_name,
            "completed_successfully": False,
            "termination_reason": result.termination_reason,
        }

    records = result.records
    final = records[-1]
    speed_errors = [float(record["speed_error"]) for record in records]
    accelerations = [float(record["vehicle_acceleration"]) for record in records]
    jerks = []
    for previous, current in zip(records[:-1], records[1:]):
        dt = float(current["time"]) - float(previous["time"])
        if dt > 0.0:
            jerks.append((float(current["vehicle_acceleration"]) - float(previous["vehicle_acceleration"])) / dt)

    distance = float(final["position"])
    fuel_used = float(final["engine_fuel_used"])
    residual = float(final["energy_balance_residual"])
    fuel_energy = result.final_state.fuel_energy
    residual_basis = max(abs(fuel_energy), abs(result.final_state.kinetic_energy_initial), 1.0)

    return {
        "scenario_id": result.scenario_id,
        "controller_name": result.controller_name,
        "termination_reason": result.termination_reason,
        "completed_successfully": result.termination_reason in {"time_limit", "distance_limit", "vehicle_stopped"},
        "distance_traveled": distance,
        "travel_time": float(final["time"]),
        "fuel_used": fuel_used,
        "fuel_per_distance": fuel_used / distance if distance > 0.0 else float("inf"),
        "equivalent_energy_used": fuel_energy,
        "aero_energy": float(final["aero_energy"]),
        "rolling_resistance_energy": float(final["rolling_resistance_energy"]),
        "brake_energy": float(final["brake_energy"]),
        "drivetrain_loss_energy": float(final["drivetrain_loss_energy"]),
        "coupling_slip_energy": float(final["coupling_slip_energy"]),
        "energy_balance_residual": residual,
        "energy_balance_residual_ratio": abs(residual) / residual_basis,
        "mean_speed_error": sum(speed_errors) / len(speed_errors),
        "rms_speed_error": sqrt(sum(error * error for error in speed_errors) / len(speed_errors)),
        "max_speed_error": max(abs(error) for error in speed_errors),
        "max_acceleration": max(accelerations),
        "max_deceleration": abs(min(accelerations)),
        "max_jerk": max((abs(jerk) for jerk in jerks), default=0.0),
        "mode_transition_count": 0,
        "hard_constraint_violation_count": 0,
        "safety_override_count": 0,
        "fallback_entry_count": 0,
        "numerical_failure": False,
    }
