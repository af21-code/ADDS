"""Endurance race strategy layer for ADDS track-lap results."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from math import ceil, floor
from pathlib import Path

from .track_lap import TrackLapComparison, TrackLapControllerKind, run_track_lap_comparison


@dataclass(frozen=True)
class EnduranceStrategyConfig:
    """Configuration for an endurance-style extrapolation from one reference lap."""

    race_name: str = "ADDS endurance strategy v1"
    race_duration_hours: float = 24.0
    reference_stint_laps: int = 30
    pit_stop_loss_seconds: float = 42.0
    adds_controller_kind: TrackLapControllerKind = "offline_optimized"


@dataclass(frozen=True)
class EnduranceVehicleStrategy:
    """One vehicle's simulated race strategy summary."""

    vehicle: str
    lap_time: float
    fuel_per_lap: float
    tank_capacity: float
    stint_laps: int
    pit_stops: int
    completed_laps: int
    elapsed_time: float
    remaining_time: float
    distance_km: float
    fuel_used: float
    final_tank_fuel: float


@dataclass(frozen=True)
class EnduranceStrategyThresholds:
    """Thresholds that explain when fuel saving becomes strategic."""

    relative_fuel_saving_percent: float
    minimum_reference_stint_laps_for_one_extra_lap: int | None
    current_reference_stint_laps: int
    adds_gains_stint_lap_at_current_tank: bool


@dataclass(frozen=True)
class EnduranceStrategyReport:
    """Conventional-vs-ADDS endurance strategy report."""

    schema_version: str
    config: EnduranceStrategyConfig
    track_lap: TrackLapComparison
    conventional: EnduranceVehicleStrategy
    adds: EnduranceVehicleStrategy
    thresholds: EnduranceStrategyThresholds
    deltas: dict[str, float | int | bool]
    verdict: str
    interpretation: tuple[str, ...]


def run_endurance_strategy(
    config: EnduranceStrategyConfig | None = None,
) -> EnduranceStrategyReport:
    """Run a fixed-duration endurance strategy extrapolation."""

    strategy_config = config or EnduranceStrategyConfig()
    _validate_strategy_config(strategy_config)
    track_lap = run_track_lap_comparison(strategy_config.adds_controller_kind)
    return build_endurance_strategy_report(track_lap, strategy_config)


def build_endurance_strategy_report(
    track_lap: TrackLapComparison,
    config: EnduranceStrategyConfig | None = None,
) -> EnduranceStrategyReport:
    """Build an endurance strategy report from one paired track-lap comparison."""

    strategy_config = config or EnduranceStrategyConfig(
        adds_controller_kind=track_lap.adds_controller_kind
    )
    _validate_strategy_config(strategy_config)

    conventional_lap_time = float(track_lap.comparison.conventional_summary["travel_time"])
    adds_lap_time = float(track_lap.comparison.adds_summary["travel_time"])
    conventional_fuel = float(track_lap.comparison.conventional_summary["fuel_used"])
    adds_fuel = float(track_lap.comparison.adds_summary["fuel_used"])
    lap_distance_km = float(track_lap.comparison.conventional_summary["distance_traveled"]) / 1_000.0
    tank_capacity = conventional_fuel * strategy_config.reference_stint_laps
    race_duration = strategy_config.race_duration_hours * 3_600.0

    conventional = _simulate_fixed_duration_race(
        vehicle="Conventional",
        lap_time=conventional_lap_time,
        fuel_per_lap=conventional_fuel,
        tank_capacity=tank_capacity,
        race_duration=race_duration,
        pit_stop_loss_seconds=strategy_config.pit_stop_loss_seconds,
        lap_distance_km=lap_distance_km,
    )
    adds = _simulate_fixed_duration_race(
        vehicle="ADDS",
        lap_time=adds_lap_time,
        fuel_per_lap=adds_fuel,
        tank_capacity=tank_capacity,
        race_duration=race_duration,
        pit_stop_loss_seconds=strategy_config.pit_stop_loss_seconds,
        lap_distance_km=lap_distance_km,
    )
    thresholds = _strategy_thresholds(
        conventional_fuel_per_lap=conventional_fuel,
        adds_fuel_per_lap=adds_fuel,
        current_reference_stint_laps=strategy_config.reference_stint_laps,
        adds_stint_laps=adds.stint_laps,
    )
    deltas = _strategy_deltas(conventional, adds)
    verdict, interpretation = _strategy_interpretation(
        conventional=conventional,
        adds=adds,
        thresholds=thresholds,
        deltas=deltas,
    )
    return EnduranceStrategyReport(
        schema_version="1.0",
        config=strategy_config,
        track_lap=track_lap,
        conventional=conventional,
        adds=adds,
        thresholds=thresholds,
        deltas=deltas,
        verdict=verdict,
        interpretation=interpretation,
    )


