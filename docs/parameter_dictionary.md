# Parameter Dictionary

This document defines the initial model parameters required before implementing
the minimum viable simulator. Values are intentionally not fixed here; this file
specifies names, units, meaning, and validation expectations.

## Parameter Principles

- Use SI units.
- Keep vehicle, environment, controller, and solver parameters separate.
- Validate physical plausibility before simulation starts.
- Store parameter sets with stable identifiers and versions.
- Never tune ADDS-only parameters using test scenarios that are hidden from the
  conventional baseline.

## Vehicle Body Parameters

| Parameter | Unit | Description | Validation |
| --- | --- | --- | --- |
| `vehicle.mass` | kg | Vehicle mass including payload. | `> 0` |
| `vehicle.frontal_area` | m^2 | Effective frontal area. | `> 0` |
| `vehicle.drag_coefficient` | none | Aerodynamic drag coefficient. | `> 0` |
| `vehicle.rolling_resistance_coefficient` | none | Baseline rolling resistance coefficient. | `>= 0` |
| `vehicle.wheel_radius` | m | Effective rolling tire radius. | `> 0` |
| `vehicle.wheel_inertia` | kg m^2 | Lumped driven-wheel inertia if explicitly modeled. | `>= 0` |
| `vehicle.max_brake_force` | N | Maximum foundation-brake force. | `> 0` |
| `vehicle.max_longitudinal_acceleration` | m/s^2 | Optional comfort or physical acceleration bound. | `> 0` |
| `vehicle.max_longitudinal_deceleration` | m/s^2 | Optional comfort or physical deceleration bound. | `> 0` |

## Environment Parameters

| Parameter | Unit | Description | Validation |
| --- | --- | --- | --- |
| `environment.gravity` | m/s^2 | Gravitational acceleration. | `> 0` |
| `environment.air_density` | kg/m^3 | Air density used for drag. | `> 0` |
| `environment.wind_speed` | m/s | Longitudinal wind speed, positive in vehicle travel direction. | finite |
| `environment.tire_friction_coefficient` | none | Effective tire-road friction coefficient. | `> 0` |

## Engine Parameters

| Parameter | Unit | Description | Validation |
| --- | --- | --- | --- |
| `engine.inertia` | kg m^2 | Engine rotational inertia. | `> 0` |
| `engine.idle_speed` | rad/s | Target idle speed. | `> 0` |
| `engine.max_speed` | rad/s | Maximum allowed engine speed. | `> idle_speed` |
| `engine.min_operating_speed` | rad/s | Minimum stable running speed. | `> 0` |
| `engine.max_torque_curve` | table | Maximum torque as a function of engine speed. | speed-sorted, finite |
| `engine.min_torque_curve` | table | Minimum torque as a function of engine speed. | speed-sorted, finite |
| `engine.fuel_rate_map` | table | Fuel mass flow as a function of speed and torque. | non-negative |
| `engine.idle_fuel_rate` | kg/s | Fuel flow while idling. | `>= 0` |
| `engine.friction_torque_model` | model | Internal friction and pumping torque model. | declared |
| `engine.overrun_fuel_cutoff_enabled` | boolean | Whether connected overrun fuel cut-off is modeled. | boolean |
| `engine.overrun_fuel_cutoff_min_speed` | rad/s | Minimum engine speed for fuel cut-off. | `>= idle_speed` |

## Transmission and Final Drive Parameters

| Parameter | Unit | Description | Validation |
| --- | --- | --- | --- |
| `transmission.gear_ratios` | list | Forward gear ratios. | non-empty, positive |
| `transmission.final_drive_ratio` | none | Final-drive ratio. | `> 0` |
| `transmission.efficiency_motoring` | none | Efficiency when power flows from engine to wheels. | `(0, 1]` |
| `transmission.efficiency_overrun` | none | Efficiency when power flows from wheels to engine. | `(0, 1]` |
| `transmission.shift_time` | s | Time required for a modeled gear change. | `>= 0` |
| `transmission.allowed_gears_for_reengagement` | list | Gears allowed as ADDS re-engagement targets. | subset of gears |

## Coupling Parameters

