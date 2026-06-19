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

        speed_error = observation["target_speed"] - observation["vehicle_speed"]
        base = super().command(observation)
        brake_active = base.brake_force > 1e-9
        propulsion_requested = base.engine_torque is not None and base.engine_torque > 1e-9
        mode = str(observation["coupling_mode"])

        requested_mode = "CONNECTED"
        engine_torque = base.engine_torque

        if mode == "CONNECTED":
            if speed_error < -self.model.coast_speed_margin and not brake_active:
                requested_mode = "DECOUPLING"
                engine_torque = None
        elif mode in {"DECOUPLING", "DECOUPLED"}:
            if brake_active or propulsion_requested or speed_error > self.model.reconnect_speed_margin:
                requested_mode = "CONNECTED"
            else:
                requested_mode = "DECOUPLED"
                engine_torque = 0.0
        elif mode in {"REV_MATCHING", "REENGAGING", "FAULT_SAFE"}:
            requested_mode = "CONNECTED"

        return ControlCommand(
            engine_torque=engine_torque,
            brake_force=base.brake_force,
            gear=self.gear,
            requested_mode=requested_mode,
            target_gear=self.gear,
        )
