"""Reference parameters for early Phase 1 tests and examples."""

from __future__ import annotations

from .parameters import (
    EngineParameters,
    EnvironmentParameters,
    SolverParameters,
    TransmissionParameters,
    VehicleParameters,
)
from .simulator import SimulationConfig


def default_simulation_config() -> SimulationConfig:
    """Return a documented mid-size passenger-car style configuration."""

    return SimulationConfig(
        vehicle=VehicleParameters(
            mass=1500.0,
            frontal_area=2.2,
            drag_coefficient=0.29,
            rolling_resistance_coefficient=0.010,
            wheel_radius=0.31,
            wheel_inertia=4.0,
            max_brake_force=12000.0,
            max_longitudinal_acceleration=4.0,
            max_longitudinal_deceleration=8.0,
        ),
        environment=EnvironmentParameters(
            gravity=9.80665,
            air_density=1.225,
            wind_speed=0.0,
            tire_friction_coefficient=0.9,
        ),
        engine=EngineParameters(
            inertia=0.25,
            idle_speed=85.0,
            max_speed=650.0,
            min_operating_speed=70.0,
            max_torque=220.0,
            min_torque=-35.0,
            idle_fuel_rate=0.00020,
            fuel_lower_heating_value=43_000_000.0,
            positive_load_efficiency=0.32,
            overrun_fuel_cutoff_enabled=True,
            overrun_fuel_cutoff_min_speed=110.0,
        ),
        transmission=TransmissionParameters(
            gear_ratios=(3.60, 2.10, 1.40, 1.03, 0.82, 0.67),
            final_drive_ratio=3.45,
            efficiency_motoring=0.94,
            efficiency_overrun=0.92,
            shift_time=0.0,
        ),
        solver=SolverParameters(
            plant_time_step=0.02,
            low_level_control_period=0.02,
            supervisory_control_period=0.10,
            integration_method="semi_implicit_euler",
            energy_residual_tolerance=0.03,
            logging_sample_period=0.02,
        ),
    )
