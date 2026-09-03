"""Điểm khởi chạy chương trình mô phỏng điều khiển đèn giao thông trên SUMO."""

from __future__ import annotations

import argparse
import csv
import inspect
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from statistics import fmean, stdev

# Đảm bảo in tiếng Việt chuẩn trên terminal Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from src.traffic_control.controllers import (
    CONTROLLER_REGISTRY,
    FixedTimeController,
    MaxPressureController,
    QLearningController,
)
from src.traffic_control.core.config import BenchmarkConfig
from src.traffic_control.experiment import run_experiment, write_comparison

ROOT = Path(__file__).resolve().parent
DEFAULT_SCENARIO = ROOT / "data" / "raw_data" / "cologne1" / "cologne1.sumocfg"
DEFAULT_Q_TABLE = ROOT / "checkpoints" / "q_table.json"
DEFAULT_BENCHMARK_CONTROLLERS = ["fixedtime", "maxpressure", "qlearning"]


def parse_args():
    """Xử lý các tham số dòng lệnh."""
    registered_names = CONTROLLER_REGISTRY.get_all_names(include_aliases=True)
    valid_choices = list(registered_names) + ["all"]

    parser = argparse.ArgumentParser(
        description="Mô phỏng SUMO: So sánh chuẩn hóa các thuật toán điều khiển đèn giao thông"
    )
    parser.add_argument(
        "-c", "--controller",
        choices=valid_choices,
        default="all",
        help="Thuật toán: all (so sánh), hoặc tên cụ thể/viết tắt (ft, mp, ql, v.v.)",
    )
    parser.add_argument(
        "--controllers",
        type=str,
        default=None,
        help="Danh sách các thuật toán cần so sánh khi chạy 'all' (phân tách bởi dấu phẩy, vd: 'ft,mp,ql')",
    )
    parser.add_argument(
        "-m", "--scenario", "--map",
        dest="scenario",
        type=Path,
        default=DEFAULT_SCENARIO,
        help="Đường dẫn file kịch bản mạng lưới .sumocfg",
    )
    parser.add_argument("-s", "--steps", type=int, default=900, help="Số giây mô phỏng (mặc định: 900s)")
    parser.add_argument("--action-interval", type=int, default=10, help="Số giây giữa 2 lần ra quyết định đổi đèn")
    parser.add_argument("--seed", type=int, default=0, help="Random seed đơn lẻ (mặc định: 0)")
    parser.add_argument(
        "--seeds",
        type=str,
        default=None,
        help="Danh sách các seeds phân tách bởi dấu phẩy để kiểm chuẩn đa hạt giống khoa học theo chuẩn RESCO (vd: '0,1,2')",
    )
    parser.add_argument("--yellow-seconds", type=float, default=3.0, help="Thời gian đèn vàng (giây, mặc định 3.0s theo chuẩn RESCO)")
    parser.add_argument("--minimum-green", type=float, default=10.0, help="Thời gian xanh tối thiểu an toàn G_min (giây)")
    parser.add_argument(
        "--max-green",
        type=float,
        default=0.0,
        help="Thời gian xanh tối đa G_max cho Max-Pressure chống bỏ đói pha (giây, mặc định 0: không giới hạn)",
    )
    parser.add_argument(
        "--pressure-mode",
        choices=["standard", "halting", "normalized"],
        default="standard",
        help="Chế độ tính áp lực Max-Pressure: standard (chuẩn Varaiya 2013: vehicle count đồng nhất), halting (xe dừng vào vs xe chạy ra), normalized (chuẩn hóa số làn)",
    )
    parser.add_argument("--fixed-green", type=float, default=30.0, help="Thời gian xanh cơ sở cho FT (giây)")
    parser.add_argument(
        "--proportional-splits",
        action="store_true",
        help="Kích hoạt chia thời gian xanh Fixed-Time theo tỉ lệ số làn (xấp xỉ Webster/RESCO) thay vì ép cứng bằng nhau",
    )
    parser.add_argument(
        "--reward-type",
        choices=["queue", "delay", "pressure"],
        default="queue",
        help="Hàm mục tiêu phần thưởng cho Q-Learning theo chuẩn RESCO: queue (hàng đợi dừng), delay (thời gian chờ), pressure (áp lực)",
    )
    parser.add_argument("--train", action="store_true", help="Kích hoạt chế độ huấn luyện cho Q-Learning")
    parser.add_argument("--episodes", type=int, default=1, help="Số episodes khi huấn luyện Q-Learning (mặc định: 1)")
    parser.add_argument("--alpha", type=float, default=0.1, help="Learning rate alpha cho Q-Learning (mặc định: 0.1)")
    parser.add_argument("--gamma", type=float, default=0.9, help="Discount factor gamma cho Q-Learning (mặc định: 0.9)")
    parser.add_argument("--epsilon", type=float, default=0.05, help="Tỷ lệ khám phá epsilon cho Q-Learning (mặc định: 0.05)")
    parser.add_argument(
        "--q-table-path",
        type=Path,
        default=DEFAULT_Q_TABLE,
        help="Đường dẫn file lưu/nạp Q-table JSON (mặc định: checkpoints/q_table.json)",
    )
    parser.add_argument(
        "--controller-args",
        type=str,
        default=None,
        help="Tham số bổ sung cho controller mới dưới dạng k=v,k2=v2 (vd: 'theta=10,weight=0.5')",
    )
    parser.add_argument("-g", "--gui", action="store_true", help="Mở giao diện đồ họa SUMO-GUI")
    parser.add_argument(
        "-d", "--step-delay",
        type=float,
        default=None,
        help="Độ trễ mỗi bước mô phỏng khi xem GUI (mặc định: 0.03s nếu có GUI, 0s nếu không GUI)",
    )
    parser.add_argument("-o", "--output", type=Path, default=None, help="Thư mục lưu kết quả")
    args = parser.parse_args()

    if args.step_delay is None:
        args.step_delay = 0.03 if args.gui else 0.0

    if args.steps <= 0 or args.action_interval <= 0:
        parser.error("--steps và --action-interval phải lớn hơn 0")
    if args.step_delay < 0 or args.yellow_seconds < 0:
        parser.error("--step-delay và --yellow-seconds không được âm")
    if args.minimum_green < 0 or args.max_green < 0:
        parser.error("--minimum-green và --max-green không được âm")
    if args.episodes <= 0:
        parser.error("--episodes phải lớn hơn hoặc bằng 1")
    return args


