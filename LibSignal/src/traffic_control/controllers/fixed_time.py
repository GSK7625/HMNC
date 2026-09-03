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

    Thuật toán không phụ thuộc vào mật độ xe thực tế. Sau khi đèn xanh sáng đủ
    `green_seconds`, đèn sẽ tự động chuyển sang pha tiếp theo theo vòng tròn:
    (pha_hien_tai + 1) % tong_so_pha.
    """

    def __init__(
        self,
        green_seconds: float = 30.0,
        minimum_green_seconds: float = 0.0,
        proportional_splits: bool = False,
        phase_splits: dict[str, list[float]] | list[float] | None = None,
        **kwargs,
    ):
        if green_seconds <= 0:
            raise ValueError(f"green_seconds phải là số dương, nhận được: {green_seconds}")
        super().__init__(minimum_green_seconds=0.0, **kwargs)
        self.green_seconds = float(green_seconds)
        self.proportional_splits = bool(proportional_splits)
        self.phase_splits = phase_splits
        self.name = "fixedtime"
        self.display_name = "Fixed-Time"

    def get_phase_duration(self, observation) -> float:
        """Lấy thời gian đèn xanh cho pha hiện tại (hỗ trợ chia đều hoặc chia theo tỉ lệ làn/lưu lượng)."""
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

        # 2. Nếu bật tính tỉ lệ số làn (Lane-proportional splits / xấp xỉ Webster)
        if self.proportional_splits and num_phases > 1:
            total_cycle_green = self.green_seconds * num_phases
            lane_counts = []
            for movements in observation.phase_movements:
                unique_in_lanes = {in_lane for in_lane, _ in movements if in_lane}
                lane_counts.append(max(1, len(unique_in_lanes)))
            total_lanes = sum(lane_counts)
            ratio = lane_counts[observation.current_phase] / total_lanes
            duration = max(10.0, round(total_cycle_green * ratio))
            return float(duration)

        return self.green_seconds

    def select_phase(self, observation):
        """Giữ nguyên pha cho đến khi đủ thời gian xanh quy định, sau đó đổi sang pha kế tiếp."""
        required_green = self.get_phase_duration(observation)
        # 1. Nếu chưa đủ thời gian xanh cố định -> Giữ nguyên pha hiện tại
        if observation.green_elapsed < required_green:
            return observation.current_phase

        # 2. Đã đủ thời gian -> Chuyển sang pha kế tiếp theo chu kỳ vòng tròn
        total_phases = len(observation.phase_movements)
        return (observation.current_phase + 1) % total_phases
