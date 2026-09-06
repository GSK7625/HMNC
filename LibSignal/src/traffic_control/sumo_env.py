"""Môi trường giao tiếp SUMO thông qua thư viện TraCI."""

import os
import sys
from pathlib import Path
from statistics import fmean


def _find_sumo_home() -> Path:
    """Tự động tìm kiếm thư mục cài đặt SUMO trên máy tính (hỗ trợ pip eclipse-sumo, portable và hệ thống)."""
    candidates = []

    # 1. Biến môi trường SUMO_HOME đã được thiết lập sẵn
    if os.environ.get("SUMO_HOME"):
        candidates.append(Path(os.environ["SUMO_HOME"]))

    # 2. Tự động nhận diện nếu đã cài đặt qua `pip install eclipse-sumo`
    try:
        import sumo
        if hasattr(sumo, "SUMO_HOME") and sumo.SUMO_HOME:
            candidates.append(Path(sumo.SUMO_HOME))
    except ImportError:
        pass

    # 3. Thư mục sumo portable nội bộ trong thư mục gốc của repository (nếu có)
    candidates.append(Path(__file__).resolve().parents[2] / "sumo")
    candidates.append(Path(__file__).resolve().parents[3] / "sumo")

    # 4. Các đường dẫn cài đặt mặc định trên Windows
    candidates.extend(
        [
            Path(r"C:\Program Files (x86)\Eclipse\Sumo"),
            Path(r"C:\Program Files\Eclipse\Sumo"),
            Path(r"C:\Sumo"),
        ]
    )

    # 5. Các đường dẫn cài đặt mặc định trên Linux / macOS
    candidates.extend(
        [
            Path("/usr/share/sumo"),
            Path("/usr/local/share/sumo"),
            Path("/opt/homebrew/opt/sumo/share/sumo"),
            Path("/usr/local/opt/sumo/share/sumo"),
        ]
    )

    for candidate in candidates:
        if (candidate / "tools" / "traci").is_dir() and (candidate / "bin").is_dir():
            os.environ["SUMO_HOME"] = str(candidate)
            tools = str(candidate / "tools")
            if tools not in sys.path:
                sys.path.insert(0, tools)
            os.environ["PATH"] = str(candidate / "bin") + os.pathsep + os.environ.get("PATH", "")
            return candidate

    raise RuntimeError(
        "Không tìm thấy SUMO trên hệ thống!\n"
        "----------------------------------------------------------------------\n"
        "Cách khắc phục đơn giản nhất (chỉ cần 1 lệnh pip):\n"
        "    pip install eclipse-sumo\n"
        "\n"
        "Hoặc cài đặt bản chính thức từ: https://eclipse.dev/sumo/ và thiết lập biến SUMO_HOME.\n"
        "----------------------------------------------------------------------"
    )


# Tìm kiếm và cấu hình SUMO_HOME trước khi import sumolib/traci
SUMO_HOME = _find_sumo_home()

import sumolib  # noqa: E402
import traci  # noqa: E402


from .core.observation import IntersectionObservation, TrafficSnapshot


class _SignalRuntime:
    """Lưu trữ trạng thái nội bộ của một cụm đèn tín hiệu giao thông."""

    def __init__(self, phase_states, phase_movements, incoming_lanes, lane_lengths=None):
        self.phase_states = phase_states  # Chuỗi ký tự biểu diễn đèn (ví dụ 'GGGrrr') cho từng pha xanh
        self.phase_movements = phase_movements  # Các luồng di chuyển tương ứng mỗi pha
        self.incoming_lanes = incoming_lanes  # Danh sách các làn đi vào ngã tư
        self.lane_lengths = lane_lengths or {}  # Chiều dài cố định của từng làn (mét)
        self.current_phase = 0  # Chỉ số pha hiện tại
        self.target_phase = 0  # Pha đích đang chuẩn bị chuyển sang (khi qua đèn vàng)
        self.green_elapsed = 0.0  # Thời gian đèn xanh đã duy trì (giây)
        self.yellow_remaining = 0.0  # Thời gian đèn vàng còn lại (giây)


def _is_green_phase(state: str) -> bool:
    """Kiểm tra xem chuỗi trạng thái đèn có phải là pha đèn xanh hay không."""
    return "y" not in state.lower() and any(char in "Gg" for char in state)


def _yellow_transition(current_state: str, target_state: str) -> str:
    """Tạo trạng thái đèn vàng chuyển tiếp giữa pha hiện tại và pha kế tiếp."""
    result = []
    for cur_char, tgt_char in zip(current_state, target_state):
        # Đèn đang xanh mà pha tới bị đỏ -> chuyển sang vàng để dọn đường
        if cur_char in "Gg" and tgt_char not in "Gg":
            result.append("y")
        else:
            # Các hướng sắp xanh sẽ giữ đỏ trong lúc dọn đường
            result.append(cur_char if cur_char not in "Gg" else "g")
    return "".join(result)


