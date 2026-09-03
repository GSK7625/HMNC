"""Unit tests cho ControllerRegistry, Auto-discovery và Cơ chế An toàn Safety Guard."""

from __future__ import annotations

import unittest
from dataclasses import dataclass

from src.traffic_control.controllers.base import BaseController
from src.traffic_control.controllers.registry import ControllerRegistry


@dataclass
class MockObservation:
    tls_id: str
    current_phase: int
    green_elapsed: float
    lane_vehicle_count: dict[str, int]
    phase_movements: tuple[tuple[tuple[str, str], ...], ...]


class TestRegistryAndSafetyGuard(unittest.TestCase):
    def setUp(self):
        self.registry = ControllerRegistry()
        self.movements = (
            ((("in_1", "out_1"),),),
            ((("in_2", "out_2"),),),
        )

    def test_controller_registration_and_retrieval(self):
        @self.registry.register(name="test_algo", aliases=["ta", "test_a"], display_name="Test Algorithm")
        class TestAlgoController(BaseController):
            def decide_phase(self, observation):
                return 1

        # Lấy bằng tên chính
        cls1 = self.registry.get("test_algo")
        self.assertEqual(cls1, TestAlgoController)

        # Lấy bằng aliases
        cls2 = self.registry.get("ta")
        self.assertEqual(cls2, TestAlgoController)

        cls3 = self.registry.get("TEST_A")  # Case insensitive
        self.assertEqual(cls3, TestAlgoController)

        # Kiểm tra metadata
        meta = self.registry.get_metadata("ta")
        self.assertEqual(meta.name, "test_algo")
        self.assertEqual(meta.display_name, "Test Algorithm")
        self.assertIn("ta", meta.aliases)

    def test_unregistered_controller_raises_key_error(self):
        with self.assertRaises(KeyError):
            self.registry.get("non_existent_controller")

    def test_safety_guard_enforces_minimum_green(self):
        """Kiểm tra cơ chế an toàn: Nếu chưa đủ minimum_green_seconds, controller BẮT BUỘC giữ pha hiện tại."""
        class SwitchEveryTimeController(BaseController):
            def __init__(self, minimum_green_seconds=10.0):
                super().__init__(minimum_green_seconds=minimum_green_seconds)

            def decide_phase(self, observation):
                # Thuật toán luôn muốn đổi từ pha 0 sang pha 1
                return 1

        ctrl = SwitchEveryTimeController(minimum_green_seconds=10.0)

        # Tình huống 1: green_elapsed = 4.0s (< 10.0s) -> Bắt buộc giữ pha 0
        obs1 = MockObservation(
            tls_id="tls_1",
            current_phase=0,
            green_elapsed=4.0,
            lane_vehicle_count={},
            phase_movements=self.movements,
        )
        self.assertEqual(ctrl.select_phase(obs1), 0)

        # Tình huống 2: green_elapsed = 10.0s (đạt minimum green) -> Cho phép đổi sang pha 1
        obs2 = MockObservation(
            tls_id="tls_1",
            current_phase=0,
            green_elapsed=10.0,
            lane_vehicle_count={},
            phase_movements=self.movements,
        )
        self.assertEqual(ctrl.select_phase(obs2), 1)

    def test_open_closed_principle_plug_new_algorithm(self):
        """Minh chứng nguyên lý Open-Closed: Thêm một thuật toán mới hoàn toàn tự do."""
        @self.registry.register(name="greedy_max", aliases=["gm"], display_name="Greedy Max")
        class GreedyMaxController(BaseController):
            def __init__(self, multiplier=2.0, minimum_green_seconds=10.0, **kwargs):
                super().__init__(minimum_green_seconds=minimum_green_seconds)
                self.multiplier = multiplier

            def decide_phase(self, observation):
                return 1

        cls = self.registry.get("gm")
        instance = cls(multiplier=3.5, minimum_green_seconds=12.0)
        self.assertEqual(instance.multiplier, 3.5)
        self.assertEqual(instance.minimum_green_seconds, 12.0)
        self.assertEqual(instance.name, "greedy_max")
        self.assertEqual(instance.display_name, "Greedy Max")


if __name__ == "__main__":
    unittest.main()
