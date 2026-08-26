"""Command-line entry point for the SUMO-only FT/MP project."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from src.traffic_control.controllers import FixedTimeController, MaxPressureController
from src.traffic_control.experiment import run_experiment, write_comparison


ROOT = Path(__file__).resolve().parent
DEFAULT_SCENARIO = ROOT / "data" / "raw_data" / "cologne1" / "cologne1.sumocfg"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="SUMO traffic-signal demo tự cài đặt: Fixed-Time và Max-Pressure"
    )
    parser.add_argument(
        "--controller",
        choices=["fixedtime", "maxpressure", "all"],
        default="all",
    )
    parser.add_argument("--scenario", type=Path, default=DEFAULT_SCENARIO)
    parser.add_argument("--steps", type=int, default=900)
    parser.add_argument("--action-interval", type=int, default=10)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--yellow-seconds", type=float, default=5.0)
    parser.add_argument("--fixed-green", type=float, default=30.0)
    parser.add_argument("--minimum-green", type=float, default=10.0)
    parser.add_argument("--gui", action="store_true")
    parser.add_argument("--step-delay", type=float, default=0.0)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    if args.steps <= 0 or args.action_interval <= 0:
        parser.error("--steps và --action-interval phải dương")
    if args.step_delay < 0 or args.yellow_seconds < 0:
        parser.error("--step-delay và --yellow-seconds không được âm")
    return args


def print_summary(summaries: list[dict[str, object]], output_dir: Path) -> None:
    print("\n=== KẾT QUẢ SUMO FT/MP ===")
    print("Controller | Travel time (s) | Queue (xe) | Waiting (s) | Throughput | Đổi pha")
    print("-" * 96)
    for item in summaries:
        print(
            f"{item['controller']} | "
            f"{float(item['average_travel_time_s']):.2f} | "
            f"{float(item['average_queue_vehicles']):.2f} | "
            f"{float(item['average_current_waiting_s']):.2f} | "
            f"{item['throughput']} | {item['phase_switches']}"
        )
    print(f"\nKết quả chi tiết: {output_dir}")


def child_command(args: argparse.Namespace, controller: str, output: Path) -> list[str]:
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--controller",
        controller,
        "--scenario",
        str(args.scenario.resolve()),
        "--steps",
        str(args.steps),
        "--action-interval",
        str(args.action_interval),
        "--seed",
        str(args.seed),
        "--yellow-seconds",
        str(args.yellow_seconds),
        "--fixed-green",
        str(args.fixed_green),
        "--minimum-green",
        str(args.minimum_green),
        "--step-delay",
        str(args.step_delay),
        "--output",
        str(output),
    ]
    if args.gui:
        command.append("--gui")
    return command


def main() -> int:
    args = parse_args()
    output_dir = (
        args.output.resolve()
        if args.output
        else ROOT / "results" / datetime.now().strftime("%Y%m%d-%H%M%S")
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.controller == "all":
        summaries = []
        for controller_name in ("fixedtime", "maxpressure"):
            subprocess.run(
                child_command(args, controller_name, output_dir),
                cwd=ROOT,
                check=True,
            )
            summary_file = output_dir / controller_name / "summary.json"
            summaries.append(json.loads(summary_file.read_text(encoding="utf-8")))
        write_comparison(output_dir, summaries)
        (ROOT / "results" / "latest.txt").write_text(
            str(output_dir), encoding="utf-8"
        )
        print_summary(summaries, output_dir)
        return 0

    controller = (
        FixedTimeController(green_seconds=args.fixed_green)
        if args.controller == "fixedtime"
        else MaxPressureController(minimum_green_seconds=args.minimum_green)
    )
    print(
        f"Đang chạy {controller.name}: {args.scenario.resolve()} | "
        f"seed={args.seed} | {args.steps}s"
    )
    summary = run_experiment(
        controller=controller,
        sumo_config=args.scenario,
        steps=args.steps,
        action_interval=args.action_interval,
        seed=args.seed,
        gui=args.gui,
        yellow_seconds=args.yellow_seconds,
        step_delay=args.step_delay,
        output_dir=output_dir,
    )
    write_comparison(output_dir, [summary])
    (ROOT / "results" / "latest.txt").write_text(str(output_dir), encoding="utf-8")
    print_summary([summary], output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
