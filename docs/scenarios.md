# Scenario Specification

Scenarios define the conditions under which the conventional and ADDS vehicles
are compared. A scenario must be reproducible, versioned, and independent of the
controller being evaluated.

## Scenario Contract

Each scenario should define:

- Stable scenario identifier.
- Human-readable description.
- Initial state.
- Route distance or time horizon.
- Target speed profile.
- Road grade profile.
- Driver model or direct control trace.
- Environmental assumptions.
- Disturbances and random seed, if stochastic.
- Termination conditions.
- Required metrics.
- Expected qualitative behavior.

## Fair Comparison Rules

For paired conventional-versus-ADDS evaluation:

1. Use identical vehicle parameters except for controller authority.
2. Use identical scenario definitions and initial conditions.
3. Reset all dynamic states between runs.
4. Use paired random seeds for disturbances.
5. Apply the same driver model and speed-tracking objective.
6. Use the same solver, logging, and metric configuration.
7. Report invalid or failed runs rather than excluding them silently.

## Minimum Scenario Catalog

### S01: Level-Road Coast-Down

Purpose:

- Validate aerodynamic drag, rolling resistance, connected engine braking, and
  decoupled coasting behavior.

Setup:

- Straight level road.
- Initial speed above idle-synchronous speed in a mid gear.
- Accelerator released.
- No foundation braking.
- No road preview required.

Expected behavior:

- The conventional vehicle decelerates faster when connected engine braking is
  active.
- The ADDS vehicle may coast farther when decoupled.
- Idle fuel use must be counted for the decoupled ADDS vehicle.

### S02: Constant-Speed Cruise

Purpose:

- Validate steady-state force balance and fuel use.

Setup:

- Level road.
- Fixed target speed.
- Speed-tracking driver model.
- No intentional decoupling event.

Expected behavior:

- Tractive force balances aerodynamic drag and rolling resistance.
- Speed error remains bounded.
- Energy balance residual remains within tolerance.

### S03: Mild Descent With Lower Speed Ahead

Purpose:

- Test whether decoupling is blocked or avoided when engine braking is valuable.

Setup:

- Initial cruise speed.
- Negative grade.
- Lower target speed or speed limit ahead.
- Route preview available.

Expected behavior:

- A good ADDS controller should avoid overspeed.
- Connected operation may outperform decoupled coasting because engine braking
  reduces foundation-brake demand.

### S04: Rolling Terrain

Purpose:

- Evaluate route-preview usage over alternating uphill and downhill sections.

Setup:

- Repeating grade profile.
- Moderate target speed.
- Preview horizon varied across experiments.

Expected behavior:

- Decoupling decisions should depend on upcoming grade and target-speed changes.
- The policy should not decouple immediately before a high-torque uphill demand.

### S05: Sudden Positive Torque Demand While Decoupled

Purpose:

- Evaluate response delay and rev-matched re-engagement.

Setup:

- Vehicle initially decoupled and coasting.
- Driver requests acceleration at a defined time or distance.
- Target gear is feasible.

Expected behavior:

- Controller begins rev-matching promptly.
- Re-engagement occurs within the response-delay target.
- Slip speed, slip energy, acceleration disturbance, and jerk remain bounded.

### S06: Brake Demand During Decoupling Request

Purpose:

- Verify transition guards and safety-supervisor behavior.

Setup:

- ADDS controller requests decoupling.
- Brake demand rises above the configured block threshold.

Expected behavior:

- The safety supervisor rejects or cancels decoupling.
- Event logs record the intervention reason.
- The vehicle remains in a conservative connected or braking-compatible state.

### S07: Low-Speed Urban Cycle

Purpose:

- Test whether decoupling is useful or harmful at low speeds with frequent
  acceleration and braking.

Setup:

- Low target speeds.
- Repeated stops or near-stops.
- Frequent driver demand changes.

Expected behavior:

- ADDS may spend little time decoupled because response requirements dominate.
- Excessive mode switching should be penalized.

### S08: Highway Lift-Off And Reacceleration

Purpose:

- Study a high-value ADDS use case with long coasting potential.

Setup:

- Highway speed.
- A gradual target reduction that can be followed by natural coast-down rather
  than mandatory foundation braking.
- Later reacceleration demand.
- Mild grade or level road.

The initial catalog implementation uses a level-road target profile of
`30 m/s` at `0 s`, `26 m/s` at `10 s`, holds `26 m/s` until `14 s`, and returns
to `30 m/s` at `20 s`. The earlier two-second speed reduction was removed
because its approximately `-3 m/s^2` target slope represented a braking event,
not a physically credible highway coasting opportunity.

Expected behavior:

- ADDS may save fuel if coast duration is long enough.
- The benefit must be compared against idle fuel use and re-engagement costs.
- The initial nominal result must not be generalized across vehicle resistance,
  payload, or grade perturbations without rerunning the acceptance gates.
- The current guarded baseline suppresses marginal coast entries when the
  one-second target reduction is below `0.25 m/s` or positive grade exceeds
  approximately `0.5%`.

### S09: Parameter Uncertainty Sweep

Purpose:

- Evaluate robustness under plausible parameter variation.

Setup:

- Repeat selected scenarios with varied mass, drag, rolling resistance, road
  grade, and tire friction.

Expected behavior:

- Conclusions should not depend on a single nominal vehicle.
- Policies should fail conservatively outside supported ranges.

### S10: Invalid Observation Or Actuator Fault

Purpose:

- Verify fallback behavior.

Setup:

- Inject invalid sensor values, stale preview, or actuator response failure.

Expected behavior:

- The runtime monitor detects the issue.
- The vehicle enters `FAULT_SAFE` or another declared conservative behavior.
- The run records the fault without numerical instability.

## Scenario Metadata

Each scenario file or configuration should include:

```text
scenario_id
scenario_version
description
author
created_date
route_definition
driver_definition
environment_definition
initial_state
termination_conditions
expected_metrics
known_limitations
```

## Dataset Splits

For machine learning, scenarios should be divided into:

- Training scenarios.
- Validation scenarios for model selection.
- Frozen test scenarios for final reporting.
- Stress scenarios for known edge cases.

Adjacent time windows from the same route should not be split across training and
test sets, because that leaks route structure into evaluation.
