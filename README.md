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
|-- app
|   `-- streamlit_app.py
|-- adds_sim
|   |-- __init__.py
|   |-- batch.py
|   |-- benchmarks.py
|   |-- cli.py
|   |-- comparison.py
|   |-- controllers.py
|   |-- data.py
|   |-- defaults.py
|   |-- learned_controller.py
|   |-- metrics.py
|   |-- ml.py
|   |-- parameters.py
|   |-- profiles.py
|   |-- robustness.py
|   |-- run_robustness.py
|   |-- scenario_catalog.py
|   |-- simulator.py
|   |-- train_imitation.py
|   `-- visualization.py
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
|-- requirements.txt
`-- tests
    |-- test_phase1_acceptance.py
    |-- test_phase2_state_machine.py
    |-- test_phase3_baselines.py
    |-- test_phase4_data_infrastructure.py
    |-- test_phase5_imitation_learning.py
    |-- test_phase6_robustness.py
    `-- test_phase7_visualization.py
```

The current implementation covers the initial Phase 1 physical simulator and a
first Phase 2 drivetrain state machine, Phase 3 deterministic baselines, and
Phase 4 scenario/data infrastructure. It also includes a first Phase 5
behavioral-cloning pipeline for an interpretable learned ADDS controller.
Phase 6 robustness and sensitivity evaluation is available for compact
uncertainty sweeps. A first Phase 7A Streamlit visualization prototype is
available for reviewing conventional-vs-ADDS scenario comparisons. Advanced ML,
optimized ADDS policy training, and real-time integration are deferred until the
scenario catalog and exported datasets are broader.

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
The Python simulator now provides:

- Deterministic fixed-step longitudinal vehicle dynamics.
- Aerodynamic drag, rolling resistance, grade force, tire-force limits, and
  equivalent inertia.
- Basic connected-drivetrain engine, transmission, final-drive, fuel, and loss
  modeling.
- Constant torque, coast-down, and speed-tracking controllers.
- A first ADDS state machine with `CONNECTED`, `DECOUPLING`, `DECOUPLED`,
  `REV_MATCHING`, `REENGAGING`, and `FAULT_SAFE` modes.
- Deterministic transition guards for brake-demand blocking, low-speed blocking,
  fault fallback, and re-engagement slip limits.
- Basic rev-matching and controlled re-engagement behavior.
- Conventional and transparent rule-based ADDS baseline controllers.
- A compact benchmark catalog and paired conventional-vs-ADDS comparison helper.
- A versioned Phase 4 scenario catalog with train, validation, test, and stress
  splits.
- Reproducible batch evaluation with manifest, summary CSV, and trajectory CSV
  export.
- A lightweight imitation-learning pipeline that clones rule-based ADDS
  thresholds from train-split expert trajectories.
- JSON checkpoints plus training and evaluation reports for the initial learned
  controller.
- Robustness evaluation across deterministic mass, drag, rolling resistance,
  tire-friction, and grade perturbations.
- JSON and CSV robustness reports for sensitivity and constraint-regression
  checks.
- Dashboard-ready comparison helpers and a Streamlit visualization prototype.
- A project-facing dashboard layout with overview, scenario comparison, catalog
  summary, and result downloads.
- Automatic dashboard insights that summarize fuel benefit, state transitions,
  speed-tracking impact, and safety signals for the selected scenario.
- An explicit dashboard research verdict that rejects efficiency claims when
  mobility or safety comparability gates do not pass.
- Event-level dashboard diagnostics for ADDS mode durations and transition
  timing.
- Physical logging and summary metrics.
- Unit tests for the initial Phase 1 through Phase 7A acceptance cases.

The current ADDS implementation is intentionally simple. It is suitable for
state-machine verification, early transition studies, baseline trade-off checks,
dataset plumbing, first-pass imitation-learning experiments, and compact
robustness sweeps, not for production drivetrain control or real vehicle claims.

## Running The Simulator

Run the acceptance tests:

```bash
python3 -B -m unittest discover -s tests -v
```

Run the demo constant-speed scenario:

```bash
python3 -B -m adds_sim.cli
```

Run a paired benchmark comparison:

```bash
python3 -B - <<'PY'
from adds_sim import *

config = default_simulation_config()
simulator = LongitudinalSimulator(config)

for scenario in benchmark_scenarios():
    comparison = run_paired_comparison(
        simulator,
        scenario,
        ConventionalBaselineController(scenario.initial_gear),
        RuleBasedADDSController(scenario.initial_gear),
    )
    print(
        scenario.scenario_id,
        "fuel_delta=", round(comparison.deltas["delta_fuel_used"], 8),
        "relative_fuel_change=", round(comparison.deltas["relative_fuel_change"], 3),
        "adds_transitions=", comparison.adds_summary["mode_transition_count"],
        "safety_overrides=", comparison.adds_summary["safety_override_count"],
    )
PY
```

Run a reproducible Phase 4 batch export:

```bash
python3 -B - <<'PY'
from pathlib import Path
from adds_sim import *

output_dir = Path("/tmp/adds_phase4_batch")
result = run_batch_evaluation(
    LongitudinalSimulator(default_simulation_config()),
    phase4_scenario_catalog(),
    output_dir,
)

print("manifest:", result.manifest_path)
print("summary:", result.summary_path)
print("trajectories:", len(result.trajectory_paths))
PY
```

Train the initial imitation-learning controller:

```bash
python3 -B -m adds_sim.train_imitation /tmp/adds_phase5_imitation
```

This writes:

```text
/tmp/adds_phase5_imitation/learned_adds_thresholds.json
/tmp/adds_phase5_imitation/training_report.json
/tmp/adds_phase5_imitation/evaluation_report.json
```

Run robustness and sensitivity evaluation:

```bash
python3 -B -m adds_sim.run_robustness /tmp/adds_phase6_robustness
```

This writes:

```text
/tmp/adds_phase6_robustness/robustness_report.json
/tmp/adds_phase6_robustness/robustness_runs.csv
```

Run the Phase 7A Streamlit visualization prototype:

```bash
python3 -m pip install -r requirements.txt
python3 -m streamlit run app/streamlit_app.py --server.address localhost
```

The dashboard lets you select a catalog scenario, compare the conventional
baseline against either the rule-based or learned ADDS controller, and inspect
speed, fuel, engine-speed, coupling-mode, and slip-energy curves side by side.

## License

No license has been selected. Until a license is added, all rights are reserved
by the project owner.
