# 🚦 SUMO Traffic Signal Control Benchmark Framework

Hệ thống mô phỏng, huấn luyện và kiểm chuẩn khoa học (Scientific Benchmark) các thuật toán điều khiển đèn tín hiệu giao thông thông minh trên nền tảng **Eclipse SUMO** & **TraCI**.

Dự án được thiết kế theo tiêu chuẩn công nghiệp và học thuật, hỗ trợ cả **Giao diện đồ họa (Sleepy Chicken GUI Dashboard)** lẫn **Giao diện dòng lệnh (CLI)**, tuân thủ chặt chẽ phương pháp luận kiểm chuẩn quốc tế theo chuẩn **RESCO** (*NeurIPS 2021 Benchmark Suite*).

---

## 🌟 Tính năng nổi bật

- 🧩 **Kiến trúc Plug-and-Play (Open-Closed Principle)**: Mở rộng thuật toán mới dễ dàng thông qua `@register_controller` và Controller Registry tự động nhận diện mà không cần chỉnh sửa code lõi.
- 📐 **Tuân thủ quy chuẩn quốc tế RESCO**:
  - Khử triệt để hiện tượng **Survival Bias** nhờ chỉ số **Penalized Travel Time** (tính phạt đối với xe còn mắc kẹt trong mạng lưới).
  - Tích hợp cơ chế an toàn **Safety Guard**: Thời gian xanh tối thiểu $G_{min} = 10.0\text{s}$, thời gian đèn vàng $Y = 3.0\text{s}$, chu kỳ ra quyết định $\Delta t = 10.0\text{s}$.
- 🧠 **Đa dạng trường phái điều khiển**:
  - Heuristic cổ điển: **Fixed-Time** (tối ưu chu kỳ Webster $C_0$ và phân bổ Green Splits).
  - Heuristic thích nghi luồng: **Max-Pressure** (Varaiya 2013, Starvation Guard, Idle Protection, khử trùng lặp làn).
  - Học tăng cường dạng bảng: **Tabular Q-Learning** (Decentralized IDQL, State Discretization, Switch Penalty, Transfer Priors).
  - Học tăng cường sâu: **Deep Q-Network** (Double IDQN, PyTorch MLP, Experience Replay Buffer, Target Network, Continuous State Vector).
- 📊 **Mô-đun trực quan hóa khoa học tự động (`visualization.py`)**: Tự động sinh biểu đồ thanh sai số đa hạt giống ($\text{Mean} \pm \text{Std}$), chuỗi thời gian diễn biến hàng đợi/độ trễ, đường cong hội tụ RL (Loss & Reward) với độ phân giải cao 300 DPI.
- 🗺️ **11 Kịch bản giao thông thực tế**: Tích hợp sẵn từ ngã tư đơn (Cologne, Hangzhou, Ingolstadt) đến mạng lưới hành lang (Atlanta 1x5) và bàn cờ quy mô lớn (Manhattan 28x7, Hangzhou 4x4).
- 🧪 **Kiểm định chất lượng nghiêm ngặt**: Đạt **64/64 Unit Tests** tự động, bao phủ toàn bộ logic điều khiển, chuyển pha, cập nhật Bellman, Replay Buffer và trực quan hóa.

---

## 📌 Các thuật toán điều khiển cốt lõi

### 1. Fixed-Time (FT)
- **Nguyên lý**: Điều khiển đèn theo chu kỳ thời gian cố định.
- **Tính toán chu kỳ tối ưu Webster (1958)**:
  $$C_0 = \frac{1.5L + 5}{1 - Y}$$
  Trong đó $L$ là tổng thời gian tổn thất qua các pha vàng ($L = \sum Y_i$), $Y = \sum y_i$ là tổng tỷ số lưu lượng tới hạn trên các pha.
- **Phân bổ thời gian xanh (Green Splits Equisaturation)**:
  $$g_i = (C_0 - L) \times \frac{y_i}{Y}$$
