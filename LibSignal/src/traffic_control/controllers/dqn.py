"""Bộ điều khiển đèn giao thông theo thuật toán Deep Q-Network (DQN / Double DQN)."""

from __future__ import annotations

import collections
import os
from pathlib import Path
import random
from typing import TYPE_CHECKING

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

from .base import BaseController
from .registry import register_controller

if TYPE_CHECKING:
    from ..core.observation import IntersectionObservation

DEFAULT_DQN_MODEL_PATH = Path("checkpoints/dqn_model.pt")


class QNetwork(nn.Module):
    """Mạng nơ-ron đa tầng (MLP) xấp xỉ hàm giá trị Q(s, a)."""

    def __init__(self, state_dim: int, action_dim: int, hidden_dims: tuple[int, ...] = (64, 64)):
        super().__init__()
        layers: list[nn.Module] = []
        prev_dim = state_dim
        for h_dim in hidden_dims:
            layers.append(nn.Linear(prev_dim, h_dim))
            layers.append(nn.ReLU())
            prev_dim = h_dim
        layers.append(nn.Linear(prev_dim, action_dim))
        self.network = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.network(x)


class ReplayBuffer:
    """Bộ nhớ đệm tái hiện trải nghiệm (Experience Replay Buffer)."""

    def __init__(self, capacity: int = 5000):
        self.buffer: collections.deque = collections.deque(maxlen=int(capacity))

    def push(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        next_state: np.ndarray,
        done: bool = False,
    ) -> None:
        self.buffer.append((
            np.asarray(state, dtype=np.float32),
            int(action),
            float(reward),
            np.asarray(next_state, dtype=np.float32),
            bool(done),
        ))

    def sample(
        self,
        batch_size: int,
        device: torch.device,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        batch = random.sample(self.buffer, batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)

        states_t = torch.tensor(np.array(states), dtype=torch.float32, device=device)
        actions_t = torch.tensor(actions, dtype=torch.int64, device=device)
        rewards_t = torch.tensor(rewards, dtype=torch.float32, device=device)
        next_states_t = torch.tensor(np.array(next_states), dtype=torch.float32, device=device)
        dones_t = torch.tensor(dones, dtype=torch.float32, device=device)

        return states_t, actions_t, rewards_t, next_states_t, dones_t

    def __len__(self) -> int:
        return len(self.buffer)


class DQNAgent:
    """Agent DQN độc lập quản lý mạng nơ-ron chính, mạng mục tiêu và bộ tối ưu hóa."""

    def __init__(
        self,
        state_dim: int,
        action_dim: int,
        lr: float = 1e-3,
        gamma: float = 0.95,
        buffer_size: int = 5000,
        hidden_dims: tuple[int, ...] = (64, 64),
        double_dqn: bool = True,
        device: torch.device | None = None,
    ):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.gamma = float(gamma)
        self.double_dqn = bool(double_dqn)
        self.device = device or torch.device("cpu")

        self.policy_net = QNetwork(state_dim, action_dim, hidden_dims).to(self.device)
        self.target_net = QNetwork(state_dim, action_dim, hidden_dims).to(self.device)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.target_net.eval()

        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=float(lr))
        self.loss_fn = nn.SmoothL1Loss()
        self.replay_buffer = ReplayBuffer(capacity=buffer_size)

    def get_q_values(self, state: np.ndarray) -> np.ndarray:
        """Tính toán giá trị Q cho tất cả các hành động từ trạng thái s."""
        state_t = torch.tensor(state, dtype=torch.float32, device=self.device).unsqueeze(0)
        self.policy_net.eval()
        with torch.no_grad():
            q_vals = self.policy_net(state_t).squeeze(0).cpu().numpy()
        return q_vals

    def update(self, batch_size: int) -> float | None:
        """Thực hiện một bước tối ưu hóa Bellman từ mẫu ngẫu nhiên trong Replay Buffer."""
        if len(self.replay_buffer) < batch_size:
            return None

        states, actions, rewards, next_states, dones = self.replay_buffer.sample(
            batch_size, self.device
        )

        self.policy_net.train()
        # Q(s, a) hiện tại
        q_eval = self.policy_net(states).gather(1, actions.unsqueeze(1)).squeeze(1)

        # Tính target Q theo chuẩn Double DQN hoặc DQN thông thường
        with torch.no_grad():
            if self.double_dqn:
                # Double DQN: Policy net chọn action tốt nhất, Target net đánh giá Q-value
                best_actions = self.policy_net(next_states).argmax(dim=1, keepdim=True)
                next_q = self.target_net(next_states).gather(1, best_actions).squeeze(1)
            else:
                # Standard DQN: max_{a'} Q_target(s', a')
                next_q = self.target_net(next_states).max(dim=1)[0]

            q_target = rewards + (1.0 - dones) * self.gamma * next_q

        loss = self.loss_fn(q_eval, q_target)

        self.optimizer.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(self.policy_net.parameters(), max_norm=1.0)
        self.optimizer.step()

        return float(loss.item())

    def sync_target_network(self, tau: float = 1.0) -> None:
        """Đồng bộ trọng số mạng đích (Hard update khi tau=1.0, Soft update khi tau < 1.0)."""
        if tau >= 1.0:
            self.target_net.load_state_dict(self.policy_net.state_dict())
        else:
            for target_param, policy_param in zip(
                self.target_net.parameters(), self.policy_net.parameters()
            ):
                target_param.data.copy_(
                    tau * policy_param.data + (1.0 - tau) * target_param.data
                )


