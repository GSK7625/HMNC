"""Bộ điều khiển đèn giao thông theo thuật toán Max-Pressure (MP)."""

from __future__ import annotations

from .base import BaseController
from .registry import register_controller


@register_controller(
    name="maxpressure",
    aliases=["mp"],
    display_name="Max-Pressure",
    description="Ưu tiên bật đèn xanh cho hướng có áp lực xe lớn nhất",
)
class MaxPressureController(BaseController):
    """Bộ điều khiển Max-Pressure: Bật đèn xanh cho hướng có áp lực xe lớn nhất.

    Công thức tính áp lực:
        P(pha) = sum(N_in - N_out)
        - N_in : Số xe chờ ở các làn đi vào ngã tư.
        - N_out: Số xe ở các làn thoát ra phía trước.

    Quy tắc an toàn: Đèn xanh hiện tại phải sáng ít nhất `minimum_green_seconds`
    trước khi được phép đổi sang pha khác (được bảo vệ tự động bởi BaseController).
    """

    def __init__(
        self,
        minimum_green_seconds: float = 10.0,
        max_green_seconds: float = 60.0,
        use_halting: bool | None = None,
        pressure_mode: str = "halting",
        turning_ratios: dict[tuple[str, str], float] | None = None,
        capacities: dict[str, float] | None = None,
        exclude_boundary_exits: bool = True,
        **kwargs,
    ):
        super().__init__(minimum_green_seconds=minimum_green_seconds, **kwargs)
        self.max_green_seconds = float(max_green_seconds)
        self.turning_ratios = turning_ratios
        self.capacities = capacities
        self.exclude_boundary_exits = bool(exclude_boundary_exits)
        if use_halting is True:
            self.pressure_mode = "halting"
            self.use_halting = True
        elif use_halting is False:
            self.pressure_mode = "standard"
            self.use_halting = False
        else:
            self.pressure_mode = str(pressure_mode).lower()
            self.use_halting = (self.pressure_mode == "halting")

        self.name = "maxpressure"
        self.display_name = "Max-Pressure"

    def _break_tie_by_waiting(self, candidates: list[int], observation) -> int:
        """Phá vỡ thế hòa áp lực (Tie-breaking) một cách khoa học:
        Ưu tiên pha có tổng thời gian chờ tích lũy lớn nhất (lane_waiting_time),
        hoặc số xe dừng chờ lớn nhất (lane_halting_count) nhằm giải tỏa tắc nghẽn tốt nhất.
        """
        if len(candidates) <= 1:
            return candidates[0]

        waiting_scores = []
        for phase_idx in candidates:
            if phase_idx >= len(observation.phase_movements):
                waiting_scores.append(-1.0)
                continue
            movements = observation.phase_movements[phase_idx]
            unique_in_lanes = {m[0] for m in movements if m and m[0]}
            # 1. Tổng thời gian chờ
            wait_time = sum(
                (getattr(observation, "lane_waiting_time", {}) or {}).get(lane, 0.0)
                for lane in unique_in_lanes
            )
            # 2. Tổng số xe dừng chờ (làm tie-breaker phụ)
            halt_count = sum(
                (getattr(observation, "lane_halting_count", {}) or {}).get(lane, 0)
                for lane in unique_in_lanes
            )
            score = wait_time * 10.0 + halt_count
            waiting_scores.append(score)

        max_score = max(waiting_scores)
        if max_score > 0:
            best_idx = waiting_scores.index(max_score)
            return candidates[best_idx]
        return candidates[0]

    def decide_phase(self, observation) -> int:
        """Logic cốt lõi Max-Pressure: Chọn pha có áp lực xe lớn nhất.

        Cải tiến chuẩn lý thuyết & kỹ thuật giao thông:
        1. Chống bỏ đói (Starvation Guard): Nếu pha hiện tại đã sáng quá max_green_seconds
           và có pha khác chờ, chuyển sang pha khác có áp lực lớn nhất (tie-break bằng waiting time).
        2. Chống đổi pha khi vắng xe (Idle Protection): Nếu tất cả các pha đều không có áp lực dương,
           giữ nguyên pha hiện tại để tránh hao phí đèn vàng lãng phí.
        3. Tie-breaking Hysteresis: Nếu pha hiện tại cũng đạt áp lực tối đa (hòa áp lực),
           ưu tiên giữ nguyên pha hiện tại thay vì đổi pha vô ích.
        4. Tie-breaking công bằng: Nếu nhiều pha hòa áp lực, ưu tiên pha có thời gian chờ xe lớn nhất.
        5. Khử trừ áp lực hạ lưu làn thoát biên theo đúng định lý Varaiya 2013.
        """
        pressures = self.phase_pressures(
            observation,
            use_halting=self.use_halting,
            pressure_mode=self.pressure_mode,
            turning_ratios=self.turning_ratios,
            capacities=self.capacities,
            exclude_boundary_exits=self.exclude_boundary_exits,
        )
        num_phases = len(pressures)
        if num_phases <= 0:
            return observation.current_phase

        cur_phase = observation.current_phase

        # 1. Cơ chế chống bỏ đói (Starvation Guard): chuyển pha nếu đã xanh quá max_green_seconds
        if self.max_green_seconds > 0 and observation.green_elapsed >= self.max_green_seconds and num_phases > 1:
            other_pressures = [
                (p if idx != cur_phase else -float("inf"))
                for idx, p in enumerate(pressures)
            ]
            best_other_val = max(other_pressures)
            if best_other_val > -float("inf"):
                best_candidates = [idx for idx, p in enumerate(other_pressures) if p == best_other_val]
                return self._break_tie_by_waiting(best_candidates, observation)

        max_val = max(pressures)

        # 2. Xử lý vắng xe: Nếu tất cả các pha đều không có áp lực dương (max_val <= 0)
        # Giữ nguyên pha hiện tại để tránh kích hoạt chu kỳ đèn vàng 3-5 giây vô ích
        if max_val <= 0:
            return cur_phase

        # 3. Tie-breaking: Nếu pha hiện tại cũng đạt áp lực tối đa (hòa áp lực)
        # Giữ nguyên pha hiện tại (Hysteresis) để tối đa hóa thông lượng
        if 0 <= cur_phase < num_phases and pressures[cur_phase] == max_val:
            return cur_phase

        # 4. Chọn pha có áp lực lớn nhất (phá vỡ hòa bằng thời gian chờ xe)
        best_candidates = [idx for idx, p in enumerate(pressures) if p == max_val]
        return self._break_tie_by_waiting(best_candidates, observation)
