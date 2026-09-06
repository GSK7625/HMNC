"""Module trực quan hóa và vẽ biểu đồ khoa học tự động chuẩn bài báo (Publication-Quality Charts).

Cung cấp các chức năng:
1. plot_benchmark_comparison: Vẽ biểu đồ cột 4 chỉ số cốt lõi (Penalized TT, Delay, Queue, Throughput)
   kèm thanh sai số lỗi (Error bars Mean ± Std) khi đánh giá đa hạt giống khoa học.
2. plot_time_series: Vẽ biểu đồ chuỗi thời gian diễn biến hàng đợi và độ trễ từ decision_trace.csv.
3. plot_learning_curve: Vẽ biểu đồ tiến trình hội tụ (Learning curve) khi huấn luyện Q-Learning / DQN.
4. generate_all_plots: Tự động phát hiện dữ liệu và xuất toàn bộ ảnh đồ thị chất lượng cao (300 DPI).
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

# Cấu hình backend Agg không giao diện để chạy an toàn trên mọi luồng, server, CI/CD
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# Bảng màu nhận diện chuẩn hóa theo từng thuật toán
CONTROLLER_COLORS: dict[str, str] = {
    "fixedtime": "#64748B",       # Xám đá / Slate (Baseline Heuristic)
    "ft": "#64748B",
    "maxpressure": "#0284C7",     # Xanh đại dương (Adaptive Flow)
    "mp": "#0284C7",
    "qlearning": "#16A34A",       # Xanh lá mạ (Reinforcement Learning)
    "ql": "#16A34A",
    "dqn": "#EA580C",             # Cam cháy đậm (Deep RL)
    "deepq": "#EA580C",
    "deep_q": "#EA580C",
}
DEFAULT_PALETTE = ["#0284C7", "#EA580C", "#16A34A", "#64748B", "#8B5CF6", "#D97706", "#EC4899"]


def _get_color(name: str, index: int = 0) -> str:
    key = name.strip().lower()
    for k, v in CONTROLLER_COLORS.items():
        if k in key:
            return v
    return DEFAULT_PALETTE[index % len(DEFAULT_PALETTE)]


def _setup_figure_style():
    """Thiết lập thông số hiển thị đẹp, rõ ràng theo chuẩn đồ họa khoa học."""
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Segoe UI", "DejaVu Sans", "Arial", "Helvetica"],
        "axes.edgecolor": "#CBD5E1",
        "axes.linewidth": 1.0,
        "grid.color": "#E2E8F0",
        "grid.linestyle": "--",
        "grid.linewidth": 0.7,
        "grid.alpha": 0.7,
    })


def plot_benchmark_comparison(results_dir: Path | str, output_file: Path | str | None = None) -> Path | None:
    """Vẽ biểu đồ cột 4 chỉ số khoa học so sánh giữa các thuật toán."""
    res_dir = Path(results_dir)
    if not res_dir.is_dir():
        return None

    _setup_figure_style()

    # 1. Kiểm tra xem có file tổng hợp đa hạt giống (multi_seed_summary) hay không
    multi_seed_json = res_dir / "multi_seed_summary.json"
    multi_seed_csv = res_dir / "multi_seed_summary.csv"
    comp_json = res_dir / "comparison.json"
    comp_csv = res_dir / "comparison.csv"

    is_multi_seed = False
    data: list[dict] = []

    if multi_seed_json.is_file():
        try:
            data = json.loads(multi_seed_json.read_text(encoding="utf-8"))
            is_multi_seed = True
        except Exception:
            data = []
    elif multi_seed_csv.is_file():
        with multi_seed_csv.open("r", encoding="utf-8-sig") as f:
            data = list(csv.DictReader(f))
            is_multi_seed = True

    if not data and comp_json.is_file():
        try:
            data = json.loads(comp_json.read_text(encoding="utf-8"))
        except Exception:
            data = []
    elif not data and comp_csv.is_file():
        with comp_csv.open("r", encoding="utf-8-sig") as f:
            data = list(csv.DictReader(f))

    if not data:
        return None

    labels = []
    colors = []
    for idx, item in enumerate(data):
        name = item.get("controller_name") or item.get("controller") or f"Controller {idx}"
        labels.append(name)
        c_id = item.get("controller", name)
        colors.append(_get_color(str(c_id), idx))

    fig, axes = plt.subplots(2, 2, figsize=(13, 10), constrained_layout=True)

    metrics_meta = [
        (
            axes[0, 0],
            "penalized_travel_time_mean" if is_multi_seed else "penalized_travel_time_s",
            "penalized_travel_time_std" if is_multi_seed else None,
            "Penalized Travel Time (giây)",
            "Thời gian di chuyển có phạt (Thấp hơn là tốt hơn ↓)",
            "#0284C7",
        ),
        (
            axes[0, 1],
            "average_delay_mean" if is_multi_seed else "average_delay_s",
            "average_delay_std" if is_multi_seed else None,
            "Độ trễ trung bình (giây)",
            "Độ trễ trung bình mỗi xe (Thấp hơn là tốt hơn ↓)",
            "#D97706",
        ),
        (
            axes[1, 0],
            "average_queue_mean" if is_multi_seed else "average_queue_vehicles",
            "average_queue_std" if is_multi_seed else None,
            "Hàng đợi trung bình (xe)",
            "Số xe dừng chờ trung bình (Thấp hơn là tốt hơn ↓)",
            "#DC2626",
        ),
        (
            axes[1, 1],
            "throughput_mean" if is_multi_seed else "throughput",
            "throughput_std" if is_multi_seed else None,
            "Thông lượng (xe hoàn thành)",
            "Tổng số xe về đích (Cao hơn là tốt hơn ↑)",
            "#15803D",
        ),
    ]

    x_positions = np.arange(len(labels))
    bar_width = 0.55

    for ax, val_key, std_key, y_label, title, theme_color in metrics_meta:
        values = []
        errors = []
        for item in data:
            v = float(item.get(val_key, item.get(val_key.replace("_mean", "_s"), 0.0)))
            values.append(v)
            if is_multi_seed and std_key:
                errors.append(float(item.get(std_key, 0.0)))
            else:
                errors.append(0.0)

        err_param = errors if (is_multi_seed and any(e > 0 for e in errors)) else None
        bars = ax.bar(
            x_positions,
            values,
            width=bar_width,
            yerr=err_param,
            capsize=5,
            color=colors,
            edgecolor="#1E293B",
            linewidth=1.0,
            alpha=0.9,
            zorder=3,
        )

        ax.grid(axis="y", linestyle="--", alpha=0.7, zorder=0)
        ax.set_title(title, fontsize=12, fontweight="bold", pad=10, color="#0F172A")
        ax.set_ylabel(y_label, fontsize=10, fontweight="bold", color="#334155")
        ax.set_xticks(x_positions)
        ax.set_xticklabels(labels, fontsize=10, fontweight="bold", rotation=10, ha="right")

        # Đặt nhãn giá trị số lên trên từng cột
        for bar, val, err in zip(bars, values, errors):
            height = bar.get_height()
            label_text = f"{val:.1f} ± {err:.1f}" if (is_multi_seed and err > 0) else f"{val:.1f}"
            y_offset = height + (err if err else 0.0)
            ax.annotate(
                label_text,
                xy=(bar.get_x() + bar.get_width() / 2, y_offset),
                xytext=(0, 4),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=9,
                fontweight="bold",
                color="#0F172A",
            )

        y_max = max(v + e for v, e in zip(values, errors)) if values else 10
        ax.set_ylim(0, max(1.0, y_max * 1.22))

    seed_note = "Đa hạt giống khoa học (Multi-Seed: Mean ± Std)" if is_multi_seed else "Kiểm chuẩn đơn hạt giống (Single-Seed)"
    fig.suptitle(
        f"SO SÁNH HIỆU NĂNG ĐIỀU KHIỂN ĐÈN GIAO THÔNG (RESCO BENCHMARK)\n({seed_note})",
        fontsize=14,
        fontweight="bold",
        color="#0F172A",
        y=1.02,
    )

    out_path = Path(output_file) if output_file else res_dir / "benchmark_comparison.png"
    fig.savefig(str(out_path), dpi=300, bbox_inches="tight")
    plt.close(fig)
    return out_path


def plot_time_series(results_dir: Path | str, output_file: Path | str | None = None) -> Path | None:
    """Vẽ biểu đồ chuỗi thời gian diễn biến hàng đợi và độ trễ từ decision_trace.csv."""
    res_dir = Path(results_dir)
    if not res_dir.is_dir():
        return None

    _setup_figure_style()

    # Tìm kiếm các file decision_trace.csv (hỗ trợ cả cấu trúc đơn seed và đa seed seed_0/)
    search_dir = res_dir
    seed_0 = res_dir / "seed_0"
    if seed_0.is_dir():
        search_dir = seed_0

    trace_files = list(search_dir.glob("*/decision_trace.csv"))
    if not trace_files:
        return None

    fig, (ax_queue, ax_delay) = plt.subplots(2, 1, figsize=(12, 8), sharex=True, constrained_layout=True)

    has_data = False

    for idx, trace_file in enumerate(trace_files):
        controller_name = trace_file.parent.name
        color = _get_color(controller_name, idx)

        times = []
        queues = []
        delays = []

        try:
            with trace_file.open("r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    t = float(row.get("simulation_time_s", row.get("elapsed_s", 0.0)))
                    q = float(row.get("average_queue_vehicles", 0.0))
                    d = float(row.get("average_delay_s", row.get("average_current_waiting_s", 0.0)))
                    times.append(t)
                    queues.append(q)
                    delays.append(d)
        except Exception:
            continue

        if not times:
            continue

        has_data = True
        label_disp = controller_name.upper()
        if "fixed" in controller_name.lower():
            label_disp = "Fixed-Time (Webster)"
        elif "pressure" in controller_name.lower():
            label_disp = "Max-Pressure (Varaiya)"
        elif "ql" in controller_name.lower() or "qlearn" in controller_name.lower():
            label_disp = "Q-Learning (IDQL)"
        elif "dqn" in controller_name.lower():
            label_disp = "DQN (Double IDQN)"

        # Vẽ hàng đợi
        ax_queue.plot(times, queues, label=label_disp, color=color, linewidth=2.0, alpha=0.9)
        ax_queue.fill_between(times, queues, color=color, alpha=0.08)

        # Vẽ độ trễ
        ax_delay.plot(times, delays, label=label_disp, color=color, linewidth=2.0, alpha=0.9)
        ax_delay.fill_between(times, delays, color=color, alpha=0.08)

    if not has_data:
        plt.close(fig)
        return None

    ax_queue.set_title("Diễn biến Hàng đợi Dừng chờ xe theo Thời gian (Queue Length over Time)", fontsize=11, fontweight="bold")
    ax_queue.set_ylabel("Hàng đợi TB (xe)", fontsize=10, fontweight="bold")
    ax_queue.grid(True, linestyle="--", alpha=0.7)
    ax_queue.legend(loc="upper right", framealpha=0.9, fontsize=9)
    ax_queue.set_ylim(bottom=0)

    ax_delay.set_title("Diễn biến Độ trễ / Thời gian chờ tích lũy theo Thời gian (Delay over Time)", fontsize=11, fontweight="bold")
    ax_delay.set_xlabel("Thời gian mô phỏng (giây)", fontsize=10, fontweight="bold")
    ax_delay.set_ylabel("Độ trễ TB (giây)", fontsize=10, fontweight="bold")
    ax_delay.grid(True, linestyle="--", alpha=0.7)
    ax_delay.legend(loc="upper right", framealpha=0.9, fontsize=9)
    ax_delay.set_ylim(bottom=0)

    fig.suptitle(
        "DIEN BIEN LUU LUONG GIAO THONG THEO THOI GIAN THUC (TIME-SERIES DYNAMICS)",
        fontsize=13,
        fontweight="bold",
        color="#0F172A",
    )

    out_path = Path(output_file) if output_file else res_dir / "traffic_time_series.png"
    fig.savefig(str(out_path), dpi=300, bbox_inches="tight")
    plt.close(fig)
    return out_path


def plot_learning_curve(results_dir: Path | str, output_file: Path | str | None = None) -> Path | None:
    """Vẽ biểu đồ đường cong học tập (Learning Curve) qua từng episode huấn luyện RL."""
    res_dir = Path(results_dir)
    if not res_dir.is_dir():
        return None

    _setup_figure_style()

    curve_file = res_dir / "learning_curve.json"
    data = []
    if curve_file.is_file():
        try:
            data = json.loads(curve_file.read_text(encoding="utf-8"))
        except Exception:
            data = []

    if not data:
        csv_curve = res_dir / "learning_curve.csv"
        if csv_curve.is_file():
            with csv_curve.open("r", encoding="utf-8-sig") as f:
                data = list(csv.DictReader(f))

    if not data:
        return None

    episodes = [int(row["episode"]) for row in data]
    delays = [float(row["delay_s"]) for row in data]
    penalized_tt = [float(row.get("penalized_tt_s", 0.0)) for row in data]
    queues = [float(row["queue_vehicles"]) for row in data]
    epsilons = [float(row["epsilon"]) for row in data]

    fig, (ax_perf, ax_queue, ax_eps) = plt.subplots(3, 1, figsize=(11, 10), sharex=True, constrained_layout=True)

    # Subplot 1: Delay & Penalized TT
    ax_perf.plot(episodes, delays, marker="o", color="#EA580C", linewidth=2.0, label="Độ trễ TB (Delay s)")
    if any(p > 0 for p in penalized_tt):
        ax_perf.plot(episodes, penalized_tt, marker="s", color="#0284C7", linewidth=2.0, linestyle="--", label="Penalized Travel Time (s)")
    ax_perf.set_title("Sự suy giảm Độ trễ & Thời gian di chuyển (Performance Convergence)", fontsize=11, fontweight="bold")
    ax_perf.set_ylabel("Thời gian (giây)", fontsize=10, fontweight="bold")
    ax_perf.grid(True, linestyle="--", alpha=0.7)
    ax_perf.legend(loc="upper right", fontsize=9)

    # Subplot 2: Queue Length
    ax_queue.plot(episodes, queues, marker="^", color="#DC2626", linewidth=2.0, label="Hàng đợi dừng chờ (xe)")
    ax_queue.set_title("Sự suy giảm Hàng đợi dừng xe (Congestion Reduction)", fontsize=11, fontweight="bold")
    ax_queue.set_ylabel("Hàng đợi (xe)", fontsize=10, fontweight="bold")
    ax_queue.grid(True, linestyle="--", alpha=0.7)
    ax_queue.legend(loc="upper right", fontsize=9)

    # Subplot 3: Epsilon Exploration Decay
    ax_eps.plot(episodes, epsilons, marker="d", color="#16A34A", linewidth=2.0, label="Tỷ lệ khám phá (Epsilon)")
    ax_eps.set_title("Lịch trình suy giảm tỷ lệ khám phá (Epsilon Decay Schedule)", fontsize=11, fontweight="bold")
    ax_eps.set_xlabel("Tập huấn luyện (Episode)", fontsize=10, fontweight="bold")
    ax_eps.set_ylabel("Epsilon", fontsize=10, fontweight="bold")
    ax_eps.grid(True, linestyle="--", alpha=0.7)
    ax_eps.legend(loc="upper right", fontsize=9)
    ax_eps.set_ylim(0, 1.0)

    fig.suptitle(
        "DUONG CONG HOI TU HUAN LUYEN RL (TRAINING & CONVERGENCE CURVES)",
        fontsize=13,
        fontweight="bold",
        color="#0F172A",
    )

    out_path = Path(output_file) if output_file else res_dir / "learning_curve.png"
    fig.savefig(str(out_path), dpi=300, bbox_inches="tight")
    plt.close(fig)
    return out_path


def generate_all_plots(results_dir: Path | str) -> list[Path]:
    """Tự động kiểm tra và vẽ toàn bộ các biểu đồ khả dụng cho một lượt chạy kết quả."""
    res_dir = Path(results_dir)
    generated: list[Path] = []

    p_bench = plot_benchmark_comparison(res_dir)
    if p_bench and p_bench.is_file():
        generated.append(p_bench)

    p_time = plot_time_series(res_dir)
    if p_time and p_time.is_file():
        generated.append(p_time)

    p_learn = plot_learning_curve(res_dir)
    if p_learn and p_learn.is_file():
        generated.append(p_learn)

    return generated
