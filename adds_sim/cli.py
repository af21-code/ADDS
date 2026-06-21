"""Command-line entry point for a small Phase 1 demonstration run."""

from __future__ import annotations

import json

from .controllers import SpeedTrackingController
from .defaults import default_simulation_config
from .metrics import summarize_run
from .profiles import ConstantProfile
from .simulator import LongitudinalSimulator, Scenario


def main() -> None:
    config = default_simulation_config()
    simulator = LongitudinalSimulator(config)
    scenario = Scenario(
        scenario_id="demo_constant_speed_cruise",
        initial_speed=25.0,
        initial_gear=5,
        time_limit=20.0,
        target_speed_profile=ConstantProfile(25.0),
        grade_profile=ConstantProfile(0.0),
        drivetrain_connected=True,
    )
    result = simulator.run(scenario, SpeedTrackingController(gear=5))
    print(json.dumps(summarize_run(result), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
