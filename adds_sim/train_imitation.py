"""Train and evaluate the initial imitation-learning ADDS controller."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from .benchmarks import with_adds_enabled
from .comparison import run_paired_comparison
from .controllers import ConventionalBaselineController, RuleBasedADDSController
from .defaults import default_simulation_config
from .learned_controller import LearnedADDSController
from .metrics import summarize_run
from .ml import collect_imitation_examples, train_behavioral_cloning_model
from .scenario_catalog import entries_by_split, phase4_scenario_catalog
from .simulator import LongitudinalSimulator


@dataclass(frozen=True)
class ImitationTrainingArtifacts:
    """Paths produced by an imitation-training run."""

    output_dir: Path
    checkpoint_path: Path
    training_report_path: Path
    evaluation_report_path: Path


def train_and_evaluate_imitation(output_dir: Path) -> ImitationTrainingArtifacts:
    """Train on the catalog train split and evaluate on held-out splits."""

    output_dir.mkdir(parents=True, exist_ok=True)
    simulator = LongitudinalSimulator(default_simulation_config())
    grouped = entries_by_split(phase4_scenario_catalog())
    train_entries = grouped["train"]
    examples = collect_imitation_examples(simulator, train_entries)
    report = train_behavioral_cloning_model(examples)

    checkpoint_path = output_dir / "learned_adds_thresholds.json"
    training_report_path = output_dir / "training_report.json"
    evaluation_report_path = output_dir / "evaluation_report.json"
    report.model.save(checkpoint_path)
    training_report_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "training_examples": report.model.training_examples,
                "training_scenarios": report.model.training_scenarios,
                "label_counts": report.label_counts,
                "checkpoint": str(checkpoint_path),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    evaluation_rows = []
    for split, entries in grouped.items():
        if split == "train":
            continue
        for entry in entries:
            scenario = with_adds_enabled(entry.scenario, True)
            learned_controller = LearnedADDSController(gear=scenario.initial_gear, model=report.model)
            comparison = run_paired_comparison(
                simulator,
                entry.scenario,
                ConventionalBaselineController(gear=scenario.initial_gear),
                learned_controller,
            )
            expert_result = simulator.run(
                scenario,
                RuleBasedADDSController(gear=scenario.initial_gear),
            )
            learned_summary = comparison.adds_summary
            expert_summary = summarize_run(expert_result)
            agreement = _requested_mode_agreement(
                expert_result.records,
                comparison.adds_result.records,
            )
            evaluation_rows.append(
                {
                    "split": split,
                    "scenario_id": scenario.scenario_id,
                    "completed_successfully": learned_summary["completed_successfully"],
                    "learned_fuel_used": learned_summary["fuel_used"],
                    "relative_fuel_change": comparison.deltas["relative_fuel_change"],
                    "delta_rms_speed_error": comparison.deltas["delta_rms_speed_error"],
                    "learned_mode_transition_count": learned_summary["mode_transition_count"],
                    "expert_mode_transition_count": expert_summary["mode_transition_count"],
                    "requested_mode_agreement": agreement,
                    "safety_override_count": learned_summary["safety_override_count"],
                    "hard_constraint_violation_count": learned_summary["hard_constraint_violation_count"],
                }
            )
    evaluation_report_path.write_text(
        json.dumps(
            {
                "schema_version": "2.0",
                "checkpoint": str(checkpoint_path),
                "evaluations": evaluation_rows,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    return ImitationTrainingArtifacts(
        output_dir=output_dir,
        checkpoint_path=checkpoint_path,
        training_report_path=training_report_path,
        evaluation_report_path=evaluation_report_path,
    )


def _requested_mode_agreement(
    expert_records: tuple[dict[str, float | int | str | bool], ...],
    learned_records: tuple[dict[str, float | int | str | bool], ...],
) -> float:
    """Return time-aligned high-level action agreement for two trajectories."""

    total_records = max(len(expert_records), len(learned_records))
    if total_records == 0:
        return 0.0
    matching = sum(
        1
        for expert, learned in zip(expert_records, learned_records)
        if expert["requested_mode"] == learned["requested_mode"]
    )
    return matching / total_records


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the initial ADDS behavioral-cloning controller.")
    parser.add_argument("output_dir", type=Path, help="Directory for checkpoint and reports.")
    args = parser.parse_args()
    artifacts = train_and_evaluate_imitation(args.output_dir)
    print(f"checkpoint: {artifacts.checkpoint_path}")
    print(f"training_report: {artifacts.training_report_path}")
    print(f"evaluation_report: {artifacts.evaluation_report_path}")


if __name__ == "__main__":
    main()
