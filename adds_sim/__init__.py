"""ADDS Phase 1 longitudinal vehicle simulator."""

from .batch import BatchEvaluationResult, run_batch_evaluation
from .benchmarks import benchmark_scenarios
from .comparison import PairedComparisonResult, run_paired_comparison
from .controllers import (
    CoastController,
    ConstantEngineTorqueController,
    ConventionalBaselineController,
    RuleBasedADDSController,
    ScriptedModeController,
    SpeedTrackingController,
)
from .defaults import default_simulation_config
from .learned_controller import LearnedADDSController
from .metrics import summarize_run
from .ml import (
    BehavioralCloningModel,
    ImitationExample,
    TrainingReport,
    collect_imitation_examples,
    train_behavioral_cloning_model,
)
from .parameters import (
    CouplingParameters,
    EngineParameters,
    EnvironmentParameters,
    SafetyParameters,
    SolverParameters,
    TransmissionParameters,
    VehicleParameters,
)
from .profiles import ConstantProfile, OffsetProfile, PiecewiseLinearProfile
from .robustness import (
    ParameterPerturbation,
    RobustnessReport,
    RobustnessRun,
    apply_perturbation_to_config,
    apply_perturbation_to_scenario,
    default_perturbations,
    run_robustness_evaluation,
    write_robustness_report,
)
from .scenario_catalog import ScenarioCatalogEntry, entries_by_split, phase4_scenario_catalog
from .simulator import LongitudinalSimulator, Scenario, SimulationConfig, SimulationResult, VehicleState

__all__ = [
    "CoastController",
    "ConstantEngineTorqueController",
    "ConstantProfile",
    "ConventionalBaselineController",
    "CouplingParameters",
    "BatchEvaluationResult",
    "BehavioralCloningModel",
    "EngineParameters",
    "EnvironmentParameters",
    "ImitationExample",
    "LearnedADDSController",
    "LongitudinalSimulator",
    "OffsetProfile",
    "ParameterPerturbation",
    "PiecewiseLinearProfile",
    "PairedComparisonResult",
    "RuleBasedADDSController",
    "RobustnessReport",
    "RobustnessRun",
    "Scenario",
    "ScenarioCatalogEntry",
    "ScriptedModeController",
    "SafetyParameters",
    "SimulationConfig",
    "SimulationResult",
    "SolverParameters",
    "SpeedTrackingController",
    "TrainingReport",
    "TransmissionParameters",
    "VehicleParameters",
    "VehicleState",
    "apply_perturbation_to_config",
    "apply_perturbation_to_scenario",
    "benchmark_scenarios",
    "collect_imitation_examples",
    "default_simulation_config",
    "default_perturbations",
    "entries_by_split",
    "phase4_scenario_catalog",
    "run_batch_evaluation",
    "run_paired_comparison",
    "run_robustness_evaluation",
    "summarize_run",
    "train_behavioral_cloning_model",
    "write_robustness_report",
]