def instantiate_controller(controller_name: str, args):
    """Khởi tạo thể hiện của thuật toán điều khiển từ Controller Registry."""
    cls = CONTROLLER_REGISTRY.get(controller_name)
    metadata = CONTROLLER_REGISTRY.get_metadata(controller_name)

    kwargs = {
        "minimum_green_seconds": args.minimum_green,
    }

    # Xử lý tham số đặc thù của FixedTime
    if issubclass(cls, FixedTimeController) or metadata.name == "fixedtime":
        kwargs["green_seconds"] = args.fixed_green
        kwargs["proportional_splits"] = getattr(args, "proportional_splits", False)

    # Xử lý tham số đặc thù của MaxPressure
    elif issubclass(cls, MaxPressureController) or metadata.name == "maxpressure":
        kwargs["max_green_seconds"] = getattr(args, "max_green", 0.0)
        kwargs["pressure_mode"] = getattr(args, "pressure_mode", "standard")

    # Xử lý tham số đặc thù của QLearning
    elif issubclass(cls, QLearningController) or metadata.name == "qlearning":
        is_learning = args.train or not args.q_table_path.is_file()
        kwargs.update({
            "alpha": args.alpha,
            "gamma": args.gamma,
            "epsilon": args.epsilon if is_learning else 0.0,
            "learning": is_learning,
            "reward_type": getattr(args, "reward_type", "queue"),
            "q_table_path": args.q_table_path,
        })

    # Nạp các tham số tùy biến nếu có từ --controller-args
    if args.controller_args:
        for pair in args.controller_args.split(","):
            if "=" in pair:
                key, val = pair.split("=", 1)
                key = key.strip()
                val = val.strip()
                try:
                    if "." in val:
                        val = float(val)
                    else:
                        val = int(val)
                except ValueError:
                    if val.lower() == "true":
                        val = True
                    elif val.lower() == "false":
                        val = False
                kwargs[key] = val

    sig = inspect.signature(cls.__init__)
    has_varkw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
    if not has_varkw:
        kwargs = {k: v for k, v in kwargs.items() if k in sig.parameters}

    return cls(**kwargs)


