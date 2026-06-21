"""Fixed-step longitudinal vehicle simulator."""

from __future__ import annotations

from dataclasses import dataclass
from math import cos, sin

from .controllers import Controller
from .parameters import (
    CouplingParameters,
    EngineParameters,
    EnvironmentParameters,
    SafetyParameters,
    SolverParameters,
    TransmissionParameters,
    VehicleParameters,
)
from .profiles import ConstantProfile, ScalarProfile


@dataclass(frozen=True)
class SimulationConfig:
    vehicle: VehicleParameters
    environment: EnvironmentParameters
    engine: EngineParameters
    transmission: TransmissionParameters
    coupling: CouplingParameters
    safety: SafetyParameters
    solver: SolverParameters

    def validate(self) -> None:
        self.vehicle.validate()
        self.environment.validate()
        self.engine.validate()
        self.transmission.validate()
        self.coupling.validate()
        self.safety.validate()
        self.solver.validate()


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    initial_speed: float
    initial_gear: int
    time_limit: float
    distance_limit: float | None = None
    target_speed_profile: ScalarProfile = ConstantProfile(0.0)
    grade_profile: ScalarProfile = ConstantProfile(0.0)
    drivetrain_connected: bool = True
    adds_enabled: bool = False
    initial_coupling_mode: str | None = None
    random_seed: int = 0

    def validate(self, config: SimulationConfig) -> None:
        if self.initial_speed < 0.0:
            raise ValueError("scenario.initial_speed must be >= 0")
        if self.time_limit <= 0.0:
            raise ValueError("scenario.time_limit must be > 0")
        if self.distance_limit is not None and self.distance_limit <= 0.0:
            raise ValueError("scenario.distance_limit must be > 0 when set")
        config.transmission.gear_ratio(self.initial_gear)
        if self.initial_coupling_mode is not None and self.initial_coupling_mode not in COUPLING_MODES:
            raise ValueError(f"unknown initial_coupling_mode: {self.initial_coupling_mode}")


@dataclass
class VehicleState:
    time: float
    step_index: int
    position: float
    speed: float
    acceleration: float
    engine_speed: float
    coupling_mode: str
    mode_time: float
    transition_count: int
    target_gear: int
    coupling_capacity: float
    last_safety_override: bool
    last_safety_override_reason: str
    fuel_used: float
    aero_energy: float
    rolling_resistance_energy: float
    brake_energy: float
    drivetrain_loss_energy: float
    engine_loss_energy: float
    coupling_slip_energy: float
    fuel_energy: float
    kinetic_energy_initial: float
    potential_energy_change: float


COUPLING_MODES = {
    "CONNECTED",
    "DECOUPLING",
    "DECOUPLED",
    "REV_MATCHING",
    "REENGAGING",
    "FAULT_SAFE",
}


@dataclass(frozen=True)
class SimulationResult:
    scenario_id: str
    controller_name: str
    records: tuple[dict[str, float | int | str | bool], ...]
    final_state: VehicleState
    termination_reason: str