- **Cơ chế fallback**: Tự động chia đều thời gian xanh nếu không kích hoạt tính toán tỷ lệ.

### 2. Max-Pressure (MP)
- **Nguyên lý** (Varaiya, 2013): Tối ưu hóa phân tán bằng cách chọn pha đèn có áp lực ròng lớn nhất:
  $$P(p) = \sum_{l \in In(p)} x_l - \sum_{m \in Out(p)} x_m$$
  với $x_l$ là số xe trên nhánh vào và $x_m$ là số xe trên nhánh thoát.
- **4 Chế độ tính áp lực (`--pressure-mode`)**:
  - `halting` *(mặc định theo RESCO & Varaiya)*: Số xe dừng chờ ở nhánh vào trừ đi số xe đang lưu thông ở nhánh ra.
  - `standard`: Tổng số xe nhánh vào trừ tổng số xe nhánh ra.
  - `density`: Chuẩn hóa số xe theo chiều dài nhánh đường (mật độ xe).
  - `normalized`: Chuẩn hóa theo số làn của từng nhánh.
- **Starvation Guard ($G_{max} = 60.0\text{s}$)**: Ép buộc chuyển sang pha kế tiếp nếu một nhánh phải chờ quá lâu, triệt tiêu hiện tượng bỏ đói pha trong điều kiện bất đối xứng lưu lượng.
- **Idle Protection**: Nếu áp lực mạng lưới bằng 0 ở mọi pha (vắng xe), hệ thống giữ nguyên pha hiện tại, tránh đổi đèn lãng phí.
- **Khử trùng lặp làn (Lane Deduplication)**: Tự động loại bỏ việc tính trùng số lượng xe khi nhiều kết nối pha chia sẻ chung một làn đường.

### 3. Tabular Q-Learning (QL)
- **Mô hình**: Học tăng cường phi tập trung độc lập cho từng ngã tư (Decentralized Independent Q-Learning - IDQL).
- **Rời rạc hóa trạng thái**: Chuyển đổi số lượng xe dừng thành các mức rời rạc:
  - `coarse`: 3 mức [0, 1-3, >3].
  - `refined` *(mặc định)*: 5 mức chi tiết [0, 1-2, 3-5, 6-9, >9].
  - `fine`: 6 mức chi tiết [0, 1-2, 3-5, 6-9, 10-14, >14].
  - Tùy chọn `--include-green-stage`: Ghép thêm giai đoạn thời gian xanh hiện tại vào vector trạng thái để triệt tiêu hiện tượng **State Aliasing**.
- **Hàm phần thưởng chuẩn RESCO (`--reward-type`)**:
  - `queue`: Phạt theo tổng độ dài hàng đợi xe dừng ($r_t = -\sum Q_{in}$).
  - `delay`: Phạt theo tổng thời gian chờ tích lũy ($r_t = -\sum W_{in}$).
  - `pressure`: Phạt theo áp lực chênh lệch mạng lưới ($r_t = -|P(p)|$).
