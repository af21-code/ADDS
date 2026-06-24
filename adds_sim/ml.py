"""Lightweight behavioral cloning for ADDS high-level mode decisions."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .benchmarks import with_adds_enabled
from .controllers import RuleBasedADDSController
from .scenario_catalog import ScenarioCatalogEntry
from .simulator import LongitudinalSimulator


@dataclass(frozen=True)
class ImitationExample:
    """One expert mode decision sample."""

    scenario_id: str
    split: str
    time: float
    vehicle_speed: float
    speed_error: float
    target_speed: float
    target_speed_preview: float
    coast_predicted_speed: float
    road_grade: float
    coupling_mode: str
    requested_mode: str


@dataclass(frozen=True)
class BehavioralCloningModel:
    """Interpretable threshold model cloned from rule-based ADDS behavior."""

    model_type: str
    schema_version: str
    training_examples: int
    training_scenarios: tuple[str, ...]
    coast_speed_margin: float
    reconnect_speed_margin: float
    source_controller: str

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "BehavioralCloningModel":
        data = json.loads(path.read_text(encoding="utf-8"))
        data["training_scenarios"] = tuple(data["training_scenarios"])
        return cls(**data)


@dataclass(frozen=True)
class TrainingReport:
    """Summary of a behavioral cloning training run."""

    model: BehavioralCloningModel
    label_counts: dict[str, int]


def collect_imitation_examples(
    simulator: LongitudinalSimulator,
    entries: tuple[ScenarioCatalogEntry, ...],
    expert_factory=RuleBasedADDSController,
) -> tuple[ImitationExample, ...]:
    """Collect expert mode requests from complete scenario trajectories."""

    examples: list[ImitationExample] = []
    for entry in entries:
        scenario = with_adds_enabled(entry.scenario, True)
        expert = expert_factory(scenario.initial_gear)
        result = simulator.run(scenario, expert)
        for record in result.records:
            preview_horizon = float(record["target_speed_preview_horizon"])
            force_to_hold_speed = (
                float(record["aero_force"])
                + float(record["rolling_resistance_force"])
                + float(record["grade_force"])
            )
            natural_deceleration = max(force_to_hold_speed, 0.0) / simulator.config.vehicle.mass
            examples.append(
                ImitationExample(
                    scenario_id=scenario.scenario_id,
                    split=entry.split,
                    time=float(record["time"]),
                    vehicle_speed=float(record["vehicle_speed"]),
                    speed_error=float(record["speed_error"]),
                    target_speed=float(record["target_speed"]),
                    target_speed_preview=float(record["target_speed_preview"]),
                    coast_predicted_speed=max(
                        0.0,
                        float(record["vehicle_speed"]) - natural_deceleration * preview_horizon,
                    ),
                    road_grade=float(record["road_grade"]),
                    coupling_mode=str(record["coupling_mode"]),
                    requested_mode=str(record["requested_mode"]),
                )
            )
    return tuple(examples)


def train_behavioral_cloning_model(examples: tuple[ImitationExample, ...]) -> TrainingReport:
    """Fit an interpretable threshold policy from expert examples."""

    if not examples:
        raise ValueError("cannot train behavioral cloning model without examples")

    label_counts: dict[str, int] = {}
    for example in examples:
        label_counts[example.requested_mode] = label_counts.get(example.requested_mode, 0) + 1

    decoupling_examples = [
        example
        for example in examples
        if example.coupling_mode == "CONNECTED" and example.requested_mode == "DECOUPLING"
    ]
    predicted_errors = [
        example.coast_predicted_speed - example.target_speed_preview
        for example in decoupling_examples
    ]
    coast_speed_margin = max(predicted_errors, default=0.4)
    reconnect_speed_margin = max((-error for error in predicted_errors), default=0.1)

    model = BehavioralCloningModel(
        model_type="threshold_behavioral_cloning",
        schema_version="2.0",
        training_examples=len(examples),
        training_scenarios=tuple(sorted({example.scenario_id for example in examples})),
        coast_speed_margin=max(0.0, coast_speed_margin),
        reconnect_speed_margin=max(0.0, reconnect_speed_margin),
        source_controller="rule_based_adds",
    )
    return TrainingReport(model=model, label_counts=label_counts)
