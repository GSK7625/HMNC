"""Experiment loop and CSV/JSON result export."""

from __future__ import annotations

import csv
import json
import time
from pathlib import Path
from statistics import fmean

from .controllers import Controller
from .sumo_env import SumoEnvironment


def run_experiment(
    *,
    controller: Controller,
    sumo_config: Path,
    steps: int,
    action_interval: int,
    seed: int,
    gui: bool,
    yellow_seconds: float,
    step_delay: float,
    output_dir: Path,
) -> dict[str, object]:
    if steps <= 0 or action_interval <= 0:
        raise ValueError("steps and action_interval must be positive")

    agent_dir = output_dir / controller.name
    agent_dir.mkdir(parents=True, exist_ok=True)
    trace: list[dict[str, object]] = []
    phase_switches = 0
    previous_actions: dict[str, int] | None = None
    started = time.perf_counter()

    with SumoEnvironment(
        sumo_config,
        gui=gui,
        seed=seed,
        yellow_seconds=yellow_seconds,
    ) as environment:
        elapsed = 0
        decision = 0
        while elapsed < steps and environment.has_vehicles_expected():
            observations = environment.observe()
            actions = {
                tls_id: controller.select_phase(observation)
                for tls_id, observation in observations.items()
            }
            pressures = {
                tls_id: controller.phase_pressures(observation)
                for tls_id, observation in observations.items()
            }
            green_elapsed = {
                tls_id: observation.green_elapsed
                for tls_id, observation in observations.items()
            }
            if previous_actions is not None:
                phase_switches += sum(
                    action != previous_actions[tls_id]
                    for tls_id, action in actions.items()
                )
            previous_actions = actions.copy()

            interval = min(action_interval, steps - elapsed)
            for _ in range(interval):
                environment.step(actions)
                elapsed += 1
                if gui and step_delay:
                    time.sleep(step_delay)
                if not environment.has_vehicles_expected():
                    break

            snapshot = environment.snapshot()
            trace.append(
                {
                    "decision": decision,
                    "elapsed_s": elapsed,
                    "simulation_time_s": snapshot.simulation_time,
                    "actions": json.dumps(actions, sort_keys=True),
                    "green_elapsed_before_action_s": json.dumps(
                        green_elapsed, sort_keys=True
                    ),
                    "phase_pressures": json.dumps(pressures, sort_keys=True),
                    "average_queue_vehicles": snapshot.average_queue,
                    "average_current_waiting_s": snapshot.average_current_waiting,
                    "throughput": snapshot.throughput,
                    "average_completed_travel_time_s": (
                        snapshot.average_completed_travel_time
                    ),
                }
            )
            decision += 1

        final_snapshot = environment.snapshot()

    summary: dict[str, object] = {
        "controller": controller.name,
        "sumo_config": str(sumo_config.resolve()),
        "seed": seed,
        "simulated_seconds": elapsed,
        "action_interval_s": action_interval,
        "yellow_seconds": yellow_seconds,
        "decisions": len(trace),
        "departed_vehicles": final_snapshot.departed,
        "throughput": final_snapshot.throughput,
        "completion_rate": (
            final_snapshot.throughput / final_snapshot.departed
            if final_snapshot.departed
            else 0.0
        ),
        "average_travel_time_s": final_snapshot.average_completed_travel_time,
        "average_queue_vehicles": fmean(
            float(row["average_queue_vehicles"]) for row in trace
        ),
        "average_current_waiting_s": fmean(
            float(row["average_current_waiting_s"]) for row in trace
        ),
        "phase_switches": phase_switches,
        "wall_clock_s": time.perf_counter() - started,
    }

    with (agent_dir / "decision_trace.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(trace[0]))
        writer.writeheader()
        writer.writerows(trace)
    (agent_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return summary


def write_comparison(output_dir: Path, summaries: list[dict[str, object]]) -> None:
    with (output_dir / "comparison.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)