@register_controller(
    name="dqn",
    aliases=["deepq", "deep_q"],
    display_name="DQN",
    description="Học tăng cường sâu Deep Q-Network (Mnih et al.) với Replay Buffer & Target Network",
)
class DQNController(BaseController):
    """Bộ điều khiển đèn giao thông sử dụng Deep Q-Network (DQN / Double DQN).

    Đặc tính kỹ thuật:
    1. Trạng thái (State): Vector thực liên tục chuẩn hóa (Continuous State Vector):
       - Số xe chờ / hàng đợi mỗi pha: count / 20.0
       - Tổng số xe mỗi pha: count / 20.0
       - Thời gian chờ tích lũy mỗi pha: waiting_time / 100.0
       - Áp lực xe mỗi pha: pressure / 20.0
       - One-hot vector pha đèn hiện tại
       - Thời gian xanh hiện tại đã sáng: min(green_elapsed / 60.0, 1.0)
    2. Hành động (Action): Chỉ số pha đèn xanh tiếp theo (0, ..., num_phases - 1).
    3. Trải nghiệm (Experience Replay): Buffer decorrelate các mẫu dữ liệu giao thông liên tiếp.
    4. Mạng mục tiêu (Target Network): Ổn định mục tiêu tối ưu Bellman với Double DQN.
    5. Đa ngã tư (Decentralized IDQN): Mỗi ngã tư có thể sở hữu agent riêng biệt hoặc kế thừa tri thức.
    """

    DEFAULT_MODEL_PATH = DEFAULT_DQN_MODEL_PATH

    def __init__(
        self,
        minimum_green_seconds: float = 10.0,
        lr: float = 1e-3,
        alpha: float | None = None,
        gamma: float = 0.95,
        epsilon: float = 0.05,
        learning: bool = True,
        batch_size: int = 32,
        buffer_size: int = 5000,
        target_update_interval: int = 20,
        tau: float = 1.0,
        hidden_dims: tuple[int, ...] = (64, 64),
        reward_type: str = "queue",
        double_dqn: bool = True,
        model_path: Path | str | None = None,
        device: str | None = None,
        **kwargs,
    ):
        super().__init__(minimum_green_seconds=minimum_green_seconds, **kwargs)

        learning_rate = float(alpha) if alpha is not None else float(lr)
        if learning_rate <= 0:
            raise ValueError("learning_rate (hoặc alpha) phải lớn hơn 0")
        if not (0.0 <= gamma <= 1.0):
            raise ValueError("gamma phải nằm trong khoảng [0, 1]")
        if not (0.0 <= epsilon <= 1.0):
            raise ValueError("epsilon phải nằm trong khoảng [0, 1]")
        if batch_size <= 0 or buffer_size <= 0:
            raise ValueError("batch_size và buffer_size phải lớn hơn 0")

        self.lr = learning_rate
        self.gamma = float(gamma)
        self.epsilon = float(epsilon)
        self.learning = bool(learning)
        self.batch_size = int(batch_size)
        self.buffer_size = int(buffer_size)
        self.target_update_interval = int(target_update_interval)
        self.tau = float(tau)
        self.hidden_dims = tuple(int(x) for x in hidden_dims)
        self.reward_type = str(reward_type).lower()
        self.double_dqn = bool(double_dqn)
        self.name = "dqn"
        self.display_name = "DQN"

        if device:
            self.device = torch.device(device)
        else:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Quản lý agent theo từng cụm đèn: {tls_id: DQNAgent}
        self.agents: dict[str, DQNAgent] = {}
        # Lưu vết (state, action, current_phase) trước đó: {tls_id: (state, action, prev_phase)}
        self.last_state_action: dict[str, tuple[np.ndarray, int, int]] = {}
        self.step_counts: dict[str, int] = {}
        self.losses: dict[str, list[float]] = {}

        if model_path:
            p = Path(model_path)
            if p.is_file():
                self.load_model(p)

    def get_or_create_agent(self, tls_id: str, state_dim: int, action_dim: int) -> DQNAgent:
        """Lấy agent hiện có hoặc khởi tạo agent mới cho ngã tư cụ thể."""
        if (
            tls_id not in self.agents
            or self.agents[tls_id].state_dim != state_dim
            or self.agents[tls_id].action_dim != action_dim
        ):
            agent = DQNAgent(
                state_dim=state_dim,
                action_dim=action_dim,
                lr=self.lr,
                gamma=self.gamma,
                buffer_size=self.buffer_size,
                hidden_dims=self.hidden_dims,
                double_dqn=self.double_dqn,
                device=self.device,
            )
            # Cơ chế Transfer Prior: nếu có agent khác cùng kích thước đã học, sao chép trọng số
            for other_id, other_agent in self.agents.items():
                if (
                    other_id != tls_id
                    and other_agent.state_dim == state_dim
                    and other_agent.action_dim == action_dim
                ):
                    agent.policy_net.load_state_dict(other_agent.policy_net.state_dict())
                    agent.target_net.load_state_dict(other_agent.target_net.state_dict())
                    break

            self.agents[tls_id] = agent
            self.step_counts[tls_id] = 0

        return self.agents[tls_id]

    def reset(self, seed: int | None = None) -> None:
        """Đặt lại bộ nhớ vết chuyển trạng thái giữa các episode."""
        self.last_state_action.clear()

    def vectorize_observation(self, observation: IntersectionObservation) -> np.ndarray:
        """Chuyển đổi IntersectionObservation thành vector trạng thái số thực liên tục."""
        num_phases = len(observation.phase_movements)
        haltings = (
            observation.lane_halting_count
            if getattr(observation, "lane_halting_count", None)
            else observation.lane_vehicle_count or {}
        )
        veh_counts = observation.lane_vehicle_count or {}
        waiting_times = getattr(observation, "lane_waiting_time", {}) or {}
        pressures = self.phase_pressures(observation, use_halting=True)

        features: list[float] = []

        # 1. Trích xuất đặc trưng từng pha đèn (Queue, Vehicles, Waiting Time, Pressure)
        for p in range(num_phases):
            movements = observation.phase_movements[p]
            in_lanes = {in_lane for in_lane, _ in movements if in_lane}

            q_val = sum(haltings.get(lane, 0) for lane in in_lanes) / 20.0
            v_val = sum(veh_counts.get(lane, 0) for lane in in_lanes) / 20.0
            w_val = sum(waiting_times.get(lane, 0.0) for lane in in_lanes) / 100.0
            p_val = (pressures[p] if p < len(pressures) else 0.0) / 20.0

            features.extend([q_val, v_val, w_val, p_val])

        # 2. One-hot encoding của pha hiện tại
        one_hot = [0.0] * num_phases
        if 0 <= observation.current_phase < num_phases:
            one_hot[observation.current_phase] = 1.0
        features.extend(one_hot)

        # 3. Thời gian xanh đã sáng chuẩn hóa
        green_norm = min(float(observation.green_elapsed) / 60.0, 1.0)
        features.append(green_norm)

        return np.array(features, dtype=np.float32)

    def _compute_reward(self, observation: IntersectionObservation, switched: bool) -> float:
        """Tính phần thưởng âm chuẩn hóa theo RESCO (queue, delay, pressure)."""
        all_in_lanes = {
            in_lane
            for movements in observation.phase_movements
            for in_lane, _ in movements
            if in_lane
        }
        switch_penalty = 1.0 if switched else 0.0

        if self.reward_type == "delay":
            waiting_times = getattr(observation, "lane_waiting_time", {}) or {}
            metric_val = sum(waiting_times.get(lane, 0.0) for lane in all_in_lanes)
        elif self.reward_type == "pressure":
            pressures = self.phase_pressures(observation, use_halting=True)
            metric_val = abs(pressures[observation.current_phase]) if pressures else 0.0
        else:
            # Mặc định "queue" (số xe dừng chờ / hàng đợi)
            haltings = getattr(observation, "lane_halting_count", None)
            if haltings:
                metric_val = sum(haltings.get(lane, 0) for lane in all_in_lanes)
            else:
                metric_val = sum(observation.lane_vehicle_count.get(lane, 0) for lane in all_in_lanes)

        return -float(metric_val + switch_penalty)

    def select_phase(self, observation: IntersectionObservation) -> int:
        """Lựa chọn pha đèn tiếp theo với Safety Guard, Replay Buffer và Deep Q-Learning."""
        # Chế độ inference thuần túy (không học): nếu chưa hết G_min thì bắt buộc giữ nguyên pha
        if not self.learning and observation.green_elapsed < self.minimum_green_seconds:
            return observation.current_phase

        tls_id = getattr(observation, "tls_id", "default_tls")
        num_phases = len(observation.phase_movements)
        current_state = self.vectorize_observation(observation)
        agent = self.get_or_create_agent(tls_id, len(current_state), num_phases)

        # 1. Cập nhật Replay Buffer và huấn luyện mạng nếu có transition trước đó
        # THỰC HIỆN TRƯỚC HẾT để Replay Buffer không bao giờ bỏ sót mẫu dữ liệu khi vướng G_min!
        if self.learning and tls_id in self.last_state_action:
            prev_state, prev_action, prev_phase = self.last_state_action[tls_id]
            switched = (prev_action != prev_phase)
            reward = self._compute_reward(observation, switched)

            agent.replay_buffer.push(
                state=prev_state,
                action=prev_action,
                reward=reward,
                next_state=current_state,
                done=False,
            )

            # Thực hiện bước cập nhật mạng nơ-ron
            loss = agent.update(self.batch_size)
            if loss is not None:
                self.losses.setdefault(tls_id, []).append(loss)

            self.step_counts[tls_id] += 1
            if self.step_counts[tls_id] % self.target_update_interval == 0:
                agent.sync_target_network(self.tau)

        # 2. An toàn: nếu chưa hết thời gian xanh tối thiểu (G_min), bắt buộc giữ nguyên pha (Action Masking)
        if observation.green_elapsed < self.minimum_green_seconds:
            action = observation.current_phase
            if self.learning:
                self.last_state_action[tls_id] = (current_state, action, observation.current_phase)
            return action

        # 3. Chọn hành động theo Epsilon-Greedy
        if self.learning and random.random() < self.epsilon:
            action = random.randint(0, num_phases - 1)
        else:
            q_values = agent.get_q_values(current_state)
            max_q = float(np.max(q_values))
            min_q = float(np.min(q_values))
            best_actions = [i for i, v in enumerate(q_values) if abs(v - max_q) < 1e-5]

            all_equal = abs(max_q - min_q) < 1e-5

            if all_equal and not self.learning:
                # Chống kẹt pha khi mạng chưa học: nếu đã xanh quá 30s, an toàn chuyển pha kế tiếp
                if observation.green_elapsed >= 30.0:
                    action = (observation.current_phase + 1) % num_phases
                else:
                    action = observation.current_phase
            elif observation.current_phase in best_actions:
                # Hysteresis: ưu tiên giữ nguyên pha hiện tại nếu điểm số bằng nhau để tránh nhảy đèn
                action = observation.current_phase
            else:
                action = int(np.argmax(q_values))

        # 4. Ghi nhận cho lần cập nhật bước kế tiếp
        if self.learning:
            self.last_state_action[tls_id] = (current_state, action, observation.current_phase)

        return action

    def decay_epsilon(self, decay_rate: float = 0.9, min_epsilon: float = 0.01) -> float:
        """Giảm dần tỷ lệ khám phá epsilon qua các episode huấn luyện."""
        self.epsilon = max(float(min_epsilon), self.epsilon * float(decay_rate))
        return self.epsilon

    def save_model(self, filepath: Path | str | None = None) -> None:
        """Lưu trọng số các mạng DQN ra file PyTorch (.pt)."""
        path = Path(filepath) if filepath is not None else self.DEFAULT_MODEL_PATH
        path.parent.mkdir(parents=True, exist_ok=True)

        checkpoint_data = {
            "version": "1.0",
            "hidden_dims": self.hidden_dims,
            "double_dqn": self.double_dqn,
            "agents": {},
        }
        for tls_id, agent in self.agents.items():
            checkpoint_data["agents"][tls_id] = {
                "state_dim": agent.state_dim,
                "action_dim": agent.action_dim,
                "policy_net": agent.policy_net.state_dict(),
                "target_net": agent.target_net.state_dict(),
            }

        torch.save(checkpoint_data, path)

    def load_model(self, filepath: Path | str | None = None) -> None:
        """Nạp trọng số mô hình DQN từ file PyTorch (.pt)."""
        path = Path(filepath) if filepath is not None else self.DEFAULT_MODEL_PATH
        if not path.is_file():
            raise FileNotFoundError(f"Không tìm thấy file checkpoint DQN tại: {path}")

        checkpoint_data = torch.load(path, map_location=self.device)
        agents_data = checkpoint_data.get("agents", {})

        for tls_id, a_data in agents_data.items():
            state_dim = a_data["state_dim"]
            action_dim = a_data["action_dim"]
            agent = self.get_or_create_agent(tls_id, state_dim, action_dim)
            agent.policy_net.load_state_dict(a_data["policy_net"])
            agent.target_net.load_state_dict(a_data["target_net"])
            agent.policy_net.eval()
            agent.target_net.eval()
