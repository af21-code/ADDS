# Machine Learning Strategy

## 1. Purpose

Machine learning in ADDS is used to improve the high-level drivetrain decision
policy under variable routes, driver demand, and vehicle conditions. It is not
used to replace physical simulation, transition guards, or low-level safety
control.

The ML system should answer:

- Whether to remain connected or begin decoupling.
- When to prepare for re-engagement.
- Which feasible gear to target.
- How early rev-matching should begin.
- Which trade-off among efficiency, comfort, and responsiveness is appropriate.

Low-level rev-matching and coupling control should initially remain
deterministic. This hierarchical design limits the action space and makes unsafe
behavior easier to detect.

## 2. Learning Formulation

The initial learning problem is a constrained, partially observable sequential
decision problem.

### Observation

Candidate observation features include:

- Vehicle speed and acceleration.
- Engine speed, torque, and available torque limits.
- Current and target gear.
- Coupling mode, slip speed, and time in mode.
- Accelerator and brake demand.
- Target speed and speed error.
- Current road grade.
- Previewed grade and target-speed samples over a fixed horizon.
- Estimated vehicle mass, resistance, and tire-force margin.
- Previous action and recent transition count.

Features must be restricted to information available under the declared sensing
and preview assumptions.

### Action

The first ML policy should use a small discrete action set:

- Hold current mode.
- Request decoupling.
- Request preparation for re-engagement.
- Request re-engagement in a feasible target gear.

Continuous low-level references may be added later, after the discrete policy is
stable and measurable.

### State and Memory

A feed-forward policy may begin with stacked recent observations. Recurrent or
state-space policies can be evaluated if partial observability materially limits
performance. Policy memory must be reset and logged consistently.

## 3. Baselines

AI performance is meaningful only relative to strong baselines:

1. **Conventional controller:** no adaptive coasting authority.
2. **Rule-based ADDS:** thresholds based on speed, demand, grade, expected coast
   duration, and transition feasibility.
3. **Offline oracle:** optimization with full scenario knowledge, used as an
   upper-bound reference rather than a deployable controller.
4. **Model-predictive controller:** optional online benchmark using a finite
   preview horizon.

The learned policy should use the same observation limits as the online baseline.

The current interpretable baseline and behavioral clone use a one-second
target-speed preview. They estimate the unpowered coast speed from current
resistance and vehicle mass, then permit decoupling only when the predicted
speed remains inside a bounded corridor around the preview target. The
conventional and adaptive controllers use the same proportional speed-tracking
gain, so a reported benefit cannot come from weakening the ADDS tracking
objective.

Two deterministic guards wrap both the rule-based and learned decisions:
the one-second preview must decrease by at least `0.25 m/s`, and road grade must
not exceed `0.005 rad` (approximately `0.5%`) during coast entry. The first
guard prevents short late-cycle events whose transition overhead outweighs
their benefit. The second keeps the system connected where positive grade makes
unpowered coasting unattractive. These are initial research thresholds rather
than calibrated production values.

## 4. Recommended Training Sequence

### Stage A: Generate Safe Expert Data

Use rule-based, model-predictive, or offline optimization policies to generate
valid trajectories across a broad scenario distribution. Record both accepted
actions and safety-supervisor interventions.

### Stage B: Behavioral Cloning

Train an initial classifier or hierarchical policy to imitate expert mode
decisions. This produces a stable starting point and exposes ambiguities in the
observation and action definitions.

The current schema `2.0` clone learns the upper and lower coast-feasibility
corridor from expert transition samples. It is intentionally small and
interpretable; it is not yet an optimized ML policy.

Held-out evaluation includes lower-speed and higher-speed coast profiles that
are excluded from the train split. Reports compare the learned controller
against the conventional baseline and record its high-level requested-mode
agreement with the rule-based expert.

### Stage C: Offline Policy Improvement

Where data coverage is adequate, evaluate conservative offline reinforcement
learning or cost-sensitive policy improvement. Avoid extrapolating into
poorly-covered actions without explicit uncertainty handling.

### Stage D: Constrained Online Reinforcement Learning

Fine-tune in simulation only after the simulator and baselines pass verification.
Use curriculum learning, domain randomization, and explicit constraint
enforcement.

### Stage E: Distillation and Calibration

If the final policy is too large or unstable, distill it into a smaller model.
Calibrate confidence or uncertainty estimates for fallback decisions.

## 5. Objective Design

The optimization objective should be reported as separate physical metrics even
if training uses a combined reward.

A conceptual per-step cost is:

```text
cost =
    fuel_cost
  + speed_tracking_cost
  + travel_time_cost
  + jerk_cost
  + response_delay_cost
  + coupling_slip_energy_cost
  + mode_switching_cost
  + soft_constraint_margin_cost
```

Terminal penalties may apply to incomplete routes, unrecovered faults, or invalid
states.

Reward weights must not be selected solely to produce a favorable fuel result.
The project should publish sensitivity studies and Pareto fronts where objectives
conflict.

Hard safety limits must not depend on finite reward penalties.

## 6. Safety Architecture

The ML policy is wrapped by deterministic mechanisms:

- **Action masks:** remove transitions that are invalid in the current state.
- **Transition guards:** require speed, torque, and timing conditions.
- **Command limits:** bound engine torque, target speed, and coupling capacity.
- **Runtime monitor:** detect invalid values, oscillation, timing overruns, and
  out-of-distribution observations.
- **Fallback controller:** maintain or restore a conservative connected state
  when feasible.
- **Event logger:** record every rejected or modified ML action.

Safety interventions are evaluation outcomes, not invisible corrections. A
policy that frequently relies on them is not considered successful.

## 7. Data Strategy

### Scenario Coverage

Training data should vary:

- Urban, rural, highway, and rolling-terrain routes.
- Speed limits and target-speed profiles.
- Positive and negative grades.
- Vehicle mass and payload.
- Aerodynamic and rolling resistance.
- Driver aggressiveness and reaction delay.
- Wind, tire friction, actuator delay, and sensor noise.
- Engine, transmission, and coupling parameters within supported families.

### Dataset Splits

Splits should be made by complete route, scenario family, and parameter region,
not by randomly separating adjacent time steps. The test set remains frozen and
unseen during model selection.

### Provenance

Every trajectory should record:

- Simulator and configuration version.
- Scenario identifier and random seed.
- Controller or expert version.
- Observation schema version.
- Units and sample intervals.
- Termination reason and constraint events.

## 8. Evaluation Protocol

Evaluate each policy over multiple random seeds and held-out scenario groups.
Report distributions, confidence intervals, and worst-case examples rather than
only averages.

### Efficiency

- Total fuel or equivalent energy.
- Fuel per distance.
- Resistive, braking, engine, and coupling energy terms.

### Mobility and Response

- Distance and travel time.
- Speed error and target-speed violations.
- Time from positive demand to restored wheel torque.

### Comfort and Mechanical Impact

- Peak and root-mean-square longitudinal jerk.
- Re-engagement speed mismatch.
- Coupling slip energy and peak transmitted torque.
- Transition count and mode-chatter rate.

### Safety and Robustness

- Constraint violations.
- Supervisor overrides.
- Invalid outputs or numerical failures.
- Performance under parameter shifts and unseen routes.
- Sensitivity to observation noise and delay.

## 9. Generalization and Robustness

Domain randomization should cover justified uncertainty ranges, not arbitrary
values. Evaluation should include:

- Interpolation within trained parameter ranges.
- Extrapolation just outside those ranges.
- Combined worst-case disturbances.
- Missing or stale preview information.
- Incorrect mass or grade estimates.
- Sudden driver demand during decoupled coasting.

Out-of-distribution detection can trigger a known baseline controller, but its
effectiveness must be measured independently.

## 10. Interpretability

The project should use:

- State-action occupancy plots.
- Decision maps over speed, grade, demand, and preview.
- Counterfactual scenario comparisons.
- Feature ablation and permutation tests.
- Transition-level replay with controller explanations where available.

Interpretability is used to find unsafe shortcuts, spurious correlations, and
regions where the learned policy disagrees with physical intuition.

## 11. Reproducibility

Every training run should preserve:

- Source revision.
- Full configuration.
- Random seeds.
- Dataset and normalization versions.
- Software and hardware environment.
- Model checkpoints.
- Evaluation results.

Final comparisons must rerun policy inference from a stored checkpoint rather
than relying on metrics captured during training.

## 12. Promotion Criteria

A learned controller advances only when it:

1. Completes the frozen test suite without hard constraint violations.
2. Improves a predeclared objective relative to the rule-based baseline.
3. Does not create unacceptable mobility, response, comfort, or wear trade-offs.
4. Remains stable across seeds and supported numerical time steps.
5. Uses safety overrides rarely and within a documented threshold.
6. Fails conservatively in tested out-of-distribution cases.

No simulation result alone qualifies the policy for use in a physical vehicle.

## 13. Offline Policy-Search Benchmark

The first optimization benchmark uses a fixed six-candidate grid over the
interpretable coast corridor. Candidates are ranked only on train scenarios
under the existing deterministic perturbation envelope. The ranking requires
zero fuel regression, no safety or constraint regression, no more than one
five-transition decouple/re-engage sequence, and at most `1 km/h` RMS
speed-error degradation.

Candidates are then considered in train-ranked order on the validation split.
The first candidate that passes every validation gate and produces at least one
validated fuel benefit is frozen for a single test audit. Test results cannot
be used to select a replacement candidate.

The current audit promotes candidate `C03`, with a `0.5 m/s` upper coast
corridor, `0.1 m/s` lower reconnect corridor, `0.25 m/s` minimum previewed
target drop, and `0.005 rad` maximum coast grade. The better train-ranked
candidate `C06` is rejected because it produces no validated coast benefit.
`C03` then improves the high-speed frozen test by approximately `0.96`
percentage points relative to the rule-based baseline while retaining one
five-transition sequence, comparable speed tracking, and zero safety override.
It also passes the stress-split audit.

This promotes `C03` as a stronger deterministic offline-optimized baseline. It
is exposed in the simulator and dashboard as `offline_optimized_adds`, so later
learned policies must compare against both the original rule-based baseline and
this promoted deterministic baseline. This does not demonstrate that the
behavioral-cloning policy outperforms the optimized baseline; the ML promotion
criterion therefore remains open.