- **Phạt chuyển pha (Switch Penalty)**: Trừ điểm phạt vào hàm phần thưởng khi agent quyết định đổi đèn ($r' = r - \text{penalty}$), giúp đèn vận hành ổn định, chống giật cục.
- **Tính toán Bellman khi vướng $G_{min}$**: Khi bị khóa trong thời gian xanh tối thiểu, agent vẫn lưu vết transition và thực hiện cập nhật Bellman đầy đủ:
  $$Q(s, a) \leftarrow Q(s, a) + \alpha \left[ r + \gamma \max_{a'} Q(s', a') - Q(s, a) \right]$$
- **Cơ chế Transfer Priors**: Tự động chuyển giao tri thức kinh nghiệm bảng Q giữa các nút giao có cấu trúc tương đồng.

### 4. Deep Q-Network (DQN / Double DQN)
- **Mô hình**: Mạng nơ-ron sâu đa tầng xấp xỉ hàm giá trị hành động tối ưu $Q^*(s, a)$.
- **Vector quan sát liên tục (Continuous State Vector)**:
  Mỗi pha $p$ được biểu diễn bởi vector đặc trưng gồm:
  1. Tỷ lệ hàng đợi xe dừng: $\min(Q_p / 20.0, 1.0)$
  2. Tỷ lệ mật độ phương tiện: $\min(V_p / 30.0, 1.0)$
  3. Thời gian chờ chuẩn hóa: $\min(W_p / 120.0, 1.0)$
  4. Áp lực chuẩn hóa: $\tanh(P_p / 10.0)$
  5. One-hot encoding của pha hiện tại
  6. Thời gian xanh đã trôi qua: $\min(t_{green} / 60.0, 1.0)$
- **Kiến trúc mạng nơ-ron (PyTorch MLP)**:
  $$\text{Input}(5 \times P + 1) \longrightarrow \text{Linear}(128) \longrightarrow \text{ReLU} \longrightarrow \text{Linear}(64) \longrightarrow \text{ReLU} \longrightarrow \text{Linear}(P)$$
- **Double DQN**: Tách rời việc lựa chọn hành động và ước lượng giá trị để tránh hiện tượng thổi phồng giá trị Q (Overestimation Bias):
  $$y_t = r_t + \gamma \, Q_{\text{target}}\left(s_{t+1}, \arg\max_{a'} Q_{\text{online}}(s_{t+1}, a'; \theta_t); \theta_t^-\right)$$
- **Kỹ thuật tối ưu hóa**:
  - **Experience Replay Buffer**: Bộ nhớ đệm 5,000 bước, lấy mẫu ngẫu nhiên mini-batch (kích thước 32) để phá vỡ tương quan chuỗi thời gian.
  - **Target Network Sync**: Cập nhật định kỳ mạng mục tiêu mỗi 20 bước tối ưu.
  - **Gradient Clipping**: Giới hạn chuẩn gradient tối đa $1.0$ để duy trì độ ổn định khi huấn luyện.
  - **Tie-Breaking Hysteresis**: Khi các giá trị Q-value xấp xỉ hòa nhau, ưu tiên giữ nguyên pha hiện tại.
  - **Dimension Adaptation**: Tự động nhận diện và tái khởi tạo số chiều khi người dùng đổi sang kịch bản mạng lưới có số pha khác biệt.

---

## 📂 Cấu trúc Repository

```text
LibSignal/
├── run.py                         # Điểm khởi chạy CLI (Benchmark đơn/đa seed, huấn luyện QL/DQN)
├── gui.py                         # Giao diện đồ họa tương tác (Sleepy Chicken Dashboard)
├── launch_gui.bat                 # Khởi chạy GUI 1-click tiện lợi trên Windows
├── setup.ps1                      # Tự động khởi tạo môi trường Python & kiểm tra SUMO
├── requirements.txt               # Thư viện phụ thuộc (eclipse-sumo, torch, numpy, matplotlib)
├── assets/                        # Tài nguyên biểu tượng giao diện
│   └── chicken_avatar.png         # Mascot giao diện Sleepy Chicken
├── checkpoints/                   # Trọng số mô hình đã huấn luyện hoàn chỉnh
│   ├── q_table.json               # Checkpoint Q-Learning
│   └── dqn_model.pt               # Checkpoint PyTorch Deep Q-Network
├── src/traffic_control/           # Mã nguồn lõi của framework
│   ├── core/                      # Module nền tảng chuẩn hóa
│   │   ├── config.py              # BenchmarkConfig (chuẩn hóa tham số môi trường & G_min)
│   │   ├── metrics.py             # EvaluationMetrics & MetricsCollector (chỉ số khoa học)
│   │   └── observation.py         # IntersectionObservation & TrafficSnapshot
│   ├── controllers/               # Các bộ điều khiển đèn giao thông
│   │   ├── registry.py            # Controller Registry & cơ chế Auto-discovery
│   │   ├── base.py                # BaseController, Safety Guard & tính áp lực xe P(p)
│   │   ├── fixed_time.py          # Bộ điều khiển Fixed-Time (Webster)
│   │   ├── max_pressure.py        # Bộ điều khiển Max-Pressure (Varaiya 2013)
│   │   ├── q_learning.py          # Bộ điều khiển Tabular Q-Learning (IDQL)
│   │   └── dqn.py                 # Bộ điều khiển Deep Q-Network (Double IDQN)
│   ├── sumo_env.py                # Môi trường SUMO/TraCI + tự động phát hiện SUMO_HOME
│   ├── experiment.py              # Vòng lặp mô phỏng chuẩn hóa & xuất kết quả CSV/JSON
│   └── visualization.py           # Module trực quan hóa đồ thị tự động (300 DPI)
├── data/
│   └── raw_data/                  # 11 kịch bản mạng lưới giao thông thực tế (.sumocfg)
├── tests/                         # Toàn bộ 64 unit tests kiểm định chất lượng mã nguồn
│   ├── test_controllers.py        # 21 tests kiểm tra FT, MP, observation, logic an toàn
│   ├── test_q_learning.py         # 15 tests kiểm tra Bellman, discretization, decay epsilon
│   ├── test_dqn.py                # 15 tests kiểm tra PyTorch MLP, Double DQN, Replay Buffer
│   ├── test_visualization.py      # 6 tests kiểm tra xuất biểu đồ tự động
│   ├── test_registry.py           # 4 tests kiểm tra OCP, safety guard, registry
│   └── test_metrics.py            # 3 tests kiểm tra thu thập metrics & trace CSV
└── docs/                          # Tài liệu lý thuyết, báo cáo RESCO và hướng dẫn mở rộng
```

---

## 🗺️ Danh sách 11 Kịch bản Mạng lưới Giao thông (`data/raw_data/`)

Toàn bộ các mạng lưới giao thông dưới đây đã được tích hợp đầy đủ file cấu hình `.sumocfg`, lưới đường `.net.xml` và luồng phương tiện `.rou.xml`:

| Tên kịch bản | Thư mục | Số nút giao | Đặc điểm giao thông |
| :--- | :--- | :---: | :--- |
| **Cologne 1 (Mặc định)** | `cologne1/` | 1 | Mạng lưới đô thị Cologne (Đức), chuẩn cho đánh giá cơ bản |
| **Cologne 3** | `cologne3/` | 3 (liên kết) | Kịch bản mở rộng với 3 cụm đèn liên hoàn và cấu hình làn rẽ phức tạp |
| **Ingolstadt 21** | `ingolstadt21/` | 1 | Bản đồ thực tế thành phố Ingolstadt với lưu lượng thực |
| **Manhattan (28x7)** | `manhattan_28x7/` | Đa nút giao | Mạng lưới bàn cờ quy mô lớn Manhattan với hàng chục nút giao |
| **Atlanta (1x5)** | `atlanta_1x5/` | Hành lang 5 nút | Tuyến đường trục 5 nút giao liên tiếp, kiểm tra làn sóng xanh |
| **Hangzhou (1x1)** | `hangzhou_1x1_*/` | 1 | Dữ liệu lưu lượng thực tế tại Hàng Châu (4 khung giờ khác nhau) |
| **Hangzhou (4x4)** | `hangzhou_4x4_*/` | 16 | Lưới 16 ngã tư đồng nhất và không đồng nhất (hetero) |

---

## 🚀 Cài đặt & Chuẩn bị Môi trường

### Yêu cầu hệ thống
- Python: Phiên bản **3.9 - 3.12**.
- Hệ điều hành: Windows, macOS hoặc Linux.

### Cách 1: Cài đặt siêu tốc qua pip (Khuyên dùng)
Mở terminal tại thư mục `LibSignal`:
```powershell
pip install -r requirements.txt
```
> [!TIP]
> Gói `eclipse-sumo` trên PyPI đã đi kèm sẵn file thực thi `sumo.exe`, `sumo-gui.exe`, thư viện `traci` và `sumolib`. Bạn có thể chạy ngay mà không cần quyền Administrator hay cài đặt MSI ngoài.

### Cách 2: Khởi tạo tự động bằng PowerShell (Windows)
Chạy script tự động tạo môi trường ảo `.venv` và cài đặt dependencies:
```powershell
.\setup.ps1
```

---

## 🖥️ Giao diện đồ họa (Sleepy Chicken Dashboard)

Dự án cung cấp giao diện đồ họa **Sleepy Chicken Dashboard** thân thiện, trực quan:

* **Khởi chạy nhanh trên Windows**: Nhấp đúp chuột vào file [`launch_gui.bat`](launch_gui.bat).
* **Khởi chạy bằng lệnh**:
  ```powershell
  python gui.py
  ```

### Các tính năng chính trên GUI:
1. **Quản lý kịch bản**: Tự động phát hiện 11 bản đồ có sẵn hoặc tải file `.sumocfg` tùy chọn bên ngoài.
2. **Lựa chọn thuật toán linh hoạt**:
   - Chạy kiểm chuẩn toàn bộ 4 thuật toán (`Fixed-Time`, `Max-Pressure`, `Q-Learning`, `DQN`).
   - Chọn đơn lẻ bất kỳ thuật toán nào để quan sát phản hồi.
3. **Chế độ huấn luyện Reinforcement Learning**:
   - Hỗ trợ huấn luyện trực tiếp Tabular Q-Learning hoặc Deep Q-Network với thanh tiến trình real-time.
   - Tự động lưu checkpoint mô hình khi kết thúc huấn luyện.
4. **Mô phỏng trực quan**: Bật/tắt cửa sổ SUMO-GUI và thanh trượt điều chỉnh tốc độ mô phỏng (`step-delay`).
5. **Console Log thời gian thực**: Theo dõi tiến trình mô phỏng, độ trễ và thông lượng tức thì.
6. **Bảng thành tích & Xuất dữ liệu**: Xem bảng so sánh số liệu, tự động vẽ và mở đồ thị phân tích chất lượng cao (300 DPI) chỉ với 1 click.

---

## 💻 Chạy thử nghiệm bằng dòng lệnh (CLI Reference)

Tất cả các chức năng được điều khiển tập trung thông qua file `run.py`:

```powershell
python run.py [options]
```

### Bảng tra cứu tham số dòng lệnh chi tiết:

| Tham số | Kiểu dữ liệu | Mặc định | Mô tả |
| :--- | :---: | :---: | :--- |
| `-c`, `--controller` | Chuỗi | `all` | Thuật toán chạy: `all`, `ft`, `mp`, `ql`, `dqn` |
| `--controllers` | Chuỗi | `None` | Danh sách thuật toán so sánh khi chọn `all` (vd: `ft,mp,ql,dqn`) |
| `-m`, `--scenario` | Đường dẫn | `cologne1` | Đường dẫn file kịch bản `.sumocfg` |
| `-s`, `--steps` | Số nguyên | `900` | Số giây mô phỏng (chuẩn RESCO: 900s) |
| `--action-interval` | Số nguyên | `10` | Số giây giữa 2 lần ra quyết định chọn pha ($\Delta t$) |
| `--seed` | Số nguyên | `0` | Hạt giống ngẫu nhiên đơn lẻ |
| `--seeds` | Chuỗi | `None` | Danh sách seeds để kiểm chuẩn đa hạt giống khoa học (vd: `0,1,2`) |
| `--minimum-green` | Số thực | `10.0` | Thời gian xanh tối thiểu an toàn $G_{min}$ (giây) |
| `--max-green` | Số thực | `60.0` | Thời gian xanh tối đa $G_{max}$ cho Max-Pressure chống bỏ đói pha |
| `--yellow-seconds` | Số thực | `3.0` | Thời gian đèn vàng chuyển pha $Y$ (giây) |
| `--pressure-mode` | Lựa chọn | `halting` | Chế độ tính áp lực: `halting`, `standard`, `density`, `normalized` |
| `--proportional-splits` | Cờ bật | `False` | Bật tính chu kỳ tối ưu Webster $C_0$ và phân bổ Green Splits |
| `--train` | Cờ bật | `False` | Bật chế độ huấn luyện mô hình RL (Q-Learning hoặc DQN) |
| `--episodes` | Số nguyên | `1` | Số episode khi huấn luyện |
| `--alpha` | Số thực | `0.1` | Learning rate $\alpha$ cho Q-Learning |
| `--gamma` | Số thực | `0.9` | Discount factor $\gamma$ cho Q-Learning & DQN |
| `--epsilon` | Số thực | `0.05` | Tỷ lệ khám phá $\epsilon$ khi đánh giá (hoặc khởi điểm huấn luyện) |
| `--lr` | Số thực | `0.001` | Learning rate cho optimizer Adam của DQN |
| `--batch-size` | Số nguyên | `32` | Kích thước mini-batch cho Replay Buffer của DQN |
| `--buffer-size` | Số nguyên | `5000` | Kích thước Replay Buffer của DQN |
| `--target-update` | Số nguyên | `20` | Chu kỳ cập nhật Target Network của DQN |
| `--no-double-dqn` | Cờ bật | `False` | Tắt Double DQN (chỉ dùng DQN tiêu chuẩn) |
| `-g`, `--gui` | Cờ bật | `False` | Mở giao diện mô phỏng đồ họa SUMO-GUI |
| `-d`, `--step-delay` | Số thực | `0.03`/`0.0` | Thời gian trễ mỗi bước mô phỏng (giây) |
| `-o`, `--output` | Đường dẫn | `results/` | Thư mục lưu kết quả CSV, JSON và đồ thị |

---

### Các ví dụ lệnh chạy thực nghiệm phổ biến:

#### 1. Chạy Benchmark so sánh cả 4 thuật toán trên Cologne 1 (Mặc định):
```powershell
python run.py
```

#### 2. Kiểm chuẩn đa hạt giống khoa học theo chuẩn RESCO ($seeds = [0, 1, 2]$):
```powershell
python run.py --seeds 0,1,2
```
*Hệ thống sẽ chạy từng thuật toán qua 3 seeds và tự động tính toán bảng Mean ± Std cùng các biểu đồ sai số.*

#### 3. Huấn luyện thuật toán học tăng cường sâu (DQN) 50 episodes:
```powershell
python run.py -c dqn --train --episodes 50
```

#### 4. Huấn luyện Tabular Q-Learning 50 episodes:
```powershell
python run.py -c ql --train --episodes 50
```

#### 5. Mở SUMO-GUI quan sát trực quan xe chạy và đổi đèn:
```powershell
# Xem Deep Q-Network điều khiển
python run.py -c dqn -g

# Xem Max-Pressure điều khiển
python run.py -c mp -g
```

#### 6. Chạy trên bản đồ đa nút giao phức tạp Cologne 3:
```powershell
python run.py -m "data\raw_data\cologne3\cologne3.sumocfg" -s 300
```

---

## 📊 Bộ chỉ số đánh giá chuẩn hóa (RESCO Standard Metrics)

| Chỉ số | Đơn vị | Định nghĩa toán học / Ý nghĩa khoa học |
| :--- | :---: | :--- |
| **Penalized Travel Time** | giây | Thời gian di chuyển có tính phạt cho toàn bộ xe còn kẹt trong mạng lưới ($T_{penalized} = \text{now} - t_{depart}$). Triệt tiêu hoàn toàn hiện tượng *Survival Bias*. |
| **Average Travel Time** | giây | Thời gian di chuyển trung bình của các xe đã hoàn thành toàn bộ lộ trình. |
| **Average Delay** | giây | Độ trễ trung bình của xe so với thời gian di chuyển trong điều kiện lý tưởng tự do. |
| **Total Time Loss** | giây | Tổng thời gian lãng phí/chậm trễ tích lũy của toàn bộ các phương tiện trong mạng. |
| **Average Queue** | xe | Số lượng phương tiện dừng chờ trung bình trên mỗi nút giao tại mỗi bước mô phỏng. |
| **Throughput** | xe | Tổng số lượng xe đã hoàn thành và rời khỏi mạng lưới. |
| **Completion Rate** | % | Tỷ lệ phương tiện hoàn thành lộ trình ($\text{Throughput} / \text{Departed}$). |
| **Phase Switches** | lần | Tổng số lần chuyển pha đèn (đo lường tính ổn định và mức độ mài mòn thiết bị). |

---

## 🏆 Kết quả nghiệm thu thực nghiệm (Multi-Seed Benchmark)

### 1. Kịch bản Đô thị Chuẩn - Cologne 1 (900 giây, Hạt giống: 0, 1, 2)

| Thuật toán | Phân loại | Penalized TT (s) ↓ | Thời gian đi TB (s) ↓ | Độ trễ TB (s) ↓ | Hàng đợi TB (xe) ↓ | Thông lượng (xe) ↑ | Tỷ lệ xong (%) ↑ | Đổi pha (lần) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 🥇 **DQN (Double IDQN)** | Deep RL (50 eps) | **44.76 ± 0.26** | **45.55 ± 0.19** | **21.16 ± 0.12** | **4.84 ± 0.04** | 522.7 ± 1.5 | 96.9% ± 0.0% | 41.7 |
| 🥈 **Max-Pressure** | Heuristic Thích nghi | 44.99 ± 1.18 | 45.74 ± 1.13 | 21.44 ± 0.97 | 4.90 ± 0.37 | **525.7 ± 4.9** | **97.1% ± 0.2%** | 42.7 |
| 🥉 **Q-Learning (IDQL)** | Tabular RL (50 eps) | 81.42 ± 5.07 | 83.62 ± 5.57 | 57.94 ± 5.23 | 22.07 ± 2.32 | 506.3 ± 6.4 | 95.1% ± 1.6% | 38.0 |
| 🎖️ **Fixed-Time (Webster)** | Heuristic Cố định | 96.25 ± 5.25 | 99.40 ± 3.75 | 73.16 ± 5.01 | 28.34 ± 2.23 | 491.7 ± 6.7 | 93.0% ± 1.2% | 29.0 |

### 2. Kịch bản Đa Nút giao Phức tạp - Cologne 3 (300 giây, Hạt giống: 0, 1, 2)

| Thuật toán | Phân loại | Penalized TT (s) ↓ | Thời gian đi TB (s) ↓ | Độ trễ TB (s) ↓ | Hàng đợi TB (xe) ↓ | Thông lượng (xe) ↑ | Tỷ lệ xong (%) ↑ | Đổi pha (lần) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 🥇 **DQN (Double IDQN)** | Deep RL (50 eps) | **48.78 ± 0.96** | **50.26 ± 1.11** | **17.91 ± 0.97** | **1.44 ± 0.16** | **250.7 ± 4.2** | **81.8% ± 0.9%** | 38.3 |
| 🥈 **Max-Pressure** | Heuristic Thích nghi | 50.15 ± 2.41 | 52.18 ± 1.25 | 19.33 ± 2.63 | 1.68 ± 0.10 | **250.7 ± 3.8** | 81.1% ± 1.2% | 34.0 |
| 🥉 **Fixed-Time (Webster)** | Heuristic Cố định | 60.21 ± 2.04 | 59.23 ± 0.55 | 31.44 ± 2.54 | 3.58 ± 0.28 | 210.0 ± 7.0 | 70.1% ± 2.9% | 52.0 |
| 🎖️ **Q-Learning (IDQL)** | Tabular RL (50 eps) | 67.79 ± 1.94 | 65.58 ± 2.59 | 39.16 ± 2.45 | 2.80 ± 0.19 | 209.0 ± 13.5 | 69.5% ± 3.5% | 45.0 |

---

## 🧪 Kiểm định chất lượng mã nguồn (Unit Tests)

Bộ kiểm thử tự động gồm **64 unit tests** độc lập được tổ chức theo chuẩn `unittest`:

```powershell
python -m unittest discover tests -v
```

### Phân bố các ca kiểm thử:
1. **`tests/test_controllers.py` (21 tests)**:
   - Kiểm tra công thức chu kỳ tối ưu Webster $C_0$ và Green Splits của Fixed-Time.
   - Kiểm tra các chế độ tính áp lực của Max-Pressure (`halting`, `standard`, `density`, `normalized`).
   - Kiểm tra cơ chế chống bỏ đói pha (**Starvation Guard**) và bảo vệ khi vắng xe (**Idle Protection**).
   - Kiểm tra khử trùng lặp xe trên các làn rẽ chia sẻ (**Lane Deduplication**).
   - Kiểm tra trích xuất quan sát `IntersectionObservation` và snapshot giao thông.
2. **`tests/test_q_learning.py` (15 tests)**:
   - Kiểm tra cập nhật Bellman, decay epsilon và tính độc lập đa nút giao (IDQL).
   - Kiểm tra chế độ rời rạc hóa `coarse`, `refined`, `fine` và chống State Aliasing với `green_stage`.
   - Kiểm tra cơ chế Tie-breaking Hysteresis và Transfer Priors.
   - Kiểm tra lưu và nạp checkpoint `q_table.json`.
3. **`tests/test_dqn.py` (15 tests)**:
   - Kiểm tra cấu trúc mạng nơ-ron PyTorch MLP và forward pass.
   - Kiểm tra bộ nhớ đệm `ReplayBuffer` và cập nhật mục tiêu Double DQN.
   - Kiểm tra vector hóa không gian quan sát liên tục $(5 \times P + 1)$.
   - Kiểm tra cơ chế thích ứng chiều tự động (`dimension_adaptation`) khi đổi kịch bản.
   - Kiểm tra lưu và nạp checkpoint PyTorch `dqn_model.pt`.
4. **`tests/test_visualization.py` (6 tests)**:
   - Kiểm tra xuất tự động biểu đồ so sánh đa hạt giống kèm thanh sai số ($\text{Mean} \pm \text{Std}$).
   - Kiểm tra xuất biểu đồ chuỗi thời gian, đường cong học tập RL và hàm tổng hợp `generate_all_plots`.
5. **`tests/test_registry.py` (4 tests)**:
   - Kiểm tra cơ chế đăng ký và tra cứu controller qua `@register_controller`.
   - Minh chứng nguyên lý Open-Closed: thêm thuật toán mới độc lập mà không can thiệp code cũ.
   - Kiểm tra cơ chế khóa an toàn thời gian xanh tối thiểu `SafetyGuard`.
6. **`tests/test_metrics.py` (3 tests)**:
   - Kiểm tra thu thập metrics, tính toán tổng hợp và xuất file trace CSV.

---

## 📚 Danh mục Tài liệu Chuyên sâu

- 📊 [Báo cáo Tổng hợp Nghiệm thu Khoa học (Đầy đủ)](docs/BAO_CAO_TONG_HOP_KET_QUA.md)
- 📑 [Báo cáo Đối sánh Phương pháp luận RESCO](docs/BAO_CAO_SO_SANH_RESCO.md)
- 📖 [Cơ sở Lý thuyết Fixed-Time & Max-Pressure](docs/LY_THUYET_FT_MP.md)
- 🔌 [Hướng dẫn 3 bước thêm thuật toán mới](docs/HUONG_DAN_THEM_THUAT_TOAN.md)
- 📋 [Kịch bản Demo Thuyết trình](docs/KICH_BAN_DEMO.md)
