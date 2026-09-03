"""Unit tests cho BenchmarkConfig, EvaluationMetrics và MetricsCollector."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.traffic_control.core.config import BenchmarkConfig
from src.traffic_control.core.metrics import EvaluationMetrics, MetricsCollector
from src.traffic_control.core.observation import TrafficSnapshot


class TestMetricsAndConfig(unittest.TestCase):
    def setUp(self):
        self.dummy_config_file = Path(__file__).resolve()

    def test_benchmark_config_validation(self):
        # Cấu hình hợp lệ
        cfg = BenchmarkConfig(
            scenario=self.dummy_config_file,
            steps=600,
            action_interval=10,
            seed=42,
            yellow_seconds=5.0,
            minimum_green_seconds=10.0,
        )
        self.assertEqual(cfg.steps, 600)
        self.assertEqual(cfg.seed, 42)

        # Cấu hình lỗi: file không tồn tại
        with self.assertRaises(FileNotFoundError):
            BenchmarkConfig(scenario=Path("non_existent_path.sumocfg"))

        # Cấu hình lỗi: steps <= 0
        with self.assertRaises(ValueError):
            BenchmarkConfig(scenario=self.dummy_config_file, steps=0)

        # Cấu hình lỗi: minimum_green_seconds âm
        with self.assertRaises(ValueError):
            BenchmarkConfig(scenario=self.dummy_config_file, minimum_green_seconds=-1.0)

    def test_metrics_collector_and_summary_computation(self):
        collector = MetricsCollector(controller_id="test_ctrl", controller_name="Test Controller")

        # Bước 1: Quyết định 0
        snap1 = TrafficSnapshot(
            simulation_time=10.0,
            average_queue=4.0,
            average_current_waiting=2.5,
            throughput=1,
            departed=5,
            average_completed_travel_time=10.0,
        )
        collector.record_decision(
            decision_idx=0,
            elapsed_s=10,
            snapshot=snap1,
            actions={"tls_1": 0},
            green_elapsed={"tls_1": 10.0},
            pressures={"tls_1": [5.0, 2.0]},
        )

        # Bước 2: Quyết định 1 (Đổi pha từ 0 sang 1)
        snap2 = TrafficSnapshot(
            simulation_time=20.0,
            average_queue=2.0,
            average_current_waiting=1.5,
            throughput=3,
            departed=5,
            average_completed_travel_time=12.0,
        )
        collector.record_decision(
            decision_idx=1,
            elapsed_s=20,
            snapshot=snap2,
            actions={"tls_1": 1},
            green_elapsed={"tls_1": 0.0},
            pressures={"tls_1": [1.0, 4.0]},
        )

        # Tổng hợp chỉ số
        summary = collector.compute_summary(
            final_snapshot=snap2,
            simulated_seconds=20,
            wall_clock_s=0.5,
        )

        self.assertIsInstance(summary, EvaluationMetrics)
        self.assertEqual(summary.controller_id, "test_ctrl")
        self.assertEqual(summary.controller_name, "Test Controller")
        self.assertEqual(summary.throughput, 3)
        self.assertEqual(summary.departed_vehicles, 5)
        self.assertEqual(summary.completion_rate, 0.6)  # 3 / 5
        self.assertEqual(summary.average_queue_vehicles, 3.0)  # (4.0 + 2.0) / 2
        self.assertEqual(summary.average_current_waiting_s, 2.0)  # (2.5 + 1.5) / 2
        self.assertEqual(summary.phase_switches, 1)  # 1 lần đổi pha
        self.assertEqual(summary.decisions, 2)
        self.assertEqual(summary.penalized_travel_time_s, 0.0)
        self.assertEqual(summary.average_delay_s, 0.0)
        self.assertEqual(summary.total_time_loss_s, 0.0)

    def test_export_trace_csv(self):
        collector = MetricsCollector(controller_id="test_ctrl", controller_name="Test Controller")
        snap = TrafficSnapshot(10.0, 1.0, 2.0, 0, 1, 0.0)
        collector.record_decision(0, 10, snap, {"tls_1": 0}, {"tls_1": 10.0}, {"tls_1": [1.0]})

        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "trace.csv"
            collector.export_trace_csv(csv_path)
            self.assertTrue(csv_path.is_file())
            content = csv_path.read_text(encoding="utf-8-sig")
            self.assertIn("decision", content)
            self.assertIn("simulation_time_s", content)


if __name__ == "__main__":
    unittest.main()
