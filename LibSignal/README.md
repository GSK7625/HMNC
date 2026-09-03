# 🚦 SUMO Traffic Signal Control Framework

Hệ thống mô phỏng, huấn luyện và kiểm chuẩn khoa học (Scientific Benchmark) các thuật toán điều khiển đèn tín hiệu giao thông thông minh trên nền tảng **Eclipse SUMO** & **TraCI**.

Dự án được xây dựng tinh gọn, trực quan, hỗ trợ đầy đủ giao diện đồ họa (GUI Dashboard) và dòng lệnh (CLI), tuân thủ chặt chẽ phương pháp luận kiểm chuẩn quốc tế theo chuẩn **RESCO** (Reinforcement Learning Benchmarks for Traffic Signal Control).

---

## 📌 Các thuật toán điều khiển cốt lõi

1. **Fixed-Time (FT)**:
   - Điều khiển đèn theo chu kỳ thời gian cố định.
   - Tự động phân bổ thời lượng đèn xanh đều nhau hoặc chia theo tỉ lệ số làn xe lưu thông (xấp xỉ công thức Webster / chuẩn RESCO).
2. **Max-Pressure (MP)**:
   - Thuật toán thích nghi kinh điển dựa trên lý thuyết điều khiển luồng (Varaiya, 2013).
   - Tối ưu hóa áp lực mạng lưới $P(p) = \sum(N_{in} - N_{out})$, tích hợp cơ chế chống bỏ đói pha (**Starvation Guard**) và chống nhảy đèn lãng phí khi vắng xe (**Idle Protection**).
3. **Tabular Q-Learning (QL)**:
   - Thuật toán học tăng cường phi tập trung (Decentralized Independent Q-Learning - IDQL).
   - Rời rạc hóa trạng thái hàng đợi dừng, tối ưu hàm phần thưởng theo độ dài hàng đợi/độ trễ và tích hợp hệ số phạt chuyển pha đèn liên tục (**Switch Penalty**).
4. **Kiến trúc Plug-and-Play**:
   - Hệ thống **Controller Registry** cho phép thêm bất kỳ thuật toán mới nào chỉ bằng decorator `@register_controller` mà không cần chỉnh sửa code cũ.

---

## 📂 Cấu trúc dự án

```text
LibSignal/
├── run.py                         # Điểm khởi chạy CLI (Benchmark đơn/đa seed, huấn luyện QL)
├── gui.py                         # Giao diện đồ họa Dashboard (Sleepy Chicken Theme)
├── launch_gui.bat                 # Khởi chạy GUI 1-click tiện lợi trên Windows
├── setup.ps1                      # Tự động khởi tạo venv và kiểm tra môi trường SUMO
├── requirements.txt               # Gói phụ thuộc chính (eclipse-sumo)
├── assets/
│   └── chicken_avatar.png         # Tài nguyên mascot cho giao diện GUI
├── checkpoints/
│   └── q_table.json               # Trọng số mô hình Q-Learning đã hội tụ
├── src/traffic_control/
│   ├── core/                      # Module nền tảng chuẩn hóa
│   │   ├── config.py              # BenchmarkConfig (chuẩn hóa tham số môi trường & G_min)
│   │   ├── metrics.py             # EvaluationMetrics & MetricsCollector (chỉ số khoa học)
│   │   └── observation.py         # IntersectionObservation & TrafficSnapshot
│   ├── controllers/               # Các bộ điều khiển đèn giao thông
│   │   ├── registry.py            # Controller Registry & cơ chế Auto-discovery
│   │   ├── base.py                # BaseController, Safety Guard & tính áp lực xe P(p)
│   │   ├── fixed_time.py          # Bộ điều khiển Fixed-Time
│   │   ├── max_pressure.py        # Bộ điều khiển Max-Pressure
│   │   └── q_learning.py          # Bộ điều khiển Q-Learning
│   ├── sumo_env.py                # Môi trường SUMO/TraCI + tự động phát hiện SUMO_HOME
│   └── experiment.py              # Vòng lặp mô phỏng chuẩn hóa & xuất kết quả CSV/JSON
├── data/
│   └── raw_data/                  # 11 kịch bản mạng lưới giao thông thực tế (.sumocfg)
├── tests/                         # Toàn bộ 30 unit tests kiểm định chất lượng mã nguồn
└── docs/                          # Tài liệu lý thuyết, báo cáo RESCO và hướng dẫn mở rộng
```

