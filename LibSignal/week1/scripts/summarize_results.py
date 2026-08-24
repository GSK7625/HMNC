from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import statistics
import tempfile
from pathlib import Path


FINAL_RE = re.compile(
    r"Final Travel Time is (?P<travel>[0-9.]+), mean rewards: (?P<reward>-?[0-9.]+), "
    r"queue: (?P<queue>[0-9.]+), delay: (?P<delay>[0-9.]+), throughput: (?P<throughput>[0-9]+)"
)


def read_completed_wait(csv_path: Path) -> float:
    waits: list[float] = []
    with csv_path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("completed_trip", "").lower() == "true":
                waits.append(float(row["custom_wait_s"]))
    return statistics.fmean(waits) if waits else math.nan


def read_log_metrics(logger_dir: Path) -> dict[str, float]:
    for log_path in sorted(logger_dir.glob("*.log"), reverse=True):
        match = FINAL_RE.search(log_path.read_text(encoding="utf-8", errors="replace"))
        if match:
            return {key: float(value) for key, value in match.groupdict().items()}
    return {}


def collect(repo: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    root = repo / "data" / "output_data" / "tsc"
    for method in ("fixedtime", "maxpressure"):
        method_root = root / f"sumo_{method}" / "sumo1x1"
        if not method_root.exists():
            continue
        for run_dir in sorted(method_root.glob("week1_seed_*")):
            logger_dir = run_dir / "logger"
            meta_path = logger_dir / "new_metrics_meta.json"
            csv_path = logger_dir / "new_metrics.csv"
            if not meta_path.exists() or not csv_path.exists():
                continue
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            log = read_log_metrics(logger_dir)
            rows.append(
                {
                    "method": method,
                    "seed": int(meta["seed"]),
                    "average_travel_time_s": float(meta["mean_travel_time_s"]),
                    "average_waiting_time_s": read_completed_wait(csv_path),
                    "average_queue_length": log.get("queue", math.nan),
                    "average_delay": log.get("delay", math.nan),
                    "throughput": int(meta["throughput_completed"]),
                    "completion_rate": float(meta["completion_rate"]),
                    "vehicles_logged": int(meta["n_vehicles_logged"]),
                    "prefix": meta["prefix"],
                }
            )
    return sorted(rows, key=lambda row: (str(row["method"]), int(row["seed"])))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise SystemExit("Không tìm thấy kết quả week1_seed_* để tổng hợp.")
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def aggregate(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    metric_names = (
        "average_travel_time_s",
        "average_waiting_time_s",
        "average_queue_length",
        "average_delay",
        "throughput",
        "completion_rate",
    )
    output: list[dict[str, object]] = []
    for method in ("fixedtime", "maxpressure"):
        selected = [row for row in rows if row["method"] == method]
        if not selected:
            continue
        item: dict[str, object] = {"method": method, "runs": len(selected)}
        for metric in metric_names:
            values = [float(row[metric]) for row in selected]
            valid = [value for value in values if not math.isnan(value)]
            item[f"{metric}_mean"] = statistics.fmean(valid) if valid else math.nan
            item[f"{metric}_std"] = statistics.stdev(valid) if len(valid) > 1 else 0.0
        output.append(item)
    return output


def plot(aggregate_rows: list[dict[str, object]], output: Path) -> None:
    try:
        os.environ.setdefault("MPLCONFIGDIR", tempfile.mkdtemp(prefix="libsignal-mpl-"))
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return

    display_names = {"fixedtime": "Fixed-Time", "maxpressure": "MaxPressure"}
    methods = [display_names.get(str(row["method"]), str(row["method"])) for row in aggregate_rows]
    labels = ["Travel time (s)", "Waiting time (s)", "Queue length", "Throughput"]
    keys = [
        "average_travel_time_s_mean",
        "average_waiting_time_s_mean",
        "average_queue_length_mean",
        "throughput_mean",
    ]
    fig, axes = plt.subplots(2, 2, figsize=(11, 8), constrained_layout=True)
    colors = ["#4C78A8", "#F58518"]
    for axis, label, key in zip(axes.flat, labels, keys):
        values = [float(row[key]) for row in aggregate_rows]
        errors = [float(row[key.replace("_mean", "_std")]) for row in aggregate_rows]
        axis.bar(methods, values, yerr=errors, capsize=4, color=colors[: len(methods)])
        axis.set_title(label)
        axis.set_ylim(0, max(value + error for value, error in zip(values, errors)) * 1.18)
        axis.tick_params(axis="x", labelsize=9)
        axis.grid(axis="y", alpha=0.25)
        for index, value in enumerate(values):
            axis.text(index, value + max(values) * 0.025, f"{value:.2f}", ha="center", va="bottom", fontsize=9)
    fig.suptitle("LibSignal sumo1x1 - Fixed-Time vs MaxPressure")
    fig.savefig(output, dpi=180)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    rows = collect(args.repo.resolve())
    aggregate_rows = aggregate(rows)
    args.output.mkdir(parents=True, exist_ok=True)
    write_csv(args.output / "summary.csv", rows)
    write_csv(args.output / "aggregate.csv", aggregate_rows)
    plot(aggregate_rows, args.output / "ft_vs_mp.png")
    print(f"Summarized {len(rows)} runs into {args.output.resolve()}")


if __name__ == "__main__":
    main()
