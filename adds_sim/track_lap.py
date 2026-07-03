"""Reference track-lap prototype for conventional-vs-ADDS comparisons."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from .comparison import PairedComparisonResult, run_paired_comparison
from .controllers import (
    ConventionalBaselineController,
    OfflineOptimizedADDSController,
    RuleBasedADDSController,
)
from .data import write_trajectory_csv
from .defaults import default_simulation_config
from .learned_controller import LearnedADDSController
from .ml import collect_imitation_examples, train_behavioral_cloning_model
from .profiles import PiecewiseLinearProfile
from .scenario_catalog import phase4_scenario_catalog
from .simulator import LongitudinalSimulator, Scenario, SimulationResult


TrackLapControllerKind = Literal["rule_based", "offline_optimized", "learned"]


@dataclass(frozen=True)
class TrackLapSection:
    """One longitudinal section in the reference circuit target profile."""

    name: str
    duration: float
    target_speed_end: float
    grade: float = 0.0


@dataclass(frozen=True)
class TrackLapStat:
    """One compact comparison statistic for reports and dashboards."""

    label: str
    conventional_value: float | int | bool
    adds_value: float | int | bool
    delta: float | int | bool
    unit: str
    direction: str


@dataclass(frozen=True)
class TrackLapComparison:
    """Packaged result for one reference track-lap comparison."""

    schema_version: str
    track_name: str
    description: str
    adds_controller_kind: TrackLapControllerKind
    scenario: Scenario
    sections: tuple[TrackLapSection, ...]
    comparison: PairedComparisonResult
    stats: tuple[TrackLapStat, ...]


def reference_track_lap_sections() -> tuple[TrackLapSection, ...]:
    """Return a compact reference circuit with repeated lift-off opportunities."""

    return (
        TrackLapSection("Main straight", 8.0, 32.0, 0.000),
        TrackLapSection("Turn 1 lift-off", 10.0, 28.0, 0.000),
        TrackLapSection("Turn 1 minimum speed", 5.0, 28.0, 0.000),
        TrackLapSection("Back straight acceleration", 12.0, 34.0, 0.001),
        TrackLapSection("Fast kink lift-off", 12.0, 29.0, 0.000),
        TrackLapSection("Fast kink minimum speed", 6.0, 29.0, 0.000),
        TrackLapSection("Short straight acceleration", 11.0, 33.0, -0.001),
        TrackLapSection("Technical sector lift-off", 10.0, 29.0, 0.000),
        TrackLapSection("Technical sector hold", 8.0, 29.0, 0.000),
        TrackLapSection("Final straight acceleration", 14.0, 34.0, 0.000),
    )


def build_reference_track_lap_scenario(
    track_name: str = "ADDS reference circuit v1",
    initial_speed: float = 32.0,
    initial_gear: int = 5,
    lap_distance: float = 3_000.0,
    sections: tuple[TrackLapSection, ...] | None = None,
) -> Scenario:
    """Build a distance-limited reference lap using a time-domain speed profile."""

    lap_sections = sections or reference_track_lap_sections()
    _validate_track_lap_sections(lap_sections)

    target_points: list[tuple[float, float]] = [(0.0, initial_speed)]
    grade_points: list[tuple[float, float]] = [(0.0, lap_sections[0].grade)]
    elapsed = 0.0
    distance = 0.0
    previous_speed = initial_speed
    for section in lap_sections:
        elapsed += section.duration
        distance += 0.5 * (previous_speed + section.target_speed_end) * section.duration
        target_points.append((elapsed, section.target_speed_end))
        grade_points.append((distance, section.grade))
        previous_speed = section.target_speed_end

    return Scenario(
        scenario_id=_scenario_id_from_track_name(track_name),
        initial_speed=initial_speed,
        initial_gear=initial_gear,
        time_limit=elapsed + 30.0,
        distance_limit=lap_distance,
        target_speed_profile=PiecewiseLinearProfile(tuple(target_points)),
        grade_profile=PiecewiseLinearProfile(tuple(grade_points)),
        drivetrain_connected=True,
        adds_enabled=True,
        random_seed=801,
    )


def run_track_lap_comparison(
    adds_controller_kind: TrackLapControllerKind = "offline_optimized",
    track_name: str = "ADDS reference circuit v1",
) -> TrackLapComparison:
    """Run a fair same-distance lap comparison between conventional and ADDS."""

    scenario = build_reference_track_lap_scenario(track_name=track_name)
    config = default_simulation_config()
    simulator = LongitudinalSimulator(config)
    conventional_controller = ConventionalBaselineController(scenario.initial_gear)
    adds_controller = _adds_controller(
        kind=adds_controller_kind,
        gear=scenario.initial_gear,
        simulator=simulator,
    )
    comparison = run_paired_comparison(
        simulator=simulator,
        scenario=scenario,
        conventional_controller=conventional_controller,
        adds_controller=adds_controller,
    )
    return TrackLapComparison(
        schema_version="1.0",
        track_name=track_name,
        description=(
            "Fixed-distance longitudinal reference lap with repeated lift-off, "
            "minimum-speed, and reacceleration sectors."
        ),
        adds_controller_kind=adds_controller_kind,
        scenario=scenario,
        sections=reference_track_lap_sections(),
        comparison=comparison,
        stats=track_lap_stats(comparison),
    )


def track_lap_stats(comparison: PairedComparisonResult) -> tuple[TrackLapStat, ...]:
    """Return compact track-lap statistics in display units."""

    conventional = comparison.conventional_summary
    adds = comparison.adds_summary
    deltas = comparison.deltas
    return (
        TrackLapStat(
            "Lap time",
            float(conventional["travel_time"]),
            float(adds["travel_time"]),
            float(deltas["delta_travel_time"]),
            "s",
            "lower_is_better",
        ),
        TrackLapStat(
            "Distance",
            float(conventional["distance_traveled"]) / 1_000.0,
            float(adds["distance_traveled"]) / 1_000.0,
            (float(adds["distance_traveled"]) - float(conventional["distance_traveled"])) / 1_000.0,
            "km",
            "same_target",
        ),
        TrackLapStat(
            "Fuel used",
            float(conventional["fuel_used"]) * 1_000_000.0,
            float(adds["fuel_used"]) * 1_000_000.0,
            float(deltas["delta_fuel_used"]) * 1_000_000.0,
            "ml",
            "lower_is_better",
        ),
        TrackLapStat(
            "Relative fuel change",
            0.0,
            float(deltas["relative_fuel_change"]),
            float(deltas["relative_fuel_change"]),
            "%",
            "lower_is_better",
        ),
        TrackLapStat(
            "RMS speed error",
            float(conventional["rms_speed_error"]) * 3.6,
            float(adds["rms_speed_error"]) * 3.6,
            float(deltas["delta_rms_speed_error"]) * 3.6,
            "km/h",
            "lower_is_better",
        ),
        TrackLapStat(
            "ADDS transitions",
            int(conventional["mode_transition_count"]),
            int(adds["mode_transition_count"]),
            int(adds["mode_transition_count"]) - int(conventional["mode_transition_count"]),
            "count",
            "context",
        ),
        TrackLapStat(
            "Safety overrides",
            int(conventional["safety_override_count"]),
            int(adds["safety_override_count"]),
            int(adds["safety_override_count"]) - int(conventional["safety_override_count"]),
            "count",
            "lower_is_better",
        ),
        TrackLapStat(
            "Decoupled duration",
            0.0,
            _mode_duration_seconds(comparison.adds_result, "DECOUPLED"),
            _mode_duration_seconds(comparison.adds_result, "DECOUPLED"),
            "s",
            "context",
        ),
        TrackLapStat(
            "Coupling slip energy",
            float(conventional["coupling_slip_energy"]) / 1_000.0,
            float(adds["coupling_slip_energy"]) / 1_000.0,
            float(deltas["delta_coupling_slip_energy"]) / 1_000.0,
            "kJ",
            "lower_is_better",
        ),
    )


def write_track_lap_report(
    output_dir: Path,
    report: TrackLapComparison,
) -> tuple[Path, Path, Path, Path]:
    """Write JSON summary, stat CSV, and paired trajectory CSV artifacts."""

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "track_lap_report.json"
    stats_path = output_dir / "track_lap_stats.csv"
    conventional_path = output_dir / "track_lap_conventional_trajectory.csv"
    adds_path = output_dir / "track_lap_adds_trajectory.csv"

    with json_path.open("w", encoding="utf-8") as file:
        json.dump(_track_lap_report_payload(report), file, indent=2)

    with stats_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=("label", "conventional_value", "adds_value", "delta", "unit", "direction"),
        )
        writer.writeheader()
        for stat in report.stats:
            writer.writerow(asdict(stat))

    write_trajectory_csv(conventional_path, report.comparison.conventional_result)
    write_trajectory_csv(adds_path, report.comparison.adds_result)
    return json_path, stats_path, conventional_path, adds_path


def _track_lap_report_payload(report: TrackLapComparison) -> dict[str, object]:
    comparison = report.comparison
    return {
        "schema_version": report.schema_version,
        "track_name": report.track_name,
        "description": report.description,
        "adds_controller_kind": report.adds_controller_kind,
        "scenario": {
            "scenario_id": report.scenario.scenario_id,
            "initial_speed": report.scenario.initial_speed,
            "initial_gear": report.scenario.initial_gear,
            "time_limit": report.scenario.time_limit,
            "distance_limit": report.scenario.distance_limit,
        },
        "sections": [asdict(section) for section in report.sections],
        "conventional_summary": comparison.conventional_summary,
        "adds_summary": comparison.adds_summary,
        "deltas": comparison.deltas,
        "stats": [asdict(stat) for stat in report.stats],
    }


def _adds_controller(
    kind: TrackLapControllerKind,
    gear: int,
    simulator: LongitudinalSimulator,
):
    if kind == "rule_based":
        return RuleBasedADDSController(gear)
    if kind == "offline_optimized":
        return OfflineOptimizedADDSController(gear)
    if kind == "learned":
        training_entries = tuple(entry for entry in phase4_scenario_catalog() if entry.split == "train")
        model = train_behavioral_cloning_model(collect_imitation_examples(simulator, training_entries)).model
        return LearnedADDSController(gear=gear, model=model)
    raise ValueError(f"unknown track lap ADDS controller kind: {kind}")


def _mode_duration_seconds(result: SimulationResult, mode: str) -> float:
    records = result.records
    if not records:
        return 0.0

    duration = 0.0
    previous_time = 0.0
    for record in records:
        current_time = float(record["time"])
        if str(record["coupling_mode"]) == mode:
            duration += max(0.0, current_time - previous_time)
        previous_time = current_time
    return duration


def _scenario_id_from_track_name(track_name: str) -> str:
    slug = "".join(character.lower() if character.isalnum() else "_" for character in track_name)
    return "_".join(part for part in slug.split("_") if part)[:80] or "track_lap_v1"


def _validate_track_lap_sections(sections: tuple[TrackLapSection, ...]) -> None:
    if not sections:
        raise ValueError("at least one track lap section is required")
    for section in sections:
        if section.duration <= 0.0:
            raise ValueError(f"track lap section duration must be > 0: {section.name}")
        if section.target_speed_end <= 0.0:
            raise ValueError(f"track lap section target speed must be > 0: {section.name}")
