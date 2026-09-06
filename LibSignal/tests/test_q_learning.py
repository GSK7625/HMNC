"""Unit tests cho QLearningController."""

from __future__ import annotations

import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from src.traffic_control.controllers import QLearningController


@dataclass
class MockObservation:
    tls_id: str
    current_phase: int
    green_elapsed: float
    lane_vehicle_count: dict[str, int]
    phase_movements: tuple[tuple[tuple[str, str], ...], ...]


class TestQLearningController(unittest.TestCase):
    def setUp(self) -> None:
        self.movements = (
            (("in_1", "out_1"),),
            (("in_2", "out_2"),),
        )

    def test_discretize_observation(self) -> None:
        ctrl = QLearningController()
        # Phase 0: 2 vehicles (bin 0)
        # Phase 1: 5 vehicles (bin 1)
        obs = MockObservation(
            tls_id="tls_1",
            current_phase=0,
            green_elapsed=15.0,
            lane_vehicle_count={"in_1": 2, "out_1": 0, "in_2": 5, "out_2": 0},
            phase_movements=self.movements,
        )
        state_key = ctrl.discretize_observation(obs)
        self.assertEqual(state_key, "0:0,1")

        # High vehicle count (bin 2)
        obs2 = MockObservation(
            tls_id="tls_1",
            current_phase=1,
            green_elapsed=15.0,
            lane_vehicle_count={"in_1": 12, "out_1": 0, "in_2": 0, "out_2": 0},
            phase_movements=self.movements,
        )
        self.assertEqual(ctrl.discretize_observation(obs2), "1:2,0")

    def test_minimum_green_enforcement(self) -> None:
        ctrl = QLearningController(minimum_green_seconds=10.0, learning=False)
        obs = MockObservation(
            tls_id="tls_1",
            current_phase=0,
            green_elapsed=5.0,  # Chưa đủ 10 giây
            lane_vehicle_count={"in_1": 0, "out_1": 0, "in_2": 10, "out_2": 0},
            phase_movements=self.movements,
        )
        # Bắt buộc phải giữ nguyên pha 0 dù Q-value pha 1 có cao thế nào
        self.assertEqual(ctrl.select_phase(obs), 0)

    def test_inference_action_selection(self) -> None:
        ctrl = QLearningController(minimum_green_seconds=10.0, learning=False, epsilon=0.0)
        # Giả lập bảng Q: Tại state "0:0,2", action 1 có Q-value cao hơn
        ctrl.q_table["0:0,2"] = [1.5, 9.8]

        obs = MockObservation(
            tls_id="tls_1",
            current_phase=0,
            green_elapsed=12.0,  # Đã qua 10 giây
            lane_vehicle_count={"in_1": 1, "out_1": 0, "in_2": 15, "out_2": 0},
            phase_movements=self.movements,
        )
        self.assertEqual(ctrl.select_phase(obs), 1)

    def test_bellman_update(self) -> None:
        alpha = 0.5
        gamma = 0.8
        ctrl = QLearningController(
            minimum_green_seconds=10.0,
            alpha=alpha,
            gamma=gamma,
            epsilon=0.0,
            learning=True,
        )

        # Trạng thái 1: "0:0,0"
        state1 = "0:0,0"
        ctrl.q_table[state1] = [0.0, 0.0]
        ctrl.last_state_action["tls_1"] = (state1, 0)

        # Trạng thái 2: "0:2,2" (xe đông trên cả 2 trục)
        obs2 = MockObservation(
            tls_id="tls_1",
            current_phase=0,
            green_elapsed=12.0,
            lane_vehicle_count={"in_1": 10, "out_1": 0, "in_2": 10, "out_2": 0},
            phase_movements=self.movements,
        )
        state2 = ctrl.discretize_observation(obs2)  # "0:2,2"
        self.assertEqual(state2, "0:2,2")
        ctrl.q_table[state2] = [2.0, 4.0]  # max_next_q = 4.0

        ctrl.select_phase(obs2)

        # Kỳ vọng:
        # total_waiting = 10 + 10 = 20
        # switched = False -> switch_penalty = 0.0 -> reward = -20.0
        # td_target = -20.0 + 0.8 * 4.0 = -20.0 + 3.2 = -16.8
        # new_q = 0.0 + 0.5 * (-16.8 - 0.0) = -8.4
        self.assertAlmostEqual(ctrl.q_table[state1][0], -8.4)

    def test_save_and_load_q_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "q_table.json"
            ctrl = QLearningController()
            ctrl.q_table = {"0:0,1": [1.2, 3.4], "1:2,0": [5.6, 7.8]}
            ctrl.save_q_table(file_path)

            ctrl2 = QLearningController(q_table_path=file_path)
            self.assertEqual(ctrl2.q_table, ctrl.q_table)

    def test_multi_intersection_isolation(self) -> None:
        """Kiểm tra tính độc lập đa ngã tư (IDQL / Decentralized): bảng Q ngã tư A không đè lên ngã tư B."""
        ctrl = QLearningController(minimum_green_seconds=10.0, learning=True)

        obs_a = MockObservation(
            tls_id="tls_A",
            current_phase=0,
            green_elapsed=15.0,
            lane_vehicle_count={"in_1": 1, "out_1": 0, "in_2": 1, "out_2": 0},
            phase_movements=self.movements,
        )
        obs_b = MockObservation(
            tls_id="tls_B",
            current_phase=0,
            green_elapsed=15.0,
            lane_vehicle_count={"in_1": 10, "out_1": 0, "in_2": 10, "out_2": 0},
            phase_movements=self.movements,
        )

        ctrl.select_phase(obs_a)
        ctrl.select_phase(obs_b)

        table_a = ctrl.get_tls_table("tls_A")
        table_b = ctrl.get_tls_table("tls_B")

        # Đảm bảo 2 bảng Q tách biệt hoàn toàn trong bộ nhớ
        self.assertIsNot(table_a, table_b)
        self.assertIn("0:0,0", table_a)
        self.assertIn("0:2,2", table_b)

    def test_reward_types(self) -> None:
        """Kiểm tra các hàm mục tiêu phần thưởng chuẩn RESCO (queue, delay, pressure)."""
        obs = MockObservation(
            tls_id="tls_1",
            current_phase=0,
            green_elapsed=15.0,
            lane_vehicle_count={"in_1": 5, "out_1": 1, "in_2": 3, "out_2": 0},
            phase_movements=self.movements,
        )
        # Giả lập thêm lane_halting_count và lane_waiting_time
        obs.lane_halting_count = {"in_1": 4, "in_2": 2}
        obs.lane_waiting_time = {"in_1": 20.0, "in_2": 10.0}

        # 1. Queue-based reward (RESCO RLCD/Queue): halting vehicles = 4 + 2 = 6, switch_penalty = 0 -> -6.0
        ctrl_queue = QLearningController(reward_type="queue")
        self.assertEqual(ctrl_queue._compute_reward(obs, switched=False), -6.0)

        # 2. Delay-based reward: waiting_time = 20.0 + 10.0 = 30.0 -> -30.0
        ctrl_delay = QLearningController(reward_type="delay")
        self.assertEqual(ctrl_delay._compute_reward(obs, switched=False), -30.0)

        # 3. Pressure-based reward: phase 0 pressure = in_1 halting (4) - out_1 vehicle (1) = 3 -> -3.0
        ctrl_pressure = QLearningController(reward_type="pressure")
        self.assertEqual(ctrl_pressure._compute_reward(obs, switched=False), -3.0)

    def test_bellman_update_with_switch_penalty(self) -> None:
        """Kiểm tra: khi agent đổi pha (prev_action != prev_phase), switched=True và áp dụng switch_penalty."""
        alpha = 0.5
        gamma = 0.8
        ctrl = QLearningController(
            minimum_green_seconds=10.0,
            alpha=alpha,
            gamma=gamma,
            epsilon=0.0,
            learning=True,
        )

        # Trạng thái 1: "0:0,0" (đang ở pha 0), agent quyết định đổi sang pha 1 (action = 1)
        state1 = "0:0,0"
        ctrl.q_table[state1] = [0.0, 0.0]
        ctrl.last_state_action["tls_1"] = (state1, 1)  # prev_action = 1, prev_phase = 0 -> switched = True

        # Trạng thái 2: "1:2,2" (đã sang pha 1)
        obs2 = MockObservation(
            tls_id="tls_1",
            current_phase=1,
            green_elapsed=12.0,
            lane_vehicle_count={"in_1": 10, "out_1": 0, "in_2": 10, "out_2": 0},
            phase_movements=self.movements,
        )
        state2 = ctrl.discretize_observation(obs2)  # "1:2,2"
        ctrl.q_table[state2] = [2.0, 4.0]  # max_next_q = 4.0

        ctrl.select_phase(obs2)

        # Kỳ vọng:
        # total_waiting = 20
        # switched = True -> switch_penalty = 1.0 -> reward = -(20 + 1) = -21.0
        # td_target = -21.0 + 0.8 * 4.0 = -21.0 + 3.2 = -17.8
        # new_q = 0.0 + 0.5 * (-17.8 - 0.0) = -8.9
        self.assertAlmostEqual(ctrl.q_table[state1][1], -8.9)

    def test_tie_breaking_favors_current_phase(self) -> None:
        """Kiểm tra cơ chế tie-breaking thông minh: khi các action hòa Q-value, giữ nguyên pha hiện tại."""
        ctrl = QLearningController(minimum_green_seconds=10.0, learning=False, epsilon=0.0)
        # Trạng thái mới toanh: cả 2 action đều có Q-value = 0.0
        ctrl.q_table["0:1,1"] = [0.0, 0.0]

        obs = MockObservation(
            tls_id="tls_1",
            current_phase=0,
            green_elapsed=15.0,
            lane_vehicle_count={"in_1": 4, "out_1": 0, "in_2": 4, "out_2": 0},
            phase_movements=self.movements,
        )
        # Đang ở pha 0, hòa điểm -> giữ nguyên pha 0
        self.assertEqual(ctrl.select_phase(obs), 0)

        # Đang ở pha 1, hòa điểm -> giữ nguyên pha 1
        obs.current_phase = 1
        ctrl.q_table["1:1,1"] = [0.0, 0.0]
        self.assertEqual(ctrl.select_phase(obs), 1)

    def test_decay_epsilon(self) -> None:
        """Kiểm tra giảm dần epsilon qua các episodes."""
        ctrl = QLearningController(epsilon=0.5)
        new_eps = ctrl.decay_epsilon(decay_rate=0.8, min_epsilon=0.05)
        self.assertAlmostEqual(new_eps, 0.4)
        # Chạy giảm nhiều lần chạm min_epsilon
        for _ in range(20):
            new_eps = ctrl.decay_epsilon(decay_rate=0.5, min_epsilon=0.05)
        self.assertEqual(new_eps, 0.05)

    def test_refined_discretization_mode(self) -> None:
        """Kiểm tra chế độ refined discretization 5 mức độ phân giải cao."""
        ctrl = QLearningController(discretization_mode="refined")
        obs_empty = MockObservation(
            tls_id="tls_1", current_phase=0, green_elapsed=15.0,
            lane_vehicle_count={"in_1": 0, "in_2": 2}, phase_movements=self.movements
        )
        self.assertEqual(ctrl.discretize_observation(obs_empty), "0:0,1")

        obs_heavy = MockObservation(
            tls_id="tls_1", current_phase=1, green_elapsed=15.0,
            lane_vehicle_count={"in_1": 12, "in_2": 25}, phase_movements=self.movements
        )
        # 12 xe -> mức 3 (đông), 25 xe -> mức 4 (tắc nghẽn)
        self.assertEqual(ctrl.discretize_observation(obs_heavy), "1:3,4")

    def test_transfer_priors_across_intersections(self) -> None:
        """Kiểm tra cơ chế Transfer Priors: ngã tư mới thừa hưởng giá trị Q từ ngã tư đã học khi gặp cùng trạng thái."""
        ctrl = QLearningController(learning=False)
        # tls_A đã học trạng thái "0:0,1"
        ctrl.q_tables["tls_A"] = {"0:0,1": [2.5, 8.9]}
        obs_b = MockObservation(
            tls_id="tls_B", current_phase=0, green_elapsed=15.0,
            lane_vehicle_count={"in_1": 2, "in_2": 5}, phase_movements=self.movements
        )
        action = ctrl.select_phase(obs_b)
        # tls_B thừa hưởng [2.5, 8.9] nên chọn action 1 thay vì action 0 (do 8.9 > 2.5)
        self.assertEqual(action, 1)
        self.assertEqual(ctrl.get_tls_table("tls_B")["0:0,1"], [2.5, 8.9])

    def test_safe_cycling_on_unvisited_state_after_long_green(self) -> None:
        """Kiểm tra tránh kẹt pha: khi unvisited state (tất cả Q=0) mà đã xanh quá 30s, an toàn chuyển sang pha kế tiếp."""
        ctrl = QLearningController(learning=False)
        obs = MockObservation(
            tls_id="tls_1", current_phase=0, green_elapsed=35.0,  # đã xanh 35s (> 30s)
            lane_vehicle_count={"in_1": 0, "in_2": 5}, phase_movements=self.movements
        )
        action = ctrl.select_phase(obs)
        # Phải an toàn chuyển sang pha 1 thay vì bị kẹt cứng ở pha 0
        self.assertEqual(action, 1)

    def test_bellman_update_during_minimum_green(self) -> None:
        """Kiểm tra: khi vướng G_min, Bellman update cho bước trước đó VẪN ĐƯỢC THỰC HIỆN ĐẦY ĐỦ."""
        alpha = 0.5
        gamma = 0.8
        ctrl = QLearningController(
            minimum_green_seconds=10.0,
            alpha=alpha,
            gamma=gamma,
            epsilon=0.0,
            learning=True,
        )
        state1 = "0:0,0"
        ctrl.q_table[state1] = [0.0, 0.0]
        # Bước trước: ở state1, đã chọn đổi sang pha 1 (action = 1)
        ctrl.last_state_action["tls_1"] = (state1, 1)

        # Bước hiện tại: đang ở pha 1, nhưng mới xanh 4s (< G_min = 10s)
        obs2 = MockObservation(
            tls_id="tls_1",
            current_phase=1,
            green_elapsed=4.0,  # Chưa đủ G_min!
            lane_vehicle_count={"in_1": 6, "out_1": 0, "in_2": 4, "out_2": 0},
            phase_movements=self.movements,
        )
        state2 = ctrl.discretize_observation(obs2)  # "1:1,1"
        ctrl.q_table[state2] = [1.0, 3.0]  # max_next_q = 3.0

        # Gọi select_phase khi vướng G_min
        action = ctrl.select_phase(obs2)

        # 1. Action phải bị ép giữ nguyên pha hiện tại (pha 1) vì an toàn G_min
        self.assertEqual(action, 1)

        # 2. Nhưng Bellman update của bước chuyển trước đó (state1, action 1) PHẢI ĐÃ ĐƯỢC CẬP NHẬT!
        # switched = True -> switch_penalty = 1.0, total_veh = 6 + 4 = 10 -> reward = -11.0
        # td_target = -11.0 + 0.8 * 3.0 = -11.0 + 2.4 = -8.6
        # new_q = 0.0 + 0.5 * (-8.6 - 0.0) = -4.3
        self.assertAlmostEqual(ctrl.q_table[state1][1], -4.3)

        # 3. last_state_action phải ghi nhận bước hiện tại để tiếp tục chuỗi Bellman
        self.assertEqual(ctrl.last_state_action["tls_1"], (state2, 1))

    def test_fine_discretization_mode_with_green_stage(self) -> None:
        """Kiểm tra chế độ phân giải cao fine (6 bins) kèm green_stage chống State Aliasing."""
        ctrl = QLearningController(discretization_mode="fine", include_green_stage=True)
        obs_early = MockObservation(
            tls_id="tls_1", current_phase=0, green_elapsed=5.0,
            lane_vehicle_count={"in_1": 1, "in_2": 8}, phase_movements=self.movements
        )
        # in_1=1 -> bin 1, in_2=8 -> bin 3, green_elapsed=5.0s -> stage 0 (early)
        self.assertEqual(ctrl.discretize_observation(obs_early), "0:1,3:0")

        obs_late = MockObservation(
            tls_id="tls_1", current_phase=0, green_elapsed=35.0,
            lane_vehicle_count={"in_1": 1, "in_2": 8}, phase_movements=self.movements
        )
        # Cùng số lượng xe nhưng thời gian xanh đã 35s -> stage 2 (late) -> không còn bị State Aliasing!
        self.assertEqual(ctrl.discretize_observation(obs_late), "0:1,3:2")


if __name__ == "__main__":
    unittest.main()
