"""ADDS Phase 1 longitudinal vehicle simulator."""

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
from .metrics import summarize_run
from .parameters import (
    CouplingParameters,
    EngineParameters,
    EnvironmentParameters,
    SafetyParameters,
    SolverParameters,
    TransmissionParameters,
    VehicleParameters,
)
from .profiles import ConstantProfile, PiecewiseLinearProfile
from .simulator import LongitudinalSimulator, Scenario, SimulationConfig, SimulationResult, VehicleState

__all__ = [
    "CoastController",
    "ConstantEngineTorqueController",
    "ConstantProfile",
    "ConventionalBaselineController",
    "CouplingParameters",
    "EngineParameters",
    "EnvironmentParameters",
    "LongitudinalSimulator",
    "PiecewiseLinearProfile",
    "PairedComparisonResult",
    "RuleBasedADDSController",
    "Scenario",
    "ScriptedModeController",
    "SafetyParameters",
    "SimulationConfig",
    "SimulationResult",
    "SolverParameters",
    "SpeedTrackingController",
    "TransmissionParameters",
    "VehicleParameters",
    "VehicleState",
    "benchmark_scenarios",
    "default_simulation_config",
    "run_paired_comparison",
    "summarize_run",
]
