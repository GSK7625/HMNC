# SUMO Traffic Signal Control - Phase 1

Project tối giản để nhóm tự cài đặt và giải thích hai thuật toán điều khiển đèn
giao thông cơ bản:

- Fixed-Time (FT);
- Max-Pressure (MP).

Repository chỉ dùng SUMO/TraCI và các map SUMO có sẵn. Toàn bộ agent, trainer,
Gym, PyTorch, CityFlow và thuật toán RL của LibSignal đã được loại bỏ để nhóm có
thể đọc và làm chủ toàn bộ code.

## Cấu trúc

```text
run.py                         CLI chạy thí nghiệm
src/traffic_control/
  controllers.py              FT và MP do nhóm tự code
  sumo_env.py                  môi trường SUMO/TraCI + xử lý pha vàng
  experiment.py               vòng lặp mô phỏng + metric + xuất kết quả
data/raw_data/                 các map/dataset có file .sumocfg
tests/test_controllers.py      unit test công thức FT/MP
docs/                          lý thuyết và kịch bản trình bày
```

## Yêu cầu

- Python 3.10-3.12;
- Eclipse SUMO;
- biến môi trường `SUMO_HOME` trỏ tới thư mục SUMO.

Không có thư viện pip bắt buộc. `traci` và `sumolib` được lấy trực tiếp từ
`%SUMO_HOME%/tools`.

Kiểm tra môi trường:

```powershell
.\setup.ps1
```

## Chạy demo

Benchmark cả FT và MP trên Cologne 1x1 trong 900 giây:

```powershell
.\run_demo.ps1 -Controller all -Steps 900
```

Mở SUMO-GUI để xem MP:

```powershell
.\run_demo.ps1 -Controller maxpressure -Steps 300 -Gui -StepDelay 0.03
```

Mở SUMO-GUI để xem FT:

```powershell
.\run_demo.ps1 -Controller fixedtime -Steps 300 -Gui -StepDelay 0.03
```

Thay map SUMO khác:

```powershell
.\run_demo.ps1 -Controller all -Steps 900 `
  -Scenario "data\raw_data\cologne3\cologne3.sumocfg"
```

## Thuật toán nằm ở đâu?

Chỉ cần đọc [`src/traffic_control/controllers.py`](src/traffic_control/controllers.py):

- FT giữ pha hiện tại cho đến khi đủ `green_seconds`, sau đó chuyển tuần hoàn;
- MP tính `P(p) = sum(N_in - N_out)` cho từng pha và chọn pha có pressure lớn
  nhất sau thời gian xanh tối thiểu.

Môi trường không quyết định thuật toán. Nó chỉ đọc map SUMO, lấy lane count,
nhận phase mà controller chọn, xử lý 5 giây đèn vàng và gọi
`traci.simulationStep()`.

## Kết quả

Mỗi lần chạy tạo:

```text
results/<timestamp>/comparison.csv
results/<timestamp>/fixedtime/summary.json
results/<timestamp>/fixedtime/decision_trace.csv
results/<timestamp>/maxpressure/summary.json
results/<timestamp>/maxpressure/decision_trace.csv
```

`decision_trace.csv` lưu action, thời gian xanh và pressure từng pha nên có thể
dùng để giải thích trực tiếp với giảng viên.

## Kiểm thử

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_controllers -v
```

## Tài liệu

- [Lý thuyết và cách đọc code](docs/LY_THUYET_FT_MP.md)
- [Kịch bản demo với giảng viên](docs/KICH_BAN_DEMO.md)

Project được rút gọn từ dữ liệu/map của
[DaRL-LibSignal/LibSignal](https://github.com/DaRL-LibSignal/LibSignal), nhưng
controller và vòng lặp SUMO trong repository hiện tại là phần nhóm tự cài đặt.
