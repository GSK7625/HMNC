"""Unit tests toàn diện cho DQNController và DQNAgent."""

from __future__ import annotations

import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch

from src.traffic_control.controllers import DQNController
from src.traffic_control.controllers.dqn import DQNAgent, QNetwork, ReplayBuffer


@dataclass
class MockObservation:
    tls_id: str
    current_phase: int
    green_elapsed: float
    lane_vehicle_count: dict[str, int]
    phase_movements: tuple[tuple[tuple[str, str], ...], ...]
    lane_halting_count: dict[str, int] | None = None
    lane_waiting_time: dict[str, float] | None = None
    lane_length: dict[str, float] | None = None
    lane_density: dict[str, float] | None = None


class TestDQNController(unittest.TestCase):
    def setUp(self) -> None:
        torch.manual_seed(42)
        np.random.seed(42)
        self.movements = (
            (("in_1", "out_1"),),
            (("in_2", "out_2"),),
        )

    def test_vectorize_observation(self) -> None:
        """Kiểm tra vector hóa quan sát: đúng kích thước (5*P + 1) và chuẩn hóa chính xác."""
        ctrl = DQNController()
        obs = MockObservation(
            tls_id="tls_1",
            current_phase=0,
            green_elapsed=15.0,
            lane_vehicle_count={"in_1": 4, "out_1": 0, "in_2": 8, "out_2": 0},
            phase_movements=self.movements,
            lane_halting_count={"in_1": 2, "in_2": 6},
            lane_waiting_time={"in_1": 20.0, "in_2": 50.0},
        )
        vec = ctrl.vectorize_observation(obs)
        # 2 pha -> 4 * 2 (queue, veh, wait, pressure) + 2 (one-hot) + 1 (green) = 11 chiều
        self.assertEqual(vec.shape, (11,))
        self.assertIsInstance(vec, np.ndarray)

        # Kiểm tra chuẩn hóa hàng đợi pha 0: 2 / 20.0 = 0.1
        self.assertAlmostEqual(vec[0], 0.1)
        # Kiểm tra chuẩn hóa xe pha 0: 4 / 20.0 = 0.2
        self.assertAlmostEqual(vec[1], 0.2)
        # Kiểm tra chuẩn hóa thời gian chờ pha 0: 20.0 / 100.0 = 0.2
        self.assertAlmostEqual(vec[2], 0.2)

        # Kiểm tra one-hot: pha 0 đang sáng -> vec[8] == 1.0, vec[9] == 0.0
        self.assertEqual(vec[8], 1.0)
        self.assertEqual(vec[9], 0.0)

        # Kiểm tra green elapsed: 15.0 / 60.0 = 0.25
        self.assertAlmostEqual(vec[10], 0.25)

    def test_minimum_green_enforcement(self) -> None:
        """Kiểm tra cơ chế Safety Guard: chưa đủ G_min bắt buộc giữ nguyên pha."""
        ctrl = DQNController(minimum_green_seconds=10.0, learning=False)
        obs = MockObservation(
            tls_id="tls_1",
            current_phase=0,
            green_elapsed=4.0,  # Chưa đủ 10 giây
            lane_vehicle_count={"in_1": 0, "out_1": 0, "in_2": 20, "out_2": 0},
            phase_movements=self.movements,
        )
        self.assertEqual(ctrl.select_phase(obs), 0)

    def test_replay_buffer(self) -> None:
        """Kiểm tra lưu và lấy mẫu ngẫu nhiên từ ReplayBuffer."""
        buf = ReplayBuffer(capacity=100)
        s1 = np.zeros(11, dtype=np.float32)
        s2 = np.ones(11, dtype=np.float32)
        buf.push(s1, 0, 1.0, s2, False)
        buf.push(s1, 1, -2.0, s2, True)

        self.assertEqual(len(buf), 2)
        states, actions, rewards, next_states, dones = buf.sample(2, torch.device("cpu"))
        self.assertEqual(states.shape, (2, 11))
        self.assertEqual(actions.shape, (2,))
        self.assertEqual(rewards.shape, (2,))
        self.assertEqual(next_states.shape, (2, 11))
        self.assertEqual(dones.shape, (2,))

    def test_qnetwork_forward(self) -> None:
        """Kiểm tra forward pass qua mạng nơ-ron QNetwork."""
        net = QNetwork(state_dim=11, action_dim=2, hidden_dims=(32, 32))
        x = torch.randn(4, 11)
        out = net(x)
        self.assertEqual(out.shape, (4, 2))

    def test_dqn_agent_update_and_target_sync(self) -> None:
        """Kiểm tra tối ưu hóa Bellman và đồng bộ hóa target network."""
        agent = DQNAgent(state_dim=11, action_dim=2, lr=1e-3, buffer_size=100)
        s = np.zeros(11, dtype=np.float32)
        s_next = np.ones(11, dtype=np.float32)

        # Đẩy đủ dữ liệu vào buffer cho batch_size = 4
        for i in range(10):
            agent.replay_buffer.push(s, i % 2, -1.0, s_next, False)

        loss = agent.update(batch_size=4)
        self.assertIsNotNone(loss)
        self.assertIsInstance(loss, float)

        # Kiểm tra sync target network
        agent.policy_net.network[0].weight.data.fill_(0.5)
        agent.sync_target_network(tau=1.0)
        self.assertTrue(
            torch.equal(
                agent.policy_net.network[0].weight,
                agent.target_net.network[0].weight,
            )
        )

    def test_multi_intersection_isolation(self) -> None:
        """Kiểm tra IDQN: mỗi ngã tư có một DQNAgent độc lập."""
        ctrl = DQNController(minimum_green_seconds=10.0, learning=True)
        obs_a = MockObservation(
            tls_id="tls_A", current_phase=0, green_elapsed=15.0,
            lane_vehicle_count={"in_1": 1, "out_1": 0, "in_2": 1, "out_2": 0},
            phase_movements=self.movements,
        )
        obs_b = MockObservation(
            tls_id="tls_B", current_phase=0, green_elapsed=15.0,
            lane_vehicle_count={"in_1": 10, "out_1": 0, "in_2": 10, "out_2": 0},
            phase_movements=self.movements,
        )

        ctrl.select_phase(obs_a)
        ctrl.select_phase(obs_b)

        agent_a = ctrl.agents.get("tls_A")
        agent_b = ctrl.agents.get("tls_B")
        self.assertIsNotNone(agent_a)
        self.assertIsNotNone(agent_b)
        self.assertIsNot(agent_a, agent_b)

    def test_save_and_load_model(self) -> None:
        """Kiểm tra lưu và nạp checkpoint (.pt) của mô hình DQN."""
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / "dqn_test.pt"
            ctrl = DQNController()
            obs = MockObservation(
                tls_id="tls_1", current_phase=0, green_elapsed=15.0,
                lane_vehicle_count={"in_1": 2, "out_1": 0, "in_2": 4, "out_2": 0},
                phase_movements=self.movements,
            )
            ctrl.select_phase(obs)
            # Thay đổi một trọng số để kiểm chứng
            agent = ctrl.agents["tls_1"]
            with torch.no_grad():
                agent.policy_net.network[0].weight.fill_(0.777)
            ctrl.save_model(model_path)
            self.assertTrue(model_path.is_file())

            # Nạp vào controller mới
            ctrl2 = DQNController(model_path=model_path)
            # Khởi tạo agent bằng observation
            ctrl2.select_phase(obs)
            agent2 = ctrl2.agents["tls_1"]
            self.assertTrue(
                torch.allclose(
                    agent2.policy_net.network[0].weight,
                    agent.policy_net.network[0].weight,
                )
            )

    def test_tie_breaking_favors_current_phase(self) -> None:
        """Kiểm tra cơ chế Hysteresis: khi các Q-value hòa nhau, ưu tiên giữ nguyên pha hiện tại."""
        ctrl = DQNController(minimum_green_seconds=10.0, learning=False, epsilon=0.0)
        obs = MockObservation(
            tls_id="tls_1", current_phase=0, green_elapsed=15.0,
            lane_vehicle_count={"in_1": 3, "out_1": 0, "in_2": 3, "out_2": 0},
            phase_movements=self.movements,
        )
        vec = ctrl.vectorize_observation(obs)
        agent = ctrl.get_or_create_agent("tls_1", len(vec), 2)
        # Giả lập Q-values hòa nhau hoàn toàn
        with torch.no_grad():
            agent.policy_net.network[-1].bias.fill_(1.0)
            agent.policy_net.network[-1].weight.zero_()

        # Pha 0 -> giữ nguyên pha 0
        action = ctrl.select_phase(obs)
        self.assertEqual(action, 0)

        # Pha 1 -> giữ nguyên pha 1
        obs.current_phase = 1
        action1 = ctrl.select_phase(obs)
        self.assertEqual(action1, 1)

    def test_safe_cycling_on_unvisited_state_after_long_green(self) -> None:
        """Kiểm tra chống kẹt pha: khi unvisited/hòa điểm mà đã xanh quá 30s, an toàn chuyển pha kế tiếp."""
        ctrl = DQNController(minimum_green_seconds=10.0, learning=False, epsilon=0.0)
        obs = MockObservation(
            tls_id="tls_1", current_phase=0, green_elapsed=35.0,  # Xanh 35s (> 30s)
            lane_vehicle_count={"in_1": 0, "out_1": 0, "in_2": 5, "out_2": 0},
            phase_movements=self.movements,
        )
        vec = ctrl.vectorize_observation(obs)
        agent = ctrl.get_or_create_agent("tls_1", len(vec), 2)
        with torch.no_grad():
            agent.policy_net.network[-1].bias.zero_()
            agent.policy_net.network[-1].weight.zero_()

        action = ctrl.select_phase(obs)
        self.assertEqual(action, 1)

    def test_decay_epsilon(self) -> None:
        """Kiểm tra suy giảm epsilon qua từng episode."""
        ctrl = DQNController(epsilon=0.5)
        new_eps = ctrl.decay_epsilon(decay_rate=0.8, min_epsilon=0.05)
        self.assertAlmostEqual(new_eps, 0.4)
        for _ in range(20):
            ctrl.decay_epsilon(decay_rate=0.5, min_epsilon=0.05)
        self.assertEqual(ctrl.epsilon, 0.05)

    def test_reward_types(self) -> None:
        """Kiểm tra các hàm mục tiêu phần thưởng chuẩn RESCO (queue, delay, pressure)."""
        obs = MockObservation(
            tls_id="tls_1", current_phase=0, green_elapsed=15.0,
            lane_vehicle_count={"in_1": 5, "out_1": 1, "in_2": 3, "out_2": 0},
            phase_movements=self.movements,
            lane_halting_count={"in_1": 4, "in_2": 2},
            lane_waiting_time={"in_1": 20.0, "in_2": 10.0},
        )
        ctrl_q = DQNController(reward_type="queue")
        self.assertEqual(ctrl_q._compute_reward(obs, switched=False), -6.0)

        ctrl_d = DQNController(reward_type="delay")
        self.assertEqual(ctrl_d._compute_reward(obs, switched=False), -30.0)

        ctrl_p = DQNController(reward_type="pressure")
        self.assertEqual(ctrl_p._compute_reward(obs, switched=False), -3.0)

    def test_replay_buffer_during_minimum_green(self) -> None:
        """Kiểm tra: khi vướng G_min, Replay Buffer VẪN ĐƯỢC PUSH transition trước đó và agent vẫn cập nhật."""
        ctrl = DQNController(
            minimum_green_seconds=10.0,
            learning=True,
            batch_size=2,
            buffer_size=100,
            epsilon=0.0,
        )
        # Giả lập transition trước đó ở state s1, action 1
        s1 = np.zeros(11, dtype=np.float32)
        ctrl.last_state_action["tls_1"] = (s1, 1, 0)

        obs2 = MockObservation(
            tls_id="tls_1",
            current_phase=1,
            green_elapsed=4.0,  # Chưa đủ G_min = 10s!
            lane_vehicle_count={"in_1": 2, "out_1": 0, "in_2": 4, "out_2": 0},
            phase_movements=self.movements,
        )

        agent = ctrl.get_or_create_agent("tls_1", 11, 2)
        initial_buffer_len = len(agent.replay_buffer)
        self.assertEqual(initial_buffer_len, 0)

        action = ctrl.select_phase(obs2)

        # 1. Action phải là giữ nguyên pha 1 do an toàn G_min
        self.assertEqual(action, 1)

        # 2. Replay Buffer PHẢI ĐƯỢC PUSH transition vừa hoàn thành (s1, 1, reward, s2, False)
        self.assertEqual(len(agent.replay_buffer), 1)

        # 3. last_state_action phải ghi nhận bước hiện tại để tiếp tục chuỗi MDP
        self.assertIn("tls_1", ctrl.last_state_action)
        cur_s, cur_a, cur_p = ctrl.last_state_action["tls_1"]
        self.assertEqual(cur_a, 1)
        self.assertEqual(cur_p, 1)

    def test_dimension_adaptation_on_scenario_switch(self) -> None:
        """Kiểm tra: khi đổi kịch bản ngã tư có số chiều khác nhau, agent tự động tái khởi tạo thích ứng mà không crash."""
        ctrl = DQNController()
        # Khởi tạo agent ban đầu với 11 chiều và 2 action
        agent1 = ctrl.get_or_create_agent("tls_1", state_dim=11, action_dim=2)
        self.assertEqual(agent1.state_dim, 11)
        self.assertEqual(agent1.action_dim, 2)

        # Chuyển sang ngã tư mới cùng ID nhưng có 16 chiều và 3 action
        agent2 = ctrl.get_or_create_agent("tls_1", state_dim=16, action_dim=3)
        self.assertEqual(agent2.state_dim, 16)
        self.assertEqual(agent2.action_dim, 3)
        self.assertIsNot(agent1, agent2)


if __name__ == "__main__":
    unittest.main()
