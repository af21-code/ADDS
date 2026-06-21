# Vehicle Dynamics

## 1. Modeling Scope

The initial ADDS plant is a longitudinal vehicle model intended to compare
drivetrain connection strategies. It should be detailed enough to represent:

- Vehicle acceleration and coast-down.
- Engine and wheel-side rotational speeds.
- Gear-dependent torque transfer.
- Connected engine braking.
- Decoupled coasting.
- Rev-matched re-engagement.
- Fuel use, drivetrain losses, and coupling slip energy.

The model should remain modular so higher-fidelity submodels can replace initial
approximations without changing controller interfaces.

## 2. Coordinates and Conventions

Unless explicitly stated otherwise:

- SI units are used.
- Forward vehicle motion and tractive force are positive.
- Road grade angle is positive uphill.
- Engine and wheel angular speeds are non-negative in forward operation.
- Power flowing from the engine toward the wheels is positive.
- Braking forces and resistive forces oppose forward motion.

All sign conventions must be encoded once and tested at subsystem boundaries.

## 3. Symbol and Signal Mapping

The equations in this document use compact symbols for readability. Runtime logs
should use the explicit signal names from the signal dictionary.

| Equation symbol | Runtime signal or parameter | Unit | Meaning |
| --- | --- | --- | --- |
| `v` | `vehicle_speed` | m/s | Longitudinal vehicle speed. |
| `dv_dt` | `vehicle_acceleration` | m/s^2 | Longitudinal acceleration. |
| `omega_w` | `wheel_speed` | rad/s | Driven-wheel angular speed. |
| `omega_e` | `engine_speed` | rad/s | Engine crankshaft speed. |
| `omega_sync` | `synchronous_engine_speed` | rad/s | Engine speed matching wheel speed in the selected or target gear. |
| `omega_target` | `engine_speed_target` | rad/s | Engine speed target during idle control or rev-matching. |
| `slip_speed` | `coupling_slip_speed` | rad/s | Engine-side speed minus synchronous wheel-side speed. |
| `T_e` | `engine_torque` | N m | Delivered engine torque. |
| `T_c` | `coupling_torque` | N m | Torque transmitted through the coupling. |
| `P_slip` | `coupling_slip_power` | W | Power dissipated by coupling slip. |
| `E_slip` | `coupling_slip_energy` | J | Cumulative coupling slip energy. |
| `fuel_rate` | `engine_fuel_rate` | kg/s | Instantaneous fuel mass flow. |

## 4. Longitudinal Force Balance

For vehicle mass `m`, speed `v`, and longitudinal acceleration `dv_dt`:

```text
m_eq * dv_dt =
    F_tire
  - F_aero
  - F_roll
  - F_grade
  - F_brake
```

where `m_eq` may include reflected rotational inertia. If explicit wheel,
engine, or driveline inertias are modeled separately, they must not also be
included in `m_eq`.

The force terms use these signs:

- `F_tire` is positive when it propels the vehicle forward.
- `F_brake` is non-negative and opposes forward motion.
- `F_grade` is positive uphill and negative downhill.
- `F_aero` is positive when relative airflow creates drag and negative only in
  strong tailwind cases where the air effectively assists forward motion.
- `F_roll` is non-negative during forward motion and opposes travel.

### Aerodynamic Drag

```text
v_rel = v - v_wind

F_aero = 0.5 * rho * C_d * A_f * v_rel * abs(v_rel)
```

where:

- `rho` is air density.
- `C_d` is drag coefficient.
- `A_f` is frontal area.
- `v_wind` is longitudinal wind speed, positive in the vehicle travel direction.

With this convention, a headwind increases `v_rel`, while a tailwind decreases
it.

### Rolling Resistance

An initial model is:

```text
F_roll = m * g * C_rr * cos(theta)
```

for nonzero vehicle speed, with a smooth low-speed treatment to avoid a force
discontinuity. A speed-dependent coefficient may be introduced later.

### Grade Force

```text
F_grade = m * g * sin(theta)
```

where `theta` is positive uphill. A negative grade therefore reduces the required
tractive force or increases the need for braking.

### Tire Force Limit

The commanded longitudinal tire force must satisfy a simplified friction bound:

```text
abs(F_tire) <= mu * F_z
```

where `mu` is the tire-road friction coefficient and `F_z` is the normal load
available to the driven tire model. The initial model may use a lumped normal
load. Later versions can include axle load distribution, load transfer, and
combined-slip limits.

## 5. Wheel and Vehicle Kinematics

For effective tire radius `r_w`, no-slip wheel speed is:

```text
omega_w = v / r_w
```

If wheel rotational dynamics are modeled explicitly:

```text
J_w * domega_w_dt =
    T_axle
  - F_tire * r_w
  - T_wheel_loss
```

The project should choose either an equivalent-mass approximation or explicit
wheel dynamics for a given model version and avoid counting rotational inertia
twice.

## 6. Transmission Kinematics

For selected gear ratio `i_g`, final-drive ratio `i_f`, and total ratio `i_t`:

```text
i_t = i_g * i_f

omega_sync = i_t * omega_w
```

This is the target engine speed for zero-slip re-engagement in the selected gear,
subject to engine idle and maximum-speed limits.

When the coupling is locked:

```text
omega_e ~= omega_sync
```

When decoupled, `omega_e` and `omega_w` evolve independently.

## 7. Engine Model

The initial engine model should include:

- Engine speed state `omega_e`.
- Commanded and delivered engine torque.
- Speed- and command-dependent torque limits.
- Rotational inertia `J_e`.
- Internal friction and pumping torque.
- Idle-speed control.
- Fuel rate map or calibrated approximation.
- Overrun fuel cut-off conditions.

Engine rotational dynamics while decoupled are:

