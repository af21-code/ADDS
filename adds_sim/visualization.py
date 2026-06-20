"""Dashboard-oriented comparison helpers for ADDS visualization prototypes."""

from __future__ import annotations

from dataclasses import dataclass

from .comparison import PairedComparisonResult, run_paired_comparison
from .controllers import ConventionalBaselineController, RuleBasedADDSController
from .defaults import default_simulation_config
from .learned_controller import LearnedADDSController
from .ml import collect_imitation_examples, train_behavioral_cloning_model
from .scenario_catalog import ScenarioCatalogEntry, phase4_scenario_catalog
from .simulator import LongitudinalSimulator, SimulationResult


MODE_ORDER = (
    "CONNECTED",
    "DECOUPLING",
    "DECOUPLED",
    "REV_MATCHING",
    "REENGAGING",
    "FAULT_SAFE",
)
MODE_TO_INDEX = {mode: index for index, mode in enumerate(MODE_ORDER)}


@dataclass(frozen=True)
class DashboardScenarioOption:
    """Scenario metadata exposed to the Streamlit prototype."""

    scenario_id: str
    split: str
    description: str
    tags: tuple[str, ...]


@dataclass(frozen=True)
class DashboardComparison:
    """One dashboard-ready conventional-vs-ADDS comparison."""

    scenario: DashboardScenarioOption
    adds_controller_kind: str
    comparison: PairedComparisonResult
    conventional_records: tuple[dict[str, float | int | str | bool], ...]
    adds_records: tuple[dict[str, float | int | str | bool], ...]
    metric_cards: tuple[dict[str, float | int | str | bool], ...]


def available_dashboard_scenarios(
    entries: tuple[ScenarioCatalogEntry, ...] | None = None,
) -> tuple[DashboardScenarioOption, ...]:
    """Return scenario choices in a UI-friendly, stable order."""

    catalog = entries or phase4_scenario_catalog()
    return tuple(
        DashboardScenarioOption(
            scenario_id=entry.scenario.scenario_id,
            split=entry.split,
            description=entry.description,
            tags=entry.tags,
        )
        for entry in catalog
    )


def build_dashboard_comparison(
    scenario_id: str,
    adds_controller_kind: str = "rule_based",
    entries: tuple[ScenarioCatalogEntry, ...] | None = None,
) -> DashboardComparison:
    """Run and package one comparison for the dashboard prototype."""

    catalog = entries or phase4_scenario_catalog()
    entry = _find_entry(catalog, scenario_id)
    simulator = LongitudinalSimulator(default_simulation_config())
    conventional_controller = ConventionalBaselineController(entry.scenario.initial_gear)

    if adds_controller_kind == "rule_based":
        adds_controller = RuleBasedADDSController(entry.scenario.initial_gear)
    elif adds_controller_kind == "learned":
        training_entries = tuple(item for item in catalog if item.split == "train")
        examples = collect_imitation_examples(simulator, training_entries)
        model = train_behavioral_cloning_model(examples).model
        adds_controller = LearnedADDSController(gear=entry.scenario.initial_gear, model=model)
    else:
        raise ValueError(f"unknown adds_controller_kind: {adds_controller_kind}")

    comparison = run_paired_comparison(
        simulator=simulator,
        scenario=entry.scenario,
        conventional_controller=conventional_controller,
        adds_controller=adds_controller,
    )

    scenario = DashboardScenarioOption(
        scenario_id=entry.scenario.scenario_id,
        split=entry.split,
        description=entry.description,
        tags=entry.tags,
    )
    return DashboardComparison(
        scenario=scenario,
        adds_controller_kind=adds_controller_kind,
        comparison=comparison,
        conventional_records=records_for_dashboard(comparison.conventional_result, "Conventional"),
        adds_records=records_for_dashboard(comparison.adds_result, "ADDS"),
        metric_cards=metric_cards_for_dashboard(comparison),
    )


def records_for_dashboard(
    result: SimulationResult,
    vehicle_label: str,
) -> tuple[dict[str, float | int | str | bool], ...]:
    """Add UI labels and display units without mutating simulator records."""

    records: list[dict[str, float | int | str | bool]] = []
    for record in result.records:
        enriched = dict(record)
        mode = str(record["coupling_mode"])
        enriched["vehicle"] = vehicle_label
        enriched["coupling_mode_index"] = MODE_TO_INDEX.get(mode, -1)
        enriched["fuel_used_ml"] = float(record["engine_fuel_used"]) * 1_000_000.0
        enriched["speed_kmh"] = float(record["vehicle_speed"]) * 3.6
        enriched["target_speed_kmh"] = float(record["target_speed"]) * 3.6
        enriched["engine_speed_rpm"] = float(record["engine_speed"]) * 60.0 / (2.0 * 3.141592653589793)
        enriched["synchronous_engine_speed_rpm"] = float(record["synchronous_engine_speed"]) * 60.0 / (2.0 * 3.141592653589793)
        records.append(enriched)
    return tuple(records)


def metric_cards_for_dashboard(
    comparison: PairedComparisonResult,
) -> tuple[dict[str, float | int | str | bool], ...]:
    """Return compact metric cards for the Streamlit overview."""

    deltas = comparison.deltas
    conventional = comparison.conventional_summary
    adds = comparison.adds_summary
    return (
        {
            "label": "Fuel delta",
            "value": float(deltas["delta_fuel_used"]) * 1_000_000.0,
            "unit": "ml",
            "direction": "lower_is_better",
        },
        {
            "label": "Relative fuel change",
            "value": float(deltas["relative_fuel_change"]),
            "unit": "%",
            "direction": "lower_is_better",
        },
        {
            "label": "RMS speed error delta",
            "value": float(deltas["delta_rms_speed_error"]) * 3.6,
            "unit": "km/h",
            "direction": "lower_is_better",
        },
        {
            "label": "ADDS transitions",
            "value": int(adds["mode_transition_count"]),
            "unit": "count",
            "direction": "context",
        },
        {
            "label": "ADDS safety overrides",
            "value": int(adds["safety_override_count"]),
            "unit": "count",
            "direction": "lower_is_better",
        },
        {
            "label": "Constraint regression",
            "value": bool(deltas["constraint_regression"]),
            "unit": "",
            "direction": "lower_is_better",
        },
        {
            "label": "Conventional fuel",
            "value": float(conventional["fuel_used"]) * 1_000_000.0,
            "unit": "ml",
            "direction": "context",
        },
        {
            "label": "ADDS fuel",
            "value": float(adds["fuel_used"]) * 1_000_000.0,
            "unit": "ml",
            "direction": "context",
        },
    )


def _find_entry(
    entries: tuple[ScenarioCatalogEntry, ...],
    scenario_id: str,
) -> ScenarioCatalogEntry:
    for entry in entries:
        if entry.scenario.scenario_id == scenario_id:
            return entry
    raise ValueError(f"unknown scenario_id: {scenario_id}")
