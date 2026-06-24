"""Deterministic controllers for ADDS simulator baselines."""

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
class ConventionalBaselineController(SpeedTrackingController):
    """Conventional connected-drivetrain speed-tracking baseline."""

    name: str = "conventional_baseline"

    def command(self, observation: dict[str, float]) -> ControlCommand:
        command = super().command(observation)
        return ControlCommand(
            engine_torque=command.engine_torque,
            brake_force=command.brake_force,
            gear=command.gear,
            requested_mode="CONNECTED",
            target_gear=command.gear,
        )


def coast_is_feasible(
    observation: dict[str, float],
    coast_speed_margin: float,
    reconnect_speed_margin: float,
    minimum_target_speed_drop: float,
    maximum_coast_grade: float,
) -> bool:
    """Return whether previewed unpowered coasting remains inside policy guards."""

    target_speed = observation["target_speed"]
    target_speed_preview = observation["target_speed_preview"]
    preview_horizon = observation["target_speed_preview_horizon"]
    natural_deceleration = max(observation["force_to_hold_speed"], 0.0) / observation["vehicle_mass"]
    predicted_speed = max(
        0.0,
        observation["vehicle_speed"] - natural_deceleration * preview_horizon,
    )
    return (
        observation["vehicle_speed"] >= observation["minimum_decoupling_speed"]
        and target_speed - target_speed_preview >= minimum_target_speed_drop
        and observation["road_grade"] <= maximum_coast_grade
        and target_speed_preview - reconnect_speed_margin
        <= predicted_speed
        <= target_speed_preview + coast_speed_margin
    )


@dataclass(frozen=True)
class RuleBasedADDSController(SpeedTrackingController):
    """Transparent rule-based ADDS baseline.

    The policy decouples only when a one-second target preview indicates that
    unpowered coasting can follow a decreasing speed target within a declared
    corridor. It reconnects when propulsion, braking, or tighter tracking
    becomes necessary.
    """

    coast_speed_margin: float = 0.4
    reconnect_speed_margin: float = 0.1
    minimum_target_speed_drop: float = 0.25
    maximum_coast_grade: float = 0.005
    name: str = "rule_based_adds"

    def command(self, observation: dict[str, float]) -> ControlCommand:
        base = super().command(observation)
        mode = str(observation["coupling_mode"])
        coast_is_feasible = self._coast_is_feasible(observation)

        requested_mode = "CONNECTED"
        engine_torque = base.engine_torque
        brake_force = base.brake_force

        if mode == "CONNECTED":
            if coast_is_feasible:
                requested_mode = "DECOUPLING"
                engine_torque = None
                brake_force = 0.0
        elif mode in {"DECOUPLING", "DECOUPLED"}:
            if coast_is_feasible:
                requested_mode = "DECOUPLED"
                engine_torque = 0.0
                brake_force = 0.0
            else:
                requested_mode = "CONNECTED"
        elif mode in {"REV_MATCHING", "REENGAGING"}:
            requested_mode = "CONNECTED"
        elif mode == "FAULT_SAFE":
            requested_mode = "CONNECTED"

        return ControlCommand(
            engine_torque=engine_torque,
            brake_force=brake_force,
            gear=self.gear,
            requested_mode=requested_mode,
            target_gear=self.gear,
        )

    def _coast_is_feasible(self, observation: dict[str, float]) -> bool:
        return coast_is_feasible(
            observation=observation,
            coast_speed_margin=self.coast_speed_margin,
            reconnect_speed_margin=self.reconnect_speed_margin,
            minimum_target_speed_drop=self.minimum_target_speed_drop,
            maximum_coast_grade=self.maximum_coast_grade,
        )


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