def print_summary(summaries: list[dict], output_dir: Path):
    """In bảng kết quả so sánh trực quan chuẩn hóa ra màn hình terminal."""
    print("\n=== KẾT QUẢ SO SÁNH CHUẨN HÓA CÁC THUẬT TOÁN ĐIỀU KHIỂN ĐÈN ===")
    headers = [
        ("Thuật toán", 14),
        ("Thời gian đi (s)", 17),
        ("Penalized TT (s)", 17),
        ("Độ trễ TB (s)", 14),
        ("Hàng đợi (xe)", 14),
        ("Thông lượng", 11),
        ("Tỷ lệ xong", 11),
        ("Đổi pha", 8),
    ]
    header_str = " | ".join(f"{h[0]:<{h[1]}}" for h in headers)
    print(header_str)
    print("-" * len(header_str))

    for item in summaries:
        name = item.get("controller_name") or item.get("controller", "Unknown")
        travel_time = f"{float(item.get('average_travel_time_s', 0.0)):.2f}"
        penalized_tt = f"{float(item.get('penalized_travel_time_s', item.get('average_travel_time_s', 0.0))):.2f}"
        delay = f"{float(item.get('average_delay_s', 0.0)):.2f}"
        queue = f"{float(item.get('average_queue_vehicles', 0.0)):.2f}"
        throughput = str(item.get("throughput", 0))
        comp_rate = f"{float(item.get('completion_rate', 0.0)) * 100:.1f}%"
        switches = str(item.get("phase_switches", 0))

        print(
            f"{name:<14} | "
            f"{travel_time:>17} | "
            f"{penalized_tt:>17} | "
            f"{delay:>14} | "
            f"{queue:>14} | "
            f"{throughput:>11} | "
            f"{comp_rate:>11} | "
            f"{switches:>8}"
        )
    print(f"\n📁 Kết quả chi tiết đã được lưu tại: {output_dir}")


