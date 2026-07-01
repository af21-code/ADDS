# Roadmap

The roadmap is organized by technical maturity rather than fixed calendar dates.
Each phase has an exit criterion so that later optimization is not built on an
unverified physical model.

## Phase 0: Definition and Documentation

### Goals

- Define project scope, terminology, assumptions, and non-goals.
- Define the conventional and ADDS vehicle variants.
- Establish system boundaries, operating modes, and comparison metrics.
- Identify model parameters and required data sources.

### Deliverables

- Initial project documentation.
- Parameter and signal dictionaries.
- Scenario and metric specifications.
- A list of open modeling decisions.

### Exit Criteria

- All required states, inputs, outputs, and units are documented.
- The baseline comparison is defined without known structural bias.
- Initial acceptance tests can be expressed before implementation.

## Phase 1: Minimum Viable Vehicle Simulator

### Goals

- Implement deterministic longitudinal vehicle dynamics.
- Add aerodynamic drag, rolling resistance, road grade, tire limits, and wheel
  inertia at an appropriate level of fidelity.
- Add a basic engine, transmission, final drive, and fuel model.
- Support configurable fixed-step simulation and result logging.

### Deliverables

- Conventional connected-drivetrain simulation.
- Standard units and parameter validation.
- Basic drive-cycle runner.
- Energy-balance and force-balance tests.

### Exit Criteria

- Constant-speed, coast-down, acceleration, and grade tests match analytical
  expectations within defined tolerances.
- Energy accounting errors remain below a documented threshold.
- Runs are deterministic for a fixed configuration and seed.

## Phase 2: Decoupling and Re-Engagement

### Goals

- Add coupling states and transition dynamics.
- Model independent engine and wheel-side speeds while decoupled.
- Add idle control and rev-matching.
- Track slip energy, transition time, acceleration disturbance, and jerk.

### Deliverables

- ADDS state machine.
- Controlled decoupling and re-engagement sequences.
- Fault handling and transition guards.
- Unit scenarios for every valid and invalid transition.

### Exit Criteria

- No state transition bypasses required guards.
- Re-engagement meets specified speed-mismatch and jerk limits in nominal tests.
- Mechanical and energy quantities remain finite and physically plausible.

## Phase 3: Baseline Controllers

### Goals

- Implement a conventional reference controller.
- Implement a transparent rule-based ADDS controller.
- Add an oracle or offline optimization benchmark where computationally
  practical.
- Optionally add a model-predictive controller as a stronger online baseline.

### Deliverables

- Baseline policy definitions and tuned parameters.
- Standardized benchmark suite.
- Initial trade-off curves for efficiency, comfort, and response.
- Equal speed-tracking gains for paired conventional and ADDS baselines.
- Preview-based coast-feasibility logic for gradual target-speed reductions.

### Exit Criteria

- Baselines complete all benchmark scenarios without constraint violations.
- Results reveal understandable regions where decoupling helps or hurts.
- The simulator can distinguish controller quality from model artifacts.
- At least one declared scenario passes the initial fuel, mobility, and safety
  acceptance gates without relying on degraded speed tracking.

## Phase 4: Scenario and Data Infrastructure

### Goals

- Add standard drive cycles, synthetic roads, grade profiles, and demand events.
- Add parameter randomization and sensor noise.
- Define training, validation, and test splits by route and condition.
- Add experiment tracking and reproducible configuration management.

### Deliverables

- Scenario generator and versioned scenario catalog.
- Held-out coast profiles below and above the training speed range.
- Dataset schema and trajectory export format.
- Reproducible batch evaluation.
- Automated summary tables and plots.

### Exit Criteria

- Test scenarios are isolated from training data.
- Learned-controller reports include paired baseline deltas and expert-action
  agreement on held-out scenarios.
- Experiments can be rerun from stored configuration, seed, and model version.
- Coverage includes nominal, boundary, and failure-oriented cases.

## Phase 5: Machine Learning Controller

### Goals

- Train an initial policy through imitation learning or offline learning from
  safe baseline and optimization trajectories.
- Introduce constrained reinforcement learning in simulation if it adds value.
- Separate high-level mode decisions from low-level transition control.
- Enforce safety through action masks, guards, and fallback logic.

### Deliverables

- Trained policy checkpoints.
- Training curves and evaluation reports.
- Policy interface compatible with non-ML controllers.
- Ablation studies for observations, preview horizon, and reward terms.
- Leakage-resistant offline policy search with train ranking, validation
  selection, frozen-test audit, and explicit non-promotion reports.

### Exit Criteria

- The learned policy outperforms the rule-based baseline on at least one
  predeclared objective without degrading mandatory constraints.
