"""Cấu hình chuẩn hóa cho thí nghiệm mô phỏng và kiểm chuẩn (Benchmark)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class BenchmarkConfig:
    """Cấu hình điều kiện môi trường chuẩn dùng chung để so sánh công bằng giữa các thuật toán.

    Tất cả các thuật toán khi tham gia so sánh trong cùng một đợt đánh giá
    BẮT BUỘC phải dùng chung bộ tham số này.
    """

    scenario: Path  # Đường dẫn tới file cấu hình mạng lưới SUMO (.sumocfg)
    steps: int = 900  # Tổng số giây mô phỏng (mặc định: 900s)
    action_interval: int = 10  # Chu kỳ ra quyết định điều khiển đèn (giây)
    seed: int = 0  # Hạt giống ngẫu nhiên (seed) để tạo lưu lượng xe tái lặp 100%
    yellow_seconds: float = 3.0  # Thời gian đèn vàng chuyển tiếp an toàn (giây, chuẩn RESCO/SUMO)
    minimum_green_seconds: float = 10.0  # Quy chuẩn thời gian xanh tối thiểu (G_min) bắt buộc
    step_length: float = 1.0  # Bước nhảy mô phỏng SUMO (giây)
    gui: bool = False  # Bật giao diện SUMO-GUI
    step_delay: float = 0.0  # Độ trễ hiển thị GUI (giây)
    extra_params: dict = field(default_factory=dict)  # Tham số mở rộng nếu cần

    def __post_init__(self):
        self.scenario = Path(self.scenario).resolve()
        self.steps = int(self.steps)
        self.action_interval = int(self.action_interval)
        self.seed = int(self.seed)
        self.yellow_seconds = float(self.yellow_seconds)
        self.minimum_green_seconds = float(self.minimum_green_seconds)
        self.step_length = float(self.step_length)
        self.gui = bool(self.gui)
        self.step_delay = float(self.step_delay)
        self.validate()

    def validate(self) -> None:
        """Kiểm tra tính hợp lệ của cấu hình chuẩn."""
        if not self.scenario.is_file():
            raise FileNotFoundError(f"Không tìm thấy file kịch bản SUMO: {self.scenario}")
        if self.steps <= 0:
            raise ValueError(f"steps phải là số dương, nhận được: {self.steps}")
        if self.action_interval <= 0:
            raise ValueError(f"action_interval phải là số dương, nhận được: {self.action_interval}")
        if self.yellow_seconds < 0:
            raise ValueError(f"yellow_seconds không được âm, nhận được: {self.yellow_seconds}")
        if self.minimum_green_seconds < 0:
            raise ValueError(f"minimum_green_seconds không được âm, nhận được: {self.minimum_green_seconds}")
        if self.step_length <= 0:
            raise ValueError(f"step_length phải là số dương, nhận được: {self.step_length}")
        if self.step_delay < 0:
            raise ValueError(f"step_delay không được âm, nhận được: {self.step_delay}")

    def to_dict(self) -> dict:
        """Chuyển đổi cấu hình sang dạng từ điển để lưu file JSON/log."""
        return {
            "scenario": str(self.scenario),
            "steps": self.steps,
            "action_interval": self.action_interval,
            "seed": self.seed,
            "yellow_seconds": self.yellow_seconds,
            "minimum_green_seconds": self.minimum_green_seconds,
            "step_length": self.step_length,
            "gui": self.gui,
            "step_delay": self.step_delay,
            "extra_params": self.extra_params,
        }