def aggregate_multi_seed_results(controller_runs: dict[str, list[dict]], output_dir: Path) -> list[dict]:
    """Tổng hợp số liệu qua nhiều seed thành Mean ± Std theo chuẩn nghiên cứu RESCO."""
    aggregated = []
    for c_name, runs in controller_runs.items():
        if not runs:
            continue
        c_disp = runs[0].get("controller_name", c_name)
        n = len(runs)

        def calc_stat(key):
            vals = [float(r.get(key, 0.0)) for r in runs]
            mean_val = fmean(vals)
            std_val = stdev(vals) if n > 1 else 0.0
            return mean_val, std_val

        p_tt_m, p_tt_s = calc_stat("penalized_travel_time_s")
        tt_m, tt_s = calc_stat("average_travel_time_s")
        d_m, d_s = calc_stat("average_delay_s")
        q_m, q_s = calc_stat("average_queue_vehicles")
        tp_m, tp_s = calc_stat("throughput")
        cr_m, cr_s = calc_stat("completion_rate")

        aggregated.append({
            "controller": c_name,
            "controller_name": c_disp,
            "seeds_count": n,
            "penalized_travel_time_mean": round(p_tt_m, 2),
            "penalized_travel_time_std": round(p_tt_s, 2),
            "average_travel_time_mean": round(tt_m, 2),
            "average_travel_time_std": round(tt_s, 2),
            "average_delay_mean": round(d_m, 2),
            "average_delay_std": round(d_s, 2),
            "average_queue_mean": round(q_m, 2),
            "average_queue_std": round(q_s, 2),
            "throughput_mean": round(tp_m, 1),
            "throughput_std": round(tp_s, 1),
            "completion_rate_mean": round(cr_m, 4),
            "completion_rate_std": round(cr_s, 4),
        })

    # Lưu kết quả tổng hợp đa hạt giống
    (output_dir / "multi_seed_summary.json").write_text(
        json.dumps(aggregated, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Xuất file CSV đa seed
    csv_file = output_dir / "multi_seed_summary.csv"
    if aggregated:
        with csv_file.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(aggregated[0].keys()))
            writer.writeheader()
            writer.writerows(aggregated)

    return aggregated


def print_multi_seed_summary(aggregated: list[dict], output_dir: Path):
    """In bảng thống kê khoa học Mean ± Std qua nhiều hạt giống (seeds)."""
    print("\n=== BÁO CÁO KIỂM CHUẨN ĐA HẠT GIỐNG (MULTI-SEED BENCHMARK: Mean ± Std) ===")
    headers = [
        ("Thuật toán", 14),
        ("Penalized TT (s)", 20),
        ("Thời gian đi (s)", 20),
        ("Độ trễ TB (s)", 18),
        ("Hàng đợi (xe)", 16),
        ("Thông lượng", 15),
        ("Tỷ lệ xong", 15),
    ]
    header_str = " | ".join(f"{h[0]:<{h[1]}}" for h in headers)
    print(header_str)
    print("-" * len(header_str))

    for item in aggregated:
        name = item.get("controller_name", item.get("controller"))
        p_tt = f"{item['penalized_travel_time_mean']:.2f} ± {item['penalized_travel_time_std']:.2f}"
        tt = f"{item['average_travel_time_mean']:.2f} ± {item['average_travel_time_std']:.2f}"
        delay = f"{item['average_delay_mean']:.2f} ± {item['average_delay_std']:.2f}"
        queue = f"{item['average_queue_mean']:.2f} ± {item['average_queue_std']:.2f}"
        tp = f"{item['throughput_mean']:.1f} ± {item['throughput_std']:.1f}"
        cr = f"{item['completion_rate_mean'] * 100:.1f}% ± {item['completion_rate_std'] * 100:.1f}%"

        print(
            f"{name:<14} | "
            f"{p_tt:>20} | "
            f"{tt:>20} | "
            f"{delay:>18} | "
            f"{queue:>16} | "
            f"{tp:>15} | "
            f"{cr:>15}"
        )
    print(f"\n📁 Kết quả đa hạt giống khoa học đã lưu tại: {output_dir}")


def build_child_command(args, controller_name: str, output: Path, seed: int | None = None) -> list[str]:
    """Tạo lệnh gọi tiến trình con khi chạy so sánh đồng bộ các thuật toán."""
    current_seed = seed if seed is not None else args.seed
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--controller", controller_name,
        "--scenario", str(args.scenario.resolve()),
        "--steps", str(args.steps),
        "--action-interval", str(args.action_interval),
        "--seed", str(current_seed),
        "--yellow-seconds", str(args.yellow_seconds),
        "--minimum-green", str(args.minimum_green),
        "--fixed-green", str(args.fixed_green),
        "--pressure-mode", str(getattr(args, "pressure_mode", "standard")),
        "--reward-type", str(args.reward_type),
        "--alpha", str(args.alpha),
        "--gamma", str(args.gamma),
        "--epsilon", str(args.epsilon),
        "--q-table-path", str(args.q_table_path.resolve()),
        "--step-delay", str(args.step_delay),
        "--output", str(output),
    ]
    if getattr(args, "proportional_splits", False) or args.controller == "all":
        command.append("--proportional-splits")
    if getattr(args, "max_green", 0.0) > 0:
        command.extend(["--max-green", str(args.max_green)])
    if args.controller_args:
        command.extend(["--controller-args", args.controller_args])
    if args.gui:
        command.append("--gui")
    return command


