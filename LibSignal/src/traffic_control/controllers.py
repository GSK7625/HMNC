"""Traffic-signal controllers implemented by the project team.

Only two classical controllers are intentionally included in phase 1:

* Fixed-Time: cycle through green phases after a fixed green duration.
* Max-Pressure: choose the phase with the largest incoming-minus-outgoing
  vehicle pressure after respecting a minimum green duration.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class ObservationLike(Protocol):
    current_phase: int
    green_elapsed: float
    lane_vehicle_count: dict[str, int]
    phase_movements: tuple[tuple[tuple[str, str], ...], ...]


class Controller(Protocol):
    name: str

    def select_phase(self, observation: ObservationLike) -> int: ...

    def phase_pressures(self, observation: ObservationLike) -> list[float]: ...


def calculate_phase_pressures(observation: ObservationLike) -> list[float]:
    """Return P(p) = sum(N_in - N_out) for every valid green phase."""
    counts = observation.lane_vehicle_count
    return [
        float(
            sum(
                counts.get(in_lane, 0) - counts.get(out_lane, 0)
                for in_lane, out_lane in movements
            )
        )
        for movements in observation.phase_movements
    ]


@dataclass(frozen=True)
class FixedTimeController:
    """Cycle through phases after a fixed amount of effective green time."""

    green_seconds: float = 30.0
    name: str = "fixedtime"

    def __post_init__(self) -> None:
        if self.green_seconds <= 0:
            raise ValueError("green_seconds must be positive")

    def select_phase(self, observation: ObservationLike) -> int:
        if observation.green_elapsed < self.green_seconds:
            return observation.current_phase
        phase_count = len(observation.phase_movements)
        return (observation.current_phase + 1) % phase_count

    def phase_pressures(self, observation: ObservationLike) -> list[float]:
        # Recorded only to demonstrate that FT does not use pressure to decide.
        return calculate_phase_pressures(observation)


@dataclass(frozen=True)
class MaxPressureController:
    """Select the phase with maximum local lane pressure."""

    minimum_green_seconds: float = 10.0
    name: str = "maxpressure"

    def __post_init__(self) -> None:
        if self.minimum_green_seconds < 0:
            raise ValueError("minimum_green_seconds must be non-negative")

    def select_phase(self, observation: ObservationLike) -> int:
        if observation.green_elapsed < self.minimum_green_seconds:
            return observation.current_phase
        pressures = self.phase_pressures(observation)
        # max() keeps the first phase on ties, making decisions deterministic.
        return max(range(len(pressures)), key=pressures.__getitem__)

    def phase_pressures(self, observation: ObservationLike) -> list[float]:
        return calculate_phase_pressures(observation)
