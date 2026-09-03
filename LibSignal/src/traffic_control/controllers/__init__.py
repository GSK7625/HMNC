"""Gói chứa các bộ điều khiển đèn giao thông với cơ chế Plug-and-Play Registry."""

from .base import BaseController, Controller, calculate_phase_pressures
from .registry import CONTROLLER_REGISTRY, ControllerMetadata, register_controller

# Tự động quét và nạp toàn bộ các controller trong thư mục này
CONTROLLER_REGISTRY.auto_discover()

# Import tường minh các baseline controllers để hỗ trợ type hint và backward compatibility
from .fixed_time import FixedTimeController
from .max_pressure import MaxPressureController
from .q_learning import DEFAULT_Q_TABLE_PATH, QLearningController

__all__ = [
    "Controller",
    "BaseController",
    "calculate_phase_pressures",
    "CONTROLLER_REGISTRY",
    "ControllerMetadata",
    "register_controller",
    "FixedTimeController",
    "MaxPressureController",
    "QLearningController",
    "DEFAULT_Q_TABLE_PATH",
]
