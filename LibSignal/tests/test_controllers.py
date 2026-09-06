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
    lane_length: dict[str, float] | None = None
    lane_density: dict[str, float] | None = None
    exit_lanes: set[str] | None = None


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

    def test_fixed_time_controller_minimum_green(self) -> None:
        ctrl = FixedTimeController(green_seconds=30.0)
        # Even with minimum green = 10, FixedTime uses green_seconds = 30
        obs = MockObservation(
            current_phase=0,
            green_elapsed=15.0,
            lane_vehicle_count={"in_1": 0, "out_1": 0, "in_2": 10, "out_2": 0},
            phase_movements=((("in_1", "out_1"),), (("in_2", "out_2"),)),
        )
        self.assertEqual(ctrl.select_phase(obs), 0)

    def test_fixed_time_controller_switches_phases(self) -> None:
        ctrl = FixedTimeController(green_seconds=30.0)
        # In phase 0 with elapsed < 30s -> stay in 0
        obs = MockObservation(
            current_phase=0,
            green_elapsed=20.0,
            lane_vehicle_count={"in_1": 0, "out_1": 0, "in_2": 10, "out_2": 0},
            phase_movements=((("in_1", "out_1"),), (("in_2", "out_2"),)),
        )
        self.assertEqual(ctrl.select_phase(obs), 0)

        # In phase 0 with elapsed >= 30s -> switch to 1
        obs.green_elapsed = 30.0
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
        """Kiểm tra khử trùng lặp và tỷ lệ phân chia luồng rẽ (turning split ratio)."""
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
                (("in_1", "out_1"), ("in_1", "out_2")),  # in_1 xuất hiện 2 lần rẽ 2 hướng
                (("in_2", "out_3"),),
            ),
        )
        pressures = calculate_phase_pressures(obs)
        # in_1 có 10 xe, rẽ 2 nhánh out_1 (2) và out_2 (3) -> ratio = 0.5
        # out_val = 0.5 * 2 + 0.5 * 3 = 2.5. Áp lực = 10 - 2.5 = 7.5
        self.assertEqual(pressures[0], 7.5)
        # in_2 có 5 xe - out_3: 0 = 5.0
        self.assertEqual(pressures[1], 5.0)

    def test_fixed_time_proportional_splits(self) -> None:
        """Kiểm tra chia thời gian xanh Fixed-Time theo tỉ lệ số làn (Webster)."""
        ctrl = FixedTimeController(green_seconds=20.0, proportional_splits=True, yellow_seconds=0.0)
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


    def test_max_pressure_turning_ratio_three_branches(self) -> None:
        """Kiểm tra tỷ lệ phân chia luồng rẽ khi 1 làn vào rẽ ra 3 nhánh thoát (ratio = 1/3)."""
        obs = MockObservation(
            current_phase=0,
            green_elapsed=15.0,
            lane_vehicle_count={
                "in_1": 12,
                "out_1": 3,
                "out_2": 6,
                "out_3": 9,
            },
            phase_movements=(
                (("in_1", "out_1"), ("in_1", "out_2"), ("in_1", "out_3")),
            ),
        )
        pressures = calculate_phase_pressures(obs)
        # out_val = (1/3)*3 + (1/3)*6 + (1/3)*9 = 1 + 2 + 3 = 6.0
        # Áp lực = 12 - 6.0 = 6.0
        self.assertAlmostEqual(pressures[0], 6.0)

    def test_max_pressure_custom_turning_ratios(self) -> None:
        """Kiểm tra cung cấp tỷ lệ phân chia luồng rẽ tùy biến."""
        obs = MockObservation(
            current_phase=0,
            green_elapsed=15.0,
            lane_vehicle_count={
                "in_1": 10,
                "out_1": 4,
                "out_2": 8,
            },
            phase_movements=((("in_1", "out_1"), ("in_1", "out_2")),),
        )
        # 70% đi thẳng ra out_1, 30% rẽ ra out_2
        ratios = {("in_1", "out_1"): 0.7, ("in_1", "out_2"): 0.3}
        pressures = calculate_phase_pressures(obs, turning_ratios=ratios)
        # out_val = 0.7 * 4 + 0.3 * 8 = 2.8 + 2.4 = 5.2
        # Áp lực = 10 - 5.2 = 4.8
        self.assertAlmostEqual(pressures[0], 4.8)

    def test_max_pressure_density_mode(self) -> None:
        """Kiểm tra density mode: cả làn vào và làn ra đều đồng nhất dùng mật độ xe."""
        obs = MockObservation(
            current_phase=0,
            green_elapsed=15.0,
            lane_vehicle_count={"in_1": 10, "out_1": 20},
            lane_length={"in_1": 100.0, "out_1": 200.0},
            phase_movements=((("in_1", "out_1"),),),
        )
        # in_density = 10 / 100 = 0.1 xe/m
        # out_density = 20 / 200 = 0.1 xe/m
        # Áp lực = 0.1 - 0.1 = 0.0
        pressures = calculate_phase_pressures(obs, pressure_mode="density")
        self.assertAlmostEqual(pressures[0], 0.0)

    def test_fixed_time_yellow_sync_no_drift(self) -> None:
        """Kiểm tra Fixed-Time đồng bộ chu kỳ và loại bỏ hiện tượng trôi 10s do 3s đèn vàng."""
        # Chu kỳ pha 30s, đèn vàng 3s, action_interval 10s -> target_green = 27s
        ctrl = FixedTimeController(green_seconds=30.0, action_interval=10.0, yellow_seconds=3.0)
        obs = MockObservation(
            current_phase=0,
            green_elapsed=26.0,  # 26s < 27s -> chưa đủ chu kỳ
            lane_vehicle_count={},
            phase_movements=((("in_1", "out_1"),), (("in_2", "out_2"),)),
        )
        self.assertEqual(ctrl.select_phase(obs), 0)

        # Tại 27s green_elapsed (tương ứng trọn vẹn 30s sau khi trừ 3s vàng) -> chuyển pha chính xác!
        obs.green_elapsed = 27.0
        self.assertEqual(ctrl.select_phase(obs), 1)

    def test_fixed_time_duration_quantized_to_action_interval(self) -> None:
        """Kiểm tra thời gian xanh luôn được làm tròn thành bội số của action_interval."""
        ctrl = FixedTimeController(green_seconds=26.0, action_interval=10.0)
        # 26s được làm tròn thành 30s (bội số của 10s)
        self.assertEqual(ctrl.green_seconds, 30.0)

        ctrl_down = FixedTimeController(green_seconds=24.0, action_interval=10.0)
        # 24s được làm tròn thành 20s (bội số của 10s)
        self.assertEqual(ctrl_down.green_seconds, 20.0)

        # Kiểm tra proportional_splits làm tròn bội số:
        # Phase 0: 1 làn, Phase 1: 2 làn. Tổng chu kỳ = 30 * 2 = 60s
        # Phase 0: 1/3 * 60 = 20s (bội số của 10s)
        # Phase 1: 2/3 * 60 = 40s (bội số của 10s)
        ctrl_prop = FixedTimeController(green_seconds=30.0, action_interval=10.0, proportional_splits=True)
        obs_p0 = MockObservation(
            current_phase=0,
            green_elapsed=0.0,
            lane_vehicle_count={},
            phase_movements=(
                (("in_1", "out_1"),),
                (("in_2", "out_2"), ("in_3", "out_3")),
            ),
        )
        self.assertEqual(ctrl_prop.get_phase_duration(obs_p0), 20.0)
        obs_p0.current_phase = 1
        self.assertEqual(ctrl_prop.get_phase_duration(obs_p0), 40.0)

    def test_fixed_time_webster_flow_equisaturation(self) -> None:
        """Kiểm tra Fixed-Time điều chỉnh thời gian xanh theo chuẩn Webster y_i = q_i / s_i khi có dòng xe thực tế."""
        # 2 pha, mỗi pha 1 làn vào (s_0 = s_1 = 1)
        # Chu kỳ xanh tổng: 30 * 2 = 60s
        ctrl = FixedTimeController(green_seconds=30.0, action_interval=10.0, proportional_splits=True, yellow_seconds=0.0)
        obs = MockObservation(
            current_phase=0,
            green_elapsed=0.0,
            lane_vehicle_count={"in_1": 10, "in_2": 50},  # Pha 0 có 10 xe, Pha 1 có 50 xe (đông gấp 5 lần)
            phase_movements=(
                (("in_1", "out_1"),),
                (("in_2", "out_2"),),
            ),
        )
        ctrl.record_traffic(obs)
        # y_0 = (10 + 1) / 1 = 11; y_1 = (50 + 1) / 1 = 51. Tổng y = 62.
        # Pha 0 ratio ~ 11/62 = 17.7% -> duration ~ 10.6s -> làm tròn 10s (bội số 10s)
        # Pha 1 ratio ~ 51/62 = 82.3% -> duration ~ 49.4s -> làm tròn 50s (bội số 10s)
        duration_p0 = ctrl.get_phase_duration(obs)
        self.assertEqual(duration_p0, 10.0)

        obs.current_phase = 1
        duration_p1 = ctrl.get_phase_duration(obs)
        self.assertEqual(duration_p1, 50.0)

    def test_max_pressure_tie_breaking_waiting_time(self) -> None:
        """Kiểm tra khi hòa áp lực, Max-Pressure ưu tiên pha có tổng thời gian chờ xe lớn nhất."""
        ctrl = MaxPressureController(minimum_green_seconds=10.0)
        # Đang ở pha 0, green_elapsed = 15s (đã qua min green)
        # Cả pha 1 và pha 2 đều có áp lực = 8.0, cao hơn pha 0 (áp lực = 0)
        # Pha 1: xe chờ 5 giây. Pha 2: xe chờ 60 giây.
        obs = MockObservation(
            current_phase=0,
            green_elapsed=15.0,
            lane_vehicle_count={"in_0": 2, "out_0": 2, "in_1": 8, "out_1": 0, "in_2": 8, "out_2": 0},
            lane_waiting_time={"in_0": 0.0, "in_1": 5.0, "in_2": 60.0},
            phase_movements=(
                (("in_0", "out_0"),),
                (("in_1", "out_1"),),
                (("in_2", "out_2"),),
            ),
        )
        # Thay vì thiên vị pha 1 (index nhỏ hơn), thuật toán phải chọn pha 2 vì thời gian chờ lớn hơn nhiều!
        self.assertEqual(ctrl.select_phase(obs), 2)

    def test_max_pressure_capacities_weighting(self) -> None:
        """Kiểm tra Max-Pressure hỗ trợ nhân trọng số năng lực thông hành làn C(u) chuẩn Varaiya 2013."""
        obs = MockObservation(
            current_phase=0,
            green_elapsed=15.0,
            lane_vehicle_count={"in_1": 10, "out_1": 2, "in_2": 10, "out_2": 2},
            phase_movements=((("in_1", "out_1"),), (("in_2", "out_2"),)),
        )
        # Bình thường: áp lực = 10 - 2 = 8 cho cả 2 pha
        pressures_unweighted = calculate_phase_pressures(obs)
        self.assertEqual(pressures_unweighted, [8.0, 8.0])

        # Gán trọng số năng lực: làn in_2 có capacity = 2.0 (vd: làn cao tốc 2 làn)
        caps = {"in_1": 1.0, "in_2": 2.0}
        pressures_weighted = calculate_phase_pressures(obs, capacities=caps)
        # Pha 0: 1.0 * (10 - 2) = 8.0
        # Pha 1: 2.0 * (10 - 2) = 16.0
        self.assertEqual(pressures_weighted, [8.0, 16.0])

    def test_fixed_time_webster_c0_calculation(self) -> None:
        """Kiểm tra FixedTimeController tính chu kỳ tối ưu Webster C_0 = (1.5L + 5)/(1 - Y)."""
        ctrl = FixedTimeController(
            green_seconds=30.0,
            action_interval=10.0,
            proportional_splits=True,
            yellow_seconds=3.0,
            webster_cycle=True,
        )
        obs = MockObservation(
            current_phase=0,
            green_elapsed=0.0,
            lane_vehicle_count={"in_1": 20, "in_2": 30},
            phase_movements=((("in_1", "out_1"),), (("in_2", "out_2"),)),
        )
        ctrl.record_traffic(obs)
        c0 = ctrl.compute_webster_cycle(obs, [21.0, 31.0], num_phases=2)
        # C_0 phải nằm trong khoảng hợp lý [30s, 150s]
        self.assertGreaterEqual(c0, 30.0)
        self.assertLessEqual(c0, 150.0)

        # Thời gian pha phải là bội số của action_interval (10s)
        duration_p0 = ctrl.get_phase_duration(obs)
        self.assertEqual(duration_p0 % 10.0, 0.0)

    def test_calculate_phase_pressures_boundary_exit_exclusion(self) -> None:
        """Kiểm tra chuẩn Varaiya 2013: làn thoát biên không bị trừ áp lực hạ lưu."""
        # Ngã tư có out_1 là làn thoát ra ngoài mạng lưới (boundary exit)
        obs = MockObservation(
            current_phase=0,
            green_elapsed=15.0,
            lane_vehicle_count={"in_1": 10, "out_1": 6, "in_2": 8, "out_2": 2},
            phase_movements=((("in_1", "out_1"),), (("in_2", "out_2"),)),
            exit_lanes={"out_1"},  # out_1 là làn thoát biên
        )
        # Khi exclude_boundary_exits=True (mặc định):
        # Pha 0: in_1 (10) - out_1 (0 vì là thoát biên) = 10.0
        # Pha 1: in_2 (8) - out_2 (2) = 6.0
        pressures = calculate_phase_pressures(obs, exclude_boundary_exits=True)
        self.assertEqual(pressures, [10.0, 6.0])

        # Khi tắt exclude_boundary_exits=False:
        # Pha 0 bị trừ cả 6 xe trên out_1: 10 - 6 = 4.0
        pressures_unexcluded = calculate_phase_pressures(obs, exclude_boundary_exits=False)
        self.assertEqual(pressures_unexcluded, [4.0, 6.0])

    def test_calculate_phase_pressures_empty_outgoing_lane(self) -> None:
        """Kiểm tra độ bền: tính áp lực chính xác khi làn vào không có nhánh thoát (outs rỗng)."""
        obs = MockObservation(
            current_phase=0,
            green_elapsed=15.0,
            lane_vehicle_count={"in_deadend": 7, "in_normal": 4, "out_normal": 1},
            phase_movements=(
                (("in_deadend", ""),),  # Làn cụt, out_lane rỗng
                (("in_normal", "out_normal"),),
            ),
        )
        # Pha 0: in_deadend (7) - out (0) = 7.0 (không bị UnboundLocalError)
        # Pha 1: in_normal (4) - out_normal (1) = 3.0
        pressures = calculate_phase_pressures(obs)
        self.assertEqual(pressures, [7.0, 3.0])


if __name__ == "__main__":
    unittest.main()