---

## 🗺️ Danh sách kịch bản bản đồ có sẵn (`data/raw_data/`)

Toàn bộ các mạng lưới giao thông dưới đây đã được tích hợp đầy đủ file cấu hình `.sumocfg`, lưới đường `.net.xml` và luồng xe `.rou.xml`:

| Tên kịch bản | Thư mục | Số ngã tư | Đặc điểm giao thông |
| :--- | :--- | :---: | :--- |
| **Cologne 1 (Mặc định)** | `cologne1/` | 1 | Mạng lưới đô thị Cologne (Đức), chuẩn cho đánh giá cơ bản |
| **Cologne 3** | `cologne3/` | 1 | Kịch bản mở rộng với cấu hình làn rẽ phức tạp |
| **Ingolstadt 21** | `ingolstadt21/` | 1 | Bản đồ thực tế thành phố Ingolstadt |
| **Manhattan (28x7)** | `manhattan_28x7/` | Đa ngã tư | Bản đồ lưới bàn cờ quy mô lớn Manhattan |
| **Atlanta (1x5)** | `atlanta_1x5/` | Tuyến hành lang | Tuyến đường trục 5 nút giao liên tiếp |
| **Hangzhou (1x1)** | `hangzhou_1x1_*/` | 1 | Dữ liệu lưu lượng thực tế tại Hàng Châu (4 khung giờ khác nhau) |
| **Hangzhou (4x4)** | `hangzhou_4x4_*/` | 16 | Lưới 16 ngã tư đồng nhất và không đồng nhất (hetero) |

---

## 🚀 Cài đặt & Chuẩn bị môi trường

### Yêu cầu hệ thống
- Python 3.10 - 3.12.
- Hệ điều hành: Windows, macOS hoặc Linux.

### Cách 1: Cài đặt siêu tốc qua pip (Khuyên dùng - Không cần cài MSI)
Mở terminal tại thư mục `LibSignal` và chạy:
```powershell
pip install -r requirements.txt
```
> [!TIP]
> Gói `eclipse-sumo` trên PyPI đã bao gồm sẵn toàn bộ file thực thi `sumo.exe`, `sumo-gui.exe`, thư viện `traci` và `sumolib`. Bạn có thể chạy ngay mà không cần quyền Administrator hay chỉnh sửa biến môi trường hệ thống.

### Cách 2: Kiểm tra tự động bằng PowerShell
Chạy script để kiểm tra môi trường hoặc tự động tạo virtualenv:
```powershell
.\setup.ps1
```

---

## 🖥️ Giao diện đồ họa trực quan (GUI Dashboard)

Dự án cung cấp giao diện đồ họa **Sleepy Chicken Dashboard** thân thiện, trực quan:

* **Khởi chạy nhanh trên Windows**: Nhấp đúp chuột vào file [`launch_gui.bat`](launch_gui.bat).
* **Khởi chạy bằng lệnh**:
  ```powershell
  python gui.py
  ```

### Tính năng trên giao diện:
1. **Lựa chọn kịch bản**: Tự động nhận diện toàn bộ các bản đồ trong `data/raw_data/` hoặc chọn file `.sumocfg` bên ngoài.
2. **Chọn chế độ chạy**:
   - Chạy so sánh (Benchmark) tất cả hoặc nhóm thuật toán tùy chọn.
   - Chạy đơn lẻ từng thuật toán để quan sát chi tiết.
   - Huấn luyện Q-Learning (Training Mode) với số episode tùy ý.
3. **Mô phỏng trực quan**: Bật/tắt cửa sổ SUMO-GUI và thanh trượt điều chỉnh tốc độ mô phỏng.
4. **Console Log thời gian thực**: Theo dõi tiến trình mô phỏng, độ trễ và thông lượng tức thì.
5. **Bảng thành tích & Xuất dữ liệu**: Xem bảng so sánh số liệu, mở file CSV hoặc thư mục kết quả chỉ với 1 click.

