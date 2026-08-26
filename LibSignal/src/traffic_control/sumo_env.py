"""Small SUMO/TraCI environment owned by this project.

The module reads green phases and controlled lane movements directly from an
existing SUMO network.  It deliberately avoids LibSignal's World, Registry,
Agent, Gym and training abstractions.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from statistics import fmean
from typing import Mapping


def _find_sumo_home() -> Path:
    candidates: list[Path] = []
    if os.environ.get("SUMO_HOME"):
        candidates.append(Path(os.environ["SUMO_HOME"]))
    candidates.extend(
        [
            Path(r"C:\Program Files (x86)\Eclipse\Sumo"),
            Path(r"C:\Program Files\Eclipse\Sumo"),
        ]
    )
    for candidate in candidates:
        if (candidate / "tools" / "traci").is_dir() and (candidate / "bin").is_dir():
            os.environ["SUMO_HOME"] = str(candidate)
            tools = str(candidate / "tools")
            if tools not in sys.path:
                sys.path.append(tools)
            os.environ["PATH"] = str(candidate / "bin") + os.pathsep + os.environ.get(
                "PATH", ""
            )
            return candidate
    raise RuntimeError("Không tìm thấy SUMO. Hãy cài SUMO và đặt SUMO_HOME.")


SUMO_HOME = _find_sumo_home()

import sumolib  # noqa: E402
import traci  # noqa: E402


@dataclass(frozen=True)
class IntersectionObservation:
    tls_id: str
    current_phase: int
    green_elapsed: float
    lane_vehicle_count: dict[str, int]
    phase_movements: tuple[tuple[tuple[str, str], ...], ...]


@dataclass(frozen=True)
class TrafficSnapshot:
    simulation_time: float
    average_queue: float
    average_current_waiting: float
    throughput: int
    departed: int
    average_completed_travel_time: float


@dataclass
class _SignalRuntime:
    phase_states: tuple[str, ...]
    phase_movements: tuple[tuple[tuple[str, str], ...], ...]
    incoming_lanes: tuple[str, ...]
    current_phase: int = 0
    target_phase: int = 0
    green_elapsed: float = 0.0
    yellow_remaining: float = 0.0


def _is_green_phase(state: str) -> bool:
    return "y" not in state.lower() and any(char in "Gg" for char in state)


def _yellow_transition(current: str, target: str) -> str:
    chars: list[str] = []
    for current_char, target_char in zip(current, target):
        if current_char in "Gg" and target_char not in "Gg":
            chars.append("y")
        else:
            # Movements that will become green stay red during clearance.
            chars.append(current_char if current_char not in "Gg" else "g")
    return "".join(chars)


class SumoEnvironment:
    """TraCI wrapper for external traffic-light control."""

    def __init__(
        self,
        config_file: Path,
        *,
        gui: bool = False,
        seed: int = 0,
        yellow_seconds: float = 5.0,
        step_length: float = 1.0,
    ) -> None:
        self.config_file = config_file.resolve()
        if not self.config_file.is_file():
            raise FileNotFoundError(self.config_file)
        if yellow_seconds < 0 or step_length <= 0:
            raise ValueError("Invalid yellow_seconds or step_length")
        self.seed = seed
        self.yellow_seconds = yellow_seconds
        self.step_length = step_length
        self._closed = False
        self._depart_times: dict[str, float] = {}
        self._completed_travel_times: list[float] = []
        self._departed_ids: set[str] = set()

        binary = sumolib.checkBinary("sumo-gui" if gui else "sumo")
        command = [
            binary,
            "-c",
            str(self.config_file),
            "--seed",
            str(seed),
            "--step-length",
            str(step_length),
            "--no-warnings",
            "true",
            "--no-step-log",
            "true",
            "--duration-log.disable",
            "true",
        ]
        traci.start(command)
        self.connection = traci
        self.signals = self._load_signals()
        self.start_time = float(self.connection.simulation.getTime())

    def _load_signals(self) -> dict[str, _SignalRuntime]:
        result: dict[str, _SignalRuntime] = {}
        for tls_id in self.connection.trafficlight.getIDList():
            logics = self.connection.trafficlight.getAllProgramLogics(tls_id)
            current_program = self.connection.trafficlight.getProgram(tls_id)
            logic = next(
                (item for item in logics if item.programID == current_program), logics[0]
            )
            phase_states = tuple(
                phase.state for phase in logic.phases if _is_green_phase(phase.state)
            )
            if not phase_states:
                continue

            controlled_links = self.connection.trafficlight.getControlledLinks(tls_id)
            all_movements: list[tuple[tuple[str, str], ...]] = []
            incoming: set[str] = set()
            for state in phase_states:
                movements: list[tuple[str, str]] = []
                for index, signal_char in enumerate(state):
                    if signal_char not in "Gg" or index >= len(controlled_links):
                        continue
                    for link in controlled_links[index]:
                        in_lane, out_lane = link[0], link[1]
                        movement = (in_lane, out_lane)
                        if movement not in movements:
                            movements.append(movement)
                        incoming.add(in_lane)
                all_movements.append(tuple(movements))

            runtime = _SignalRuntime(
                phase_states=phase_states,
                phase_movements=tuple(all_movements),
                incoming_lanes=tuple(sorted(incoming)),
            )
            self.connection.trafficlight.setRedYellowGreenState(tls_id, phase_states[0])
            result[tls_id] = runtime

        if not result:
            raise RuntimeError("SUMO network không có traffic light điều khiển được.")
        return result

    @property
    def intersection_ids(self) -> tuple[str, ...]:
        return tuple(self.signals)

    @property
    def simulation_time(self) -> float:
        return float(self.connection.simulation.getTime())

    def observe(self) -> dict[str, IntersectionObservation]:
        observations: dict[str, IntersectionObservation] = {}
        for tls_id, runtime in self.signals.items():
            lanes = {
                lane
                for phase in runtime.phase_movements
                for movement in phase
                for lane in movement
            }
            counts = {
                lane: int(self.connection.lane.getLastStepVehicleNumber(lane))
                for lane in lanes
            }
            observations[tls_id] = IntersectionObservation(
                tls_id=tls_id,
                current_phase=runtime.current_phase,
                green_elapsed=runtime.green_elapsed,
                lane_vehicle_count=counts,
                phase_movements=runtime.phase_movements,
            )
        return observations

    def step(self, actions: Mapping[str, int]) -> None:
        for tls_id, runtime in self.signals.items():
            action = int(actions[tls_id])
            if not 0 <= action < len(runtime.phase_states):
                raise ValueError(f"Invalid phase {action} for {tls_id}")
            if runtime.yellow_remaining <= 0 and action != runtime.current_phase:
                current_state = runtime.phase_states[runtime.current_phase]
                target_state = runtime.phase_states[action]
                runtime.target_phase = action
                runtime.green_elapsed = 0.0
                if self.yellow_seconds > 0:
                    yellow_state = _yellow_transition(current_state, target_state)
                    self.connection.trafficlight.setRedYellowGreenState(
                        tls_id, yellow_state
                    )
                    runtime.yellow_remaining = self.yellow_seconds
                else:
                    self.connection.trafficlight.setRedYellowGreenState(
                        tls_id, target_state
                    )
                    runtime.current_phase = action

        self.connection.simulationStep()
        now = self.simulation_time
        for vehicle_id in self.connection.simulation.getDepartedIDList():
            self._departed_ids.add(vehicle_id)
            self._depart_times[vehicle_id] = now
        for vehicle_id in self.connection.simulation.getArrivedIDList():
            departed_at = self._depart_times.pop(vehicle_id, None)
            if departed_at is not None:
                self._completed_travel_times.append(now - departed_at)

        for tls_id, runtime in self.signals.items():
            if runtime.yellow_remaining > 0:
                runtime.yellow_remaining -= self.step_length
                if runtime.yellow_remaining <= 0:
                    runtime.current_phase = runtime.target_phase
                    runtime.green_elapsed = 0.0
                    self.connection.trafficlight.setRedYellowGreenState(
                        tls_id, runtime.phase_states[runtime.current_phase]
                    )
            else:
                runtime.green_elapsed += self.step_length

    def snapshot(self) -> TrafficSnapshot:
        queue_by_intersection = [
            sum(
                self.connection.lane.getLastStepHaltingNumber(lane)
                for lane in runtime.incoming_lanes
            )
            for runtime in self.signals.values()
        ]
        active = self.connection.vehicle.getIDList()
        current_waiting = [
            self.connection.vehicle.getAccumulatedWaitingTime(vehicle_id)
            for vehicle_id in active
        ]
        return TrafficSnapshot(
            simulation_time=self.simulation_time,
            average_queue=fmean(queue_by_intersection) if queue_by_intersection else 0.0,
            average_current_waiting=fmean(current_waiting) if current_waiting else 0.0,
            throughput=len(self._completed_travel_times),
            departed=len(self._departed_ids),
            average_completed_travel_time=(
                fmean(self._completed_travel_times)
                if self._completed_travel_times
                else 0.0
            ),
        )

    def has_vehicles_expected(self) -> bool:
        return self.connection.simulation.getMinExpectedNumber() > 0

    def close(self) -> None:
        if not self._closed:
            self.connection.close()
            self._closed = True

    def __enter__(self) -> "SumoEnvironment":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()
