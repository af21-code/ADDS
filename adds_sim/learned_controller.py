"""Learned ADDS controller implementations."""

from __future__ import annotations

from dataclasses import dataclass

from .controllers import ControlCommand, SpeedTrackingController
from .ml import BehavioralCloningModel


@dataclass(frozen=True)
class LearnedADDSController(SpeedTrackingController):
    """Behavioral-cloning ADDS controller using a saved threshold model."""

    model: BehavioralCloningModel | None = None
    name: str = "learned_adds"

    def command(self, observation: dict[str, float]) -> ControlCommand:
        if self.model is None:
            raise ValueError("LearnedADDSController requires a BehavioralCloningModel")

        base = super().command(observation)
        mode = str(observation["coupling_mode"])
        target_speed = observation["target_speed"]
        target_speed_preview = observation["target_speed_preview"]
        preview_horizon = observation["target_speed_preview_horizon"]
        natural_deceleration = max(observation["force_to_hold_speed"], 0.0) / observation["vehicle_mass"]
        predicted_speed = max(
            0.0,
            observation["vehicle_speed"] - natural_deceleration * preview_horizon,
        )
        coast_is_feasible = (
            observation["vehicle_speed"] >= observation["minimum_decoupling_speed"]
            and target_speed_preview < target_speed - 1e-9
            and target_speed_preview - self.model.reconnect_speed_margin
            <= predicted_speed
            <= target_speed_preview + self.model.coast_speed_margin
        )

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
        elif mode in {"REV_MATCHING", "REENGAGING", "FAULT_SAFE"}:
            requested_mode = "CONNECTED"

        return ControlCommand(
            engine_torque=engine_torque,
            brake_force=brake_force,
            gear=self.gear,
            requested_mode=requested_mode,
            target_gear=self.gear,
        )
