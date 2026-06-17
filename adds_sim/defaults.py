"""Reference parameters for early Phase 1 tests and examples."""

from __future__ import annotations

from .parameters import (
    CouplingParameters,
    EngineParameters,
    EnvironmentParameters,
    SafetyParameters,
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
        coupling=CouplingParameters(
            max_torque_capacity=320.0,
            opening_time=0.30,
            closing_time=0.35,
            locked_slip_threshold=2.0,
            reengagement_slip_limit=8.0,
            reengagement_torque_limit=80.0,
            max_slip_energy_per_event=25_000.0,
            max_slip_power=80_000.0,
            min_mode_dwell_time=0.10,
        ),
        safety=SafetyParameters(
            min_vehicle_speed_for_decoupling=5.0,
            max_vehicle_speed=70.0,
            brake_demand_decouple_block_threshold=0.05,
            positive_torque_reconnect_threshold=0.05,
            max_engine_speed_overshoot=20.0,
            fallback_timeout=1.0,
            max_supervisor_overrides_per_km=5.0,
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