def _validate_strategy_config(strategy_config: EnduranceStrategyConfig) -> None:
    if strategy_config.race_duration_hours <= 0.0:
        raise ValueError("race_duration_hours must be > 0")
    if strategy_config.reference_stint_laps <= 0:
        raise ValueError("reference_stint_laps must be > 0")
    if strategy_config.pit_stop_loss_seconds < 0.0:
        raise ValueError("pit_stop_loss_seconds must be >= 0")


def write_endurance_strategy_report(
    output_dir: Path,
    report: EnduranceStrategyReport,
) -> tuple[Path, Path]:
    """Write endurance strategy JSON and compact CSV artifacts."""

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "endurance_strategy_report.json"
    csv_path = output_dir / "endurance_strategy_summary.csv"

    with json_path.open("w", encoding="utf-8") as file:
        json.dump(_report_payload(report), file, indent=2)

    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=(
                "vehicle",
                "lap_time",
                "fuel_per_lap",
                "stint_laps",
                "pit_stops",
                "completed_laps",
                "elapsed_time",
                "remaining_time",
                "distance_km",
                "fuel_used",
            ),
        )
        writer.writeheader()
        writer.writerow(_vehicle_csv_row(report.conventional))
        writer.writerow(_vehicle_csv_row(report.adds))
    return json_path, csv_path


def _simulate_fixed_duration_race(
    vehicle: str,
    lap_time: float,
    fuel_per_lap: float,
    tank_capacity: float,
    race_duration: float,
    pit_stop_loss_seconds: float,
    lap_distance_km: float,
) -> EnduranceVehicleStrategy:
    stint_laps = max(1, floor(tank_capacity / fuel_per_lap))
    elapsed = 0.0
    fuel_in_tank = tank_capacity
    completed_laps = 0
    pit_stops = 0
    fuel_used = 0.0

    while elapsed + lap_time <= race_duration + 1e-9:
        if fuel_in_tank + 1e-12 < fuel_per_lap:
            elapsed += pit_stop_loss_seconds
            if elapsed + lap_time > race_duration + 1e-9:
                break
            pit_stops += 1
            fuel_in_tank = tank_capacity

        fuel_in_tank -= fuel_per_lap
        fuel_used += fuel_per_lap
        elapsed += lap_time
        completed_laps += 1

    return EnduranceVehicleStrategy(
        vehicle=vehicle,
        lap_time=lap_time,
        fuel_per_lap=fuel_per_lap,
        tank_capacity=tank_capacity,
        stint_laps=stint_laps,
        pit_stops=pit_stops,
        completed_laps=completed_laps,
        elapsed_time=elapsed,
        remaining_time=max(0.0, race_duration - elapsed),
        distance_km=completed_laps * lap_distance_km,
        fuel_used=fuel_used,
        final_tank_fuel=fuel_in_tank,
    )


def _strategy_thresholds(
    conventional_fuel_per_lap: float,
    adds_fuel_per_lap: float,
    current_reference_stint_laps: int,
    adds_stint_laps: int,
) -> EnduranceStrategyThresholds:
    saving = conventional_fuel_per_lap - adds_fuel_per_lap
    relative_saving = 100.0 * saving / conventional_fuel_per_lap if conventional_fuel_per_lap > 0.0 else 0.0
    minimum_laps = None
    if saving > 0.0 and adds_fuel_per_lap > 0.0:
        minimum_laps = max(1, ceil(adds_fuel_per_lap / saving))
    return EnduranceStrategyThresholds(
        relative_fuel_saving_percent=relative_saving,
        minimum_reference_stint_laps_for_one_extra_lap=minimum_laps,
        current_reference_stint_laps=current_reference_stint_laps,
        adds_gains_stint_lap_at_current_tank=adds_stint_laps > current_reference_stint_laps,
    )


