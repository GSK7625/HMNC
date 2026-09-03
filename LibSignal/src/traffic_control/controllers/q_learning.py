"""Bộ điều khiển đèn giao thông theo thuật toán Q-Learning (Tabular Q-Learning)."""

from __future__ import annotations

import json
import random
from pathlib import Path

from .base import BaseController
from .registry import register_controller

DEFAULT_Q_TABLE_PATH = Path("checkpoints/q_table.json")


@register_controller(
    name="qlearning",
    aliases=["ql"],
    display_name="Q-Learning",
    description="Học máy tăng cường Tabular Q-Learning tối ưu theo hàng đợi xe",
)
class QLearningController(BaseController):
    """Bộ điều khiển đèn giao thông sử dụng Tabular Q-Learning.

    Nguyên lý:
    1. Trạng thái (State):
       - Rời rạc hóa số lượng xe trên các làn vào của từng pha đèn thành 3 mức:
         0 (Thấp: <= 3 xe), 1 (Vừa: 4-8 xe), 2 (Cao: > 8 xe).
       - State key có dạng: "<current_phase>:<bin_p0>,<bin_p1>,..."
    2. Hành động (Action):
       - Chỉ số pha đèn xanh tiếp theo (0, 1, ..., num_phases - 1).
       - An toàn: Chỉ đổi pha khi pha hiện tại đã sáng ít nhất `minimum_green_seconds`.
    3. Phần thưởng (Reward):
       - R = - (Tổng số xe trên các làn vào ngã tư) - Phạt đổi pha (nếu có).
    4. Cập nhật Bellman:
       - Q(s, a) = Q(s, a) + alpha * [r + gamma * max_a'(Q(s', a')) - Q(s, a)].
    """

    def __init__(
        self,
        minimum_green_seconds: float = 10.0,
        alpha: float = 0.1,
        gamma: float = 0.9,
        epsilon: float = 0.05,
        learning: bool = True,
        reward_type: str = "queue",
        q_table: dict | None = None,
        q_table_path: Path | str | None = None,
        **kwargs,
    ):
        super().__init__(minimum_green_seconds=minimum_green_seconds, **kwargs)

        if not (0.0 <= alpha <= 1.0):
            raise ValueError("alpha (learning rate) phải nằm trong khoảng [0, 1]")
        if not (0.0 <= gamma <= 1.0):
            raise ValueError("gamma (discount factor) phải nằm trong khoảng [0, 1]")
        if not (0.0 <= epsilon <= 1.0):
            raise ValueError("epsilon phải nằm trong khoảng [0, 1]")

        self.alpha = float(alpha)
        self.gamma = float(gamma)
        self.epsilon = float(epsilon)
        self.learning = bool(learning)
        self.reward_type = str(reward_type).lower()
        self.name = "qlearning"
        self.display_name = "Q-Learning"

        # Bảng Q đa ngã tư: {tls_id: {state_key: [q_action_0, q_action_1, ...]}}
        # Tương đương kiến trúc Decentralized Independent Q-Learning (IDQL / IDQN) trong RESCO
        self.q_tables: dict[str, dict[str, list[float]]] = {}
        if q_table is not None:
            self.q_tables["default_tls"] = q_table

        # Lưu vết (state, action) trước đó của từng cụm đèn: {tls_id: (prev_state, prev_action)}
        self.last_state_action: dict[str, tuple[str, int]] = {}

        if q_table_path:
            path = Path(q_table_path)
            if path.is_file():
                self.load_q_table(path)

    @property
    def q_table(self) -> dict[str, list[float]]:
        """Hỗ trợ tương thích ngược cho các đoạn mã hoặc bài test truy cập trực tiếp ctrl.q_table."""
        if not self.q_tables:
            self.q_tables["default_tls"] = {}
            return self.q_tables["default_tls"]
        if "default_tls" in self.q_tables:
            return self.q_tables["default_tls"]
        # Trả về bảng Q của ngã tư đầu tiên
        return next(iter(self.q_tables.values()))

    @q_table.setter
    def q_table(self, value: dict[str, list[float]]) -> None:
        self.q_tables["default_tls"] = value

    def get_tls_table(self, tls_id: str) -> dict[str, list[float]]:
        """Lấy bảng Q riêng biệt cho ngã tư cụ thể (ngăn chặn xung đột ghi đè giữa các ngã tư)."""
        if tls_id not in self.q_tables:
            # Nếu chỉ có default_tls duy nhất vừa được khởi tạo, gán chuyển sang tls_id này
            if "default_tls" in self.q_tables and len(self.q_tables) == 1 and not self.q_tables["default_tls"]:
                del self.q_tables["default_tls"]
                self.q_tables[tls_id] = {}
            elif "default_tls" in self.q_tables and len(self.q_tables) == 1 and self.q_tables["default_tls"]:
                # Có dữ liệu nạp sẵn từ single table
                self.q_tables[tls_id] = self.q_tables.pop("default_tls")
            else:
                self.q_tables[tls_id] = {}
        return self.q_tables[tls_id]

    def reset(self, seed: int | None = None):
        """Đặt lại bộ nhớ trạng thái trước đó giữa các episode."""
        self.last_state_action.clear()

    @staticmethod
    def _discretize_vehicle_count(count: int) -> int:
        """Rời rạc hóa số lượng xe chờ thành 3 mức: 0 (thấp), 1 (vừa), 2 (cao)."""
        if count <= 3:
            return 0
        if count <= 8:
            return 1
        return 2

    def discretize_observation(self, observation) -> str:
        """Chuyển đổi dữ liệu IntersectionObservation thành khóa trạng thái rời rạc."""
        # Ưu tiên sử dụng số xe dừng chờ nếu có, fallback về tổng xe
        counts = (
            observation.lane_halting_count
            if getattr(observation, "lane_halting_count", None)
            else observation.lane_vehicle_count or {}
        )
        phase_bins = []
        for movements in observation.phase_movements:
            # Lấy danh sách làn vào duy nhất của pha này
            in_lanes = {in_lane for in_lane, _ in movements if in_lane}
            total_in = sum(counts.get(lane, 0) for lane in in_lanes)
            phase_bins.append(str(self._discretize_vehicle_count(total_in)))

        return f"{observation.current_phase}:{','.join(phase_bins)}"

    def _compute_reward(self, observation, switched: bool) -> float:
        """Tính phần thưởng âm dựa trên hàm mục tiêu quy định (chuẩn hóa theo RESCO)."""
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
            # Mặc định "queue" (số xe dừng chờ / hàng đợi theo chuẩn RESCO RLCD/Queue)
            haltings = getattr(observation, "lane_halting_count", None)
            if haltings:
                metric_val = sum(haltings.get(lane, 0) for lane in all_in_lanes)
            else:
                metric_val = sum(observation.lane_vehicle_count.get(lane, 0) for lane in all_in_lanes)

        return -float(metric_val + switch_penalty)

    def select_phase(self, observation):
        """Lựa chọn pha đèn tiếp theo dựa trên chính sách Q-Learning và cập nhật Bellman."""
        # 1. An toàn: nếu chưa hết thời gian xanh tối thiểu thì giữ nguyên pha
        if observation.green_elapsed < self.minimum_green_seconds:
            return observation.current_phase

        tls_id = getattr(observation, "tls_id", "default_tls")
        num_phases = len(observation.phase_movements)
        current_state = self.discretize_observation(observation)
        tls_table = self.get_tls_table(tls_id)

        # Đảm bảo state hiện tại có trong Q-table của ngã tư này
        if current_state not in tls_table:
            tls_table[current_state] = [0.0] * num_phases

        # 2. Cập nhật Bellman nếu đang ở chế độ học và có trạng thái trước đó
        if self.learning and tls_id in self.last_state_action:
            prev_state, prev_action = self.last_state_action[tls_id]
            if prev_state not in tls_table:
                tls_table[prev_state] = [0.0] * num_phases

            prev_phase = int(prev_state.split(":")[0])
            switched = prev_action != prev_phase
            reward = self._compute_reward(observation, switched)

            max_next_q = max(tls_table[current_state])
            old_q = tls_table[prev_state][prev_action]

            # Bellman update formula
            td_target = reward + self.gamma * max_next_q
            tls_table[prev_state][prev_action] = old_q + self.alpha * (td_target - old_q)

        # 3. Chọn hành động tiếp theo theo chiến lược Epsilon-Greedy
        if self.learning and random.random() < self.epsilon:
            action = random.randint(0, num_phases - 1)
        else:
            q_values = tls_table[current_state]
            max_q = max(q_values)
            # Tie-breaking thông minh: Nếu tất cả Q-values bằng nhau (vd: trạng thái mới khi eval)
            # hoặc pha hiện tại nằm trong nhóm Q-value tối đa -> ưu tiên giữ nguyên pha hiện tại
            # để tránh kích hoạt đèn vàng lãng phí (Action Hysteresis)
            best_actions = [i for i, v in enumerate(q_values) if v == max_q]
            if observation.current_phase in best_actions:
                action = observation.current_phase
            else:
                action = best_actions[0]

        # 4. Ghi nhận cho lần cập nhật bước kế tiếp
        if self.learning:
            self.last_state_action[tls_id] = (current_state, action)

        return action

    def decay_epsilon(self, decay_rate: float = 0.9, min_epsilon: float = 0.01) -> float:
        """Giảm dần tỷ lệ khám phá epsilon qua các episode huấn luyện."""
        self.epsilon = max(float(min_epsilon), self.epsilon * float(decay_rate))
        return self.epsilon

    DEFAULT_Q_TABLE_PATH = DEFAULT_Q_TABLE_PATH

    def save_q_table(self, filepath: Path | str | None = None):
        """Lưu bảng Q ra file JSON (hỗ trợ cả đơn ngã tư và đa ngã tư MARL)."""
        path = Path(filepath) if filepath is not None else self.DEFAULT_Q_TABLE_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            # Nếu chỉ có 1 ngã tư duy nhất, lưu dạng phẳng để giữ tương thích ngược hoàn hảo
            if len(self.q_tables) == 1 and "default_tls" in self.q_tables:
                json.dump(self.q_tables["default_tls"], f, indent=2, ensure_ascii=False)
            else:
                json.dump(self.q_tables, f, indent=2, ensure_ascii=False)

    def load_q_table(self, filepath: Path | str | None = None):
        """Đọc bảng Q từ file JSON (tự động nhận diện cấu trúc đơn hay đa ngã tư)."""
        path = Path(filepath) if filepath is not None else self.DEFAULT_Q_TABLE_PATH
        if not path.is_file():
            raise FileNotFoundError(f"Không tìm thấy file Q-table tại: {path}")
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        self.q_tables.clear()
        if not data:
            return

        # Kiểm tra dữ liệu là flat table {state: [q]} hay nested table {tls_id: {state: [q]}}
        first_val = next(iter(data.values()))
        if isinstance(first_val, list):
            self.q_tables["default_tls"] = {
                str(k): [float(v) for v in vals] for k, vals in data.items()
            }
        elif isinstance(first_val, dict):
            for tls_id, table in data.items():
                self.q_tables[str(tls_id)] = {
                    str(k): [float(v) for v in vals] for k, vals in table.items()
                }
