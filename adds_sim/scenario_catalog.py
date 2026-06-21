"""Versioned scenario catalog and split helpers."""

from __future__ import annotations

from dataclasses import dataclass

from .profiles import ConstantProfile, PiecewiseLinearProfile
from .simulator import Scenario


@dataclass(frozen=True)
class ScenarioCatalogEntry:
    """A scenario plus metadata required for reproducible batch evaluation."""

    scenario: Scenario
    split: str
    version: str
    description: str
    tags: tuple[str, ...]


def phase4_scenario_catalog() -> tuple[ScenarioCatalogEntry, ...]:
    """Return deterministic Phase 4 scenario catalog entries.

    Scenario IDs are unique across splits to avoid train/test leakage by
    construction.
    """

    return (
        ScenarioCatalogEntry(
            scenario=Scenario(
                scenario_id="train_constant_speed_cruise",
                initial_speed=25.0,
                initial_gear=5,
                time_limit=20.0,
                target_speed_profile=ConstantProfile(25.0),
                grade_profile=ConstantProfile(0.0),
                random_seed=1001,
            ),
            split="train",
            version="1.0",
            description="Level-road constant-speed cruise for force balance and fuel tracking.",
            tags=("cruise", "level-road", "nominal"),
        ),
        ScenarioCatalogEntry(
            scenario=Scenario(
                scenario_id="train_highway_lift_off",
                initial_speed=30.0,
                initial_gear=5,
                time_limit=18.0,
                target_speed_profile=PiecewiseLinearProfile(((0.0, 30.0), (2.0, 24.0), (12.0, 24.0), (18.0, 30.0))),
                grade_profile=ConstantProfile(0.0),
                random_seed=1002,
            ),
            split="train",
            version="1.0",
            description="Highway lift-off and reacceleration scenario with coasting opportunity.",
            tags=("highway", "coast", "nominal"),
        ),
        ScenarioCatalogEntry(
            scenario=Scenario(
                scenario_id="validation_rolling_terrain",
                initial_speed=24.0,
                initial_gear=5,
                time_limit=24.0,
                target_speed_profile=ConstantProfile(24.0),
                grade_profile=PiecewiseLinearProfile(((0.0, 0.0), (120.0, -0.025), (260.0, 0.02), (420.0, -0.015), (600.0, 0.0))),
                random_seed=2001,
            ),
            split="validation",
            version="1.0",
            description="Rolling-terrain route for checking grade-sensitive decisions.",
            tags=("rolling-terrain", "grade", "validation"),
        ),
        ScenarioCatalogEntry(
            scenario=Scenario(
                scenario_id="test_mild_descent_lower_speed",
                initial_speed=26.0,
                initial_gear=5,
                time_limit=16.0,
                target_speed_profile=PiecewiseLinearProfile(((0.0, 26.0), (4.0, 22.0), (16.0, 22.0))),
                grade_profile=ConstantProfile(-0.025),
                random_seed=3001,
            ),
            split="test",
            version="1.0",
            description="Held-out descent with lower speed target where engine braking can matter.",
            tags=("descent", "speed-reduction", "test"),
        ),
        ScenarioCatalogEntry(
            scenario=Scenario(
                scenario_id="stress_low_speed_urban",
                initial_speed=12.0,
                initial_gear=3,
                time_limit=22.0,
                target_speed_profile=PiecewiseLinearProfile(((0.0, 12.0), (4.0, 6.0), (8.0, 14.0), (14.0, 4.0), (22.0, 10.0))),
                grade_profile=ConstantProfile(0.0),
                random_seed=4001,
            ),
            split="stress",
            version="1.0",
            description="Low-speed demand changes where frequent decoupling should be unattractive.",
            tags=("urban", "low-speed", "stress"),
        ),
    )


def entries_by_split(entries: tuple[ScenarioCatalogEntry, ...]) -> dict[str, tuple[ScenarioCatalogEntry, ...]]:
    """Group catalog entries by split."""

    grouped: dict[str, list[ScenarioCatalogEntry]] = {}
    for entry in entries:
        grouped.setdefault(entry.split, []).append(entry)
    return {split: tuple(items) for split, items in sorted(grouped.items())}
