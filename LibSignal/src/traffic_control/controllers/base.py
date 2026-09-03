"""Lớp cơ sở và các hàm tính toán dùng chung cho bộ điều khiển đèn giao thông."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.observation import IntersectionObservation


class Controller:
    """Lớp cơ sở mẫu cho các bộ điều khiển đèn giao thông.

    Được thiết kế với cơ chế bảo vệ an toàn (Safety Guard):
    - Tự động áp dụng thời gian xanh tối thiểu (minimum_green_seconds)
      nhằm tránh việc đổi đèn quá nhanh gây nguy hiểm và mất an toàn giao thông.
    """

    name: str = "base_controller"
    display_name: str = "Base Controller"

    def __init__(self, minimum_green_seconds: float = 0.0, **kwargs):
        if minimum_green_seconds < 0:
            raise ValueError(f"minimum_green_seconds không được là số âm: {minimum_green_seconds}")
        self.minimum_green_seconds = float(minimum_green_seconds)

    def select_phase(self, observation: IntersectionObservation) -> int:
        """Lựa chọn pha đèn tiếp theo với cơ chế bảo vệ an toàn giao thông.

        Nếu thời gian xanh chưa đạt `minimum_green_seconds`, bắt buộc giữ nguyên pha hiện tại.
        Nếu đã thỏa mãn an toàn, gọi `decide_phase(observation)` để thuật toán đưa ra quyết định.
        """
        if self.minimum_green_seconds > 0 and observation.green_elapsed < self.minimum_green_seconds:
            return observation.current_phase
        return self.decide_phase(observation)

    def decide_phase(self, observation: IntersectionObservation) -> int:
        """Logic cốt lõi của thuật toán điều khiển đèn giao thông.

        Các thuật toán mới chỉ cần cài đặt phương thức này.
        """
        raise NotImplementedError("Thuật toán cần cài đặt phương thức decide_phase() hoặc select_phase()")

    def reset(self, seed: int | None = None) -> None:
        """Đặt lại trạng thái nội bộ của controller giữa các episode hoặc lượt chạy."""
        pass

    def step_update(
        self,
        observation: IntersectionObservation,
        action: int,
        reward: float | None = None,
    ) -> None:
        """Hook cập nhật trạng thái/trọng số cho các thuật toán học máy (RL)."""
        pass

    def phase_pressures(
        self,
        observation: IntersectionObservation,
        use_halting: bool = False,
        pressure_mode: str | None = None,
    ) -> list[float]:
        """Tính toán áp lực xe cho từng pha đèn (hỗ trợ ghi log và so sánh)."""
        mode = pressure_mode or getattr(self, "pressure_mode", "halting" if use_halting else "standard")
        return calculate_phase_pressures(observation, use_halting=use_halting, pressure_mode=mode)


# Alias tương đương để hỗ trợ đặt tên chuẩn OOP
BaseController = Controller


def calculate_phase_pressures(
    observation: IntersectionObservation,
    use_halting: bool = False,
    pressure_mode: str | None = None,
) -> list[float]:
    """Tính áp lực xe cho từng pha đèn: P(pha) = sum(N_in) - sum(N_out).

    Khử trùng lặp làn (Deduplication) để tránh nhân đôi xe khi một làn có nhiều hướng rẽ.
    - pressure_mode == "standard" (Chuẩn Varaiya, 2013 / LibSignal / CityFlow):
      Đồng nhất sử dụng lane_vehicle_count cho cả làn vào và làn thoát để bảo đảm tính
      nhất quán thứ nguyên toán học (Dimensional Consistency).
    - pressure_mode == "halting" (hoặc use_halting=True):
      Làn vào dùng halting_count (xe dừng chờ), làn thoát dùng lane_vehicle_count (xe đang lưu thông).
    - pressure_mode == "normalized":
      Chuẩn hóa mật độ xe theo số làn vào và ra (in_density - out_density).
    """
    mode = pressure_mode
    if mode is None:
        mode = "halting" if use_halting else "standard"
    mode = mode.lower()

    if mode == "halting":
        if getattr(observation, "lane_halting_count", None):
            in_counts = observation.lane_halting_count
        else:
            in_counts = observation.lane_vehicle_count or {}
    else:
        in_counts = observation.lane_vehicle_count or {}

    # Làn thoát (downstream) luôn đo bằng tổng số xe trên làn để phát hiện tắc nghẽn hạ lưu
    out_counts = observation.lane_vehicle_count or {}

    pressures = []

    for movements in observation.phase_movements:
        # Gom nhóm tập hợp các làn vào và làn ra duy nhất cho pha này (khử trùng lặp)
        unique_in_lanes = {in_lane for in_lane, _ in movements if in_lane}
        unique_out_lanes = {out_lane for _, out_lane in movements if out_lane}

        in_count = sum(in_counts.get(in_lane, 0) for in_lane in unique_in_lanes)
        out_count = sum(out_counts.get(out_lane, 0) for out_lane in unique_out_lanes)

        if mode == "normalized":
            in_density = in_count / max(1, len(unique_in_lanes))
            out_density = out_count / max(1, len(unique_out_lanes))
            pressures.append(float(in_density - out_density))
        else:
            pressures.append(float(in_count - out_count))

    return pressures
