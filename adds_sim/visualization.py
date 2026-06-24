"""Dashboard-oriented comparison helpers for ADDS visualization prototypes."""

from __future__ import annotations

from dataclasses import dataclass

from .comparison import PairedComparisonResult, run_paired_comparison
from .controllers import ConventionalBaselineController, RuleBasedADDSController
from .defaults import default_simulation_config
from .learned_controller import LearnedADDSController
from .ml import collect_imitation_examples, train_behavioral_cloning_model
from .robustness import (
    apply_perturbation_to_config,
    apply_perturbation_to_scenario,
    default_perturbations,
)
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
    verdict: "DashboardVerdict"
    insights: tuple["DashboardInsight", ...]
    mode_durations: tuple["DashboardModeDuration", ...]
    mode_transitions: tuple["DashboardModeTransition", ...]


@dataclass(frozen=True)
class DashboardEvaluationThresholds:
    """Conservative gates for accepting a simulated efficiency benefit."""

    minimum_fuel_reduction_percent: float = 1.0
    maximum_rms_speed_error_increase_kmh: float = 1.0
    maximum_safety_overrides: int = 0


@dataclass(frozen=True)
class DashboardVerdict:
    """Research-level decision derived from paired-comparison gates."""

    code: str
    title: str
    severity: str
    efficiency_claim_accepted: bool
    reasons: tuple[str, ...]
    thresholds: DashboardEvaluationThresholds


@dataclass(frozen=True)
class DashboardInsight:
    """Human-readable interpretation of one comparison result."""

    severity: str
    title: str
    message: str


@dataclass(frozen=True)
class DashboardModeDuration:
    """Time spent in one ADDS coupling mode."""

    mode: str
    duration: float
    duration_percent: float


@dataclass(frozen=True)
class DashboardModeTransition:
    """One detected ADDS coupling-mode transition."""

    transition_index: int
    time: float
    from_mode: str
    to_mode: str
    speed_kmh: float
    engine_speed_rpm: float
    coupling_slip_speed: float
    coupling_slip_energy: float


@dataclass(frozen=True)
class DashboardCatalogRow:
    """One scenario-level row for the dashboard catalog summary."""

    scenario_id: str
    split: str
    description: str
    adds_controller_kind: str
    fuel_delta_ml: float
    relative_fuel_change: float
    rms_speed_error_delta_kmh: float
    adds_transitions: int
    adds_safety_overrides: int
    constraint_regression: bool
    verdict_code: str
    efficiency_claim_accepted: bool


@dataclass(frozen=True)
class DashboardSensitivityRow:
    """One dashboard-ready scenario result under a parameter perturbation."""

    perturbation: str
    mass_scale: float
    drag_scale: float
    rolling_resistance_scale: float
    tire_friction_scale: float
    grade_offset_percent: float
    relative_fuel_change: float
    rms_speed_error_delta_kmh: float
    adds_transitions: int
    adds_safety_overrides: int
    constraint_regression: bool
    verdict_code: str
    efficiency_claim_accepted: bool


@dataclass(frozen=True)
class DashboardSensitivitySummary:
    """Sensitivity envelope for one scenario and ADDS controller."""

    scenario_id: str
    adds_controller_kind: str
    accepted_runs: int
    total_runs: int
    acceptance_rate_percent: float
    best_relative_fuel_change: float
    worst_relative_fuel_change: float
    maximum_rms_speed_error_delta_kmh: float
    rows: tuple[DashboardSensitivityRow, ...]


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
    verdict = evaluate_dashboard_comparison(comparison)
    return DashboardComparison(
        scenario=scenario,
        adds_controller_kind=adds_controller_kind,
        comparison=comparison,
        conventional_records=records_for_dashboard(comparison.conventional_result, "Conventional"),
        adds_records=records_for_dashboard(comparison.adds_result, "ADDS"),
        metric_cards=metric_cards_for_dashboard(comparison),
        verdict=verdict,
        insights=insights_for_dashboard(comparison),
        mode_durations=mode_duration_rows(comparison.adds_result.records),
        mode_transitions=mode_transition_rows(comparison.adds_result.records),
    )


