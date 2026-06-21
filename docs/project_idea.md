# Project Idea

## 1. Motivation

A conventional combustion-engine vehicle loses kinetic energy through several
mechanisms when the driver releases the accelerator. Some losses are unavoidable,
such as aerodynamic drag and rolling resistance. Others depend on drivetrain
state, including engine pumping losses, friction, and engine braking transmitted
through an engaged gear.

Temporarily disconnecting the engine from the driven wheels can allow the vehicle
to coast farther. This may reduce fuel consumption in suitable situations, but
decoupling is not universally beneficial. It can reduce immediate traction
availability, remove engine braking, require fuel to keep the engine idling, and
create discomfort or wear if re-engagement is poorly timed.

ADDS investigates this trade-off with a controlled simulation framework.

## 2. Core Hypothesis

An adaptive supervisory controller can use vehicle state, road context, driver
demand, and predicted near-future conditions to choose among connected driving,
decoupled coasting, and rev-matched re-engagement. A well-designed controller may
reduce fuel or energy consumption while preserving:

- Speed tracking.
- Driver response.
- Longitudinal stability.
- Ride comfort.
- Drivetrain durability.
- Compliance with operating constraints.

The expected benefit depends on route topology, traffic, speed, gear, engine
characteristics, driver behavior, and the quality of future-state prediction.

## 3. Research Questions

The project will answer the following questions:

1. In which operating regions does decoupling reduce total energy use?
2. When is engine braking more valuable than extended coasting?
3. How much route preview is needed to make useful decisions?
4. What target engine speed and coupling trajectory produce smooth
   re-engagement?
5. How should responsiveness, comfort, and mechanical wear be balanced against
   efficiency?
6. Can a learned policy outperform deterministic and model-predictive baselines
   on unseen routes and disturbances?
7. Which learned behaviors remain robust under parameter uncertainty?

## 4. Compared Vehicle Concepts

### 4.1 Conventional Vehicle

The reference vehicle follows a conventional connection policy. When a drive
gear is engaged and the clutch or coupling is closed, wheel speed constrains
engine speed through the selected ratio. Accelerator lift can therefore produce
engine braking and pumping losses.

The reference model may still include ordinary gear shifts, clutch transitions,
idle control, and fuel cut-off. It must not be artificially simplified in a way
that favors ADDS.

### 4.2 ADDS Vehicle

The ADDS vehicle uses the same physical vehicle parameters but adds supervisory
authority over the drivetrain coupling. Its controller may:

- Remain connected when propulsion or engine braking is useful.
- Initiate decoupling when extended coasting is expected to be beneficial.
- Keep the engine idling, shut it down, or use another defined decoupled-engine
  policy in later experiments.
- Predict the synchronous engine speed for the current or selected gear.
- Command engine torque for rev-matching.
- Re-engage while limiting slip, jerk, and torque disturbance.

Engine stop-start should be treated as a separate capability. Initial ADDS
experiments should keep the engine running at idle while decoupled so that the
effect of mechanical decoupling can be isolated.

## 5. Decision Problem

At each control step, the supervisory controller observes a state vector that may
include:

- Vehicle speed and acceleration.
- Engine speed and torque.
- Selected gear and transmission ratio.
- Coupling state, slip speed, and temperature estimate.
- Accelerator and brake demand.
- Road grade and curvature.
- Tire-road friction estimate.
- Distance and time to predicted speed changes.
- Predicted driver or drive-cycle demand.
- Recent mode history and time since the last transition.

The controller chooses a discrete mode and, where required, continuous commands
such as engine torque, target engine speed, or coupling capacity.

The decision must satisfy hard constraints before optimizing soft objectives.

## 6. Objectives and Constraints

### Primary Objective

Minimize fuel or equivalent energy consumption over a complete scenario.

### Secondary Objectives

- Minimize speed-tracking error and travel-time deviation.
- Minimize longitudinal jerk.
- Minimize re-engagement delay.
- Minimize clutch or coupling slip energy.
- Avoid excessive switching between modes.
- Preserve a requested reserve of propulsion or braking response.

### Hard Constraints

- Do not decouple during braking situations that require engine braking or
  immediate wheel torque.
- Do not exceed engine speed, engine torque, clutch, transmission, tire, or
  vehicle acceleration limits.
- Do not re-engage outside allowed speed mismatch and torque mismatch bounds.
- Do not violate minimum dwell times or transition sequencing.
- Enter a deterministic fallback mode if observations or commands are invalid.

The exact constraint values will be configuration parameters and must be justified
by the modeled vehicle.

## 7. Initial Use Cases

### Highway Lift-Off

The driver releases the accelerator on a mild or level road. ADDS evaluates
whether decoupled coasting saves more fuel than connected overrun fuel cut-off,
considering the additional distance traveled and future speed demand.

### Approaching a Lower Speed Limit

Route preview indicates a lower target speed ahead. Remaining connected may be
preferable because engine braking can reduce brake use and prevent overspeed.

### Rolling Terrain

The system uses grade preview to decide whether to coast on a descent, remain
connected for speed control, or prepare for propulsion on the next ascent.

### Renewed Acceleration Demand

While decoupled, the driver requests torque. The controller selects a target gear,
rev-matches the engine, closes the coupling, and restores propulsion within a
defined response time.

### Disturbance and Uncertainty

Vehicle mass, drag, rolling resistance, road grade, friction, and driver demand
vary from their nominal values. The controller must remain stable and useful.

## 8. Expected Deliverables

- A configurable longitudinal vehicle and powertrain simulator.
- Conventional, heuristic ADDS, and optimization-based baselines.
- A machine learning training and evaluation pipeline.
- Standard drive cycles and synthetic scenario generators.
- Comparison reports and visualization tools.
- Robustness, ablation, and sensitivity studies.
- Documented assumptions, limitations, and reproducible experiments.

## 9. Success Criteria

The project will be considered successful when it can:

1. Reproduce physically plausible longitudinal behavior and energy flows.
2. Execute valid decoupling and rev-matched re-engagement transitions.
3. Compare both vehicle concepts under identical conditions.
4. Demonstrate where adaptive decoupling helps, where it does not, and why.
5. Show that any learned policy respects constraints and generalizes beyond its
   training scenarios.
6. Produce results that can be independently reproduced from versioned
   configurations.

## 10. Non-Goals

The initial project does not claim:

- Production readiness or road safety certification.
- Complete representation of driver psychology or traffic behavior.
- Full three-dimensional vehicle dynamics.
- Detailed component fatigue or thermal life prediction.
- Guaranteed real-world fuel savings.
- Compatibility with a specific commercial transmission or vehicle.
