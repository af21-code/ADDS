"""Parameter definitions and validation for the Phase 1 simulator."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


def _require_finite(name: str, value: float) -> None:
    if not isfinite(value):
        raise ValueError(f"{name} must be finite")


def _require_positive(name: str, value: float) -> None:
    _require_finite(name, value)
    if value <= 0.0:
        raise ValueError(f"{name} must be > 0")


def _require_non_negative(name: str, value: float) -> None:
    _require_finite(name, value)
    if value < 0.0:
        raise ValueError(f"{name} must be >= 0")


@dataclass(frozen=True)
class VehicleParameters:
    """Vehicle body parameters in SI units."""

    mass: float
    frontal_area: float
    drag_coefficient: float
    rolling_resistance_coefficient: float
    wheel_radius: float
    wheel_inertia: float
    max_brake_force: float
    max_longitudinal_acceleration: float
    max_longitudinal_deceleration: float

    def validate(self) -> None:
        _require_positive("vehicle.mass", self.mass)
        _require_positive("vehicle.frontal_area", self.frontal_area)
        _require_positive("vehicle.drag_coefficient", self.drag_coefficient)
        _require_non_negative("vehicle.rolling_resistance_coefficient", self.rolling_resistance_coefficient)
        _require_positive("vehicle.wheel_radius", self.wheel_radius)
        _require_non_negative("vehicle.wheel_inertia", self.wheel_inertia)
        _require_positive("vehicle.max_brake_force", self.max_brake_force)
        _require_positive("vehicle.max_longitudinal_acceleration", self.max_longitudinal_acceleration)
        _require_positive("vehicle.max_longitudinal_deceleration", self.max_longitudinal_deceleration)


@dataclass(frozen=True)
class EnvironmentParameters:
    """Environment parameters in SI units."""

    gravity: float
    air_density: float
    wind_speed: float
    tire_friction_coefficient: float

    def validate(self) -> None:
        _require_positive("environment.gravity", self.gravity)
        _require_positive("environment.air_density", self.air_density)
        _require_finite("environment.wind_speed", self.wind_speed)
        _require_positive("environment.tire_friction_coefficient", self.tire_friction_coefficient)


@dataclass(frozen=True)
class EngineParameters:
    """Basic combustion engine model parameters."""

    inertia: float
    idle_speed: float
    max_speed: float
    min_operating_speed: float
    max_torque: float
    min_torque: float
    idle_fuel_rate: float
    fuel_lower_heating_value: float
    positive_load_efficiency: float
    overrun_fuel_cutoff_enabled: bool
    overrun_fuel_cutoff_min_speed: float

    def validate(self) -> None:
        _require_positive("engine.inertia", self.inertia)
        _require_positive("engine.idle_speed", self.idle_speed)
        _require_positive("engine.max_speed", self.max_speed)
        if self.max_speed <= self.idle_speed:
            raise ValueError("engine.max_speed must be > engine.idle_speed")
        _require_positive("engine.min_operating_speed", self.min_operating_speed)
        _require_positive("engine.max_torque", self.max_torque)
        _require_finite("engine.min_torque", self.min_torque)
        if self.min_torque > 0.0:
            raise ValueError("engine.min_torque must be <= 0 for engine braking")
        _require_non_negative("engine.idle_fuel_rate", self.idle_fuel_rate)
        _require_positive("engine.fuel_lower_heating_value", self.fuel_lower_heating_value)
        _require_positive("engine.positive_load_efficiency", self.positive_load_efficiency)
        if self.positive_load_efficiency > 1.0:
            raise ValueError("engine.positive_load_efficiency must be <= 1")
        _require_non_negative("engine.overrun_fuel_cutoff_min_speed", self.overrun_fuel_cutoff_min_speed)


@dataclass(frozen=True)
class TransmissionParameters:
    """Transmission and final drive parameters."""

    gear_ratios: tuple[float, ...]
    final_drive_ratio: float
    efficiency_motoring: float
    efficiency_overrun: float
    shift_time: float

    def validate(self) -> None:
        if not self.gear_ratios:
            raise ValueError("transmission.gear_ratios must be non-empty")
        for index, ratio in enumerate(self.gear_ratios, start=1):
            _require_positive(f"transmission.gear_ratios[{index}]", ratio)
        _require_positive("transmission.final_drive_ratio", self.final_drive_ratio)
        _require_positive("transmission.efficiency_motoring", self.efficiency_motoring)
        _require_positive("transmission.efficiency_overrun", self.efficiency_overrun)
        if self.efficiency_motoring > 1.0:
            raise ValueError("transmission.efficiency_motoring must be <= 1")
        if self.efficiency_overrun > 1.0:
            raise ValueError("transmission.efficiency_overrun must be <= 1")
        _require_non_negative("transmission.shift_time", self.shift_time)

    def gear_ratio(self, gear: int) -> float:
        if gear < 1 or gear > len(self.gear_ratios):
            raise ValueError(f"gear {gear} is outside the available range 1..{len(self.gear_ratios)}")
        return self.gear_ratios[gear - 1]

    def total_ratio(self, gear: int) -> float:
        return self.gear_ratio(gear) * self.final_drive_ratio


@dataclass(frozen=True)
class SolverParameters:
    """Fixed-step solver and logging parameters."""

    plant_time_step: float
    low_level_control_period: float
    supervisory_control_period: float
    integration_method: str
    energy_residual_tolerance: float
    logging_sample_period: float

    def validate(self) -> None:
        _require_positive("solver.plant_time_step", self.plant_time_step)
        _require_positive("solver.low_level_control_period", self.low_level_control_period)
        _require_positive("solver.supervisory_control_period", self.supervisory_control_period)
        _require_non_negative("solver.energy_residual_tolerance", self.energy_residual_tolerance)
        _require_positive("logging.sample_period", self.logging_sample_period)
        if self.integration_method != "semi_implicit_euler":
            raise ValueError("only semi_implicit_euler is supported in Phase 1")
