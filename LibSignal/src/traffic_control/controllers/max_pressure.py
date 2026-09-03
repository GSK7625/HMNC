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
        max_green_seconds: float = 0.0,
        use_halting: bool | None = None,
        pressure_mode: str = "standard",
        **kwargs,
    ):
        super().__init__(minimum_green_seconds=minimum_green_seconds, **kwargs)
        self.max_green_seconds = float(max_green_seconds)
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

    def decide_phase(self, observation) -> int:
        """Logic cốt lõi Max-Pressure: Chọn pha có áp lực xe lớn nhất.

        Cải tiến chuẩn lý thuyết & kỹ thuật giao thông:
        1. Chống bỏ đói (Starvation Guard): Nếu pha hiện tại đã sáng quá max_green_seconds
           và có pha khác chờ, chuyển sang pha khác có áp lực lớn nhất.
        2. Chống đổi pha khi vắng xe (Idle Protection): Nếu tất cả các pha đều không có áp lực dương,
           giữ nguyên pha hiện tại để tránh hao phí đèn vàng lãng phí.
        3. Tie-breaking Hysteresis: Nếu pha hiện tại cũng đạt áp lực tối đa (hòa áp lực),
           ưu tiên giữ nguyên pha hiện tại thay vì đổi pha vô ích.
        """
        pressures = self.phase_pressures(observation, use_halting=self.use_halting, pressure_mode=self.pressure_mode)
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
                return best_candidates[0]

        max_val = max(pressures)

        # 2. Xử lý vắng xe: Nếu tất cả các pha đều không có áp lực dương (max_val <= 0)
        # Giữ nguyên pha hiện tại để tránh kích hoạt chu kỳ đèn vàng 3-5 giây vô ích
        if max_val <= 0:
            return cur_phase

        # 3. Tie-breaking: Nếu pha hiện tại cũng đạt áp lực tối đa (hòa áp lực)
        # Giữ nguyên pha hiện tại (Hysteresis) để tối đa hóa thông lượng
        if 0 <= cur_phase < num_phases and pressures[cur_phase] == max_val:
            return cur_phase

        # 4. Chọn pha có áp lực lớn nhất
        best_candidates = [idx for idx, p in enumerate(pressures) if p == max_val]
        return best_candidates[0]
