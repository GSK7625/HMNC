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
        turning_ratios: dict[tuple[str, str], float] | None = None,
        capacities: dict[str, float] | None = None,
        exit_lanes: set[str] | None = None,
        exclude_boundary_exits: bool = True,
    ) -> list[float]:
        """Tính toán áp lực xe cho từng pha đèn (hỗ trợ ghi log và so sánh)."""
        mode = pressure_mode or getattr(self, "pressure_mode", "halting" if use_halting else "standard")
        ratios = turning_ratios or getattr(self, "turning_ratios", None)
        caps = capacities or getattr(self, "capacities", None)
        exits = exit_lanes if exit_lanes is not None else getattr(self, "exit_lanes", None)
        return calculate_phase_pressures(
            observation,
            use_halting=use_halting,
            pressure_mode=mode,
            turning_ratios=ratios,
            capacities=caps,
            exit_lanes=exits,
            exclude_boundary_exits=exclude_boundary_exits,
        )


# Alias tương đương để hỗ trợ đặt tên chuẩn OOP
BaseController = Controller


def calculate_phase_pressures(
    observation: IntersectionObservation,
    use_halting: bool = False,
    pressure_mode: str | None = None,
    turning_ratios: dict[tuple[str, str], float] | None = None,
    capacities: dict[str, float] | None = None,
    exit_lanes: set[str] | None = None,
    exclude_boundary_exits: bool = True,
) -> list[float]:
    """Tính áp lực xe cho từng pha đèn theo chuẩn lý thuyết Max-Pressure (Varaiya 2013).

    Quy tắc chuẩn hóa:
    1. Sử dụng đồng nhất một đại lượng cho cả làn vào và làn ra (Dimensional Consistency):
       - "standard": Đồng nhất sử dụng số lượng xe (lane_vehicle_count).
       - "density": Đồng nhất sử dụng mật độ xe (lane_density hoặc xe / mét chiều dài làn).
       - "halting" (khuyến nghị theo RESCO): Làn vào dùng số xe dừng chờ (lane_halting_count), làn thoát dùng số xe (lane_vehicle_count).
       - "normalized": Chuẩn hóa áp lực trung bình theo số lượng làn vào.
    2. Xử lý làn thoát biên (Boundary / Sink Exit Lanes theo Varaiya 2013):
       Các làn thoát dẫn ra ngoài mạng lưới (không kết nối vào cụm đèn nào khác) có áp lực hạ lưu x_l = 0.
       Không trừ áp lực hạ lưu của làn thoát biên để tránh phạt nhầm các phương tiện đang thoát tự do.
    3. Trọng số năng lực thông hành (Capacity / Saturation Flow Weighting theo Varaiya 2013):
       Mỗi làn vào u có trọng số C(u) đại diện cho năng lực thoát xe (mặc định 1.0 hoặc theo capacities).
       P(u) = C(u) * [Q(u) - sum_{v} r(u, v) * Q(v)].
    4. Nhân tỷ lệ phân chia luồng rẽ (turning split ratio):
       Nếu một làn vào u kết nối với nhiều nhánh thoát v_1, v_2, ..., v_k trong pha:
       Tỷ lệ phân chia cho mỗi nhánh thoát là r(u, v) = 1.0 / k (hoặc theo ma trận turning_ratios).
       Áp lực hạ lưu ứng với làn vào u là sum_{v} r(u, v) * Q(v).
       Áp lực của làn vào u là: P(u) = C(u) * [Q(u) - sum_{v} r(u, v) * Q(v)].
       Tổng áp lực pha là: P(pha) = sum_{u in unique_in_lanes} P(u).
    """
    mode = pressure_mode
    if mode is None:
        mode = "halting" if use_halting else "standard"
    mode = mode.lower()

    # 1. Xác định đại lượng đo Q đồng nhất cho làn vào và làn thoát
    if mode == "density":
        if getattr(observation, "lane_density", None):
            in_q = observation.lane_density
            out_q = observation.lane_density
        else:
            lengths = getattr(observation, "lane_length", {}) or {}
            counts = observation.lane_vehicle_count or {}
            in_q = {l: counts.get(l, 0) / max(1.0, lengths.get(l, 100.0)) for l in counts}
            out_q = in_q
    elif mode == "halting":
        in_q = getattr(observation, "lane_halting_count", None) or observation.lane_vehicle_count or {}
        out_q = observation.lane_vehicle_count or {}
    else:  # "standard" hoặc "normalized"
        # Đồng nhất số xe cho cả làn vào và làn thoát
        in_q = observation.lane_vehicle_count or {}
        out_q = observation.lane_vehicle_count or {}

    # Xác định danh sách làn thoát biên
    known_exit_lanes = set()
    if exit_lanes is not None:
        known_exit_lanes = set(exit_lanes)
    elif getattr(observation, "exit_lanes", None):
        known_exit_lanes = set(observation.exit_lanes)

    pressures = []

    for movements in observation.phase_movements:
        # Gom nhóm các luồng di chuyển duy nhất (in_lane, out_lane) và liên kết theo từng làn vào
        seen_movements = set()
        in_to_outs: dict[str, list[str]] = {}
        unique_in_lanes = []

        for m in movements:
            if not m:
                continue
            in_lane, out_lane = m[0], m[1]
            if not in_lane:
                continue
            pair = (in_lane, out_lane)
            if pair in seen_movements:
                continue
            seen_movements.add(pair)

            if in_lane not in in_to_outs:
                in_to_outs[in_lane] = []
                unique_in_lanes.append(in_lane)
            if out_lane:
                in_to_outs[in_lane].append(out_lane)

        if not unique_in_lanes:
            pressures.append(0.0)
            continue

        phase_pressure = 0.0

        for in_lane in unique_in_lanes:
            outs = in_to_outs.get(in_lane, [])
            in_val = float(in_q.get(in_lane, 0))
            out_val = 0.0

            if outs:
                num_branches = len(outs)
                for out_lane in outs:
                    # Nhân tỷ lệ phân chia luồng rẽ nếu ngã tư có nhiều nhánh thoát
                    if turning_ratios and (in_lane, out_lane) in turning_ratios:
                        ratio = float(turning_ratios[(in_lane, out_lane)])
                    else:
                        ratio = 1.0 / num_branches

                    # Chuẩn Varaiya 2013: nếu out_lane là làn thoát biên, x_out = 0
                    if exclude_boundary_exits and out_lane in known_exit_lanes:
                        lane_out_q = 0.0
                    else:
                        lane_out_q = float(out_q.get(out_lane, 0))

                    out_val += ratio * lane_out_q
            cap = float(capacities.get(in_lane, 1.0)) if capacities else 1.0
            phase_pressure += cap * (in_val - out_val)

        if mode == "normalized":
            phase_pressure = phase_pressure / max(1, len(unique_in_lanes))

        pressures.append(float(phase_pressure))

    return pressures