def build_dashboard_catalog_summary(
    adds_controller_kind: str = "rule_based",
    entries: tuple[ScenarioCatalogEntry, ...] | None = None,
) -> tuple[DashboardCatalogRow, ...]:
    """Run all catalog scenarios and return compact dashboard summary rows."""

    catalog = entries or phase4_scenario_catalog()
    rows: list[DashboardCatalogRow] = []
    for entry in catalog:
        comparison = build_dashboard_comparison(
            scenario_id=entry.scenario.scenario_id,
            adds_controller_kind=adds_controller_kind,
            entries=catalog,
        )
        verdict = comparison.verdict
        rows.append(
            DashboardCatalogRow(
                scenario_id=entry.scenario.scenario_id,
                split=entry.split,
                description=entry.description,
                adds_controller_kind=adds_controller_kind,
                fuel_delta_ml=float(comparison.comparison.deltas["delta_fuel_used"]) * 1_000_000.0,
                relative_fuel_change=float(comparison.comparison.deltas["relative_fuel_change"]),
                rms_speed_error_delta_kmh=float(comparison.comparison.deltas["delta_rms_speed_error"]) * 3.6,
                adds_transitions=int(comparison.comparison.adds_summary["mode_transition_count"]),
                adds_safety_overrides=int(comparison.comparison.adds_summary["safety_override_count"]),
                constraint_regression=bool(comparison.comparison.deltas["constraint_regression"]),
                verdict_code=verdict.code,
                efficiency_claim_accepted=verdict.efficiency_claim_accepted,
            )
        )
    return tuple(rows)