class LongitudinalSimulator:
    """Conventional connected-drivetrain simulator with optional free coasting."""

    def __init__(self, config: SimulationConfig) -> None:
        config.validate()
        self.config = config

    def wheel_speed(self, vehicle_speed: float) -> float:
        return vehicle_speed / self.config.vehicle.wheel_radius

    def synchronous_engine_speed(self, vehicle_speed: float, gear: int) -> float:
        return self.config.transmission.total_ratio(gear) * self.wheel_speed(vehicle_speed)

    def equivalent_mass(self, gear: int, drivetrain_connected: bool) -> float:
        vehicle = self.config.vehicle
        engine = self.config.engine
        transmission = self.config.transmission
        wheel_term = vehicle.wheel_inertia / (vehicle.wheel_radius * vehicle.wheel_radius)
        if not drivetrain_connected:
            return vehicle.mass + wheel_term
        ratio = transmission.total_ratio(gear)
        engine_term = engine.inertia * (ratio / vehicle.wheel_radius) ** 2
        return vehicle.mass + wheel_term + engine_term

    def resistive_forces(self, vehicle_speed: float, road_grade: float) -> dict[str, float]:
        vehicle = self.config.vehicle
        environment = self.config.environment
        v_rel = vehicle_speed - environment.wind_speed
        aero_force = 0.5 * environment.air_density * vehicle.drag_coefficient * vehicle.frontal_area * v_rel * abs(v_rel)
        rolling_force = vehicle.mass * environment.gravity * vehicle.rolling_resistance_coefficient * cos(road_grade)
        grade_force = vehicle.mass * environment.gravity * sin(road_grade)
        return {
            "aero_force": aero_force,
            "rolling_resistance_force": rolling_force,
            "grade_force": grade_force,
        }

    def force_to_hold_speed(self, vehicle_speed: float, road_grade: float) -> float:
        forces = self.resistive_forces(vehicle_speed, road_grade)
        return forces["aero_force"] + forces["rolling_resistance_force"] + forces["grade_force"]

    def tire_force_limit(self, road_grade: float) -> float:
        vehicle = self.config.vehicle
        environment = self.config.environment
        normal_load = vehicle.mass * environment.gravity * max(cos(road_grade), 0.0)
        return environment.tire_friction_coefficient * normal_load

    def run(self, scenario: Scenario, controller: Controller) -> SimulationResult:
        scenario.validate(self.config)
        dt = self.config.solver.plant_time_step
        initial_state = self._initial_state(scenario)
        state = initial_state
        records: list[dict[str, float | int | str | bool]] = []
        termination_reason = "time_limit"

        while state.time < scenario.time_limit - 1e-12:
            if scenario.distance_limit is not None and state.position >= scenario.distance_limit:
                termination_reason = "distance_limit"
                break

            record, state = self._step(scenario, controller, state, dt)
            records.append(record)

            if state.speed <= 0.0 and record["vehicle_acceleration"] <= 0.0:
                termination_reason = "vehicle_stopped"
                break

        return SimulationResult(
            scenario_id=scenario.scenario_id,
            controller_name=getattr(controller, "name", controller.__class__.__name__),
            records=tuple(records),
            final_state=state,
            termination_reason=termination_reason,
        )

    def _initial_state(self, scenario: Scenario) -> VehicleState:
        mode = self._initial_coupling_mode(scenario)
        drivetrain_connected = self._mode_has_locked_drivetrain(mode)
        engine_speed = (
            self.synchronous_engine_speed(scenario.initial_speed, scenario.initial_gear)
            if drivetrain_connected
            else self.config.engine.idle_speed
        )
        engine_speed = max(engine_speed, self.config.engine.min_operating_speed)
        kinetic = 0.5 * self.equivalent_mass(scenario.initial_gear, drivetrain_connected) * scenario.initial_speed**2
        return VehicleState(
            time=0.0,
            step_index=0,
            position=0.0,
            speed=scenario.initial_speed,
            acceleration=0.0,
            engine_speed=engine_speed,
            coupling_mode=mode,
            mode_time=0.0,
            transition_count=0,
            target_gear=scenario.initial_gear,
            coupling_capacity=self.config.coupling.max_torque_capacity if drivetrain_connected else 0.0,
            last_safety_override=False,
            last_safety_override_reason="",
            fuel_used=0.0,
            aero_energy=0.0,
            rolling_resistance_energy=0.0,
            brake_energy=0.0,
            drivetrain_loss_energy=0.0,
            engine_loss_energy=0.0,
            coupling_slip_energy=0.0,
            fuel_energy=0.0,
            kinetic_energy_initial=kinetic,
            potential_energy_change=0.0,
        )

    @staticmethod
    def _mode_has_locked_drivetrain(mode: str) -> bool:
        return mode in {"CONNECTED", "DECOUPLING", "FAULT_SAFE"}

    def _initial_coupling_mode(self, scenario: Scenario) -> str:
        if scenario.initial_coupling_mode is not None:
            return scenario.initial_coupling_mode
        if scenario.adds_enabled:
            return "CONNECTED" if scenario.drivetrain_connected else "DECOUPLED"
        return "CONNECTED" if scenario.drivetrain_connected else "DECOUPLED"

    def _step(
        self,
        scenario: Scenario,
        controller: Controller,
        state: VehicleState,
        dt: float,
    ) -> tuple[dict[str, float | int | str | bool], VehicleState]:
        gear = state.target_gear if scenario.adds_enabled else scenario.initial_gear
        grade = scenario.grade_profile.value_at(state.position)
        target_speed = scenario.target_speed_profile.value_at(state.time)
        total_ratio = self.config.transmission.total_ratio(gear)
        forces = self.resistive_forces(state.speed, grade)
        force_to_hold = forces["aero_force"] + forces["rolling_resistance_force"] + forces["grade_force"]
        current_mode = state.coupling_mode if scenario.adds_enabled else self._initial_coupling_mode(scenario)
        drivetrain_locked = self._mode_has_locked_drivetrain(current_mode)
        engine_speed_observed = (
            self.synchronous_engine_speed(state.speed, gear)
            if drivetrain_locked
            else state.engine_speed
        )
        engine_speed_observed = max(engine_speed_observed, self.config.engine.min_operating_speed)

        observation = {
            "time": state.time,
            "position": state.position,
            "vehicle_speed": state.speed,
            "vehicle_acceleration": state.acceleration,
            "engine_speed": engine_speed_observed,
            "coupling_mode": current_mode,
            "mode_time": state.mode_time,
            "target_speed": target_speed,
            "road_grade": grade,
            "force_to_hold_speed": force_to_hold,
            "vehicle_mass": self.config.vehicle.mass,
            "wheel_radius": self.config.vehicle.wheel_radius,
            "total_drive_ratio": total_ratio,
            "transmission_efficiency_motoring": self.config.transmission.efficiency_motoring,
            "max_brake_force": self.config.vehicle.max_brake_force,
        }
        command = controller.command(observation)
        gear = command.target_gear or command.gear
        total_ratio = self.config.transmission.total_ratio(gear)
        mode, mode_time, transition_count, safety_override, safety_reason = self._advance_coupling_mode(
            scenario=scenario,
            state=state,
            command=command,
            gear=gear,
            dt=dt,
        )
        drivetrain_locked = self._mode_has_locked_drivetrain(mode)
        synchronous_engine_speed = self.synchronous_engine_speed(state.speed, gear)
        engine_speed, engine_torque_request, coupling_capacity = self._engine_speed_and_request(
            mode=mode,
            state=state,
            synchronous_engine_speed=synchronous_engine_speed,
            command_engine_torque=command.engine_torque,
            dt=dt,
        )

        engine_torque, engine_fuel_rate, engine_state = self._engine_response(
            engine_torque_request,
            engine_speed,
            drivetrain_locked,
        )
        wheel_speed = self.wheel_speed(state.speed)
        wheel_torque, drivetrain_loss_power = self._wheel_torque_and_loss(
            engine_torque,
            engine_speed,
            wheel_speed,
            total_ratio,
            drivetrain_locked,
        )
        coupling_torque, coupling_slip_power, coupling_slip_step = self._coupling_effects(
            mode=mode,
            engine_speed=engine_speed,
            synchronous_engine_speed=synchronous_engine_speed,
            coupling_capacity=coupling_capacity,
            dt=dt,
        )
        if mode == "REENGAGING":
            wheel_torque += coupling_torque * total_ratio * self.config.transmission.efficiency_motoring
        drivetrain_force = wheel_torque / self.config.vehicle.wheel_radius
        tire_limit = self.tire_force_limit(grade)
        drivetrain_force = max(-tire_limit, min(tire_limit, drivetrain_force))

        brake_force = min(max(command.brake_force, 0.0), self.config.vehicle.max_brake_force)
        brake_force = min(brake_force, tire_limit)
        net_force = drivetrain_force - brake_force - forces["aero_force"] - forces["rolling_resistance_force"] - forces["grade_force"]
        mass_eq = self.equivalent_mass(gear, drivetrain_locked)
        acceleration = net_force / mass_eq
        acceleration = max(
            -self.config.vehicle.max_longitudinal_deceleration,
            min(self.config.vehicle.max_longitudinal_acceleration, acceleration),
        )

        next_speed = max(0.0, state.speed + acceleration * dt)
        distance_step = max(0.0, 0.5 * (state.speed + next_speed) * dt)
        next_position = state.position + distance_step
        fuel_step = engine_fuel_rate * dt
        fuel_energy_step = fuel_step * self.config.engine.fuel_lower_heating_value
        engine_power = engine_torque * engine_speed
        engine_loss_step = self._engine_loss_energy_step(engine_power, fuel_energy_step, dt, drivetrain_locked)
        potential_step = self.config.vehicle.mass * self.config.environment.gravity * sin(grade) * distance_step

        next_state = VehicleState(
            time=state.time + dt,
            step_index=state.step_index + 1,
            position=next_position,
            speed=next_speed,
            acceleration=acceleration,
            engine_speed=engine_speed,
            coupling_mode=mode,
            mode_time=mode_time,
            transition_count=transition_count,
            target_gear=gear,
            coupling_capacity=coupling_capacity,
            last_safety_override=safety_override,
            last_safety_override_reason=safety_reason,
            fuel_used=state.fuel_used + fuel_step,
            aero_energy=state.aero_energy + max(forces["aero_force"] * distance_step, 0.0),
            rolling_resistance_energy=state.rolling_resistance_energy + max(forces["rolling_resistance_force"] * distance_step, 0.0),
            brake_energy=state.brake_energy + brake_force * distance_step,
            drivetrain_loss_energy=state.drivetrain_loss_energy + drivetrain_loss_power * dt,
            engine_loss_energy=state.engine_loss_energy + engine_loss_step,
            coupling_slip_energy=state.coupling_slip_energy + coupling_slip_step,
            fuel_energy=state.fuel_energy + fuel_energy_step,
            kinetic_energy_initial=state.kinetic_energy_initial,
            potential_energy_change=state.potential_energy_change + potential_step,
        )

        kinetic_energy = 0.5 * mass_eq * next_speed**2
        energy_balance_residual = self._energy_balance_residual(next_state, kinetic_energy)
        record: dict[str, float | int | str | bool] = {
            "time": next_state.time,
            "step_index": next_state.step_index,
            "scenario_id": scenario.scenario_id,
            "random_seed": scenario.random_seed,
            "terminal": False,
            "termination_reason": "",
            "position": next_state.position,
            "vehicle_speed": next_state.speed,
            "vehicle_acceleration": next_state.acceleration,
            "target_speed": target_speed,
            "speed_error": target_speed - next_state.speed,
            "road_grade": grade,
            "wheel_speed": wheel_speed,
            "wheel_torque": wheel_torque,
            "tire_force_longitudinal": drivetrain_force,
            "tire_force_limit": tire_limit,
            "tire_force_margin": tire_limit - abs(drivetrain_force) - brake_force,
            "brake_force": brake_force,
            "brake_power": brake_force * state.speed,
            "engine_speed": engine_speed,
            "engine_speed_target": synchronous_engine_speed if mode in {"REV_MATCHING", "REENGAGING"} else engine_speed,
            "engine_torque_command": engine_torque_request if engine_torque_request is not None else self.config.engine.min_torque,
            "engine_torque": engine_torque,
            "engine_torque_available_min": self.config.engine.min_torque,
            "engine_torque_available_max": self.config.engine.max_torque,
            "engine_fuel_rate": engine_fuel_rate,
            "engine_fuel_used": next_state.fuel_used,
            "engine_power": engine_power,
            "engine_state": engine_state,
            "selected_gear": gear,
            "target_gear": gear,
            "gear_ratio": self.config.transmission.gear_ratio(gear),
            "final_drive_ratio": self.config.transmission.final_drive_ratio,
            "total_drive_ratio": total_ratio,
            "synchronous_engine_speed": self.synchronous_engine_speed(next_state.speed, gear),
            "coupling_mode": mode,
            "coupling_capacity_command": coupling_capacity,
            "coupling_capacity": coupling_capacity,
            "coupling_torque": coupling_torque,
            "coupling_slip_speed": engine_speed - synchronous_engine_speed,
            "coupling_slip_power": coupling_slip_power,
            "coupling_slip_energy": next_state.coupling_slip_energy,
            "mode_time": mode_time,
            "transition_count": transition_count,
            "aero_force": forces["aero_force"],
            "rolling_resistance_force": forces["rolling_resistance_force"],
            "grade_force": forces["grade_force"],
            "drivetrain_loss_power": drivetrain_loss_power,
            "aero_energy": next_state.aero_energy,
            "rolling_resistance_energy": next_state.rolling_resistance_energy,
            "brake_energy": next_state.brake_energy,
            "drivetrain_loss_energy": next_state.drivetrain_loss_energy,
            "engine_loss_energy": next_state.engine_loss_energy,
            "energy_balance_residual": energy_balance_residual,
            "controller_name": getattr(controller, "name", controller.__class__.__name__),
            "controller_version": "phase2" if scenario.adds_enabled else "phase1",
            "requested_mode": command.requested_mode,
            "applied_mode": mode,
            "safety_override": safety_override,
            "safety_override_reason": safety_reason,
            "fallback_active": mode == "FAULT_SAFE",
            "controller_latency": 0.0,
        }
        return record, next_state

    def _advance_coupling_mode(
        self,
        scenario: Scenario,
        state: VehicleState,
        command,
        gear: int,
        dt: float,
    ) -> tuple[str, float, int, bool, str]:
        if not scenario.adds_enabled:
            mode = "CONNECTED" if scenario.drivetrain_connected else "DECOUPLED"
            return mode, state.mode_time + dt, state.transition_count, False, ""

        old_mode = state.coupling_mode
        mode = old_mode
        mode_time = state.mode_time + dt
        transition_count = state.transition_count
        safety_override = False
        safety_reason = ""

        def transition(next_mode: str) -> None:
            nonlocal mode, mode_time, transition_count
            if next_mode != mode:
                mode = next_mode
                mode_time = 0.0
                transition_count += 1

        brake_demand = max(command.brake_force, 0.0) / self.config.vehicle.max_brake_force
        positive_torque_demand = 0.0
        if command.engine_torque is not None and command.engine_torque > 0.0:
            positive_torque_demand = command.engine_torque / self.config.engine.max_torque

        if command.force_fault:
            safety_override = True
            safety_reason = "FORCED_FAULT"
            transition("FAULT_SAFE")
            return mode, mode_time, transition_count, safety_override, safety_reason

        if mode == "CONNECTED":
            if command.requested_mode in {"DECOUPLING", "DECOUPLED"}:
                if brake_demand > self.config.safety.brake_demand_decouple_block_threshold:
                    safety_override = True
                    safety_reason = "BRAKE_DEMAND_BLOCKS_DECOUPLING"
                elif state.speed < self.config.safety.min_vehicle_speed_for_decoupling:
                    safety_override = True
                    safety_reason = "LOW_SPEED_BLOCKS_DECOUPLING"
                else:
                    transition("DECOUPLING")
        elif mode == "DECOUPLING":
            if brake_demand > self.config.safety.brake_demand_decouple_block_threshold:
                safety_override = True
                safety_reason = "BRAKE_DEMAND_CANCELS_DECOUPLING"
                transition("CONNECTED")
            elif mode_time >= self.config.coupling.opening_time:
                transition("DECOUPLED")
        elif mode == "DECOUPLED":
            if command.requested_mode in {"REV_MATCHING", "REENGAGING", "CONNECTED"} or (
                positive_torque_demand > self.config.safety.positive_torque_reconnect_threshold
            ):
                self.config.transmission.gear_ratio(gear)
                transition("REV_MATCHING")
        elif mode == "REV_MATCHING":
            slip = abs(state.engine_speed - self.synchronous_engine_speed(state.speed, gear))
            if slip <= self.config.coupling.reengagement_slip_limit:
                transition("REENGAGING")
        elif mode == "REENGAGING":
            slip = abs(state.engine_speed - self.synchronous_engine_speed(state.speed, gear))
            if mode_time >= self.config.coupling.closing_time and slip <= self.config.coupling.reengagement_slip_limit:
                transition("CONNECTED")
            elif slip > self.config.coupling.reengagement_slip_limit * 4.0:
                safety_override = True
                safety_reason = "REENGAGEMENT_SLIP_TOO_HIGH"
                transition("REV_MATCHING")
        elif mode == "FAULT_SAFE":
            transition("CONNECTED")

        return mode, mode_time, transition_count, safety_override, safety_reason

    def _engine_speed_and_request(
        self,
        mode: str,
        state: VehicleState,
        synchronous_engine_speed: float,
        command_engine_torque: float | None,
        dt: float,
    ) -> tuple[float, float | None, float]:
        engine = self.config.engine
        coupling = self.config.coupling
        if mode in {"CONNECTED", "DECOUPLING", "FAULT_SAFE"}:
            return max(synchronous_engine_speed, engine.min_operating_speed), command_engine_torque, coupling.max_torque_capacity
        if mode == "DECOUPLED":
            return engine.idle_speed, 0.0, 0.0

        if mode == "REV_MATCHING":
            error = synchronous_engine_speed - state.engine_speed
            requested_torque = max(engine.min_torque, min(engine.max_torque, error * engine.inertia / dt))
            next_engine_speed = state.engine_speed + requested_torque / engine.inertia * dt
            next_engine_speed = max(engine.min_operating_speed, min(engine.max_speed, next_engine_speed))
            return next_engine_speed, requested_torque, 0.0

        if mode == "REENGAGING":
            fraction = min(1.0, dt / self.config.coupling.closing_time)
            next_engine_speed = state.engine_speed + (synchronous_engine_speed - state.engine_speed) * fraction
            next_engine_speed = max(engine.min_operating_speed, min(engine.max_speed, next_engine_speed))
            capacity_fraction = min(1.0, max(state.mode_time, 0.0) / self.config.coupling.closing_time)
            return next_engine_speed, command_engine_torque, coupling.max_torque_capacity * capacity_fraction

        return state.engine_speed, command_engine_torque, 0.0

    def _coupling_effects(
        self,
        mode: str,
        engine_speed: float,
        synchronous_engine_speed: float,
        coupling_capacity: float,
        dt: float,
    ) -> tuple[float, float, float]:
        if mode != "REENGAGING":
            return 0.0, 0.0, 0.0

        slip_speed = engine_speed - synchronous_engine_speed
        if abs(slip_speed) <= self.config.coupling.locked_slip_threshold:
            return 0.0, 0.0, 0.0
        damping_torque = -0.5 * slip_speed
        coupling_torque = max(-coupling_capacity, min(coupling_capacity, damping_torque))
        slip_power = min(abs(coupling_torque * slip_speed), self.config.coupling.max_slip_power)
        return coupling_torque, slip_power, slip_power * dt

    def _engine_response(
        self,
        requested_torque: float | None,
        engine_speed: float,
        drivetrain_connected: bool,
    ) -> tuple[float, float, str]:
        engine = self.config.engine
        if not drivetrain_connected and (requested_torque is None or requested_torque == 0.0):
            return 0.0, engine.idle_fuel_rate, "IDLE"

        if requested_torque is None:
            torque = engine.min_torque if engine_speed >= engine.idle_speed else 0.0
            if engine.overrun_fuel_cutoff_enabled and engine_speed >= engine.overrun_fuel_cutoff_min_speed:
                return torque, 0.0, "OVERRUN_FUEL_CUTOFF"
            return torque, engine.idle_fuel_rate, "RUNNING"

        torque = max(engine.min_torque, min(engine.max_torque, requested_torque))
        if torque > 0.0:
            mechanical_power = torque * engine_speed
            fuel_rate = engine.idle_fuel_rate + mechanical_power / (
                engine.positive_load_efficiency * engine.fuel_lower_heating_value
            )
            return torque, fuel_rate, "RUNNING"
        if engine.overrun_fuel_cutoff_enabled and torque < 0.0 and engine_speed >= engine.overrun_fuel_cutoff_min_speed:
            return torque, 0.0, "OVERRUN_FUEL_CUTOFF"
        return torque, engine.idle_fuel_rate, "IDLE"

    def _wheel_torque_and_loss(
        self,
        engine_torque: float,
        engine_speed: float,
        wheel_speed: float,
        total_ratio: float,
        drivetrain_connected: bool,
    ) -> tuple[float, float]:
        if not drivetrain_connected:
            return 0.0, 0.0
        transmission = self.config.transmission
        engine_power = engine_torque * engine_speed
        if engine_torque >= 0.0:
            wheel_torque = engine_torque * total_ratio * transmission.efficiency_motoring
            wheel_power = wheel_torque * wheel_speed
            return wheel_torque, max(engine_power - wheel_power, 0.0)

        wheel_torque = engine_torque * total_ratio / transmission.efficiency_overrun
        wheel_power = wheel_torque * wheel_speed
        return wheel_torque, max(abs(wheel_power) - abs(engine_power), 0.0)

    @staticmethod
    def _engine_loss_energy_step(
        engine_power: float,
        fuel_energy_step: float,
        dt: float,
        drivetrain_connected: bool,
    ) -> float:
        if not drivetrain_connected:
            return fuel_energy_step
        if engine_power >= 0.0:
            return max(fuel_energy_step - engine_power * dt, 0.0)
        return -engine_power * dt

    @staticmethod
    def _energy_balance_residual(state: VehicleState, kinetic_energy: float) -> float:
        delta_kinetic = kinetic_energy - state.kinetic_energy_initial
        accounted = (
            delta_kinetic
            + state.potential_energy_change
            + state.aero_energy
            + state.rolling_resistance_energy
            + state.brake_energy
            + state.drivetrain_loss_energy
            + state.coupling_slip_energy
            + state.engine_loss_energy
        )
        return state.fuel_energy - accounted