def _strategy_deltas(
    conventional: EnduranceVehicleStrategy,
    adds: EnduranceVehicleStrategy,
) -> dict[str, float | int | bool]:
    lap_equivalent_advantage = (
        (adds.completed_laps - conventional.completed_laps) * conventional.lap_time
        + (conventional.elapsed_time - adds.elapsed_time)
    )
    return {
        "delta_completed_laps": adds.completed_laps - conventional.completed_laps,
        "delta_pit_stops": adds.pit_stops - conventional.pit_stops,
        "delta_distance_km": adds.distance_km - conventional.distance_km,
        "delta_elapsed_time": adds.elapsed_time - conventional.elapsed_time,
        "delta_fuel_used": adds.fuel_used - conventional.fuel_used,
        "relative_fuel_change": _relative_change(conventional.fuel_used, adds.fuel_used),
        "lap_equivalent_advantage_seconds": lap_equivalent_advantage,
        "adds_strategy_advantage": lap_equivalent_advantage > 0.0,
        "adds_saves_pit_stop": adds.pit_stops < conventional.pit_stops,
    }


def _strategy_interpretation(
    conventional: EnduranceVehicleStrategy,
    adds: EnduranceVehicleStrategy,
    thresholds: EnduranceStrategyThresholds,
    deltas: dict[str, float | int | bool],
) -> tuple[str, tuple[str, ...]]:
    messages: list[str] = []
    delta_completed_laps = int(deltas["delta_completed_laps"])
    if delta_completed_laps < 0:
        verdict = "FUEL_SAVING_WITH_LAP_LOSS"
        messages.append(
            "ADDS saves simulated fuel, but it completes fewer laps within the fixed race duration."
        )
        if bool(deltas["adds_saves_pit_stop"]):
            messages.append(
                "The lower pit count is not a strategic win here because it is caused by completing fewer laps."
            )
    elif (
        abs(float(deltas["relative_fuel_change"])) < 0.1
        and delta_completed_laps == 0
        and int(deltas["delta_pit_stops"]) == 0
    ):
        verdict = "NEUTRAL_NO_BENEFIT"
        messages.append("ADDS is effectively neutral in this endurance extrapolation.")
    elif bool(deltas["adds_saves_pit_stop"]):
        verdict = "STRATEGIC_ADVANTAGE"
        messages.append("ADDS saves at least one simulated pit stop under the current endurance assumptions.")
    elif delta_completed_laps > 0:
        verdict = "DISTANCE_ADVANTAGE"
        messages.append("ADDS completes more laps within the fixed race duration.")
    elif bool(deltas["adds_strategy_advantage"]):
        verdict = "TIME_ADVANTAGE"
        messages.append("ADDS has a positive lap-equivalent time advantage without changing pit count.")
    else:
        verdict = "FUEL_ONLY_BENEFIT"
        messages.append("ADDS saves simulated fuel, but the current saving does not yet become a race-strategy advantage.")

    if thresholds.minimum_reference_stint_laps_for_one_extra_lap is None:
        messages.append("The current lap fuel result does not define a positive extra-stint-lap threshold.")
    elif thresholds.adds_gains_stint_lap_at_current_tank:
        messages.append(
            "The configured tank is large enough for ADDS to gain at least one additional lap per stint."
        )
    else:
        messages.append(
            "At the configured tank size, ADDS does not gain an extra stint lap; "
            f"the estimated threshold is {thresholds.minimum_reference_stint_laps_for_one_extra_lap} "
            "conventional-reference laps."
        )

    messages.append(
        f"Current stint lengths: Conventional {conventional.stint_laps} laps, ADDS {adds.stint_laps} laps."
    )
    return verdict, tuple(messages)


def _report_payload(report: EnduranceStrategyReport) -> dict[str, object]:
    return {
        "schema_version": report.schema_version,
        "config": asdict(report.config),
        "track_lap": {
            "track_name": report.track_lap.track_name,
            "adds_controller_kind": report.track_lap.adds_controller_kind,
            "scenario_id": report.track_lap.scenario.scenario_id,
        },
        "conventional": asdict(report.conventional),
        "adds": asdict(report.adds),
        "thresholds": asdict(report.thresholds),
        "deltas": report.deltas,
        "verdict": report.verdict,
        "interpretation": list(report.interpretation),
    }


def _vehicle_csv_row(strategy: EnduranceVehicleStrategy) -> dict[str, object]:
    data = asdict(strategy)
    return {
        key: data[key]
        for key in (
            "vehicle",
            "lap_time",
            "fuel_per_lap",
            "stint_laps",
            "pit_stops",
            "completed_laps",
            "elapsed_time",
            "remaining_time",
            "distance_km",
            "fuel_used",
        )
    }


def _relative_change(baseline: float, candidate: float) -> float:
    if baseline == 0.0:
        return 0.0 if candidate == 0.0 else float("inf")
    return 100.0 * (candidate - baseline) / baseline
