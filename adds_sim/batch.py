"""Reproducible batch evaluation infrastructure."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .comparison import run_paired_comparison
from .controllers import ConventionalBaselineController, RuleBasedADDSController
from .data import write_summary_csv, write_trajectory_csv
from .scenario_catalog import ScenarioCatalogEntry
from .simulator import LongitudinalSimulator


@dataclass(frozen=True)
class BatchEvaluationResult:
    """File outputs created by a batch evaluation."""

    output_dir: Path
    manifest_path: Path
    summary_path: Path
    trajectory_paths: tuple[Path, ...]


def run_batch_evaluation(
    simulator: LongitudinalSimulator,
    entries: tuple[ScenarioCatalogEntry, ...],
    output_dir: Path,
    write_trajectories: bool = True,
) -> BatchEvaluationResult:
    """Run paired conventional-vs-ADDS comparisons for catalog entries."""

    output_dir.mkdir(parents=True, exist_ok=True)
    trajectory_dir = output_dir / "trajectories"
    summary_rows: list[dict[str, object]] = []
    trajectory_paths: list[Path] = []

    manifest = {
        "schema_version": "1.0",
        "runner": "adds_sim.batch.run_batch_evaluation",
        "scenario_count": len(entries),
        "controllers": ("conventional_baseline", "rule_based_adds"),
        "scenarios": [
            {
                "scenario_id": entry.scenario.scenario_id,
                "split": entry.split,
                "version": entry.version,
                "random_seed": entry.scenario.random_seed,
                "tags": entry.tags,
            }
            for entry in entries
        ],
    }

    for entry in entries:
        scenario = entry.scenario
        comparison = run_paired_comparison(
            simulator,
            scenario,
            ConventionalBaselineController(scenario.initial_gear),
            RuleBasedADDSController(scenario.initial_gear),
        )
        for controller_name, summary, result in (
            ("conventional_baseline", comparison.conventional_summary, comparison.conventional_result),
            ("rule_based_adds", comparison.adds_summary, comparison.adds_result),
        ):
            row = dict(summary)
            row["split"] = entry.split
            row["controller_name"] = controller_name
            summary_rows.append(row)
            if write_trajectories:
                trajectory_path = trajectory_dir / f"{scenario.scenario_id}__{controller_name}.csv"
                write_trajectory_csv(trajectory_path, result)
                trajectory_paths.append(trajectory_path)

    manifest_path = output_dir / "manifest.json"
    summary_path = output_dir / "summary.csv"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_summary_csv(summary_path, summary_rows)

    return BatchEvaluationResult(
        output_dir=output_dir,
        manifest_path=manifest_path,
        summary_path=summary_path,
        trajectory_paths=tuple(trajectory_paths),
    )