| Parameter | Unit | Description | Validation |
| --- | --- | --- | --- |
| `coupling.max_torque_capacity` | N m | Maximum torque the coupling can transmit. | `> 0` |
| `coupling.opening_time` | s | Nominal time to open the coupling. | `> 0` |
| `coupling.closing_time` | s | Nominal time to close the coupling. | `> 0` |
| `coupling.locked_slip_threshold` | rad/s | Slip threshold for declaring lock-up. | `>= 0` |
| `coupling.reengagement_slip_limit` | rad/s | Maximum slip allowed before closing begins. | `>= 0` |
| `coupling.reengagement_torque_limit` | N m | Maximum torque mismatch allowed before closing begins. | `>= 0` |
| `coupling.max_slip_energy_per_event` | J | Event-level slip energy limit. | `> 0` |
| `coupling.max_slip_power` | W | Instantaneous slip power limit. | `> 0` |
| `coupling.min_mode_dwell_time` | s | Minimum time before another mode change. | `>= 0` |

## Controller Parameters

| Parameter | Unit | Description | Validation |
| --- | --- | --- | --- |
| `controller.supervisory_period` | s | High-level mode decision interval. | `> 0` |
| `controller.preview_horizon` | s | Future route horizon exposed to the controller. | `>= 0` |
| `controller.preview_sample_count` | count | Number of preview samples. | integer, `>= 0` |
| `controller.min_expected_coast_time` | s | Rule-based minimum benefit horizon for decoupling. | `>= 0` |
| `controller.max_response_delay` | s | Maximum allowed delay to restore positive wheel torque. | `> 0` |
| `controller.max_allowed_jerk` | m/s^3 | Comfort limit used by controller or metrics. | `> 0` |
| `controller.mode_chatter_window` | s | Time window for detecting excessive switching. | `> 0` |

## Safety Parameters

| Parameter | Unit | Description | Validation |
| --- | --- | --- | --- |
| `safety.min_vehicle_speed_for_decoupling` | m/s | Minimum speed at which ADDS may decouple. | `>= 0` |
| `safety.max_vehicle_speed` | m/s | Maximum supported simulated vehicle speed. | `> 0` |
| `safety.brake_demand_decouple_block_threshold` | 0..1 | Brake demand above which decoupling is blocked. | `[0, 1]` |
| `safety.positive_torque_reconnect_threshold` | 0..1 | Accelerator demand that triggers reconnection. | `[0, 1]` |
| `safety.max_engine_speed_overshoot` | rad/s | Allowed transient overshoot above engine limit. | `>= 0` |
| `safety.fallback_timeout` | s | Maximum time allowed in unresolved transition before fallback. | `> 0` |
| `safety.max_supervisor_overrides_per_km` | 1/km | Evaluation threshold for excessive intervention. | `>= 0` |

## Solver and Logging Parameters

| Parameter | Unit | Description | Validation |
| --- | --- | --- | --- |
| `solver.plant_time_step` | s | Physical integration interval. | `> 0` |
| `solver.low_level_control_period` | s | Low-level controller interval. | `> 0` |
| `solver.supervisory_control_period` | s | Supervisory controller interval. | `> 0` |
| `solver.integration_method` | enum | Numerical integration method. | supported value |
| `solver.energy_residual_tolerance` | J or ratio | Maximum accepted energy-balance residual. | `>= 0` |
| `logging.sample_period` | s | Log output interval. | `> 0` |
| `logging.include_debug_signals` | boolean | Whether to store diagnostic signals. | boolean |

## Scenario Parameters

| Parameter | Unit | Description | Validation |
| --- | --- | --- | --- |
| `scenario.initial_speed` | m/s | Initial vehicle speed. | `>= 0` |
| `scenario.initial_engine_speed` | rad/s | Initial engine speed. | within engine limits |
| `scenario.initial_gear` | count | Initial selected gear. | allowed gear |
| `scenario.distance_limit` | m | Optional route distance end condition. | `> 0` if set |
| `scenario.time_limit` | s | Optional time end condition. | `> 0` if set |
| `scenario.target_speed_profile` | table | Target speed over time or distance. | finite |
| `scenario.grade_profile` | table | Road grade over time or distance. | finite |
| `scenario.disturbances` | list | Declared disturbances and randomization ranges. | declared |

## Open Parameter Decisions

The exact values for the first reference vehicle are still open. Before
implementation, the project should choose:

- A nominal vehicle class and mass.
- A representative engine torque and fuel map source.
- Gear ratios and final-drive ratio.
- Coupling limits and transition timing.
- Solver step sizes and accepted tolerances.
- Initial comfort limits for jerk and acceleration.