def ensure_trained_q_table(args) -> None:
    """Kiểm tra và tự động huấn luyện Q-Learning nếu bảng Q chưa có hoặc chưa đủ trạng thái hội tụ."""
    q_path = Path(args.q_table_path)
    need_training = False
    state_count = 0

    if not q_path.is_file():
        need_training = True
    else:
        try:
            data = json.loads(q_path.read_text(encoding="utf-8"))
            if data and isinstance(next(iter(data.values())), dict):
                state_count = sum(len(sub) for sub in data.values())
            else:
                state_count = len(data)
            if state_count < 15:
                need_training = True
        except Exception:
            need_training = True

    if need_training:
        print(
            f"\n[Fair Benchmark] Phát hiện Q-table ({q_path.name}) chưa đủ độ bao phủ (hiện có {state_count} trạng thái)."
            f"\n>>> Tự động huấn luyện nhanh 10 episodes với Epsilon Decay để Q-Learning có tri thức trước khi thi đấu..."
        )
        ctrl = QLearningController(
            minimum_green_seconds=args.minimum_green,
            alpha=args.alpha,
            gamma=args.gamma,
            epsilon=0.5,
            learning=True,
            reward_type=getattr(args, "reward_type", "queue"),
            q_table_path=q_path if q_path.is_file() else None,
        )
        train_steps = min(args.steps, 600)
        for ep in range(1, 11):
            ctrl.reset()
            run_experiment(
                controller=ctrl,
                sumo_config=args.scenario,
                steps=train_steps,
                action_interval=args.action_interval,
                seed=args.seed + ep * 10,
                gui=False,
                yellow_seconds=args.yellow_seconds,
                step_delay=0.0,
                output_dir=ROOT / "results" / "pretrain_cache",
            )
            eps = ctrl.decay_epsilon(decay_rate=0.85, min_epsilon=0.02)
            print(f"  Episode huấn luyện {ep}/10 hoàn tất (epsilon={eps:.3f}).")
        ctrl.save_q_table(q_path)
        print(f"Đã cập nhật Q-table chất lượng cao với {len(ctrl.q_table)} trạng thái tại: {q_path.resolve()}\n")


