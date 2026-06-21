# Signal Dictionary

This document defines the initial runtime signals for the ADDS simulator. All
signals use SI units at system boundaries unless otherwise stated.

## Naming Conventions

- Use `snake_case`.
- Use positive values for forward vehicle motion and propulsion.
- Use explicit suffixes for units only when ambiguity is likely.
- Log raw physical values separately from normalized machine learning features.
- Treat unavailable signals as invalid rather than silently substituting zero.

## Time and Scenario Signals

| Signal | Unit | Description |
| --- | --- | --- |
| `time` | s | Simulation time from scenario start. |
| `step_index` | count | Integer simulation step. |
| `scenario_id` | none | Stable scenario identifier. |
| `run_id` | none | Stable simulation run identifier. |
| `random_seed` | none | Seed used for stochastic scenario elements. |
| `terminal` | boolean | Whether the scenario has ended. |
| `termination_reason` | enum | Reason for ending the simulation. |

## Vehicle Motion Signals

| Signal | Unit | Description |
| --- | --- | --- |
| `position` | m | Longitudinal distance traveled along the route. |
| `vehicle_speed` | m/s | Longitudinal vehicle speed. |
| `vehicle_acceleration` | m/s^2 | Longitudinal vehicle acceleration. |
| `vehicle_jerk` | m/s^3 | Time derivative of acceleration, normally filtered for metrics. |
| `target_speed` | m/s | Scenario or driver target speed. |
| `speed_error` | m/s | `target_speed - vehicle_speed`. |
| `road_grade` | rad | Current road grade angle, positive uphill. |
| `road_grade_preview` | rad | Previewed grade samples over a configured horizon. |
| `target_speed_preview` | m/s | Previewed target-speed samples over a configured horizon. |

## Driver Demand Signals

| Signal | Unit | Description |
| --- | --- | --- |
| `accelerator_demand` | 0..1 | Normalized accelerator request. |
| `brake_demand` | 0..1 | Normalized brake request. |
| `requested_wheel_torque` | N m | Driver or tracker wheel-torque request. |
| `requested_brake_force` | N | Foundation-brake force request before limits. |
| `positive_torque_request` | boolean | Whether the driver is requesting propulsion. |

## Wheel and Tire Signals

| Signal | Unit | Description |
| --- | --- | --- |
| `wheel_speed` | rad/s | Driven-wheel angular speed. |
| `wheel_torque` | N m | Net torque applied at driven wheels. |
| `tire_force_longitudinal` | N | Longitudinal tire force at the contact patch. |
| `tire_force_limit` | N | Current longitudinal tire-force limit. |
| `tire_force_margin` | N | Remaining force margin before saturation. |
| `brake_force` | N | Applied foundation-brake force. |
| `brake_power` | W | Power dissipated by foundation brakes. |

## Engine Signals

| Signal | Unit | Description |
| --- | --- | --- |
| `engine_speed` | rad/s | Engine crankshaft angular speed. |
| `engine_speed_target` | rad/s | Target engine speed during idle or rev-matching. |
| `engine_torque_command` | N m | Requested engine torque before limits. |
| `engine_torque` | N m | Delivered engine torque after limits. |
| `engine_torque_available_min` | N m | Minimum available engine torque at current speed. |
| `engine_torque_available_max` | N m | Maximum available engine torque at current speed. |
| `engine_fuel_rate` | kg/s | Instantaneous fuel mass flow. |
| `engine_fuel_used` | kg | Cumulative fuel mass consumed. |
| `engine_power` | W | Mechanical engine output power. |
| `engine_state` | enum | Example values: `RUNNING`, `IDLE`, `OVERRUN_FUEL_CUTOFF`, `STOPPED`. |

## Transmission and Coupling Signals

| Signal | Unit | Description |
| --- | --- | --- |
| `selected_gear` | count | Current selected gear. Neutral may be represented explicitly. |
| `target_gear` | count | Gear requested for future re-engagement. |
| `gear_ratio` | none | Current selected gear ratio. |
| `final_drive_ratio` | none | Final-drive ratio. |
| `total_drive_ratio` | none | `gear_ratio * final_drive_ratio`. |
| `synchronous_engine_speed` | rad/s | Engine speed matching wheel speed in the target gear. |
| `coupling_mode` | enum | Current mode: `CONNECTED`, `DECOUPLING`, `DECOUPLED`, `REV_MATCHING`, `REENGAGING`, `FAULT_SAFE`. |
| `coupling_capacity_command` | N m | Requested coupling torque capacity. |
| `coupling_capacity` | N m | Applied coupling torque capacity after limits. |
| `coupling_torque` | N m | Torque transmitted through the coupling. |
| `coupling_slip_speed` | rad/s | Engine speed minus synchronous engine speed. |
| `coupling_slip_power` | W | Instantaneous dissipated slip power. |
| `coupling_slip_energy` | J | Cumulative energy dissipated through slip. |
| `mode_time` | s | Time spent in the current coupling mode. |
| `transition_count` | count | Number of drivetrain mode transitions. |

## Resistive Force and Energy Signals

| Signal | Unit | Description |
| --- | --- | --- |
| `aero_force` | N | Aerodynamic drag force. |
| `rolling_resistance_force` | N | Rolling resistance force. |
| `grade_force` | N | Gravity component along the route. |
| `drivetrain_loss_power` | W | Power lost in transmission and final drive. |
| `aero_energy` | J | Cumulative aerodynamic work. |
| `rolling_resistance_energy` | J | Cumulative rolling-resistance work. |
| `brake_energy` | J | Cumulative foundation-brake energy. |
| `drivetrain_loss_energy` | J | Cumulative drivetrain loss energy. |
| `engine_loss_energy` | J | Cumulative modeled engine internal losses. |
| `energy_balance_residual` | J | Difference between accounted energy terms and total input energy. |

## Controller Signals

| Signal | Unit | Description |
| --- | --- | --- |
| `controller_name` | none | Controller implementation identifier. |
| `controller_version` | none | Controller version or artifact hash. |
| `requested_mode` | enum | Mode requested by the supervisory controller. |
| `applied_mode` | enum | Mode applied after safety-supervisor checks. |
| `action_mask` | bitset | Feasible actions available to the controller. |
| `safety_override` | boolean | Whether the safety supervisor modified or rejected a request. |
| `safety_override_reason` | enum | Reason for supervisor intervention. |
| `fallback_active` | boolean | Whether fallback behavior is currently active. |
| `controller_latency` | s | Time required to produce a controller decision. |

## Logging Requirements

Each logged trajectory must include:

- Signal schema version.
- Sample interval.
- Units.
- Controller identity.
- Scenario identity.
- Vehicle parameter identity.
- Termination reason.

Metric calculations should use logged physical signals and should not depend on
hidden controller state unless that state is itself logged.
