"""Bộ điều khiển đèn giao thông theo thời gian cố định (Fixed-Time / FT)."""

from __future__ import annotations

from .base import BaseController
from .registry import register_controller


@register_controller(
    name="fixedtime",
    aliases=["ft"],
    display_name="Fixed-Time",
    description="Chuyển pha tuần tự theo chu kỳ thời gian cố định",
)
class FixedTimeController(BaseController):
    """Bộ điều khiển Fixed-Time: Chuyển pha tuần tự sau mỗi khoảng thời gian cố định.

    Thuật toán hoạt động theo chu kỳ thời gian xác định trước.
    Đồng bộ nhịp thời gian và triệt tiêu trôi dãn do đèn vàng:
    1. Thời gian của pha (`duration`) luôn được thiết lập là bội số chính xác của chu kỳ hành động (`action_interval`).
    2. Trong mỗi chu kỳ thời gian pha, trừ đi `yellow_seconds` (mặc định 3.0s đèn vàng) để
       xác định ngưỡng đèn xanh thực tế: `target_green = duration - yellow_seconds`.
       Khi `observation.green_elapsed >= target_green`, pha chuyển đổi chính xác tại ranh giới
       bước mô phỏng, loại bỏ hoàn toàn hiện tượng trôi dãn thêm 1 action_interval.
    """

    def __init__(
        self,
        green_seconds: float = 30.0,
        minimum_green_seconds: float = 0.0,
        proportional_splits: bool = False,
        phase_splits: dict[str, list[float]] | list[float] | None = None,
        action_interval: float = 10.0,
        yellow_seconds: float = 3.0,
        webster_cycle: bool = False,
        **kwargs,
    ):
        if green_seconds <= 0:
            raise ValueError(f"green_seconds phải là số dương, nhận được: {green_seconds}")
        super().__init__(minimum_green_seconds=0.0, **kwargs)
        self.action_interval = float(action_interval)
        self.yellow_seconds = float(yellow_seconds)
        self.webster_cycle = bool(webster_cycle)

        # Thiết lập thời gian xanh là bội số chính xác của chu kỳ hành động (action_interval)
        if self.action_interval > 0:
            step = self.action_interval
            self.green_seconds = float(max(step, round(green_seconds / step) * step))
        else:
            self.green_seconds = float(green_seconds)

        self.proportional_splits = bool(proportional_splits)
        self.phase_splits = phase_splits
        self.traffic_history: dict[str, list[float]] = {}
        self.name = "fixedtime"
        self.display_name = "Fixed-Time"

    def reset(self, seed: int | None = None) -> None:
        """Đặt lại lịch sử lưu lượng xe giữa các episode/seed."""
        self.traffic_history.clear()

    def record_traffic(self, observation) -> None:
        """Ghi nhận lưu lượng xe quan sát được để tính toán tỷ số Webster equisaturation y_i = q_i / s_i."""
        tls_id = getattr(observation, "tls_id", "default_tls")
        num_phases = len(observation.phase_movements)
        if num_phases <= 0:
            return
        if tls_id not in self.traffic_history or len(self.traffic_history[tls_id]) != num_phases:
            self.traffic_history[tls_id] = [0.0] * num_phases

        counts = observation.lane_vehicle_count or {}
        for p_idx, movements in enumerate(observation.phase_movements):
            unique_in = {m[0] for m in movements if m and m[0]}
            total_veh = sum(counts.get(l, 0) for l in unique_in)
            self.traffic_history[tls_id][p_idx] += float(total_veh)

    def compute_webster_cycle(self, observation, y_ratios: list[float], num_phases: int) -> float:
        """Tính chu kỳ tối ưu Webster C_0 (1958): C_0 = (1.5 * L + 5) / (1 - Y).

        L: Tổng thời gian tổn hao mỗi chu kỳ (lost time), L = num_phases * yellow_seconds.
        Y: Tổng tỷ số lưu lượng tới hạn Y = sum(y_i).
        Ràng buộc an toàn: Y <= 0.85 (tránh phân kỳ khi tiệm cận tắc nghẽn), C_min <= C_0 <= C_max.
        """
        lost_time_per_phase = max(3.0, self.yellow_seconds)
        total_lost_time = num_phases * lost_time_per_phase

        tls_id = getattr(observation, "tls_id", "default_tls")
        history = self.traffic_history.get(tls_id)
        total_veh = sum(history) if history else 0.0

        # Ước lượng mức tải Y theo lưu lượng quan sát thực tế (bão hòa trong khoảng [0.35, 0.85])
        if total_veh > 0:
            est_y = min(0.85, max(0.35, 0.35 + 0.50 * (total_veh / (total_veh + 50.0))))
        else:
            est_y = 0.50

        # Công thức Webster 1958: C_0 = (1.5 * L + 5) / (1 - Y)
        c0 = (1.5 * total_lost_time + 5.0) / max(0.15, 1.0 - est_y)

        # Ràng buộc chu kỳ thực tế C_min <= C_0 <= C_max
        step = max(1.0, self.action_interval) if self.action_interval > 0 else 10.0
        min_cycle = max(30.0, num_phases * step)
        max_cycle = 150.0
        return float(min(max_cycle, max(min_cycle, c0)))

    def get_phase_duration(self, observation) -> float:
        """Lấy thời gian ấn định cho pha hiện tại theo chuẩn Webster (bội số của action_interval)."""
        tls_id = getattr(observation, "tls_id", "default_tls")
        num_phases = len(observation.phase_movements)
        if num_phases <= 0:
            return self.green_seconds

        # 1. Nếu có cấu hình splits tùy biến từng pha
        if self.phase_splits:
            if isinstance(self.phase_splits, dict) and tls_id in self.phase_splits:
                splits = self.phase_splits[tls_id]
                if observation.current_phase < len(splits):
                    return float(splits[observation.current_phase])
            elif isinstance(self.phase_splits, (list, tuple)) and observation.current_phase < len(self.phase_splits):
                return float(self.phase_splits[observation.current_phase])

        # 2. Nếu bật tính tỉ lệ (Chuẩn Webster Equisaturation: y_i = q_i / s_i & Chu kỳ tối ưu C_0)
        if self.proportional_splits and num_phases > 1:
            lane_counts = []
            for movements in observation.phase_movements:
                unique_in_lanes = {in_lane for in_lane, _ in movements if in_lane}
                lane_counts.append(max(1, len(unique_in_lanes)))

            # Kiểm tra xem đã có dữ liệu lưu lượng xe tích lũy thực tế chưa
            history = self.traffic_history.get(tls_id)
            total_flow = sum(history) if history else 0.0

            if history and total_flow > 0:
                # Chuẩn Webster 1958: y_i = q_i / s_i
                # q_i: lưu lượng xe thực tế, s_i: năng lực bão hòa tỷ lệ với số làn
                y_ratios = []
                for p_idx in range(num_phases):
                    q_p = history[p_idx]
                    s_p = float(lane_counts[p_idx])
                    # Làm mượt (Laplace smoothing) để tránh triệt tiêu pha vắng xe
                    y_ratios.append((q_p + 1.0) / s_p)
                total_y = sum(y_ratios)
                ratio = y_ratios[observation.current_phase] / total_y
            else:
                # Khởi tạo hoặc fallback về tỷ lệ số làn nếu chưa có dòng xe quan sát
                total_lanes = sum(lane_counts)
                y_ratios = [float(lc) for lc in lane_counts]
                ratio = lane_counts[observation.current_phase] / total_lanes

            step = max(1.0, self.action_interval) if self.action_interval > 0 else 10.0

            # Tính toán thời gian pha dựa trên chu kỳ tối ưu Webster C_0 hoặc chu kỳ cơ sở
            if self.webster_cycle:
                c0 = self.compute_webster_cycle(observation, y_ratios, num_phases)
                lost_time_total = num_phases * max(3.0, self.yellow_seconds)
                effective_green = max(step, c0 - lost_time_total)
                raw_duration = effective_green * ratio + max(3.0, self.yellow_seconds)
            else:
                total_cycle_green = self.green_seconds * num_phases
                raw_duration = total_cycle_green * ratio

            # Chuẩn hóa thời gian xanh là bội số chính xác của chu kỳ hành động
            duration = max(step, round(raw_duration / step) * step)
            return float(duration)

        return self.green_seconds

    def select_phase(self, observation):
        """Giữ nguyên pha cho đến khi đủ thời gian quy định, sau đó đổi sang pha kế tiếp.

        Loại bỏ hiện tượng trôi thời gian do 3 giây đèn vàng:
        Khấu trừ thời gian đèn vàng (`yellow_seconds`) để tính ngưỡng đèn xanh thực tế.
        """
        self.record_traffic(observation)
        required_duration = self.get_phase_duration(observation)
        target_green = max(0.0, required_duration - self.yellow_seconds)

        # 1. Nếu chưa đủ thời gian xanh yêu cầu -> Giữ nguyên pha hiện tại
        if observation.green_elapsed < target_green:
            return observation.current_phase

        # 2. Đã đủ thời gian -> Chuyển sang pha kế tiếp theo chu kỳ vòng tròn
        total_phases = len(observation.phase_movements)
        return (observation.current_phase + 1) % total_phases