- Performance is reported across multiple seeds and held-out scenarios.
- Failure cases are cataloged rather than hidden by aggregate averages.
- A candidate that fails the frozen test remains unpromoted even when its train
  objective is better; the current `C03` candidate passes the frozen test and
  becomes the offline-optimized deterministic baseline.

## Phase 6: Robustness and Higher Fidelity

### Goals

- Evaluate uncertainty in mass, drag, tire friction, grade, actuator delay, and
  powertrain maps.
- Add thermal and wear proxies where justified.
- Compare multiple vehicle and transmission parameter sets.
- Validate selected behaviors against higher-fidelity simulation or measured
  data.

### Deliverables

- Robustness envelopes and sensitivity analysis.
- Model calibration report.
- Sim-to-sim or data-validation results.
- Updated safety and fallback requirements.

### Exit Criteria

- Conclusions remain valid within documented uncertainty bounds.
- Model discrepancies and unsupported operating regions are explicit.
- The policy fails conservatively under tested out-of-distribution conditions.

## Phase 7A: Visualization Prototype

### Objective

Create a lightweight project-facing interface that makes current simulator
results inspectable before real-time integration work begins.

### Work Items

- Add dashboard-ready comparison helpers that reuse the existing paired
  conventional-vs-ADDS evaluation path.
- Provide an initial Streamlit app for selecting catalog scenarios and ADDS
  controller variants.
- Expose the promoted offline-optimized `C03` deterministic baseline as a
  dashboard-selectable controller variant.
- Present the project purpose, operating modes, and simulation-only limitations
  directly inside the dashboard.
- Show side-by-side curves for speed tracking, cumulative fuel use, engine
  speed, coupling mode, and coupling slip energy.
- Display compact metric cards for fuel delta, RMS speed-error delta,
  transition count, safety overrides, and constraint regression status.
- Add human-readable decision insights that classify a scenario as beneficial,
  neutral, or cautionary for the current ADDS policy.
- Add an explicit research verdict that accepts an efficiency claim only when
  fuel, mobility, and safety gates all pass.
- Add event-level diagnostics for mode durations, transition timing, speed, and
  slip at each detected ADDS state change.
- Add catalog-level summaries and downloadable CSV/JSON outputs.
- Add a controller-portfolio matrix for comparing all dashboard controller
  variants across every catalog scenario.
- Add a command-line controller-portfolio report that writes the same
  comparison as JSON and CSV artifacts.
- Add scenario-level robustness envelopes with per-perturbation verdicts,
  acceptance rates, trade-off plots, and CSV export.
- Keep visualization code separate from the simulator core so automated tests do
  not require launching a web server.

### Deliverables

- Streamlit dashboard prototype.
- Dashboard data-preparation helpers.
- Project overview, catalog summary, and download panels.
- Rule-based, offline-optimized, and learned ADDS controller comparison paths.
- Controller-portfolio summary and CSV export.
- Reproducible controller-portfolio report artifacts.
- Tests for dashboard comparison packaging and metric-card generation.
- Documented initial acceptance gates and verdict classification tests.
- Interactive sensitivity view for the deterministic uncertainty envelope.

### Exit Criteria

- Users can run the dashboard locally from the repository root.
- At least one train, validation, test, and stress scenario can be visualized.
- The displayed metrics match the paired comparison summaries.
- The interface clearly states that results are simulation-only research
  outputs, not real-vehicle claims.

## Phase 7: Real-Time and Integration Research

This phase is optional and begins only after simulation validity is established.

### Goals

- Measure computational latency and memory use.
- Prepare a real-time-compatible model and controller interface.
- Explore software-in-the-loop and hardware-in-the-loop execution.
- Define the evidence required before any physical drivetrain experiment.

### Deliverables

- Real-time execution profile.
- Integration interface specification.
- Hardware-in-the-loop test plan.
- Safety case outline for controlled experimental use.

### Exit Criteria

- Deadlines are met on the target research platform.
- Loss of communication or invalid policy output triggers a safe fallback.
- Physical testing is prohibited until an independent safety review approves it.

## Cross-Cutting Work

The following activities continue through all phases:

- Documentation and decision records.
- Automated testing and continuous integration.
- Dimensional analysis and unit enforcement.
- Reproducibility and experiment provenance.
- Visualization and diagnostic tooling.
- Security and integrity of model artifacts and configuration.
- Review of assumptions against published data and measured evidence.

## Initial Milestone Priorities

The first implementation milestone should prioritize:

1. A correct coast-down model.
2. A fair connected-versus-decoupled energy comparison.
3. A deterministic state machine.
4. A measurable rev-matching transition.
5. A rule-based controller.

Machine learning should begin only after these five elements are verified.
