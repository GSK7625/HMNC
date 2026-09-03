"""Module điều phối thí nghiệm mô phỏng và xuất kết quả CSV/JSON chuẩn hóa."""

from __future__ import annotations

import csv
import json
import time
from pathlib import Path

from .core.config import BenchmarkConfig
from .core.metrics import MetricsCollector
from .sumo_env import SumoEnvironment


def run_experiment(
    controller,
    sumo_config: Path | None = None,
    steps: int = 900,
    action_interval: int = 10,
    seed: int = 0,
    gui: bool = False,
    yellow_seconds: float = 3.0,
    step_delay: float = 0.0,
    output_dir: Path | None = None,
    benchmark_config: BenchmarkConfig | None = None,
) -> dict:
    """Chạy một lượt thí nghiệm điều khiển đèn giao thông với thuật toán chỉ định."""
    # Nếu truyền benchmark_config, sử dụng trực tiếp các tham số chuẩn
    if benchmark_config is not None:
        sumo_config = benchmark_config.scenario
        steps = benchmark_config.steps
        action_interval = benchmark_config.action_interval
        seed = benchmark_config.seed
        gui = benchmark_config.gui
        yellow_seconds = benchmark_config.yellow_seconds
        step_delay = benchmark_config.step_delay
    elif sumo_config is None:
        raise ValueError("Phải chỉ định sumo_config hoặc benchmark_config")

    if steps <= 0 or action_interval <= 0:
        raise ValueError("steps và action_interval phải lớn hơn 0")

    output_dir = Path(output_dir) if output_dir else Path("results")
    agent_dir = output_dir / controller.name
    agent_dir.mkdir(parents=True, exist_ok=True)

    controller_id = controller.name
    controller_name = getattr(controller, "display_name", controller.name)
    metrics_collector = MetricsCollector(controller_id=controller_id, controller_name=controller_name)
    started_time = time.perf_counter()

    # Khởi tạo môi trường SUMO
    with SumoEnvironment(
        config_file=Path(sumo_config),
        gui=gui,
        seed=seed,
        yellow_seconds=yellow_seconds,
    ) as env:
        elapsed = 0
        decision_idx = 0

        while elapsed < steps and env.has_vehicles_expected():
            # 1. Thu thập trạng thái quan sát từ các ngã tư
            observations = env.observe()

            # 2. Bộ điều khiển ra quyết định chọn pha cho từng ngã tư
            actions = {
                tls_id: controller.select_phase(obs)
                for tls_id, obs in observations.items()
            }
            pressures = {
                tls_id: controller.phase_pressures(obs)
                for tls_id, obs in observations.items()
            }
            green_elapsed = {
                tls_id: obs.green_elapsed
                for tls_id, obs in observations.items()
            }

            # 3. Tiến hành mô phỏng trong khoảng action_interval bước (giây)
            interval = min(action_interval, steps - elapsed)
            for _ in range(interval):
                env.step(actions)
                elapsed += 1
                if gui and step_delay:
                    time.sleep(step_delay)
                if not env.has_vehicles_expected():
                    break

            # 4. Ghi nhận dữ liệu quyết định và chỉ số snapshot
            snapshot = env.snapshot()
            metrics_collector.record_decision(
                decision_idx=decision_idx,
                elapsed_s=elapsed,
                snapshot=snapshot,
                actions=actions,
                green_elapsed=green_elapsed,
                pressures=pressures,
            )
            decision_idx += 1

        final_snapshot = env.snapshot()

    wall_clock_s = time.perf_counter() - started_time

    # Tính toán bộ chỉ số đánh giá chuẩn
    eval_metrics = metrics_collector.compute_summary(
        final_snapshot=final_snapshot,
        simulated_seconds=elapsed,
        wall_clock_s=wall_clock_s,
    )

    # Tổng hợp toàn bộ số liệu của lượt chạy (bao gồm cả thông tin môi trường)
    summary = {
        "controller": controller_id,
        "controller_name": controller_name,
        "sumo_config": str(Path(sumo_config).resolve()),
        "seed": seed,
        "simulated_seconds": elapsed,
        "action_interval_s": action_interval,
        "yellow_seconds": yellow_seconds,
        "decisions": eval_metrics.decisions,
        "departed_vehicles": eval_metrics.departed_vehicles,
        "throughput": eval_metrics.throughput,
        "completion_rate": eval_metrics.completion_rate,
        "average_travel_time_s": eval_metrics.average_travel_time_s,
        "penalized_travel_time_s": eval_metrics.penalized_travel_time_s,
        "average_delay_s": eval_metrics.average_delay_s,
        "total_time_loss_s": eval_metrics.total_time_loss_s,
        "average_queue_vehicles": eval_metrics.average_queue_vehicles,
        "average_current_waiting_s": eval_metrics.average_current_waiting_s,
        "phase_switches": eval_metrics.phase_switches,
        "wall_clock_s": eval_metrics.wall_clock_s,
    }

    # Xuất file CSV chi tiết từng bước và file JSON tổng kết
    metrics_collector.export_trace_csv(agent_dir / "decision_trace.csv")

    (agent_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    return summary


def write_comparison(output_dir: Path, summaries: list[dict]) -> None:
    """Xuất file so sánh tổng hợp (comparison.csv và comparison.json) giữa các thuật toán."""
    if not summaries:
        return

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Xuất CSV
    output_csv = output_dir / "comparison.csv"
    fieldnames = list(summaries[0].keys())
    with output_csv.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summaries)

    # Xuất JSON
    output_json = output_dir / "comparison.json"
    output_json.write_text(
        json.dumps(summaries, indent=2, ensure_ascii=False), encoding="utf-8"
    )
