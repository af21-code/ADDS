# Open Decisions

This document tracks modeling and project decisions that must be resolved before
or during implementation. Decisions should be updated as the project matures.

## Decision Status

Use these statuses:

- `Open`: not yet decided.
- `Proposed`: a preferred answer exists but is not final.
- `Accepted`: decision is active.
- `Deferred`: intentionally postponed.
- `Superseded`: replaced by a newer decision.

## OD-001: Reference Vehicle Class

Status: Open

Question:

- What nominal vehicle should the first simulator represent?

Options:

- Compact passenger car.
- Mid-size passenger car.
- Light commercial vehicle.
- Abstract normalized vehicle.

Impact:

- Determines mass, drag, rolling resistance, engine map, gear ratios, and
  expected decoupling benefit.

Current recommendation:

- Start with a mid-size passenger car because it is representative and easier to
  parameterize from public data.

## OD-002: Engine Fuel Map Source

Status: Open

Question:

- Should the initial engine model use a public fuel map, synthetic calibrated
  map, or analytical approximation?

Impact:

- Fuel claims depend strongly on low-load and idle behavior.

Current recommendation:

- Use a documented synthetic map for early software validation, then replace it
  with a published or measured map before drawing efficiency conclusions.

## OD-003: Engine Behavior While Decoupled

Status: Proposed

Question:

- Should the engine idle, shut down, or follow another policy while decoupled?

Impact:

- Engine stop-start can dominate fuel results and obscure the isolated effect of
  drivetrain decoupling.

Current recommendation:

- Keep the engine running at idle for the first ADDS studies. Treat stop-start as
  a future extension.

## OD-004: Initial Numerical Integration Method

Status: Open

Question:

- Which solver should the minimum viable simulator use?

Options:

- Fixed-step explicit Euler.
- Fixed-step semi-implicit Euler.
- Fixed-step Runge-Kutta.
- Adaptive ODE solver.

Impact:

- Affects determinism, stability, event handling, and implementation complexity.

Current recommendation:

- Begin with a fixed-step method for deterministic comparisons, then verify
  time-step sensitivity.

## OD-005: Coupling Fidelity

Status: Open

Question:

- How detailed should the initial clutch or coupling model be?

Options:

- Ideal open/closed switch with transition timing.
- Torque-capacity model with slip energy.
- Thermal model with temperature state.
- Detailed friction-material model.

Impact:

- Re-engagement quality and mechanical stress metrics require more than an ideal
  switch.

Current recommendation:

- Start with a torque-capacity model and slip energy. Defer thermal modeling.

## OD-006: Gear Selection Authority

Status: Open

Question:

- Can ADDS choose a new target gear during re-engagement, or must it reuse the
  gear selected before decoupling?

Impact:

- Target gear affects synchronous engine speed, rev-match effort, and response.

Current recommendation:

- Allow a constrained target-gear choice after basic same-gear re-engagement is
  verified.

## OD-007: Route Preview Assumptions

Status: Open

Question:

- What preview information is available to the controller?

Options:

- No preview.
- Target-speed preview only.
- Grade preview only.
- Target-speed and grade preview.
- Perfect future scenario knowledge for oracle experiments only.

Impact:

- Preview assumptions strongly affect controller capability and fairness.

Current recommendation:

- Support explicit preview modes and label all results accordingly.

## OD-008: Driver Model

Status: Open

Question:

- What driver model should be used for the first paired comparisons?

Options:

- Direct drive-cycle speed tracker.
- Accelerator and brake command trace.
- Simple human-like feedback driver.

Impact:

- Driver response can mask or exaggerate drivetrain strategy benefits.

Current recommendation:

- Start with a deterministic speed tracker, then add richer driver models later.

## OD-009: Initial Metric Thresholds

Status: Open

Question:

- What numerical thresholds define acceptable speed error, jerk, response delay,
  and energy residual?

Impact:

- Thresholds determine whether ADDS improvements are meaningful or merely
  efficient at the cost of drivability.

Current recommendation:

- Use conservative placeholders for development and calibrate thresholds after
  physical model validation.

## OD-010: Machine Learning Algorithm Family

Status: Deferred

Question:

- Which ML method should be used first?

Options:

- Behavioral cloning.
- Offline reinforcement learning.
- Constrained online reinforcement learning.
- Hybrid model-predictive and learned policy.

Impact:

- ML method affects data requirements, safety guarantees, and interpretability.

Current recommendation:

- Defer final choice until baselines and scenario data exist. Begin with
  behavioral cloning if expert trajectories are available.

## OD-011: Configuration Format

Status: Open

Question:

- Which human-readable configuration format should be used?

Options:

- YAML.
- JSON.
- TOML.
- Python-native configuration.

Impact:

- Affects validation, reproducibility, and ease of experiment review.

Current recommendation:

- Use YAML or TOML with schema validation; avoid executable configuration for
  early reproducibility.

## OD-012: Repository Implementation Language

Status: Open

Question:

- Which language should be used for the first simulator implementation?

Options:

- Python.
- Julia.
- MATLAB or Simulink.
- C++ with Python bindings.

Impact:

- Affects development speed, numerical libraries, ML integration, and future
  real-time work.

Current recommendation:

- Use Python for the research simulator unless real-time constraints become the
  immediate priority.

## Decision Log Template

Future accepted decisions should include:

```text
Decision ID:
Status:
Date:
Context:
Decision:
Consequences:
Alternatives considered:
Review trigger:
```
