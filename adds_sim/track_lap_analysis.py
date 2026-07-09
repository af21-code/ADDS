"""Sector-level track-lap diagnostics for ADDS performance trade-offs."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .track_lap import (
    TrackLapComparison,
    TrackLapSection,
    reference_track_lap_sections,
    run_track_lap_comparison,
)


FUEL_SIGNIFICANCE_KG = 0.0005


@dataclass(frozen=True)
class TrackLapSector:
    """Distance-domain sector derived from the reference lap profile."""

    index: int
    name: str
    start_distance: float
    end_distance: float


@dataclass(frozen=True)
class TrackLapSectorResult:
    """Conventional-vs-ADDS result for one track-lap sector."""

    sector: TrackLapSector
    conventional_time: float
    adds_time: float
    delta_time: float
    conventional_fuel_kg: float
    adds_fuel_kg: float
    delta_fuel_kg: float
    relative_fuel_change: float
    adds_transitions: int
    adds_decoupled_duration: float
    verdict: str


@dataclass(frozen=True)
class TrackLapSectorAnalysis:
    """Sector-level diagnostic report for one reference track-lap comparison."""

    schema_version: str
    adds_controller_kind: str
    sectors: tuple[TrackLapSectorResult, ...]
    worst_time_loss_sector: TrackLapSectorResult | None
    best_fuel_saving_sector: TrackLapSectorResult | None
    recommendations: tuple[str, ...]


def reference_track_lap_sectors(
    lap_distance: float = 3_000.0,
    initial_speed: float = 32.0,
    sections: tuple[TrackLapSection, ...] | None = None,
) -> tuple[TrackLapSector, ...]:
    """Return distance-domain sectors scaled to the reference lap distance."""

    lap_sections = sections or reference_track_lap_sections()
    boundaries = [0.0]
    distance = 0.0
    previous_speed = initial_speed
    for section in lap_sections:
        distance += 0.5 * (previous_speed + section.target_speed_end) * section.duration
        boundaries.append(distance)
        previous_speed = section.target_speed_end

    scale = lap_distance / boundaries[-1] if boundaries[-1] > 0.0 else 1.0
    scaled = [point * scale for point in boundaries]
    scaled[-1] = lap_distance
    return tuple(
        TrackLapSector(
            index=index + 1,
            name=section.name,
            start_distance=scaled[index],
            end_distance=scaled[index + 1],
        )
        for index, section in enumerate(lap_sections)
    )


def build_track_lap_sector_analysis(
    comparison: TrackLapComparison | None = None,
    adds_controller_kind: str = "offline_optimized",
) -> TrackLapSectorAnalysis:
    """Build a sector-level diagnostic report for a track-lap comparison."""

    track_lap = comparison or run_track_lap_comparison(adds_controller_kind)
    lap_distance = float(track_lap.scenario.distance_limit or 0.0)
    sectors = reference_track_lap_sectors(lap_distance=lap_distance, sections=track_lap.sections)
    rows = tuple(_sector_result(track_lap, sector) for sector in sectors)
    time_loss_candidates = tuple(row for row in rows if row.delta_time > 0.0)
    fuel_saving_candidates = tuple(row for row in rows if row.delta_fuel_kg < 0.0)
    worst_time_loss = max(time_loss_candidates, key=lambda row: row.delta_time, default=None)
    best_fuel_saving = min(fuel_saving_candidates, key=lambda row: row.delta_fuel_kg, default=None)
    return TrackLapSectorAnalysis(
        schema_version="1.0",
        adds_controller_kind=track_lap.adds_controller_kind,
        sectors=rows,
        worst_time_loss_sector=worst_time_loss,
        best_fuel_saving_sector=best_fuel_saving,
        recommendations=_recommendations(rows, worst_time_loss, best_fuel_saving),
    )


def write_track_lap_sector_analysis(
    output_dir: Path,
    analysis: TrackLapSectorAnalysis,
) -> tuple[Path, Path]:
    """Write sector analysis JSON and CSV artifacts."""

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "track_lap_sector_analysis.json"
    csv_path = output_dir / "track_lap_sector_analysis.csv"

    with json_path.open("w", encoding="utf-8") as file:
        json.dump(_analysis_payload(analysis), file, indent=2)

    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=(
                "sector_index",
                "sector_name",
                "start_distance",
                "end_distance",
                "conventional_time",
                "adds_time",
                "delta_time",
                "conventional_fuel_kg",
                "adds_fuel_kg",
                "delta_fuel_kg",
                "relative_fuel_change",
                "adds_transitions",
                "adds_decoupled_duration",
                "verdict",
            ),
        )
        writer.writeheader()
        for row in analysis.sectors:
            writer.writerow(_sector_csv_row(row))
    return json_path, csv_path


def _sector_result(
    track_lap: TrackLapComparison,
    sector: TrackLapSector,
) -> TrackLapSectorResult:
    conventional_records = track_lap.comparison.conventional_result.records
    adds_records = track_lap.comparison.adds_result.records
    conventional_start_time = _interpolated_at_distance(conventional_records, sector.start_distance, "time")
    conventional_end_time = _interpolated_at_distance(conventional_records, sector.end_distance, "time")
    adds_start_time = _interpolated_at_distance(adds_records, sector.start_distance, "time")
    adds_end_time = _interpolated_at_distance(adds_records, sector.end_distance, "time")
    conventional_start_fuel = _interpolated_at_distance(conventional_records, sector.start_distance, "engine_fuel_used")
    conventional_end_fuel = _interpolated_at_distance(conventional_records, sector.end_distance, "engine_fuel_used")
    adds_start_fuel = _interpolated_at_distance(adds_records, sector.start_distance, "engine_fuel_used")
    adds_end_fuel = _interpolated_at_distance(adds_records, sector.end_distance, "engine_fuel_used")

    conventional_time = conventional_end_time - conventional_start_time
    adds_time = adds_end_time - adds_start_time
    conventional_fuel_kg = conventional_end_fuel - conventional_start_fuel
    adds_fuel_kg = adds_end_fuel - adds_start_fuel
    delta_time = adds_time - conventional_time
    delta_fuel_kg = adds_fuel_kg - conventional_fuel_kg
    return TrackLapSectorResult(
        sector=sector,
        conventional_time=conventional_time,
        adds_time=adds_time,
        delta_time=delta_time,
        conventional_fuel_kg=conventional_fuel_kg,
        adds_fuel_kg=adds_fuel_kg,
        delta_fuel_kg=delta_fuel_kg,
        relative_fuel_change=_relative_change(conventional_fuel_kg, adds_fuel_kg),
        adds_transitions=_transition_count_in_sector(adds_records, sector),
        adds_decoupled_duration=_mode_duration_in_sector(adds_records, sector, "DECOUPLED"),
        verdict=_sector_verdict(delta_time, delta_fuel_kg),
    )


def _interpolated_at_distance(
    records: tuple[dict[str, float | int | str | bool], ...],
    distance: float,
    field: str,
) -> float:
    if not records:
        return 0.0
    if distance <= 0.0 and field in {"time", "engine_fuel_used"}:
        return 0.0
    if distance <= float(records[0]["position"]):
        return float(records[0][field])
    if distance >= float(records[-1]["position"]):
        return float(records[-1][field])

    for previous, current in zip(records[:-1], records[1:]):
        previous_position = float(previous["position"])
        current_position = float(current["position"])
        if previous_position <= distance <= current_position:
            span = max(current_position - previous_position, 1e-12)
            fraction = (distance - previous_position) / span
            return float(previous[field]) + (float(current[field]) - float(previous[field])) * fraction
    return float(records[-1][field])


def _transition_count_in_sector(
    records: tuple[dict[str, float | int | str | bool], ...],
    sector: TrackLapSector,
) -> int:
    transitions = 0
    for previous, current in zip(records[:-1], records[1:]):
        position = float(current["position"])
        if sector.start_distance <= position <= sector.end_distance and current["coupling_mode"] != previous["coupling_mode"]:
            transitions += 1
    return transitions


def _mode_duration_in_sector(
    records: tuple[dict[str, float | int | str | bool], ...],
    sector: TrackLapSector,
    mode: str,
) -> float:
    duration = 0.0
    for previous, current in zip(records[:-1], records[1:]):
        midpoint = 0.5 * (float(previous["position"]) + float(current["position"]))
        if sector.start_distance <= midpoint <= sector.end_distance and str(current["coupling_mode"]) == mode:
            duration += max(0.0, float(current["time"]) - float(previous["time"]))
    return duration


def _sector_verdict(delta_time: float, delta_fuel_kg: float) -> str:
    if delta_time > 0.05 and delta_fuel_kg < -FUEL_SIGNIFICANCE_KG:
        return "FUEL_SAVED_WITH_TIME_LOSS"
    if delta_time <= 0.05 and delta_fuel_kg < -FUEL_SIGNIFICANCE_KG:
        return "PRODUCTIVE_SAVING"
    if delta_time > 0.05 and delta_fuel_kg >= -FUEL_SIGNIFICANCE_KG:
        return "TIME_LOSS_WITHOUT_SAVING"
    return "NEUTRAL"


def _recommendations(
    rows: tuple[TrackLapSectorResult, ...],
    worst_time_loss: TrackLapSectorResult | None,
    best_fuel_saving: TrackLapSectorResult | None,
) -> tuple[str, ...]:
    recommendations: list[str] = []
    costly_saving = tuple(row for row in rows if row.verdict == "FUEL_SAVED_WITH_TIME_LOSS")
    if costly_saving:
        worst = max(costly_saving, key=lambda row: row.delta_time)
        recommendations.append(
            f"Prioritize sector {worst.sector.index} ({worst.sector.name}): it saves "
            f"{abs(worst.delta_fuel_kg) * 1_000.0:.2f} g but costs {worst.delta_time:.3f} s."
        )
    if worst_time_loss is not None:
        recommendations.append(
            f"Use {worst_time_loss.sector.name} as the lap-time penalty regression test."
        )
    if best_fuel_saving is not None:
        recommendations.append(
            f"Keep {best_fuel_saving.sector.name} as the fuel-saving opportunity benchmark."
        )
    if not recommendations:
        recommendations.append("No sector-level ADDS penalty was detected in the current comparison.")
    return tuple(recommendations)


def _analysis_payload(analysis: TrackLapSectorAnalysis) -> dict[str, object]:
    return {
        "schema_version": analysis.schema_version,
        "adds_controller_kind": analysis.adds_controller_kind,
        "sectors": [_sector_payload(row) for row in analysis.sectors],
        "worst_time_loss_sector": (
            _sector_payload(analysis.worst_time_loss_sector)
            if analysis.worst_time_loss_sector is not None
            else None
        ),
        "best_fuel_saving_sector": (
            _sector_payload(analysis.best_fuel_saving_sector)
            if analysis.best_fuel_saving_sector is not None
            else None
        ),
        "recommendations": list(analysis.recommendations),
    }


def _sector_payload(row: TrackLapSectorResult) -> dict[str, object]:
    data = asdict(row)
    data["sector"] = asdict(row.sector)
    return data


def _sector_csv_row(row: TrackLapSectorResult) -> dict[str, object]:
    return {
        "sector_index": row.sector.index,
        "sector_name": row.sector.name,
        "start_distance": row.sector.start_distance,
        "end_distance": row.sector.end_distance,
        "conventional_time": row.conventional_time,
        "adds_time": row.adds_time,
        "delta_time": row.delta_time,
        "conventional_fuel_kg": row.conventional_fuel_kg,
        "adds_fuel_kg": row.adds_fuel_kg,
        "delta_fuel_kg": row.delta_fuel_kg,
        "relative_fuel_change": row.relative_fuel_change,
        "adds_transitions": row.adds_transitions,
        "adds_decoupled_duration": row.adds_decoupled_duration,
        "verdict": row.verdict,
    }


def _relative_change(baseline: float, candidate: float) -> float:
    if baseline == 0.0:
        return 0.0 if candidate == 0.0 else float("inf")
    return 100.0 * (candidate - baseline) / baseline
