# Acceptance Tests

This document defines pre-implementation acceptance tests. The tests describe
observable behavior that the future simulator must satisfy before machine
learning work begins.

## Test Philosophy

- Test physics before controller performance.
- Test deterministic behavior before stochastic experiments.
- Test state-machine guards before learned policies.
- Test paired comparisons before claiming ADDS benefit.
- Treat numerical failures and hidden exclusions as failed tests.

## Phase 0 Acceptance

### A0.1 Documentation Completeness

Required files exist and are non-empty:

- `README.md`
- `docs/project_idea.md`
- `docs/roadmap.md`
- `docs/system_architecture.md`
- `docs/ml_strategy.md`
- `docs/vehicle_dynamics.md`
- `docs/glossary.md`
- `docs/signal_dictionary.md`
- `docs/parameter_dictionary.md`
- `docs/scenarios.md`
- `docs/metrics.md`
- `docs/acceptance_tests.md`
- `docs/open_decisions.md`

Pass condition:

- All files exist and use English project content.

### A0.2 Unit Ownership

Every initial signal and parameter has a declared unit or explicit unitless
status.

Pass condition:

- No physical signal or parameter is introduced without a unit.

### A0.3 Baseline Fairness Contract

The comparison method states which parameters and scenario inputs are shared by
the conventional and ADDS vehicles.

Pass condition:

- A paired run can be defined without ambiguity about shared inputs.

## Phase 1 Physical Model Acceptance

### A1.1 Static Force Balance

Setup:

- Level road.
- Constant target speed.
- Tractive force equal to aerodynamic plus rolling resistance.

Pass condition:

- Longitudinal acceleration remains near zero within the configured tolerance.

### A1.2 Coast-Down Plausibility

Setup:

- Vehicle starts at a fixed speed on level road.
- Accelerator is released.
- Run once connected and once decoupled.

Pass condition:

- Vehicle speed decreases monotonically in both cases.
- Connected coast-down decelerates faster than decoupled coast-down when engine
  braking is enabled.
- Fuel use during decoupled idle is positive if the engine remains running.

### A1.3 Grade Direction

Setup:

- Run otherwise identical cases with positive and negative road grade.

Pass condition:

- Positive grade increases required tractive force.
- Negative grade decreases required tractive force or requires braking to hold
  speed.

### A1.4 Gear Kinematics

Setup:

- Sweep vehicle speed and gear.

Pass condition:

- Synchronous engine speed equals wheel speed multiplied by gear and final-drive
  ratio.
- Invalid target gears are rejected.

### A1.5 Energy Accounting

Setup:

- Complete a deterministic drive cycle.

Pass condition:

- Energy-balance residual remains below the configured tolerance.
- All dissipated energy terms are non-negative.

## Phase 2 State-Machine Acceptance

### A2.1 Valid Decoupling Sequence

Setup:

- Connected vehicle at a supported speed.
- No brake demand.
- Controller requests decoupling.

Pass condition:

- Mode sequence follows `CONNECTED -> DECOUPLING -> DECOUPLED`.
- No illegal intermediate state occurs.
- Mode transition events are logged.

### A2.2 Brake Demand Blocks Decoupling

Setup:

- Controller requests decoupling while brake demand exceeds threshold.

Pass condition:

- Decoupling is rejected or cancelled.
- Safety override is logged with the correct reason.

### A2.3 Rev-Matched Re-Engagement

Setup:

- Vehicle is decoupled.
- Positive torque demand appears.
- Target gear is feasible.

Pass condition:

- Mode sequence follows `DECOUPLED -> REV_MATCHING -> REENGAGING -> CONNECTED`.
- Re-engagement begins only after speed and torque mismatch are within allowed
  limits.
- Slip energy and jerk remain within configured limits.

### A2.4 Failed Transition Fallback

Setup:

- Inject an actuator or observation fault during transition.

Pass condition:

- Runtime monitor detects the fault.
- Fallback behavior activates.
- Simulation remains numerically stable.

## Phase 3 Controller Acceptance

### A3.1 Conventional Baseline Completes Catalog

Setup:

- Run the conventional controller over the minimum scenario catalog.

Pass condition:

- All nominal scenarios complete without hard constraint violations.

### A3.2 Rule-Based ADDS Completes Catalog

Setup:

- Run the rule-based ADDS controller over the same scenarios and seeds.

Pass condition:

- All nominal scenarios complete without hard constraint violations.
- Safety-supervisor overrides remain below the configured threshold.

### A3.3 Paired Comparison Integrity

Setup:

- Run paired conventional and ADDS evaluations.

Pass condition:

- Both runs use identical scenario, vehicle, environment, solver, and seed
  settings except for controller authority.
- Metric deltas are computed from the paired results.

## Phase 5 ML Readiness Acceptance

Machine learning work should not begin until:

- Phase 1 physical tests pass.
- Phase 2 transition tests pass.
- Phase 3 baseline tests pass.
- Scenario splits are defined.
- Metrics are stable and computed from logs.
- Safety supervisor can reject invalid actions independently of the ML policy.

## Failure Reporting

Every failed test should report:

- Test identifier.
- Configuration identifier.
- Random seed.
- Expected behavior.
- Observed behavior.
- Relevant signal traces.
- Whether the failure is physical, numerical, controller-related, or
  configuration-related.
