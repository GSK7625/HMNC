"""Cấu trúc dữ liệu quan sát trạng thái ngã tư và ảnh chụp chỉ số giao thông."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class IntersectionObservation:
    """Dữ liệu quan sát trạng thái của một ngã tư tại thời điểm ra quyết định."""

    tls_id: str  # ID của cụm đèn tín hiệu
    current_phase: int  # Pha đèn hiện tại đang sáng (0-indexed)
    green_elapsed: float  # Thời gian đèn xanh hiện tại đã sáng liên tục (giây)
    lane_vehicle_count: dict[str, int]  # Số lượng xe trên từng làn đường: {tên_làn: số_xe}
    phase_movements: tuple[tuple[tuple[str, str], ...], ...]  # Luồng xe (in_lane, out_lane) cho mỗi pha
    lane_halting_count: dict[str, int] = field(default_factory=dict)  # Số xe dừng chờ (tốc độ < 0.1 m/s) trên từng làn
    lane_waiting_time: dict[str, float] = field(default_factory=dict)  # Thời gian chờ tích lũy trên từng làn (giây)
    lane_length: dict[str, float] = field(default_factory=dict)  # Chiều dài của từng làn đường (mét)
    lane_density: dict[str, float] = field(default_factory=dict)  # Mật độ xe trên từng làn (xe / mét)
    exit_lanes: set[str] = field(default_factory=set)  # Danh sách các làn thoát biên ra khỏi mạng lưới

    def __post_init__(self):
        self.tls_id = str(self.tls_id)
        self.current_phase = int(self.current_phase)
        self.green_elapsed = float(self.green_elapsed)
        if self.lane_halting_count is None:
            self.lane_halting_count = {}
        if self.lane_waiting_time is None:
            self.lane_waiting_time = {}
        if self.lane_length is None:
            self.lane_length = {}
        if self.lane_density is None:
            self.lane_density = {}
        if self.exit_lanes is None:
            self.exit_lanes = set()
        elif isinstance(self.exit_lanes, (list, tuple)):
            self.exit_lanes = set(self.exit_lanes)


@dataclass
class TrafficSnapshot:
    """Ảnh chụp nhanh các chỉ số đo lường hiệu suất giao thông tại một thời điểm trong SUMO."""

    simulation_time: float  # Thời điểm mô phỏng (giây)
    average_queue: float  # Số xe dừng chờ trung bình trên mỗi ngã tư
    average_current_waiting: float  # Thời gian chờ tích lũy trung bình của các xe đang trên mạng lưới (giây)
    throughput: int  # Số xe đã hoàn thành toàn bộ hành trình
    departed: int  # Tổng số xe đã xuất phát vào mạng lưới
    average_completed_travel_time: float  # Thời gian di chuyển trung bình của xe đã hoàn thành (giây)
    penalized_travel_time: float = 0.0  # Thời gian di chuyển có phạt xe kẹt (tính cả xe chưa về đích)
    average_delay: float = 0.0  # Độ trễ trung bình của các xe (giây)
    total_time_loss: float = 0.0  # Tổng thời gian mất mát tích lũy của toàn bộ xe (giây)

    def __post_init__(self):
        self.simulation_time = float(self.simulation_time)
        self.average_queue = float(self.average_queue)
        self.average_current_waiting = float(self.average_current_waiting)
        self.throughput = int(self.throughput)
        self.departed = int(self.departed)
        self.average_completed_travel_time = float(self.average_completed_travel_time)
        self.penalized_travel_time = float(self.penalized_travel_time)
        self.average_delay = float(self.average_delay)
        self.total_time_loss = float(self.total_time_loss)

