"""SUMO Traffic Signal Control Framework."""

from .core.config import BenchmarkConfig
from .core.metrics import EvaluationMetrics, MetricsCollector
from .core.observation import IntersectionObservation, TrafficSnapshot
from .controllers import (
    BaseController,
    Controller,
    CONTROLLER_REGISTRY,
    register_controller,
    FixedTimeController,
    MaxPressureController,
    QLearningController,
    DEFAULT_Q_TABLE_PATH,
    calculate_phase_pressures,
)
from .experiment import run_experiment, write_comparison
from .sumo_env import SumoEnvironment
from .visualization import (
    generate_all_plots,
    plot_benchmark_comparison,
    plot_learning_curve,
    plot_time_series,
)

__all__ = [
    "BenchmarkConfig",
    "EvaluationMetrics",
    "MetricsCollector",
    "IntersectionObservation",
    "TrafficSnapshot",
    "BaseController",
    "Controller",
    "CONTROLLER_REGISTRY",
    "register_controller",
    "FixedTimeController",
    "MaxPressureController",
    "QLearningController",
    "DEFAULT_Q_TABLE_PATH",
    "calculate_phase_pressures",
    "run_experiment",
    "write_comparison",
    "SumoEnvironment",
    "generate_all_plots",
    "plot_benchmark_comparison",
    "plot_learning_curve",
    "plot_time_series",
]
