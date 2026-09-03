"""Unit tests for Fixed-Time and Max-Pressure traffic signal controllers."""

from __future__ import annotations

import unittest
from dataclasses import dataclass

from src.traffic_control.controllers import (
    FixedTimeController,
    MaxPressureController,
    calculate_phase_pressures,
)


@dataclass
class MockObservation:
    current_phase: int
    green_elapsed: float
    lane_vehicle_count: dict[str, int]
    phase_movements: tuple[tuple[tuple[str, str], ...], ...]
    lane_halting_count: dict[str, int] | None = None
    lane_waiting_time: dict[str, float] | None = None


class TestControllers(unittest.TestCase):
    def setUp(self) -> None:
        # 2-phase intersection:
        # Phase 0: movements (lane_in_1 -> lane_out_1)
        # Phase 1: movements (lane_in_2 -> lane_out_2)
        self.movements = (
            ((("in_1", "out_1"),),),
            ((("in_2", "out_2"),),),
        )

    def test_calculate_phase_pressures(self) -> None:
        obs = MockObservation(
            current_phase=0,
            green_elapsed=15.0,
            lane_vehicle_count={
                "in_1": 10,
                "out_1": 2,  # Phase 0 pressure = 10 - 2 = 8
                "in_2": 5,
                "out_2": 0,  # Phase 1 pressure = 5 - 0 = 5
            },
            phase_movements=((("in_1", "out_1"),), (("in_2", "out_2"),)),
        )
        pressures = calculate_phase_pressures(obs)
        self.assertEqual(pressures, [8.0, 5.0])

    def test_fixed_time_controller_before_green_time(self) -> None:
        ctrl = FixedTimeController(green_seconds=30.0)
        obs = MockObservation(
            current_phase=0,
            green_elapsed=20.0,
            lane_vehicle_count={},
            phase_movements=((("in_1", "out_1"),), (("in_2", "out_2"),)),
        )
        # Still within 30s -> keep current phase 0
        self.assertEqual(ctrl.select_phase(obs), 0)

    def test_fixed_time_controller_after_green_time(self) -> None:
        ctrl = FixedTimeController(green_seconds=30.0)
        obs = MockObservation(
            current_phase=0,
            green_elapsed=30.0,
            lane_vehicle_count={},
            phase_movements=((("in_1", "out_1"),), (("in_2", "out_2"),)),
        )
        # Reached green time -> cycle to next phase (0 -> 1)
        self.assertEqual(ctrl.select_phase(obs), 1)

        # From phase 1 cycling back to 0
        obs.current_phase = 1
        obs.green_elapsed = 35.0
        self.assertEqual(ctrl.select_phase(obs), 0)

    def test_max_pressure_controller_minimum_green(self) -> None:
        ctrl = MaxPressureController(minimum_green_seconds=10.0)
        # Even if Phase 1 has much higher pressure, don't switch before minimum green
        obs = MockObservation(
            current_phase=0,
            green_elapsed=5.0,
            lane_vehicle_count={"in_1": 0, "out_1": 0, "in_2": 20, "out_2": 0},
            phase_movements=((("in_1", "out_1"),), (("in_2", "out_2"),)),
        )
        self.assertEqual(ctrl.select_phase(obs), 0)

    def test_max_pressure_controller_switches_to_max(self) -> None:
        ctrl = MaxPressureController(minimum_green_seconds=10.0)
        # After minimum green, switch to Phase 1 because its pressure is higher (20 vs 2)
        obs = MockObservation(
            current_phase=0,
            green_elapsed=12.0,
            lane_vehicle_count={"in_1": 2, "out_1": 0, "in_2": 20, "out_2": 0},
            phase_movements=((("in_1", "out_1"),), (("in_2", "out_2"),)),
        )
        self.assertEqual(ctrl.select_phase(obs), 1)

    def test_calculate_phase_pressures_deduplication(self) -> None:
        """Kiểm tra khử trùng lặp: nếu 1 làn vào có nhiều nhánh rẽ, không bị đếm x2."""
        obs = MockObservation(
            current_phase=0,
            green_elapsed=15.0,
            lane_vehicle_count={
                "in_1": 10,  # 1 làn rẽ 2 hướng
                "out_1": 2,
                "out_2": 3,
                "in_2": 5,
                "out_3": 0,
            },
            phase_movements=(
                (("in_1", "out_1"), ("in_1", "out_2")),  # in_1 xuất hiện 2 lần
                (("in_2", "out_3"),),
            ),
        )
        pressures = calculate_phase_pressures(obs)
        # in_1 có 10 xe (đếm 1 lần) - (out_1: 2 + out_2: 3) = 10 - 5 = 5.0
        self.assertEqual(pressures[0], 5.0)
        # in_2 có 5 xe - out_3: 0 = 5.0
        self.assertEqual(pressures[1], 5.0)

    def test_fixed_time_proportional_splits(self) -> None:
        """Kiểm tra chia thời gian xanh Fixed-Time theo tỉ lệ số làn (Webster)."""
        ctrl = FixedTimeController(green_seconds=20.0, proportional_splits=True)
        # Phase 0: 1 làn vào
        # Phase 1: 3 làn vào
        # Tổng chu kỳ xanh = 20 * 2 = 40s
        # Phase 0: 1/4 * 40 = 10s
        # Phase 1: 3/4 * 40 = 30s
        obs_p0 = MockObservation(
            current_phase=0,
            green_elapsed=9.0,
            lane_vehicle_count={},
            phase_movements=(
                (("in_1", "out_1"),),
                (("in_2", "out_2"), ("in_3", "out_3"), ("in_4", "out_4")),
            ),
        )
        # Tại 9s chưa hết 10s của Phase 0 -> giữ nguyên
        self.assertEqual(ctrl.select_phase(obs_p0), 0)
        obs_p0.green_elapsed = 11.0
        # Tại 11s đã qua 10s của Phase 0 -> đổi sang Phase 1
        self.assertEqual(ctrl.select_phase(obs_p0), 1)

        # Kiểm tra Phase 1 có 30s
        obs_p1 = MockObservation(
            current_phase=1,
            green_elapsed=25.0,  # 25s < 30s
            lane_vehicle_count={},
            phase_movements=(
                (("in_1", "out_1"),),
                (("in_2", "out_2"), ("in_3", "out_3"), ("in_4", "out_4")),
            ),
        )
        self.assertEqual(ctrl.select_phase(obs_p1), 1)
        obs_p1.green_elapsed = 31.0  # 31s > 30s -> quay về Phase 0
        self.assertEqual(ctrl.select_phase(obs_p1), 0)

    def test_calculate_phase_pressures_halting_in_vehicle_out(self) -> None:
        """Kiểm tra: làn vào dùng halting count, làn thoát luôn dùng vehicle count."""
        obs = MockObservation(
            current_phase=0,
            green_elapsed=15.0,
            lane_vehicle_count={
                "in_1": 10,
                "out_1": 3,  # 3 xe đang chạy trên làn thoát
                "in_2": 8,
                "out_2": 1,
            },
            lane_halting_count={
                "in_1": 6,   # 6 xe dừng chờ
                "out_1": 0,  # xe thoát không dừng (halting = 0)
                "in_2": 2,
                "out_2": 0,
            },
            phase_movements=((("in_1", "out_1"),), (("in_2", "out_2"),)),
        )
        # use_halting=True:
        # Phase 0: halting(in_1)=6 - vehicle(out_1)=3 = 3.0
        # Phase 1: halting(in_2)=2 - vehicle(out_2)=1 = 1.0
        pressures = calculate_phase_pressures(obs, use_halting=True)
        self.assertEqual(pressures, [3.0, 1.0])

    def test_max_pressure_idle_maintains_current_phase(self) -> None:
        """Kiểm tra khi vắng xe (áp lực <= 0), Max-Pressure giữ nguyên pha hiện tại."""
        ctrl = MaxPressureController(minimum_green_seconds=10.0)
        # Đang ở pha 1, đường vắng
        obs = MockObservation(
            current_phase=1,
            green_elapsed=15.0,
            lane_vehicle_count={"in_1": 0, "out_1": 0, "in_2": 0, "out_2": 0},
            phase_movements=((("in_1", "out_1"),), (("in_2", "out_2"),)),
        )
        # Không được đổi về pha 0 mà phải giữ nguyên pha 1
        self.assertEqual(ctrl.select_phase(obs), 1)

    def test_max_pressure_tie_breaking_favors_current_phase(self) -> None:
        """Kiểm tra khi hòa áp lực tối đa, ưu tiên giữ nguyên pha hiện tại (Hysteresis)."""
        ctrl = MaxPressureController(minimum_green_seconds=10.0)
        obs = MockObservation(
            current_phase=1,
            green_elapsed=15.0,
            lane_vehicle_count={"in_1": 5, "out_1": 0, "in_2": 5, "out_2": 0},
            phase_movements=((("in_1", "out_1"),), (("in_2", "out_2"),)),
        )
        # Cả pha 0 và pha 1 đều có áp lực = 5. Đang ở pha 1 -> giữ nguyên pha 1
        self.assertEqual(ctrl.select_phase(obs), 1)

    def test_max_pressure_starvation_guard(self) -> None:
        """Kiểm tra cơ chế chống bỏ đói: chuyển pha khi xanh quá max_green_seconds."""
        ctrl = MaxPressureController(minimum_green_seconds=10.0, max_green_seconds=60.0)
        obs = MockObservation(
            current_phase=0,
            green_elapsed=65.0,  # Đã xanh quá 60s
            lane_vehicle_count={"in_1": 20, "out_1": 0, "in_2": 5, "out_2": 0},
            phase_movements=((("in_1", "out_1"),), (("in_2", "out_2"),)),
        )
        # Dù pha 0 áp lực cao hơn (20 vs 5), nhưng vì quá max_green nên phải nhường cho pha 1
        self.assertEqual(ctrl.select_phase(obs), 1)

    def test_max_pressure_standard_mode(self) -> None:
        """Kiểm tra chuẩn Varaiya 2013: standard mode dùng đồng nhất vehicle count cho cả in và out."""
        obs = MockObservation(
            current_phase=0,
            green_elapsed=15.0,
            lane_vehicle_count={"in_1": 10, "out_1": 4, "in_2": 8, "out_2": 2},
            lane_halting_count={"in_1": 1, "out_1": 0, "in_2": 0, "out_2": 0},
            phase_movements=((("in_1", "out_1"),), (("in_2", "out_2"),)),
        )
        # Standard mode bỏ qua halting count, dùng vehicle count:
        # Phase 0: 10 - 4 = 6.0
        # Phase 1: 8 - 2 = 6.0
        pressures = calculate_phase_pressures(obs, pressure_mode="standard")
        self.assertEqual(pressures, [6.0, 6.0])

    def test_max_pressure_normalized_mode(self) -> None:
        """Kiểm tra normalized mode: chuẩn hóa theo mật độ số làn."""
        obs = MockObservation(
            current_phase=0,
            green_elapsed=15.0,
            lane_vehicle_count={"in_1": 10, "in_2": 10, "out_1": 2, "in_3": 6, "out_2": 2},
            phase_movements=(
                (("in_1", "out_1"), ("in_2", "out_1")),  # Phase 0: 2 làn vào, 1 làn ra -> in_avg = 20/2=10, out_avg = 2/1=2 -> 8.0
                (("in_3", "out_2"),),                    # Phase 1: 1 làn vào, 1 làn ra -> in_avg = 6/1=6, out_avg = 2/1=2 -> 4.0
            ),
        )
        pressures = calculate_phase_pressures(obs, pressure_mode="normalized")
        self.assertEqual(pressures, [8.0, 4.0])


if __name__ == "__main__":
    unittest.main()
