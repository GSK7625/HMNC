"""Định nghĩa và tính toán các chỉ số đánh giá hiệu năng giao thông chuẩn hóa."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import fmean

from .observation import TrafficSnapshot


@dataclass
class EvaluationMetrics:
    """Tập chỉ số chuẩn hóa để so sánh khách quan và an toàn giữa các thuật toán."""

    controller_id: str  # Định danh thuật toán (vd: "fixedtime", "maxpressure", "qlearning")
    controller_name: str  # Tên hiển thị (vd: "Fixed-Time", "Max-Pressure", "Q-Learning")
    average_travel_time_s: float  # Thời gian di chuyển trung bình của xe đã hoàn thành (giây)
    penalized_travel_time_s: float  # Thời gian di chuyển có phạt xe kẹt (tính cả xe chưa về đích, chống Survival Bias)
    average_delay_s: float  # Độ trễ trung bình của tất cả xe xuất phát vào mạng lưới (giây)
    total_time_loss_s: float  # Tổng thời gian chậm trễ/mất mát trong toàn bộ mô phỏng (giây)
    average_queue_vehicles: float  # Số lượng xe dừng chờ trung bình trên mỗi ngã tư (xe)
    average_current_waiting_s: float  # Thời gian chờ tích lũy trung bình của các xe trong mạng (giây)
    throughput: int  # Tổng số xe đã hoàn thành lộ trình (xe)
    departed_vehicles: int  # Tổng số xe đã xuất phát vào mạng lưới (xe)
    completion_rate: float  # Tỷ lệ hoàn thành lộ trình (Throughput / Departed) [0.0 -> 1.0]
    phase_switches: int  # Tổng số lần đổi pha đèn (chỉ số đo lường độ ổn định)
    simulated_seconds: int  # Tổng thời gian mô phỏng SUMO (giây)
    decisions: int  # Tổng số lượt ra quyết định của thuật toán
    wall_clock_s: float  # Thời gian chạy thực tế trên CPU/máy tính (giây)

    def to_dict(self) -> dict:
        """Chuyển thành từ điển dữ liệu."""
        return asdict(self)


class MetricsCollector:
    """Thu thập, theo dõi và tính toán các chỉ số đánh giá qua từng bước mô phỏng."""

    def __init__(self, controller_id: str, controller_name: str):
        self.controller_id = controller_id
        self.controller_name = controller_name
        self.trace: list[dict] = []
        self.phase_switches: int = 0
        self._previous_actions: dict[str, int] | None = None

    def record_decision(
        self,
        decision_idx: int,
        elapsed_s: int,
        snapshot: TrafficSnapshot,
        actions: dict[str, int],
        green_elapsed: dict[str, float],
        pressures: dict[str, list[float]],
    ) -> None:
        """Ghi nhận quyết định và trạng thái tại một chu kỳ điều khiển."""
        if self._previous_actions is not None:
            self.phase_switches += sum(
                actions[tls_id] != self._previous_actions.get(tls_id, actions[tls_id])
                for tls_id in actions
            )
        self._previous_actions = actions.copy()

        self.trace.append(
            {
                "decision": decision_idx,
                "elapsed_s": elapsed_s,
                "simulation_time_s": snapshot.simulation_time,
                "actions": json.dumps(actions, sort_keys=True),
                "green_elapsed_before_action_s": json.dumps(green_elapsed, sort_keys=True),
                "phase_pressures": json.dumps(pressures, sort_keys=True),
                "average_queue_vehicles": snapshot.average_queue,
                "average_current_waiting_s": snapshot.average_current_waiting,
                "throughput": snapshot.throughput,
                "average_completed_travel_time_s": snapshot.average_completed_travel_time,
                "penalized_travel_time_s": snapshot.penalized_travel_time,
                "average_delay_s": snapshot.average_delay,
            }
        )

    def compute_summary(
        self,
        final_snapshot: TrafficSnapshot,
        simulated_seconds: int,
        wall_clock_s: float,
    ) -> EvaluationMetrics:
        """Tổng hợp toàn bộ dữ liệu thành bảng chỉ số đánh giá chuẩn EvaluationMetrics."""
        avg_queue = (
            fmean(float(row["average_queue_vehicles"]) for row in self.trace)
            if self.trace
            else 0.0
        )
        avg_waiting = (
            fmean(float(row["average_current_waiting_s"]) for row in self.trace)
            if self.trace
            else 0.0
        )
        completion_rate = (
            (final_snapshot.throughput / final_snapshot.departed)
            if final_snapshot.departed > 0
            else 0.0
        )

        return EvaluationMetrics(
            controller_id=self.controller_id,
            controller_name=self.controller_name,
            average_travel_time_s=round(final_snapshot.average_completed_travel_time, 2),
            penalized_travel_time_s=round(final_snapshot.penalized_travel_time, 2),
            average_delay_s=round(final_snapshot.average_delay, 2),
            total_time_loss_s=round(final_snapshot.total_time_loss, 2),
            average_queue_vehicles=round(avg_queue, 2),
            average_current_waiting_s=round(avg_waiting, 2),
            throughput=final_snapshot.throughput,
            departed_vehicles=final_snapshot.departed,
            completion_rate=round(completion_rate, 4),
            phase_switches=self.phase_switches,
            simulated_seconds=simulated_seconds,
            decisions=len(self.trace),
            wall_clock_s=round(wall_clock_s, 2),
        )

    def export_trace_csv(self, file_path: Path) -> None:
        """Xuất file CSV lưu vết chi tiết từng bước quyết định."""
        if not self.trace:
            return
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with file_path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(self.trace[0].keys()))
            writer.writeheader()
            writer.writerows(self.trace)