---

## 💻 Chạy thử nghiệm bằng dòng lệnh (CLI)

### 1. Benchmark so sánh mặc định (FT vs MP vs QL)
Chạy so sánh cả 3 thuật toán trên bản đồ mặc định Cologne 1 trong 900 giây:
```powershell
python run.py
```

### 2. Kiểm chuẩn đa hạt giống khoa học (Multi-Seed Benchmark theo chuẩn RESCO)
Chạy kiểm chuẩn trên 3 hạt giống ngẫu nhiên (`seed=0,1,2`) để tính toán **Mean ± Std** khách quan:
```powershell
python run.py --seeds 0,1,2
```

### 3. Huấn luyện Q-Learning sâu qua nhiều episode
Huấn luyện Q-Learning 50 episodes với cơ chế Epsilon Decay để hội tụ bảng Q:
```powershell
python run.py -c ql --train --episodes 50
```

### 4. Mở giao diện trực quan SUMO-GUI
Xem trực quan chuyển động xe và đèn tín hiệu trên SUMO-GUI:
```powershell
# Xem Max-Pressure điều khiển
python run.py -c mp -g

# Xem Fixed-Time điều khiển
python run.py -c ft -g

# Xem Q-Learning điều khiển
python run.py -c ql -g
```

### 5. Chạy trên bản đồ khác
```powershell
python run.py -m "data\raw_data\cologne3\cologne3.sumocfg"
```

---

## 📊 Bộ chỉ số đánh giá chuẩn hóa (Standardized Metrics)

| Chỉ số | Đơn vị | Ý nghĩa khoa học |
| :--- | :---: | :--- |
| **Penalized Travel Time** | giây | Thời gian di chuyển có tính phạt cho xe còn kẹt lại (chống hiện tượng *Survival Bias*) |
| **Average Travel Time** | giây | Thời gian di chuyển trung bình của các xe đã về đích thành công |
| **Average Delay** | giây | Độ trễ trung bình của xe so với thời gian di chuyển trong điều kiện lý tưởng |
| **Total Time Loss** | giây | Tổng thời gian lãng phí/chậm trễ tích lũy của toàn bộ xe trong mạng |
| **Average Queue** | xe | Số lượng xe dừng chờ trung bình trên mỗi ngã tư |
| **Throughput** | xe | Tổng số xe đã hoàn thành toàn bộ lộ trình |
| **Completion Rate** | % | Tỷ lệ hoàn thành lộ trình ($\text{Throughput} / \text{Departed}$) |
| **Phase Switches** | lần | Tổng số lần chuyển pha đèn (đo lường độ ổn định và chi phí chuyển đổi) |

---

## 🧪 Kiểm định chất lượng mã nguồn (Unit Tests)

Bộ test suite bao gồm **30 unit tests** kiểm tra toàn diện:
- Logic chuyển pha của Fixed-Time, Max-Pressure và Q-Learning.
- Cơ chế an toàn **Safety Guard** ($G_{min} \ge 10s$).
- Công thức tính áp lực $P(p)$ khử trùng lặp làn (Lane Deduplication).
- Cập nhật Bellman, Epsilon Decay và tính độc lập đa ngã tư của Q-Learning.
- Cơ chế đăng ký và Auto-discovery của Controller Registry.

Chạy toàn bộ tests:
```powershell
python -m unittest discover tests -v
```

---

## 📚 Tài liệu tham khảo chuyên sâu

- 📖 [Lý thuyết chi tiết Fixed-Time & Max-Pressure](docs/LY_THUYET_FT_MP.md)
- 📋 [Kịch bản Demo thuyết trình 5-7 phút](docs/KICH_BAN_DEMO.md)
- 🔌 [Hướng dẫn 3 bước thêm thuật toán mới](docs/HUONG_DAN_THEM_THUAT_TOAN.md)
- 📑 [Báo cáo đối sánh phương pháp luận theo chuẩn RESCO](docs/BAO_CAO_SO_SANH_RESCO.md)
