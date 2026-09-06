"""Unit tests for scientific visualization and plotting module."""

from __future__ import annotations

import csv
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from src.traffic_control.visualization import (
    generate_all_plots,
    plot_benchmark_comparison,
    plot_learning_curve,
    plot_time_series,
)


class TestVisualization(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_plot_benchmark_comparison_single_seed(self):
        """Kiểm tra vẽ biểu đồ so sánh từ file comparison.json (single seed)."""
        data = [
            {
                "controller": "fixedtime",
                "controller_name": "Fixed-Time",
                "penalized_travel_time_s": 25.4,
                "average_delay_s": 8.2,
                "average_queue_vehicles": 2.1,
                "throughput": 45,
            },
            {
                "controller": "maxpressure",
                "controller_name": "Max-Pressure",
                "penalized_travel_time_s": 18.2,
                "average_delay_s": 4.1,
                "average_queue_vehicles": 0.8,
                "throughput": 58,
            },
        ]
        (self.temp_dir / "comparison.json").write_text(json.dumps(data), encoding="utf-8")

        out_path = plot_benchmark_comparison(self.temp_dir)
        self.assertIsNotNone(out_path)
        self.assertTrue(out_path.is_file())
        self.assertGreater(out_path.stat().st_size, 1000)

    def test_plot_benchmark_comparison_multi_seed(self):
        """Kiểm tra vẽ biểu đồ so sánh đa hạt giống kèm thanh sai số (Mean ± Std)."""
        data = [
            {
                "controller": "fixedtime",
                "controller_name": "Fixed-Time",
                "penalized_travel_time_mean": 24.5,
                "penalized_travel_time_std": 1.2,
                "average_delay_mean": 8.0,
                "average_delay_std": 0.5,
                "average_queue_mean": 2.0,
                "average_queue_std": 0.3,
                "throughput_mean": 46.0,
                "throughput_std": 2.0,
            },
            {
                "controller": "dqn",
                "controller_name": "DQN",
                "penalized_travel_time_mean": 16.5,
                "penalized_travel_time_std": 0.9,
                "average_delay_mean": 3.8,
                "average_delay_std": 0.4,
                "average_queue_mean": 0.6,
                "average_queue_std": 0.1,
                "throughput_mean": 60.0,
                "throughput_std": 1.5,
            },
        ]
        (self.temp_dir / "multi_seed_summary.json").write_text(json.dumps(data), encoding="utf-8")

        out_path = plot_benchmark_comparison(self.temp_dir)
        self.assertIsNotNone(out_path)
        self.assertTrue(out_path.is_file())

    def test_plot_time_series(self):
        """Kiểm tra vẽ biểu đồ chuỗi thời gian diễn biến hàng đợi và độ trễ."""
        agent_dir = self.temp_dir / "maxpressure"
        agent_dir.mkdir(parents=True)
        trace_file = agent_dir / "decision_trace.csv"

        fieldnames = ["decision", "simulation_time_s", "average_queue_vehicles", "average_delay_s"]
        rows = [
            {"decision": 0, "simulation_time_s": 0.0, "average_queue_vehicles": 0.0, "average_delay_s": 0.0},
            {"decision": 1, "simulation_time_s": 10.0, "average_queue_vehicles": 3.0, "average_delay_s": 2.5},
            {"decision": 2, "simulation_time_s": 20.0, "average_queue_vehicles": 1.0, "average_delay_s": 1.2},
            {"decision": 3, "simulation_time_s": 30.0, "average_queue_vehicles": 0.0, "average_delay_s": 0.5},
        ]
        with trace_file.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        out_path = plot_time_series(self.temp_dir)
        self.assertIsNotNone(out_path)
        self.assertTrue(out_path.is_file())

    def test_plot_learning_curve(self):
        """Kiểm tra vẽ biểu đồ đường cong học tập."""
        curve_data = [
            {"episode": 1, "delay_s": 12.5, "penalized_tt_s": 28.0, "queue_vehicles": 4.5, "epsilon": 0.8},
            {"episode": 2, "delay_s": 9.2, "penalized_tt_s": 22.1, "queue_vehicles": 3.0, "epsilon": 0.5},
            {"episode": 3, "delay_s": 5.1, "penalized_tt_s": 16.4, "queue_vehicles": 1.2, "epsilon": 0.2},
            {"episode": 4, "delay_s": 3.8, "penalized_tt_s": 14.0, "queue_vehicles": 0.7, "epsilon": 0.05},
        ]
        (self.temp_dir / "learning_curve.json").write_text(json.dumps(curve_data), encoding="utf-8")

        out_path = plot_learning_curve(self.temp_dir)
        self.assertIsNotNone(out_path)
        self.assertTrue(out_path.is_file())

    def test_generate_all_plots(self):
        """Kiểm tra hàm tổng hợp generate_all_plots."""
        # Tạo sẵn dữ liệu comparison
        (self.temp_dir / "comparison.json").write_text(
            json.dumps([
                {"controller": "ft", "penalized_travel_time_s": 20.0, "average_delay_s": 5.0, "average_queue_vehicles": 1.0, "throughput": 10}
            ]),
            encoding="utf-8",
        )
        plots = generate_all_plots(self.temp_dir)
        self.assertGreaterEqual(len(plots), 1)
        self.assertTrue(all(p.is_file() for p in plots))


if __name__ == "__main__":
    unittest.main()
