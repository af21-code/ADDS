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

## 3. Longitudinal Force Balance

For vehicle mass \(m\), speed \(v\), and longitudinal acceleration \(\dot{v}\):

\[
m_\mathrm{eq}\dot{v}
= F_\mathrm{tire} - F_\mathrm{aero} - F_\mathrm{roll}
- F_\mathrm{grade} - F_\mathrm{brake}
\]

where \(m_\mathrm{eq}\) may include reflected rotational inertia.

### Aerodynamic Drag

\[
F_\mathrm{aero}
= \frac{1}{2}\rho C_d A_f (v - v_\mathrm{wind})|v - v_\mathrm{wind}|
\]

with air density \(\rho\), drag coefficient \(C_d\), frontal area \(A_f\), and
longitudinal wind speed \(v_\mathrm{wind}\).

### Rolling Resistance

An initial model is:

\[
F_\mathrm{roll} = m g C_{rr}\cos(\theta)
\]

for nonzero vehicle speed, with a smooth low-speed treatment to avoid a force
discontinuity. A speed-dependent coefficient may be introduced later.

### Grade Force

\[
F_\mathrm{grade} = m g \sin(\theta)
\]

where \(\theta\) is positive uphill.

### Tire Force Limit

The commanded longitudinal tire force must satisfy a simplified friction bound:

\[
|F_\mathrm{tire}| \leq \mu F_z
\]

The initial model may use a lumped driven-axle normal load. Later versions can
include load transfer and combined-slip limits.

## 4. Wheel and Vehicle Kinematics

For effective tire radius \(r_w\), no-slip wheel speed is:

\[
\omega_w = \frac{v}{r_w}
\]

If wheel rotational dynamics are modeled explicitly:

\[
J_w\dot{\omega}_w
= T_\mathrm{axle} - F_\mathrm{tire}r_w - T_\mathrm{wheel,loss}
\]

The project should choose either an equivalent-mass approximation or explicit
wheel dynamics for a given model version and avoid counting rotational inertia
twice.

## 5. Transmission Kinematics

For selected gear ratio \(i_g\), final-drive ratio \(i_f\), and total ratio
\(i_t = i_g i_f\), the synchronous engine speed is:

\[
\omega_\mathrm{sync} = i_t\omega_w
\]

This is the target engine speed for zero-slip re-engagement in the selected gear,
subject to engine idle and maximum-speed limits.

When the coupling is locked:

\[
\omega_e \approx \omega_\mathrm{sync}
\]

When decoupled, \(\omega_e\) and \(\omega_w\) evolve independently.

## 6. Engine Model

The initial engine model should include:

- Engine speed state \(\omega_e\).
- Commanded and delivered engine torque.
- Speed- and command-dependent torque limits.
- Rotational inertia \(J_e\).
- Internal friction and pumping torque.
- Idle-speed control.
- Fuel rate map or calibrated approximation.
- Overrun fuel cut-off conditions.

Engine rotational dynamics while decoupled are:

\[
J_e\dot{\omega}_e
= T_e - T_\mathrm{friction} - T_\mathrm{accessory} - T_\mathrm{coupling,e}
\]

During connected operation, engine inertia may be integrated within the coupled
drivetrain equations or reflected through the gear ratio. The implementation
must conserve torque and power consistently.

## 7. Fuel Consumption

A map-based model is preferred when data are available:

\[
\dot{m}_f = f(\omega_e, T_e)
\]

The map must define:

- Idle fuel use.
- Positive-load fuel use.
- Overrun fuel cut-off.
- Invalid operating regions.

If an analytical approximation is used initially, its limitations must be
documented and sensitivity-tested. Fuel comparisons are not credible if idle,
engine braking, and low-load efficiency are omitted.

## 8. Coupling Model

The coupling transmits torque according to its capacity and slip:

\[
\Delta\omega = \omega_e - \omega_\mathrm{sync}
\]

An initial controllable model may define transmitted torque as a bounded function
of commanded capacity, slip speed, and engagement direction:

\[
|T_c| \leq T_{c,\max}(u_c)
\]

The instantaneous slip power dissipated in the coupling is:

\[
P_\mathrm{slip} = |T_c\Delta\omega|
\]

and accumulated slip energy is:

\[
E_\mathrm{slip} = \int P_\mathrm{slip}\,dt
\]

This energy is a proxy for thermal load and wear. It is not a complete clutch-life
model.

## 9. Operating Modes

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

\[
\omega_\mathrm{target}
= \operatorname{clamp}(\omega_\mathrm{sync},
\omega_\mathrm{idle}, \omega_\mathrm{max})
\]

Engine torque is controlled to reduce speed error while the coupling remains
open or transmits negligible torque.

### Re-Engaging

Coupling capacity increases after speed and torque mismatch enter allowed
bounds. The controller limits slip energy, acceleration disturbance, and jerk.
Lock-up is declared only after slip remains below a threshold for a minimum
duration.

## 10. Drivetrain Losses

Drivetrain losses may be represented by:

- Gear-dependent mechanical efficiency.
- Speed-dependent drag torque.
- Bearing and oil-churning losses.
- Final-drive efficiency.

Power-flow direction matters. A single constant efficiency applied identically
in propulsion and overrun can produce incorrect energy behavior. The initial
model should at least distinguish motoring and back-driving.

## 11. Braking

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

## 12. Re-Engagement Quality

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

## 13. Energy Accounting

The simulator should maintain an energy balance over each run:

\[
E_\mathrm{fuel}
= \Delta E_\mathrm{kinetic}
+ \Delta E_\mathrm{potential}
+ E_\mathrm{aero}
+ E_\mathrm{rolling}
+ E_\mathrm{brakes}
+ E_\mathrm{drivetrain\,loss}
+ E_\mathrm{coupling\,slip}
+ E_\mathrm{engine\,loss}
+ E_\mathrm{other}
+ E_\mathrm{residual}
\]

The exact terms depend on model fidelity. Residual energy should be reported and
used to detect sign, integration, or double-counting errors.

## 14. Numerical Considerations

- Use a solver and time step appropriate for the fastest modeled dynamics.
- Avoid discontinuous force laws where a smooth physical approximation is
  sufficient.
- Detect zero-speed crossings and prevent unintended reverse motion unless
  explicitly supported.
- Apply saturation before integration where physical limits require it.
- Test results across multiple time steps.
- Separate simulation event detection from logging frequency.

## 15. Calibration and Validation Tests

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

## 16. Known Limitations of the Initial Model

- Longitudinal motion only.
- Simplified tire-road interaction.
- Lumped component temperatures and wear proxies.
- No driveline torsional vibration unless added later.
- Approximate actuator dynamics.
- Fuel and loss accuracy limited by available maps.
- No direct claim of real-world performance without external validation.