def main():
    args = parse_args()
    output_dir = (
        args.output.resolve()
        if args.output
        else ROOT / "results" / datetime.now().strftime("%Y%m%d-%H%M%S")
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    seeds = [int(s.strip()) for s in args.seeds.split(",") if s.strip()] if args.seeds else [args.seed]

    # Chế độ chạy so sánh nhiều thuật toán qua nhiều hạt giống (Multi-Seed Scientific Benchmark)
    if args.controller == "all":
        if args.controllers:
            target_controllers = [c.strip().lower() for c in args.controllers.split(",") if c.strip()]
        else:
            target_controllers = list(DEFAULT_BENCHMARK_CONTROLLERS)

        # Đảm bảo Q-table đã được huấn luyện tốt nếu có Q-learning trong danh sách so sánh
        if any(c in ["qlearning", "ql"] for c in target_controllers):
            ensure_trained_q_table(args)

        if len(seeds) > 1:
            print(f"Bắt đầu Benchmark đa hạt giống khoa học (seeds={seeds}) cho {len(target_controllers)} thuật toán...")
            controller_runs = {c: [] for c in target_controllers}

            for s in seeds:
                seed_dir = output_dir / f"seed_{s}"
                seed_dir.mkdir(parents=True, exist_ok=True)
                print(f"\n--- Đang chạy Seed = {s} ---")
                seed_summaries = []
                for name in target_controllers:
                    subprocess.run(
                        build_child_command(args, name, seed_dir, seed=s),
                        cwd=ROOT,
                        check=True,
                    )
                    meta = CONTROLLER_REGISTRY.get_metadata(name)
                    summary_file = seed_dir / meta.name / "summary.json"
                    data = json.loads(summary_file.read_text(encoding="utf-8"))
                    seed_summaries.append(data)
                    controller_runs[name].append(data)

                write_comparison(seed_dir, seed_summaries)

            aggregated = aggregate_multi_seed_results(controller_runs, output_dir)
            (ROOT / "results" / "latest.txt").write_text(str(output_dir), encoding="utf-8")
            print_multi_seed_summary(aggregated, output_dir)
            return 0

        # Nếu chỉ chạy 1 seed
        summaries = []
        for name in target_controllers:
            subprocess.run(
                build_child_command(args, name, output_dir, seed=seeds[0]),
                cwd=ROOT,
                check=True,
            )
            meta = CONTROLLER_REGISTRY.get_metadata(name)
            summary_file = output_dir / meta.name / "summary.json"
            summaries.append(json.loads(summary_file.read_text(encoding="utf-8")))

        write_comparison(output_dir, summaries)
        (ROOT / "results" / "latest.txt").write_text(str(output_dir), encoding="utf-8")
        print_summary(summaries, output_dir)
        return 0

    # Chế độ chạy 1 thuật toán đơn lẻ qua nhiều seeds
    if len(seeds) > 1:
        print(f"Bắt đầu chạy đa hạt giống (seeds={seeds}) cho thuật toán {args.controller}...")
        c_runs = {args.controller: []}
        for s in seeds:
            seed_dir = output_dir / f"seed_{s}"
            seed_dir.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                build_child_command(args, args.controller, seed_dir, seed=s),
                cwd=ROOT,
                check=True,
            )
            meta = CONTROLLER_REGISTRY.get_metadata(args.controller)
            summary_file = seed_dir / meta.name / "summary.json"
            c_runs[args.controller].append(json.loads(summary_file.read_text(encoding="utf-8")))

        aggregated = aggregate_multi_seed_results(c_runs, output_dir)
        (ROOT / "results" / "latest.txt").write_text(str(output_dir), encoding="utf-8")
        print_multi_seed_summary(aggregated, output_dir)
        return 0

    # Chế độ chạy 1 thuật toán đơn lẻ 1 seed
    args.seed = seeds[0]
    controller = instantiate_controller(args.controller, args)

    # Nếu là Q-Learning ở chế độ huấn luyện qua nhiều episodes
    if isinstance(controller, QLearningController) and args.train and args.episodes > 1:
        print(f"\n=== BẮT ĐẦU HUẤN LUYỆN SÂU Q-LEARNING ({args.episodes} EPISODES) ===")
        train_dir = output_dir / "train_episodes"
        train_history = []
        min_eps = 0.02
        initial_eps = max(0.1, args.epsilon)
        controller.epsilon = initial_eps
        # Tỷ lệ suy giảm epsilon qua từng episode
        decay_rate = (min_eps / initial_eps) ** (1.0 / max(1, args.episodes - 1))

        for ep in range(1, args.episodes + 1):
            controller.reset()
            ep_seed = args.seed + ep * 7
            ep_summary = run_experiment(
                controller=controller,
                sumo_config=args.scenario,
                steps=args.steps,
                action_interval=args.action_interval,
                seed=ep_seed,
                gui=False,
                yellow_seconds=args.yellow_seconds,
                step_delay=0.0,
                output_dir=train_dir / f"ep_{ep}",
            )
            cur_eps = controller.epsilon
            state_cnt = sum(len(sub) for sub in controller.q_tables.values()) if controller.q_tables else len(controller.q_table)
            train_history.append({
                "episode": ep,
                "epsilon": round(cur_eps, 4),
                "delay_s": ep_summary["average_delay_s"],
                "penalized_tt_s": ep_summary["penalized_travel_time_s"],
                "travel_time_s": ep_summary["average_travel_time_s"],
                "queue_vehicles": ep_summary["average_queue_vehicles"],
                "throughput": ep_summary["throughput"],
                "completion_rate": ep_summary["completion_rate"],
                "switches": ep_summary["phase_switches"],
                "states_discovered": state_cnt,
            })
            if ep % 5 == 0 or ep == 1 or ep == args.episodes:
                print(
                    f"  [Tập {ep:2d}/{args.episodes}] eps={cur_eps:.3f} | "
                    f"Độ trễ={ep_summary['average_delay_s']:6.2f}s | "
                    f"Penalized TT={ep_summary['penalized_travel_time_s']:6.2f}s | "
                    f"Hàng đợi={ep_summary['average_queue_vehicles']:5.2f} xe | "
                    f"Thông lượng={ep_summary['throughput']:3d} | "
                    f"States={state_cnt}"
                )
            controller.decay_epsilon(decay_rate=decay_rate, min_epsilon=min_eps)

        controller.reset()

        # Lưu learning curve ra file CSV và JSON
        curve_file = output_dir / "learning_curve.csv"
        with curve_file.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(train_history[0].keys()))
            writer.writeheader()
            writer.writerows(train_history)
        (output_dir / "learning_curve.json").write_text(
            json.dumps(train_history, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"\n📁 Đã lưu toàn bộ biểu đồ học tập (Learning Curve) tại: {curve_file}")

        # Lưu bảng Q đã hội tụ
        controller.save_q_table(args.q_table_path)
        print(f"📁 Đã lưu bảng Q hội tụ ({train_history[-1]['states_discovered']} states) tại: {args.q_table_path.resolve()}\n")

        # In tóm tắt tiến trình hội tụ
        print("=== TIẾN TRÌNH HỘI TỤ (LEARNING CURVE SUMMARY) ===")
        print(f"{'Episode':<10} | {'Epsilon':<8} | {'Độ trễ (s)':<12} | {'Penalized TT':<14} | {'Hàng đợi':<10} | {'Số States':<10}")
        print("-" * 75)
        for row in train_history:
            if row['episode'] in [1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50] or row['episode'] == args.episodes:
                print(
                    f"{row['episode']:<10} | {row['epsilon']:<8.3f} | {row['delay_s']:<12.2f} | "
                    f"{row['penalized_tt_s']:<14.2f} | {row['queue_vehicles']:<10.2f} | {row['states_discovered']:<10}"
                )

        # Chuyển sang chế độ Đóng băng trọng số để Đánh giá (Freeze Evaluation)
        controller.learning = False
        controller.epsilon = 0.0
        print(f"\n>>> Đang tiến hành Đánh giá Kiểm chuẩn (Freeze Evaluation) trên test seed={args.seed}...")

    benchmark_config = BenchmarkConfig(
        scenario=args.scenario,
        steps=args.steps,
        action_interval=args.action_interval,
        seed=args.seed,
        yellow_seconds=args.yellow_seconds,
        minimum_green_seconds=args.minimum_green,
        gui=args.gui,
        step_delay=args.step_delay,
    )

    summary = run_experiment(
        controller=controller,
        output_dir=output_dir,
        benchmark_config=benchmark_config,
    )

    # Lưu lại Q-table sau khi hoàn tất nếu đang học
    if isinstance(controller, QLearningController) and controller.learning:
        controller.save_q_table(args.q_table_path)
        print(f"Đã cập nhật và lưu bảng Q tại: {args.q_table_path.resolve()}")

    write_comparison(output_dir, [summary])
    (ROOT / "results" / "latest.txt").write_text(str(output_dir), encoding="utf-8")
    print_summary([summary], output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
