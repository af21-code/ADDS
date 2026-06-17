"""Fixed-step longitudinal vehicle simulator."""

from __future__ import annotations

from dataclasses import dataclass
from math import cos, sin

from .controllers import Controller
from .parameters import (
    EngineParameters,
    EnvironmentParameters,
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
    solver: SolverParameters

    def validate(self) -> None:
        self.vehicle.validate()
        self.environment.validate()
        self.engine.validate()
        self.transmission.validate()
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
    random_seed: int = 0

    def validate(self, config: SimulationConfig) -> None:
        if self.initial_speed < 0.0:
            raise ValueError("scenario.initial_speed must be >= 0")
        if self.time_limit <= 0.0:
            raise ValueError("scenario.time_limit must be > 0")
        if self.distance_limit is not None and self.distance_limit <= 0.0:
            raise ValueError("scenario.distance_limit must be > 0 when set")
        config.transmission.gear_ratio(self.initial_gear)


@dataclass
class VehicleState:
    time: float
    step_index: int
    position: float
    speed: float
    acceleration: float
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
        kinetic = 0.5 * self.equivalent_mass(scenario.initial_gear, scenario.drivetrain_connected) * scenario.initial_speed**2
        return VehicleState(
            time=0.0,
            step_index=0,
            position=0.0,
            speed=scenario.initial_speed,
            acceleration=0.0,
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

    def _step(
        self,
        scenario: Scenario,
        controller: Controller,
        state: VehicleState,
        dt: float,
    ) -> tuple[dict[str, float | int | str | bool], VehicleState]:
        gear = scenario.initial_gear
        grade = scenario.grade_profile.value_at(state.position)
        target_speed = scenario.target_speed_profile.value_at(state.time)
        total_ratio = self.config.transmission.total_ratio(gear)
        forces = self.resistive_forces(state.speed, grade)
        force_to_hold = forces["aero_force"] + forces["rolling_resistance_force"] + forces["grade_force"]
        engine_speed = self.synchronous_engine_speed(state.speed, gear) if scenario.drivetrain_connected else self.config.engine.idle_speed
        engine_speed = max(engine_speed, self.config.engine.min_operating_speed)

        observation = {
            "time": state.time,
            "position": state.position,
            "vehicle_speed": state.speed,
            "vehicle_acceleration": state.acceleration,
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
        gear = command.gear
        total_ratio = self.config.transmission.total_ratio(gear)
        engine_speed = self.synchronous_engine_speed(state.speed, gear) if scenario.drivetrain_connected else self.config.engine.idle_speed
        engine_speed = max(engine_speed, self.config.engine.min_operating_speed)

        engine_torque, engine_fuel_rate, engine_state = self._engine_response(command.engine_torque, engine_speed, scenario.drivetrain_connected)
        wheel_speed = self.wheel_speed(state.speed)
        wheel_torque, drivetrain_loss_power = self._wheel_torque_and_loss(engine_torque, engine_speed, wheel_speed, total_ratio, scenario.drivetrain_connected)
        drivetrain_force = wheel_torque / self.config.vehicle.wheel_radius
        tire_limit = self.tire_force_limit(grade)
        drivetrain_force = max(-tire_limit, min(tire_limit, drivetrain_force))

        brake_force = min(max(command.brake_force, 0.0), self.config.vehicle.max_brake_force)
        brake_force = min(brake_force, tire_limit)
        net_force = drivetrain_force - brake_force - forces["aero_force"] - forces["rolling_resistance_force"] - forces["grade_force"]
        mass_eq = self.equivalent_mass(gear, scenario.drivetrain_connected)
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
        engine_loss_step = self._engine_loss_energy_step(engine_power, fuel_energy_step, dt, scenario.drivetrain_connected)
        potential_step = self.config.vehicle.mass * self.config.environment.gravity * sin(grade) * distance_step

        next_state = VehicleState(
            time=state.time + dt,
            step_index=state.step_index + 1,
            position=next_position,
            speed=next_speed,
            acceleration=acceleration,
            fuel_used=state.fuel_used + fuel_step,
            aero_energy=state.aero_energy + max(forces["aero_force"] * distance_step, 0.0),
            rolling_resistance_energy=state.rolling_resistance_energy + max(forces["rolling_resistance_force"] * distance_step, 0.0),
            brake_energy=state.brake_energy + brake_force * distance_step,
            drivetrain_loss_energy=state.drivetrain_loss_energy + drivetrain_loss_power * dt,
            engine_loss_energy=state.engine_loss_energy + engine_loss_step,
            coupling_slip_energy=state.coupling_slip_energy,
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
            "engine_speed_target": engine_speed,
            "engine_torque_command": command.engine_torque if command.engine_torque is not None else self.config.engine.min_torque,
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
            "coupling_mode": "CONNECTED" if scenario.drivetrain_connected else "DECOUPLED",
            "coupling_capacity_command": 0.0,
            "coupling_capacity": 0.0,
            "coupling_torque": 0.0,
            "coupling_slip_speed": 0.0,
            "coupling_slip_power": 0.0,
            "coupling_slip_energy": next_state.coupling_slip_energy,
            "mode_time": next_state.time,
            "transition_count": 0,
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
            "controller_version": "phase1",
            "requested_mode": "CONNECTED" if scenario.drivetrain_connected else "DECOUPLED",
            "applied_mode": "CONNECTED" if scenario.drivetrain_connected else "DECOUPLED",
            "safety_override": False,
            "safety_override_reason": "",
            "fallback_active": False,
            "controller_latency": 0.0,
        }
        return record, next_state

    def _engine_response(
        self,
        requested_torque: float | None,
        engine_speed: float,
        drivetrain_connected: bool,
    ) -> tuple[float, float, str]:
        engine = self.config.engine
        if not drivetrain_connected:
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