class SumoEnvironment:
    """Lớp bao bọc (Wrapper) môi trường mô phỏng SUMO qua giao thức TraCI."""

    def __init__(
        self,
        config_file: Path,
        gui: bool = False,
        seed: int = 0,
        yellow_seconds: float = 3.0,
        step_length: float = 1.0,
    ):
        self.config_file = Path(config_file).resolve()
        if not self.config_file.is_file():
            raise FileNotFoundError(f"Không tìm thấy file cấu hình: {self.config_file}")

        self.seed = seed
        self.yellow_seconds = float(yellow_seconds)
        self.step_length = float(step_length)
        self._closed = False
        self._depart_times = {}  # {mã_xe: thời_điểm_xuất_phát}
        self._completed_travel_times = []  # Danh sách thời gian di chuyển của các xe đã hoàn thành
        self._departed_ids = set()  # Tập hợp các xe đã xuất phát
        self._active_time_losses = {}  # {mã_xe: time_loss_hiện_tại}
        self._completed_time_losses = []  # Danh sách time loss của các xe đã hoàn thành

        # Lựa chọn binary SUMO có GUI hoặc chạy ngầm (CLI)
        binary = sumolib.checkBinary("sumo-gui" if gui else "sumo")
        command = [
            binary,
            "-c", str(self.config_file),
            "--seed", str(seed),
            "--step-length", str(step_length),
            "--no-warnings", "true",
            "--no-step-log", "true",
            "--duration-log.disable", "true",
        ]
        traci.start(command)
        self.connection = traci
        self.signals = self._load_signals()
        self.start_time = float(self.connection.simulation.getTime())

    def _load_signals(self):
        """Đọc và khởi tạo thông tin các cột đèn tín hiệu từ mạng lưới SUMO."""
        result = {}
        for tls_id in self.connection.trafficlight.getIDList():
            logics = self.connection.trafficlight.getAllProgramLogics(tls_id)
            current_program = self.connection.trafficlight.getProgram(tls_id)
            logic = next((item for item in logics if item.programID == current_program), logics[0])

            # Chỉ giữ lại các pha đèn xanh thực sự
            phase_states = tuple(phase.state for phase in logic.phases if _is_green_phase(phase.state))
            if not phase_states:
                continue

            controlled_links = self.connection.trafficlight.getControlledLinks(tls_id)
            all_movements = []
            incoming = set()

            for state in phase_states:
                movements = []
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

            # Tập hợp danh sách các làn và đọc chiều dài làn cố định từ SUMO
            tls_lanes = {
                lane
                for phase in all_movements
                for movement in phase
                for lane in movement
                if lane
            }
            lane_lengths = {}
            for lane in tls_lanes:
                try:
                    lane_lengths[lane] = float(self.connection.lane.getLength(lane))
                except Exception:
                    lane_lengths[lane] = 100.0

            runtime = _SignalRuntime(
                phase_states=phase_states,
                phase_movements=tuple(all_movements),
                incoming_lanes=tuple(sorted(incoming)),
                lane_lengths=lane_lengths,
            )
            # Khởi tạo đèn ở pha xanh đầu tiên
            self.connection.trafficlight.setRedYellowGreenState(tls_id, phase_states[0])
            result[tls_id] = runtime

        if not result:
            raise RuntimeError("Mạng lưới SUMO không chứa đèn tín hiệu giao thông nào có thể điều khiển.")

        # Xác định danh sách làn thoát biên (Boundary / Sink Exit Lanes theo chuẩn Varaiya 2013):
        # Các làn thoát không dẫn vào bất kỳ ngã tư có đèn nào trong mạng lưới
        all_incoming = {lane for rt in result.values() for lane in rt.incoming_lanes}
        all_outgoing = {
            m[1]
            for rt in result.values()
            for phase in rt.phase_movements
            for m in phase
            if len(m) > 1 and m[1]
        }
        self.exit_lanes = {lane for lane in all_outgoing if lane not in all_incoming}

        return result

    @property
    def intersection_ids(self):
        """Danh sách ID các ngã tư."""
        return tuple(self.signals)

    @property
    def simulation_time(self):
        """Thời gian mô phỏng hiện tại trong SUMO (giây)."""
        return float(self.connection.simulation.getTime())

    def observe(self):
        """Thu thập trạng thái quan sát của toàn bộ các ngã tư."""
        observations = {}
        for tls_id, runtime in self.signals.items():
            # Tập hợp tất cả các làn đường liên quan đến ngã tư này
            lanes = {
                lane
                for phase in runtime.phase_movements
                for movement in phase
                for lane in movement
            }
            # Đếm số lượng xe thực tế trên từng làn
            counts = {
                lane: int(self.connection.lane.getLastStepVehicleNumber(lane))
                for lane in lanes
            }
            haltings = {
                lane: int(self.connection.lane.getLastStepHaltingNumber(lane))
                for lane in lanes
            }
            waiting_times = {
                lane: float(self.connection.lane.getWaitingTime(lane))
                for lane in lanes
            }
            # Mật độ xe trên từng làn (xe / mét)
            densities = {
                lane: counts[lane] / max(1.0, runtime.lane_lengths.get(lane, 100.0))
                for lane in lanes
            }
            observations[tls_id] = IntersectionObservation(
                tls_id=tls_id,
                current_phase=runtime.current_phase,
                green_elapsed=runtime.green_elapsed,
                lane_vehicle_count=counts,
                phase_movements=runtime.phase_movements,
                lane_halting_count=haltings,
                lane_waiting_time=waiting_times,
                lane_length=runtime.lane_lengths,
                lane_density=densities,
                exit_lanes=self.exit_lanes,
            )
        return observations

    def step(self, actions):
        """Thực thi hành động chọn pha và tiến bước mô phỏng SUMO lên 1 giây."""
        for tls_id, runtime in self.signals.items():
            action = int(actions[tls_id])
            if not 0 <= action < len(runtime.phase_states):
                raise ValueError(f"Pha {action} không hợp lệ cho ngã tư {tls_id}")

            # Nếu đổi sang pha khác và không trong thời gian đèn vàng -> Bật đèn vàng chuyển tiếp
            if runtime.yellow_remaining <= 0 and action != runtime.current_phase:
                current_state = runtime.phase_states[runtime.current_phase]
                target_state = runtime.phase_states[action]
                runtime.target_phase = action
                runtime.green_elapsed = 0.0

                if self.yellow_seconds > 0:
                    yellow_state = _yellow_transition(current_state, target_state)
                    self.connection.trafficlight.setRedYellowGreenState(tls_id, yellow_state)
                    runtime.yellow_remaining = self.yellow_seconds
                else:
                    self.connection.trafficlight.setRedYellowGreenState(tls_id, target_state)
                    runtime.current_phase = action

        # Tiến mô phỏng SUMO 1 bước
        self.connection.simulationStep()
        now = self.simulation_time

        # Ghi nhận xe mới xuất phát
        for vehicle_id in self.connection.simulation.getDepartedIDList():
            self._departed_ids.add(vehicle_id)
            self._depart_times[vehicle_id] = now

        # Cập nhật time loss cho các xe đang hoạt động
        active_ids = self.connection.vehicle.getIDList()
        for vehicle_id in active_ids:
            try:
                self._active_time_losses[vehicle_id] = float(self.connection.vehicle.getTimeLoss(vehicle_id))
            except Exception:
                pass

        # Ghi nhận xe đã hoàn thành lộ trình
        for vehicle_id in self.connection.simulation.getArrivedIDList():
            departed_at = self._depart_times.pop(vehicle_id, None)
            if departed_at is not None:
                self._completed_travel_times.append(now - departed_at)
            loss = self._active_time_losses.pop(vehicle_id, 0.0)
            self._completed_time_losses.append(loss)

        # Cập nhật bộ đếm thời gian cho từng cụm đèn
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

    def snapshot(self):
        """Chụp nhanh các thống kê hiệu năng giao thông hiện tại."""
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
        now = self.simulation_time

        # Tính toán Penalized Travel Time (tính cả xe chưa về đích để triệt tiêu survival bias)
        all_travel_times = list(self._completed_travel_times)
        for dep_time in self._depart_times.values():
            all_travel_times.append(now - dep_time)
        penalized_tt = fmean(all_travel_times) if all_travel_times else 0.0

        # Tổng thời gian mất mát (Total Time Loss) và độ trễ trung bình (Average Delay)
        total_time_loss = sum(self._completed_time_losses) + sum(self._active_time_losses.values())
        avg_delay = (total_time_loss / len(self._departed_ids)) if self._departed_ids else 0.0

        return TrafficSnapshot(
            simulation_time=now,
            average_queue=fmean(queue_by_intersection) if queue_by_intersection else 0.0,
            average_current_waiting=fmean(current_waiting) if current_waiting else 0.0,
            throughput=len(self._completed_travel_times),
            departed=len(self._departed_ids),
            average_completed_travel_time=(
                fmean(self._completed_travel_times)
                if self._completed_travel_times
                else 0.0
            ),
            penalized_travel_time=penalized_tt,
            average_delay=avg_delay,
            total_time_loss=total_time_loss,
        )

    def has_vehicles_expected(self) -> bool:
        """Kiểm tra còn xe trong mô phỏng hoặc đang chờ xuất phát hay không."""
        return self.connection.simulation.getMinExpectedNumber() > 0

    def close(self):
        """Đóng kết nối TraCI với SUMO an toàn."""
        if not self._closed:
            try:
                self.connection.close()
            except Exception:
                pass
            finally:
                self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()

