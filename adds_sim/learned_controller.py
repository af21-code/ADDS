"""Learned ADDS controller implementations."""

from __future__ import annotations

from dataclasses import dataclass

from .controllers import ControlCommand, SpeedTrackingController, coast_is_feasible
from .ml import BehavioralCloningModel


@dataclass(frozen=True)
class LearnedADDSController(SpeedTrackingController):
    """Behavioral-cloning ADDS controller using a saved threshold model."""

    model: BehavioralCloningModel | None = None
    minimum_target_speed_drop: float = 0.25
    maximum_coast_grade: float = 0.005
    name: str = "learned_adds"

    def command(self, observation: dict[str, float]) -> ControlCommand:
        if self.model is None:
            raise ValueError("LearnedADDSController requires a BehavioralCloningModel")

        base = super().command(observation)
        mode = str(observation["coupling_mode"])
        coast_feasible = coast_is_feasible(
            observation=observation,
            coast_speed_margin=self.model.coast_speed_margin,
            reconnect_speed_margin=self.model.reconnect_speed_margin,
            minimum_target_speed_drop=self.minimum_target_speed_drop,
            maximum_coast_grade=self.maximum_coast_grade,
        )

        requested_mode = "CONNECTED"
        engine_torque = base.engine_torque
        brake_force = base.brake_force

        if mode == "CONNECTED":
            if coast_feasible:
                requested_mode = "DECOUPLING"
                engine_torque = None
                brake_force = 0.0
        elif mode in {"DECOUPLING", "DECOUPLED"}:
            if coast_feasible:
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
