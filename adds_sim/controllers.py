"""Deterministic controllers for the Phase 1 simulator."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ControlCommand:
    """Controller command for one simulation step.

    `engine_torque` set to `None` represents accelerator lift-off in a connected
    conventional drivetrain. The plant then applies modeled engine braking.
    """

    engine_torque: float | None
    brake_force: float
    gear: int
    requested_mode: str = "CONNECTED"
    target_gear: int | None = None
    force_fault: bool = False


class Controller:
    """Controller interface."""

    name = "controller"

    def command(self, observation: dict[str, float]) -> ControlCommand:
        raise NotImplementedError


@dataclass(frozen=True)
class CoastController(Controller):
    """Accelerator lift-off with no foundation braking."""

    gear: int
    name: str = "coast"

    def command(self, observation: dict[str, float]) -> ControlCommand:
        return ControlCommand(engine_torque=None, brake_force=0.0, gear=self.gear)


@dataclass(frozen=True)
class ConstantEngineTorqueController(Controller):
    """Applies a constant engine torque request in a fixed gear."""

    engine_torque: float
    gear: int
    brake_force: float = 0.0
    name: str = "constant_engine_torque"

    def command(self, observation: dict[str, float]) -> ControlCommand:
        return ControlCommand(engine_torque=self.engine_torque, brake_force=self.brake_force, gear=self.gear)


@dataclass(frozen=True)
class SpeedTrackingController(Controller):
    """Simple deterministic speed tracker for drive-cycle tests."""

    gear: int
    proportional_gain: float = 0.6
    acceleration_limit: float = 1.5
    name: str = "speed_tracking"

    def command(self, observation: dict[str, float]) -> ControlCommand:
        speed_error = observation["target_speed"] - observation["vehicle_speed"]
        desired_acceleration = max(
            -self.acceleration_limit,
            min(self.acceleration_limit, self.proportional_gain * speed_error),
        )
        required_force = observation["force_to_hold_speed"] + observation["vehicle_mass"] * desired_acceleration

        if required_force >= 0.0:
            wheel_torque = required_force * observation["wheel_radius"]
            engine_torque = wheel_torque / (
                observation["total_drive_ratio"] * observation["transmission_efficiency_motoring"]
            )
            return ControlCommand(engine_torque=engine_torque, brake_force=0.0, gear=self.gear)

        brake_force = min(-required_force, observation["max_brake_force"])
        return ControlCommand(engine_torque=0.0, brake_force=brake_force, gear=self.gear)


@dataclass(frozen=True)
class ScriptedModeController(Controller):
    """Time-scheduled controller useful for deterministic state-machine tests."""

    gear: int
    schedule: tuple[tuple[float, str, float | None, float, bool], ...]
    name: str = "scripted_mode"

    def command(self, observation: dict[str, float]) -> ControlCommand:
        time = observation["time"]
        selected = self.schedule[0]
        for item in self.schedule:
            if time >= item[0]:
                selected = item
            else:
                break
        _, mode, engine_torque, brake_force, force_fault = selected
        return ControlCommand(
            engine_torque=engine_torque,
            brake_force=brake_force,
            gear=self.gear,
            requested_mode=mode,
            target_gear=self.gear,
            force_fault=force_fault,
        )