def build_dashboard_sensitivity(
    scenario_id: str,
    adds_controller_kind: str = "rule_based",
    entries: tuple[ScenarioCatalogEntry, ...] | None = None,
) -> DashboardSensitivitySummary:
    """Evaluate one scenario across the default deterministic uncertainty envelope."""

    catalog = entries or phase4_scenario_catalog()
    entry = _find_entry(catalog, scenario_id)
    base_config = default_simulation_config()
    learned_model = None
    if adds_controller_kind == "learned":
        training_entries = tuple(item for item in catalog if item.split == "train")
        training_simulator = LongitudinalSimulator(base_config)
        examples = collect_imitation_examples(training_simulator, training_entries)
        learned_model = train_behavioral_cloning_model(examples).model
    elif adds_controller_kind != "rule_based":
        raise ValueError(f"unknown adds_controller_kind: {adds_controller_kind}")

    rows: list[DashboardSensitivityRow] = []
    for perturbation in default_perturbations():
        config = apply_perturbation_to_config(base_config, perturbation)
        scenario = apply_perturbation_to_scenario(entry.scenario, perturbation)
        simulator = LongitudinalSimulator(config)
        conventional_controller = ConventionalBaselineController(scenario.initial_gear)
        if adds_controller_kind == "rule_based":
            adds_controller = RuleBasedADDSController(scenario.initial_gear)
        else:
            adds_controller = LearnedADDSController(
                gear=scenario.initial_gear,
                model=learned_model,
            )
        comparison = run_paired_comparison(
            simulator=simulator,
            scenario=scenario,
            conventional_controller=conventional_controller,
            adds_controller=adds_controller,
        )
        verdict = evaluate_dashboard_comparison(comparison)
        rows.append(
            DashboardSensitivityRow(
                perturbation=perturbation.name,
                mass_scale=perturbation.mass_scale,
                drag_scale=perturbation.drag_scale,
                rolling_resistance_scale=perturbation.rolling_resistance_scale,
                tire_friction_scale=perturbation.tire_friction_scale,
                grade_offset_percent=perturbation.grade_offset * 100.0,
                relative_fuel_change=float(comparison.deltas["relative_fuel_change"]),
                rms_speed_error_delta_kmh=float(comparison.deltas["delta_rms_speed_error"]) * 3.6,
                adds_transitions=int(comparison.adds_summary["mode_transition_count"]),
                adds_safety_overrides=int(comparison.adds_summary["safety_override_count"]),
                constraint_regression=bool(comparison.deltas["constraint_regression"]),
                verdict_code=verdict.code,
                efficiency_claim_accepted=verdict.efficiency_claim_accepted,
            )
        )

    accepted_runs = sum(1 for row in rows if row.efficiency_claim_accepted)
    return DashboardSensitivitySummary(
        scenario_id=scenario_id,
        adds_controller_kind=adds_controller_kind,
        accepted_runs=accepted_runs,
        total_runs=len(rows),
        acceptance_rate_percent=100.0 * accepted_runs / len(rows) if rows else 0.0,
        best_relative_fuel_change=min((row.relative_fuel_change for row in rows), default=0.0),
        worst_relative_fuel_change=max((row.relative_fuel_change for row in rows), default=0.0),
        maximum_rms_speed_error_delta_kmh=max(
            (row.rms_speed_error_delta_kmh for row in rows),
            default=0.0,
        ),
        rows=tuple(rows),
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


def evaluate_dashboard_comparison(
    comparison: PairedComparisonResult,
    thresholds: DashboardEvaluationThresholds | None = None,
) -> DashboardVerdict:
    """Apply explicit comparability gates before accepting an efficiency claim."""

    gates = thresholds or DashboardEvaluationThresholds()
    relative_fuel_change = float(comparison.deltas["relative_fuel_change"])
    rms_speed_error_delta_kmh = float(comparison.deltas["delta_rms_speed_error"]) * 3.6
    safety_overrides = int(comparison.adds_summary["safety_override_count"])
    constraint_regression = bool(comparison.deltas["constraint_regression"])

    if constraint_regression or safety_overrides > gates.maximum_safety_overrides:
        reasons: list[str] = []
        if constraint_regression:
            reasons.append("ADDS introduced a hard-constraint regression relative to the baseline.")
        if safety_overrides > gates.maximum_safety_overrides:
            reasons.append(
                f"ADDS logged {safety_overrides} safety overrides; the acceptance limit is "
                f"{gates.maximum_safety_overrides}."
            )
        return DashboardVerdict(
            code="REJECTED_SAFETY",
            title="Efficiency claim rejected",
            severity="negative",
            efficiency_claim_accepted=False,
            reasons=tuple(reasons),
            thresholds=gates,
        )

    speed_is_comparable = rms_speed_error_delta_kmh <= gates.maximum_rms_speed_error_increase_kmh
    fuel_benefit_is_meaningful = relative_fuel_change <= -gates.minimum_fuel_reduction_percent

    if fuel_benefit_is_meaningful and speed_is_comparable:
        return DashboardVerdict(
            code="ACCEPTABLE_BENEFIT",
            title="Comparable simulated benefit",
            severity="positive",
            efficiency_claim_accepted=True,
            reasons=(
                f"Fuel use improved by {-relative_fuel_change:.2f}%, meeting the "
                f"{gates.minimum_fuel_reduction_percent:.2f}% minimum.",
                f"RMS speed-error increase was {rms_speed_error_delta_kmh:.2f} km/h, within "
                f"the {gates.maximum_rms_speed_error_increase_kmh:.2f} km/h limit.",
                "No safety override or hard-constraint regression was recorded.",
            ),
            thresholds=gates,
        )

    if not speed_is_comparable:
        return DashboardVerdict(
            code="TRADE_OFF_REQUIRES_REVIEW",
            title="Trade-off requires review",
            severity="caution",
            efficiency_claim_accepted=False,
            reasons=(
                f"RMS speed error increased by {rms_speed_error_delta_kmh:.2f} km/h, above "
                f"the {gates.maximum_rms_speed_error_increase_kmh:.2f} km/h comparability limit.",
                "Any fuel reduction is therefore not accepted as a comparable efficiency benefit.",
            ),
            thresholds=gates,
        )

    return DashboardVerdict(
        code="NO_MEANINGFUL_BENEFIT",
        title="No meaningful simulated benefit",
        severity="neutral",
        efficiency_claim_accepted=False,
        reasons=(
            f"Fuel change was {relative_fuel_change:.2f}%; acceptance requires at least "
            f"{gates.minimum_fuel_reduction_percent:.2f}% reduction.",
            "Mobility and safety gates remained within their initial limits.",
        ),
        thresholds=gates,
    )


def insights_for_dashboard(
    comparison: PairedComparisonResult,
) -> tuple[DashboardInsight, ...]:
    """Return concise interpretation notes for one dashboard comparison."""

    deltas = comparison.deltas
    adds = comparison.adds_summary
    relative_fuel_change = float(deltas["relative_fuel_change"])
    rms_speed_error_delta_kmh = float(deltas["delta_rms_speed_error"]) * 3.6
    transitions = int(adds["mode_transition_count"])
    safety_overrides = int(adds["safety_override_count"])
    constraint_regression = bool(deltas["constraint_regression"])
    mode_durations = mode_durations_seconds(comparison.adds_result.records)
    decoupled_time = mode_durations.get("DECOUPLED", 0.0)

    insights: list[DashboardInsight] = []
    if relative_fuel_change <= -1.0:
        insights.append(
            DashboardInsight(
                severity="positive",
                title="ADDS reduced simulated fuel use",
                message=(
                    f"Fuel use changed by {relative_fuel_change:.2f}% versus the "
                    "conventional baseline on the same scenario."
                ),
            )
        )
    elif relative_fuel_change >= 1.0:
        insights.append(
            DashboardInsight(
                severity="caution",
                title="ADDS increased simulated fuel use",
                message=(
                    f"Fuel use changed by {relative_fuel_change:.2f}%. This scenario "
                    "should be treated as unfavorable for the current ADDS policy."
                ),
            )
        )
    else:
        insights.append(
            DashboardInsight(
                severity="neutral",
                title="Fuel result is effectively neutral",
                message="The simulated fuel delta is within +/-1%, so the current result is not a clear efficiency win.",
            )
        )

    if transitions > 0:
        insights.append(
            DashboardInsight(
                severity="neutral",
                title="ADDS changed drivetrain state",
                message=(
                    f"The ADDS controller made {transitions} mode transitions and "
                    f"spent {decoupled_time:.2f} seconds fully decoupled."
                ),
            )
        )
    else:
        insights.append(
            DashboardInsight(
                severity="neutral",
                title="ADDS stayed connected",
                message="The adaptive drivetrain did not transition, so behavior can match the conventional baseline closely.",
            )
        )

    if rms_speed_error_delta_kmh > 1.0:
        insights.append(
            DashboardInsight(
                severity="caution",
                title="Speed tracking degraded",
                message=(
                    f"RMS speed error increased by {rms_speed_error_delta_kmh:.2f} km/h. "
                    "This is useful context before treating a fuel saving as acceptable."
                ),
            )
        )
    else:
        insights.append(
            DashboardInsight(
                severity="positive",
                title="Speed tracking remained comparable",
                message=f"RMS speed error delta is {rms_speed_error_delta_kmh:.2f} km/h.",
            )
        )

    if safety_overrides or constraint_regression:
        insights.append(
            DashboardInsight(
                severity="caution",
                title="Safety or constraint signal present",
                message=(
                    f"Safety overrides: {safety_overrides}; constraint regression: "
                    f"{constraint_regression}."
                ),
            )
        )
    else:
        insights.append(
            DashboardInsight(
                severity="positive",
                title="No safety override in this simulation",
                message="The run completed without logged safety overrides or constraint regression.",
            )
        )

    return tuple(insights)


def mode_durations_seconds(
    records: tuple[dict[str, float | int | str | bool], ...],
) -> dict[str, float]:
    """Estimate time spent in each coupling mode from sampled records."""

    durations = {mode: 0.0 for mode in MODE_ORDER}
    if not records:
        return durations

    previous_time = 0.0
    for record in records:
        current_time = float(record["time"])
        dt = max(0.0, current_time - previous_time)
        mode = str(record["coupling_mode"])
        durations[mode] = durations.get(mode, 0.0) + dt
        previous_time = current_time
    return durations


def mode_duration_rows(
    records: tuple[dict[str, float | int | str | bool], ...],
) -> tuple[DashboardModeDuration, ...]:
    """Return mode durations as ordered dashboard rows."""

    durations = mode_durations_seconds(records)
    total_time = sum(durations.values())
    rows: list[DashboardModeDuration] = []
    for mode in MODE_ORDER:
        duration = durations.get(mode, 0.0)
        rows.append(
            DashboardModeDuration(
                mode=mode,
                duration=duration,
                duration_percent=100.0 * duration / total_time if total_time > 0.0 else 0.0,
            )
        )
    return tuple(rows)


def mode_transition_rows(
    records: tuple[dict[str, float | int | str | bool], ...],
) -> tuple[DashboardModeTransition, ...]:
    """Return detected coupling-mode transitions from sampled ADDS records."""

    if not records:
        return ()

    transitions: list[DashboardModeTransition] = []
    previous_mode = str(records[0].get("previous_coupling_mode", records[0]["coupling_mode"]))
    for record in records:
        current_mode = str(record["coupling_mode"])
        if current_mode == previous_mode:
            continue
        transitions.append(
            DashboardModeTransition(
                transition_index=int(record["transition_count"]),
                time=float(record["time"]),
                from_mode=previous_mode,
                to_mode=current_mode,
                speed_kmh=float(record["vehicle_speed"]) * 3.6,
                engine_speed_rpm=float(record["engine_speed"]) * 60.0 / (2.0 * 3.141592653589793),
                coupling_slip_speed=float(record["coupling_slip_speed"]),
                coupling_slip_energy=float(record["coupling_slip_energy"]),
            )
        )
        previous_mode = current_mode
    return tuple(transitions)


def _find_entry(
    entries: tuple[ScenarioCatalogEntry, ...],
    scenario_id: str,
) -> ScenarioCatalogEntry:
    for entry in entries:
        if entry.scenario.scenario_id == scenario_id:
            return entry
    raise ValueError(f"unknown scenario_id: {scenario_id}")
