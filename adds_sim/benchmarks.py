"""Standardized Phase 3 benchmark scenarios."""

from __future__ import annotations

from dataclasses import replace

from .profiles import ConstantProfile, PiecewiseLinearProfile
from .simulator import Scenario


def with_adds_enabled(scenario: Scenario, enabled: bool) -> Scenario:
    """Return a scenario copy with ADDS authority enabled or disabled."""

    return replace(
        scenario,
        adds_enabled=enabled,
        drivetrain_connected=True,
        initial_coupling_mode="CONNECTED",
    )


def benchmark_scenarios() -> tuple[Scenario, ...]:
    """Return a compact deterministic benchmark suite for Phase 3 baselines."""

    return (
        Scenario(
            scenario_id="B01_constant_speed_cruise",
            initial_speed=25.0,
            initial_gear=5,
            time_limit=20.0,
            target_speed_profile=ConstantProfile(25.0),
            grade_profile=ConstantProfile(0.0),
        ),
        Scenario(
            scenario_id="B02_highway_lift_off",
            initial_speed=30.0,
            initial_gear=5,
            time_limit=18.0,
            target_speed_profile=PiecewiseLinearProfile(((0.0, 30.0), (2.0, 24.0), (12.0, 24.0), (18.0, 30.0))),
            grade_profile=ConstantProfile(0.0),
        ),
        Scenario(
            scenario_id="B03_mild_descent_lower_speed",
            initial_speed=26.0,
            initial_gear=5,
            time_limit=16.0,
            target_speed_profile=PiecewiseLinearProfile(((0.0, 26.0), (4.0, 22.0), (16.0, 22.0))),
            grade_profile=ConstantProfile(-0.025),
        ),
    )
