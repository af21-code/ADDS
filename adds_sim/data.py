"""Trajectory and summary export helpers."""

from __future__ import annotations

import csv
from pathlib import Path

from .simulator import SimulationResult


SUMMARY_FIELDS = (
    "scenario_id",
    "split",
    "controller_name",
    "completed_successfully",
    "termination_reason",
    "distance_traveled",
    "travel_time",
    "fuel_used",
    "fuel_per_distance",
    "equivalent_energy_used",
    "rms_speed_error",
    "max_speed_error",
    "brake_energy",
    "coupling_slip_energy",
    "mode_transition_count",
    "safety_override_count",
    "fallback_entry_count",
    "energy_balance_residual_ratio",
)


TRAJECTORY_FIELDS = (
    "time",
    "step_index",
    "scenario_id",
    "position",
    "vehicle_speed",
    "vehicle_acceleration",
    "target_speed",
    "speed_error",
    "road_grade",
    "engine_speed",
    "engine_torque",
    "engine_fuel_rate",
    "selected_gear",
    "synchronous_engine_speed",
    "coupling_mode",
    "coupling_slip_speed",
    "coupling_slip_power",
    "coupling_slip_energy",
    "brake_force",
    "aero_force",
    "rolling_resistance_force",
    "grade_force",
    "energy_balance_residual",
)


def write_trajectory_csv(path: Path, result: SimulationResult) -> None:
    """Write one trajectory CSV using stable field order."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=TRAJECTORY_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for record in result.records:
            writer.writerow(record)


def write_summary_csv(path: Path, rows: list[dict[str, object]]) -> None:
    """Write batch summary CSV using stable field order."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=SUMMARY_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