```text
J_e * domega_e_dt =
    T_e
  - T_friction
  - T_accessory
  - T_coupling_engine_side
```

During connected operation, engine inertia may be integrated within the coupled
drivetrain equations or reflected through the gear ratio. The implementation
must conserve torque and power consistently.

## 8. Fuel Consumption

A map-based model is preferred when data are available:

```text
fuel_rate = f(omega_e, T_e)
```

where `fuel_rate` is normally measured in `kg/s`.

The map must define:

- Idle fuel use.
- Positive-load fuel use.
- Overrun fuel cut-off.
- Invalid operating regions.

If an analytical approximation is used initially, its limitations must be
documented and sensitivity-tested. Fuel comparisons are not credible if idle,
engine braking, and low-load efficiency are omitted.

## 9. Coupling Model

The coupling transmits torque according to its capacity and slip:

```text
slip_speed = omega_e - omega_sync
```

An initial controllable model may define transmitted torque as a bounded function
of commanded capacity, slip speed, and engagement direction:

```text
abs(T_c) <= T_c_max(u_c)
```

where `u_c` is the coupling command and `T_c_max` is the available torque
capacity after actuator limits.

The instantaneous slip power dissipated in the coupling is:

```text
P_slip = abs(T_c * slip_speed)
```

and accumulated slip energy is:

```text
E_slip = integral(P_slip, dt)
```

This energy is a proxy for thermal load and wear. It is not a complete clutch-life
model.

## 10. Operating Modes

### Connected

The coupling is closed and the engine is kinematically linked to the driven
wheels. The model includes propulsion, engine braking, reflected inertia, and
drivetrain losses.

### Decoupling

Coupling capacity decreases according to actuator and comfort limits. Engine
torque may be shaped to unload the coupling before it opens.

### Decoupled

The wheel side is driven only by vehicle inertia, gravity, brakes, and any other
explicit propulsion source. The engine follows idle or another declared policy.

### Rev-Matching

The target speed is:

```text
omega_target = clamp(omega_sync, omega_idle, omega_max)
```

Engine torque is controlled to reduce speed error while the coupling remains
open or transmits negligible torque.

### Re-Engaging

Coupling capacity increases after speed and torque mismatch enter allowed
bounds. The controller limits slip energy, acceleration disturbance, and jerk.
Lock-up is declared only after slip remains below a threshold for a minimum
duration.

## 11. Drivetrain Losses

Drivetrain losses may be represented by:

- Gear-dependent mechanical efficiency.
- Speed-dependent drag torque.
- Bearing and oil-churning losses.
- Final-drive efficiency.

Power-flow direction matters. A single constant efficiency applied identically
in propulsion and overrun can produce incorrect energy behavior. The initial
model should at least distinguish motoring and back-driving.

## 12. Braking

Foundation brakes provide non-negative braking force up to configured limits.
When connected, engine braking contributes through the drivetrain. Brake
allocation must avoid counting demanded deceleration twice.

The model should track:

- Foundation-brake dissipated energy.
- Engine-braking energy.
- Aerodynamic and rolling-resistance losses.
- Coupling slip energy.

These terms explain why two controllers consume different fuel over the same
route.

## 13. Re-Engagement Quality

A re-engagement event should be evaluated using:

- Initial and peak speed mismatch.
- Initial and peak torque mismatch.
- Time from re-engagement request to lock-up.
- Peak and root-mean-square acceleration disturbance.
- Peak and root-mean-square jerk.
- Coupling slip energy.
- Restored wheel-torque delay.
- Aborted or supervisor-modified transitions.

Jerk may be computed from filtered acceleration to prevent numerical noise from
dominating the metric. The filter and sample interval must be declared.

## 14. Energy Accounting

The simulator should maintain an energy balance over each run:

```text
E_fuel =
    delta_E_kinetic
  + delta_E_potential
  + E_aero
  + E_rolling
  + E_brakes
  + E_drivetrain_loss
  + E_coupling_slip
  + E_engine_loss
  + E_other
  + E_residual
```

For this balance, `E_fuel` should be expressed on a declared energy basis, such
as lower heating value. The exact terms depend on model fidelity. Residual energy
should be reported and used to detect sign, integration, or double-counting
errors.

## 15. Numerical Considerations

- Use a solver and time step appropriate for the fastest modeled dynamics.
- Avoid discontinuous force laws where a smooth physical approximation is
  sufficient.
- Detect zero-speed crossings and prevent unintended reverse motion unless
  explicitly supported.
- Apply saturation before integration where physical limits require it.
- Test results across multiple time steps.
- Separate simulation event detection from logging frequency.

## 16. Calibration and Validation Tests

The initial plant should pass:

1. **Static equilibrium:** zero acceleration when tractive and resistive forces
   balance.
2. **Constant acceleration:** agreement with an analytical force-balance case.
3. **Coast-down:** plausible deceleration for connected and decoupled modes.
4. **Grade hold:** correct force direction and brake requirement.
5. **Gear kinematics:** correct synchronous engine speed in every gear.
6. **Fuel cut-off:** zero or configured fuel flow under valid overrun conditions.
7. **Idle behavior:** stable engine speed and positive idle fuel use.
8. **Rev-match:** convergence to target speed without exceeding limits.
9. **Re-engagement:** bounded slip, torque disturbance, and energy.
10. **Energy balance:** residual below the accepted numerical tolerance.

## 17. Known Limitations of the Initial Model

- Longitudinal motion only.
- Simplified tire-road interaction.
- Lumped component temperatures and wear proxies.
- No driveline torsional vibration unless added later.
- Approximate actuator dynamics.
- Fuel and loss accuracy limited by available maps.
- No direct claim of real-world performance without external validation.
