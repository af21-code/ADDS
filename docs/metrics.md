# Metric Specification

Metrics define how ADDS compares the conventional vehicle and the adaptive
decoupling vehicle. They must be calculated from logged physical signals, not
from unverified controller self-reports.

## Metric Categories

ADDS uses five metric categories:

1. Efficiency.
2. Mobility and speed tracking.
3. Comfort and drivability.
4. Mechanical impact.
5. Safety and robustness.

No single efficiency metric is sufficient. A controller is successful only if
mandatory constraints remain satisfied.

## Efficiency Metrics

| Metric | Unit | Description |
| --- | --- | --- |
| `fuel_used` | kg | Total fuel mass consumed. |
| `fuel_per_distance` | kg/m | Fuel mass divided by completed distance. |
| `equivalent_energy_used` | J | Fuel lower-heating-value equivalent or configured energy basis. |
| `idle_fuel_used` | kg | Fuel consumed while idling. |
| `overrun_fuel_cutoff_time` | s | Time spent in valid fuel cut-off. |
| `aero_energy` | J | Energy lost to aerodynamic drag. |
| `rolling_resistance_energy` | J | Energy lost to rolling resistance. |
| `brake_energy` | J | Energy dissipated by foundation brakes. |
| `drivetrain_loss_energy` | J | Energy lost in drivetrain components. |
| `coupling_slip_energy` | J | Energy dissipated during coupling slip. |
| `energy_balance_residual_ratio` | none | Energy residual normalized by input energy or another declared basis. |

## Mobility and Speed-Tracking Metrics

| Metric | Unit | Description |
| --- | --- | --- |
| `distance_traveled` | m | Completed route distance. |
| `travel_time` | s | Time required to complete the scenario. |
| `mean_speed_error` | m/s | Mean signed speed-tracking error. |
| `rms_speed_error` | m/s | Root-mean-square speed-tracking error. |
| `max_speed_error` | m/s | Maximum absolute speed-tracking error. |
| `overspeed_duration` | s | Time above target or limit by more than tolerance. |
| `underspeed_duration` | s | Time below target by more than tolerance. |
| `positive_torque_response_delay` | s | Delay from positive demand to restored wheel torque. |

## Comfort and Drivability Metrics

| Metric | Unit | Description |
| --- | --- | --- |
| `max_acceleration` | m/s^2 | Maximum longitudinal acceleration. |
| `max_deceleration` | m/s^2 | Maximum longitudinal deceleration magnitude. |
| `rms_acceleration` | m/s^2 | Root-mean-square longitudinal acceleration. |
| `max_jerk` | m/s^3 | Maximum filtered jerk magnitude. |
| `rms_jerk` | m/s^3 | Root-mean-square filtered jerk. |
| `mode_transition_count` | count | Number of drivetrain mode transitions. |
| `mode_chatter_events` | count | Excessive switching events inside the configured window. |
| `reengagement_disturbance_peak` | m/s^2 | Peak acceleration disturbance during re-engagement. |

## Mechanical Impact Metrics

| Metric | Unit | Description |
| --- | --- | --- |
| `reengagement_count` | count | Number of completed re-engagement events. |
| `aborted_reengagement_count` | count | Re-engagement attempts that did not complete normally. |
| `peak_coupling_slip_speed` | rad/s | Peak speed mismatch across the coupling. |
| `peak_coupling_torque` | N m | Peak transmitted coupling torque. |
| `peak_coupling_slip_power` | W | Peak slip power. |
| `max_slip_energy_per_event` | J | Worst event-level slip energy. |
| `mean_reengagement_time` | s | Mean time from re-engagement request to lock-up. |
| `engine_speed_overshoot` | rad/s | Peak engine speed above target or limit. |

## Safety and Robustness Metrics

| Metric | Unit | Description |
| --- | --- | --- |
| `hard_constraint_violation_count` | count | Number of non-negotiable safety or physical limit violations. |
| `safety_override_count` | count | Number of controller requests modified or rejected by the safety supervisor. |
| `safety_overrides_per_km` | 1/km | Supervisor overrides normalized by distance. |
| `fallback_entry_count` | count | Number of fallback events. |
| `fault_safe_time` | s | Time spent in fault-safe behavior. |
| `invalid_observation_count` | count | Invalid, missing, or stale observations. |
| `numerical_failure` | boolean | Whether integration or state validity failed. |
| `completed_successfully` | boolean | Whether the scenario reached normal termination. |

## Mode Occupancy Metrics

For each mode, report:

| Metric | Unit | Description |
| --- | --- | --- |
| `time_in_mode.<mode>` | s | Absolute time spent in the mode. |
| `distance_in_mode.<mode>` | m | Distance traveled in the mode. |
| `fraction_time_in_mode.<mode>` | none | Time fraction spent in the mode. |
| `fraction_distance_in_mode.<mode>` | none | Distance fraction spent in the mode. |

Mode names should match the glossary and state machine:

- `CONNECTED`
- `DECOUPLING`
- `DECOUPLED`
- `REV_MATCHING`
- `REENGAGING`
- `FAULT_SAFE`

## Paired Comparison Metrics

When comparing ADDS against the conventional baseline, report:

| Metric | Unit | Description |
| --- | --- | --- |
| `delta_fuel_used` | kg | ADDS fuel minus conventional fuel. |
| `relative_fuel_change` | % | Fuel change relative to conventional result. |
| `delta_travel_time` | s | ADDS travel time minus conventional travel time. |
| `delta_rms_speed_error` | m/s | ADDS RMS speed error minus conventional RMS speed error. |
| `delta_brake_energy` | J | ADDS brake energy minus conventional brake energy. |
| `delta_coupling_slip_energy` | J | ADDS slip energy minus conventional slip energy. |
| `constraint_regression` | boolean | Whether ADDS introduces a constraint violation absent in the baseline. |

Negative `delta_fuel_used` indicates lower fuel use by ADDS.

## Acceptance Thresholds

Initial thresholds should be conservative placeholders until calibrated:

- `hard_constraint_violation_count` must be zero.
- `numerical_failure` must be false.
- `completed_successfully` must be true.
- Energy-balance residual must remain below the configured solver tolerance.
- ADDS must not reduce travel distance relative to the baseline in fixed-distance
  scenarios.
- ADDS must not rely on frequent safety-supervisor overrides.

Specific numerical thresholds should be declared in experiment configuration and
revisited after the minimum viable simulator is validated.

The Phase 7A dashboard uses the following explicit initial research gates:

- Simulated fuel reduction must be at least `1%`.
- RMS speed-error increase must not exceed `1 km/h`.
- ADDS must introduce no hard-constraint regression.
- ADDS must log no safety-supervisor override.

Only a result that passes every gate is labeled `ACCEPTABLE_BENEFIT`. A fuel
reduction accompanied by excessive speed-tracking degradation is labeled
`TRADE_OFF_REQUIRES_REVIEW`, and the efficiency claim is not accepted. These
thresholds are conservative visualization and reporting defaults, not validated
production-vehicle limits.

## Reporting Requirements

Each report should include:

- Scenario identifiers and versions.
- Vehicle and controller identifiers.
- Solver and time-step settings.
- Summary table of absolute metrics.
- Paired conventional-versus-ADDS deltas.
- Mode timeline.
- Energy-flow breakdown.
- Re-engagement event table.
- Safety-supervisor intervention list.
- Notes on invalid or excluded runs.
