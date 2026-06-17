# ADDS: Adaptive Drivetrain Decoupling System

ADDS is an AI-assisted vehicle dynamics simulation project for studying adaptive
drivetrain decoupling. It compares two virtual vehicles under the same driving
conditions:

1. A conventional vehicle whose engine remains mechanically connected to the
   driven wheels whenever a gear is engaged.
2. An ADDS-equipped vehicle that can keep the drivetrain connected, temporarily
   decouple the engine from the wheels, and re-engage it through controlled
   rev-matching.

The central research question is:

> Under which conditions should the engine remain connected, when should it be
> decoupled, and how should it be re-engaged to improve efficiency without
> compromising control, comfort, responsiveness, or safety?

## Project Goals

- Build a reproducible longitudinal vehicle dynamics simulator.
- Compare conventional and adaptive-decoupling strategies fairly.
- Model the physical and control implications of drivetrain state changes.
- Develop rule-based reference controllers before introducing machine learning.
- Train and evaluate AI policies for connection, decoupling, and re-engagement.
- Quantify energy use, fuel use, travel time, ride comfort, drivability, and
  mechanical stress.
- Identify operating regions where adaptive decoupling is beneficial or harmful.

## Scope

The initial project focuses on a single-track longitudinal model of a
combustion-engine road vehicle with a stepped transmission and a controllable
coupling device. The simulator will represent:

- Driver or drive-cycle speed demand.
- Engine, transmission, clutch or coupling, final drive, wheels, and vehicle
  body.
- Road grade, aerodynamic drag, rolling resistance, and tire force limits.
- Fuel consumption and drivetrain losses.
- Connected, decoupled, rev-matching, and re-engagement behavior.
- Conventional and ADDS supervisory controllers.
- Deterministic scenarios and configurable disturbances.

The first versions will not attempt to replace high-fidelity multibody,
powertrain, hardware-in-the-loop, or production vehicle validation tools.
Lateral dynamics, detailed emissions chemistry, thermal aging, and production
actuator design are outside the initial scope.

## Operating Modes

ADDS uses an explicit supervisory state machine:

| Mode | Description |
| --- | --- |
| `CONNECTED` | Engine torque and engine braking can pass through the drivetrain. |
| `DECOUPLING` | The coupling opens through a controlled transition. |
| `DECOUPLED` | Vehicle coasts while engine speed evolves independently. |
| `REV_MATCHING` | Engine speed is controlled toward the target synchronous speed. |
| `REENGAGING` | The coupling closes while slip and torque disturbance are limited. |
| `FAULT_SAFE` | A conservative fallback state is applied after invalid or unsafe conditions. |

Gear selection and coupling state are separate decisions. A vehicle may retain
a selected gear while the engine is mechanically decoupled.

## Comparison Method

Both virtual vehicles must use the same:

- Vehicle parameters and initial conditions.
- Route, road grade, weather assumptions, and drive cycle.
- Driver demand or speed-tracking target.
- Transmission ratios and shift policy, unless a study explicitly varies them.
- Numerical solver settings and simulation time step.

The comparison will report at least:

- Fuel or equivalent energy consumed.
- Distance traveled and travel time.
- Speed-tracking error.
- Time spent in each operating mode.
- Number and duration of decoupling events.
- Re-engagement slip energy and peak clutch or coupling load.
- Longitudinal acceleration and jerk.
- Response delay to positive torque demand.
- Constraint violations and failed transitions.

No efficiency claim should be accepted unless mobility, safety, and drivability
constraints remain comparable.

## Repository Structure

```text
.
|-- README.md
|-- adds_sim
|   |-- __init__.py
|   |-- cli.py
|   |-- controllers.py
|   |-- defaults.py
|   |-- metrics.py
|   |-- parameters.py
|   |-- profiles.py
|   `-- simulator.py
|-- docs
    |-- acceptance_tests.md
    |-- glossary.md
    |-- metrics.md
    |-- ml_strategy.md
    |-- open_decisions.md
    |-- parameter_dictionary.md
    |-- project_idea.md
    |-- roadmap.md
    |-- scenarios.md
    |-- signal_dictionary.md
    |-- system_architecture.md
    `-- vehicle_dynamics.md
|-- pyproject.toml
`-- tests
    `-- test_phase1_acceptance.py
```

The current implementation is intentionally limited to Phase 1 physical
simulation and verification. ADDS transition logic, rev-matching control, and
machine learning are deferred until the conventional plant is stable.

## Documentation

- [Project Idea](docs/project_idea.md)
- [Roadmap](docs/roadmap.md)
- [System Architecture](docs/system_architecture.md)
- [Machine Learning Strategy](docs/ml_strategy.md)
- [Vehicle Dynamics](docs/vehicle_dynamics.md)
- [Glossary](docs/glossary.md)
- [Signal Dictionary](docs/signal_dictionary.md)
- [Parameter Dictionary](docs/parameter_dictionary.md)
- [Scenario Specification](docs/scenarios.md)
- [Metric Specification](docs/metrics.md)
- [Acceptance Tests](docs/acceptance_tests.md)
- [Open Decisions](docs/open_decisions.md)

## Guiding Principles

1. **Physics before optimization:** learned behavior must be evaluated against a
   transparent physical model.
2. **Baselines before AI:** simple, reproducible controllers establish whether
   machine learning adds value.
3. **Constraints before rewards:** safety and mechanical limits are enforced
   explicitly rather than left to reward shaping alone.
4. **Fair comparison:** both vehicle variants face identical test conditions.
5. **Reproducibility:** configurations, random seeds, model versions, and results
   must be traceable.
6. **Simulation claims remain simulation claims:** conclusions require later
   validation against higher-fidelity models and measured data.

## Current Status

The project has completed its initial documentation and system-definition phase.
A Phase 1 Python simulator now provides:

- Deterministic fixed-step longitudinal vehicle dynamics.
- Aerodynamic drag, rolling resistance, grade force, tire-force limits, and
  equivalent inertia.
- Basic connected-drivetrain engine, transmission, final-drive, fuel, and loss
  modeling.
- Constant torque, coast-down, and speed-tracking controllers.
- Physical logging and summary metrics.
- Unit tests for the initial Phase 1 acceptance cases.

ADDS state transitions, rev-matching, re-engagement, and ML controllers have not
been implemented yet.

## Running The Phase 1 Simulator

Run the acceptance tests:

```bash
python3 -m unittest discover -s tests -v
```

Run the demo constant-speed scenario:

```bash
python3 -m adds_sim.cli
```

## License

No license has been selected. Until a license is added, all rights are reserved
by the project owner.
