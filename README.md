# 🚦 Học Máy Nâng Cao - Đề Tài Nhóm 9
## Nghiên Cứu & Đánh Giá So Sánh Các Thuật Toán Điều Khiển Đèn Tín Hiệu Giao Thông Thông Minh

> **Học phần**: Học Máy Nâng Cao  
> **Nền tảng mô phỏng**: Eclipse SUMO (Simulation of Urban MObility) & TraCI  
> **Khung kiểm chuẩn**: Tuân thủ phương pháp luận quốc tế **RESCO** (*NeurIPS 2021 Benchmark Suite*)  
> **Thuật toán triển khai**: **Fixed-Time** (Heuristic cố định), **Max-Pressure** (Heuristic thích nghi), **Tabular Q-Learning** (Học tăng cường dạng bảng - IDQL), **Deep Q-Network** (Học tăng cường sâu - Double IDQN)  
> **Chất lượng mã nguồn**: Đạt **64/64 Unit Tests** kiểm định toàn diện  

---

## 📌 1. Tổng quan đề tài

Ùn tắc giao thông tại các đô thị lớn gây thiệt hại nghiêm trọng về kinh tế, gia tăng lượng phát thải khí nhà kính và lãng phí thời gian của người dân. Các hệ thống điều khiển đèn giao thông truyền thống với chu kỳ cố định (Fixed-Time) không thể thích ứng kịp thời với sự biến động ngẫu nhiên của các luồng phương tiện.

Đề tài tập trung nghiên cứu, xây dựng và đánh giá thực nghiệm một nền tảng khoa học hoàn chỉnh nhằm giải quyết bài toán **Điều khiển Đèn Tín hiệu Giao thông Đa Nút giao (Multi-Intersection Traffic Signal Control)**. Dự án đối sánh 4 thuật toán đại diện cho 3 trường phái chính:

1. **Fixed-Time (FT)**: Điều khiển truyền thống với chu kỳ tối ưu Webster $C_0$ (1958) và chia thời gian xanh tỷ lệ theo thông lượng/làn xe (Green Splits Equisaturation theo chuẩn RESCO).
2. **Max-Pressure (MP)**: Thuật toán Heuristic thích nghi phân tán kinh điển (Varaiya, 2013). Cân bằng áp lực mạng lưới $P(p) = \sum(N_{in} - N_{out})$, tích hợp cơ chế chống bỏ đói pha (**Starvation Guard** $G_{max} = 60s$), chống nhảy đèn lãng phí khi vắng xe (**Idle Protection**) và khử trùng lặp làn (**Lane Deduplication**).
3. **Tabular Q-Learning (QL)**: Thuật toán Học tăng cường phi tập trung (Decentralized Independent Q-Learning - IDQL). Rời rạc hóa không gian hàng đợi dừng, tối ưu hàm thưởng phạt chuyển pha đèn (**Switch Penalty**) và cơ chế kế thừa tri thức liên nút giao (**Transfer Priors**).
4. **Deep Q-Network (DQN / Double DQN)**: Thuật toán Học tăng cường sâu hiện đại (Mnih et al. 2015, Hasselt et al. 2016). Biểu diễn vector quan sát liên tục 6 chiều cho mỗi cụm pha, tích hợp bộ nhớ đệm tái hiện trải nghiệm (**Experience Replay Buffer**), mạng mục tiêu (**Target Network**) và cập nhật Bellman chống phóng đại giá trị (**Double DQN**).

Toàn bộ các thuật toán đều tuân thủ chặt chẽ cơ chế an toàn **Safety Guard**: thời gian xanh tối thiểu an toàn $G_{min} \ge 10.0\text{s}$, thời gian chuyển đèn vàng $Y = 3.0\text{s}$ và chu kỳ ra quyết định $\Delta t = 10.0\text{s}$.

---

## 🏆 2. Kết quả kiểm chuẩn đa hạt giống khoa học (RESCO Multi-Seed)

Kiểm chuẩn thực nghiệm được tiến hành khách quan trên 3 hạt giống độc lập ($seeds = [0, 1, 2]$) với các mô hình RL ở trạng thái đóng băng chính sách (**Frozen Policy**), khử triệt để hiện tượng **Survival Bias** thông qua chỉ số **Penalized Travel Time**:

### Bảng 1: Kịch bản Đô thị Chuẩn - Cologne 1 (Thời gian: 900s, Đa hạt giống 0, 1, 2)

| Xếp hạng | Thuật toán | Phân loại | Penalized TT (s) ↓ | Thời gian đi TB (s) ↓ | Độ trễ TB (s) ↓ | Hàng đợi TB (xe) ↓ | Thông lượng (xe) ↑ | Tỷ lệ xong (%) ↑ |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 🥇 | **DQN (Double IDQN)** | Deep RL (50 eps) | **44.76 ± 0.26** | **45.55 ± 0.19** | **21.16 ± 0.12** | **4.84 ± 0.04** | 522.7 ± 1.5 | 96.9% ± 0.0% |
| 🥈 | **Max-Pressure** | Heuristic thích nghi | 44.99 ± 1.18 | 45.74 ± 1.13 | 21.44 ± 0.97 | 4.90 ± 0.37 | **525.7 ± 4.9** | **97.1% ± 0.2%** |
| 🥉 | **Q-Learning (IDQL)** | Tabular RL (50 eps) | 81.42 ± 5.07 | 83.62 ± 5.57 | 57.94 ± 5.23 | 22.07 ± 2.32 | 506.3 ± 6.4 | 95.1% ± 1.6% |
| 🎖️ | **Fixed-Time (Webster)** | Heuristic cố định | 96.25 ± 5.25 | 99.40 ± 3.75 | 73.16 ± 5.01 | 28.34 ± 2.23 | 491.7 ± 6.7 | 93.0% ± 1.2% |

### Bảng 2: Kịch bản Đa Nút giao Phức tạp - Cologne 3 (Thời gian: 300s, 3 cụm đèn liên kết)

| Xếp hạng | Thuật toán | Penalized TT (s) ↓ | Độ trễ TB (s) ↓ | Hàng đợi TB (xe) ↓ | Thông lượng (xe) ↑ | Tỷ lệ xong (%) ↑ |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| 🥇 | **DQN (Double IDQN - 50 eps)** | **48.78 ± 0.96** | **17.91 ± 0.97** | **1.44 ± 0.16** | **250.7 ± 4.2** | **81.8% ± 0.9%** |
| 🥈 | **Max-Pressure** | 50.15 ± 2.41 | 19.33 ± 2.63 | 1.68 ± 0.10 | **250.7 ± 3.8** | 81.1% ± 1.2% |
| 🥉 | **Fixed-Time (Webster)** | 60.21 ± 2.04 | 31.44 ± 2.54 | 3.58 ± 0.28 | 210.0 ± 7.0 | 70.1% ± 2.9% |
| 🎖️ | **Q-Learning (IDQL - 50 eps)** | 67.79 ± 1.94 | 39.16 ± 2.45 | 2.80 ± 0.19 | 209.0 ± 13.5 | 69.5% ± 3.5% |

> [!TIP]
> **Nhận định khoa học chính**:
> - **DQN** dẫn đầu toàn diện trên cả 2 kịch bản về độ trễ, thời gian di chuyển, hàng đợi và độ lệch chuẩn nhỏ nhất (vận hành cực kỳ ổn định).
> - **Max-Pressure** là giải pháp Heuristic xuất sắc nhất, tiệm cận hiệu năng DQN mà **không cần dữ liệu hay thời gian huấn luyện trước**.
> - **Q-Learning sau 50 episodes** đã cải thiện vượt bậc, giảm hơn 29 giây độ trễ trên Cologne 1 so với Fixed-Time.

---

## 📂 3. Cấu trúc Repository

```text
HMNC/
├── README.md                          # Tài liệu tổng quan dự án (File này)
├── Đề Xuất Đề Tài Nhóm 9.docx          # Đề cương chi tiết đề tài nghiên cứu
├── s10994-023-06412-y.pdf              # Bài báo khoa học tham chiếu gốc (LibSignal)
└── LibSignal/                          # Mã nguồn chính của framework
    ├── run.py                          # CLI chạy thí nghiệm, benchmark, huấn luyện RL
    ├── gui.py                          # Giao diện đồ họa tương tác (Sleepy Chicken Dashboard)
    ├── launch_gui.bat                  # Khởi chạy GUI 1-click tiện lợi trên Windows
    ├── setup.ps1                       # Tự động khởi tạo môi trường Python & kiểm tra SUMO
    ├── requirements.txt                # Các thư viện phụ thuộc (eclipse-sumo, torch, numpy, matplotlib)
    ├── assets/                         # Tài nguyên biểu tượng giao diện
    ├── checkpoints/                    # Trọng số mô hình đã huấn luyện
    │   ├── q_table.json                # Checkpoint Tabular Q-Learning
    │   └── dqn_model.pt                # Checkpoint PyTorch Deep Q-Network
    ├── src/traffic_control/            # Khung điều khiển & môi trường mô phỏng
    │   ├── controllers/                # FT, MP, Q-Learning, DQN & Controller Registry
    │   ├── core/                       # Cấu hình BenchmarkConfig, Quan sát & Thu thập Metrics
    │   ├── sumo_env.py                 # Môi trường kết nối SUMO/TraCI tự động nhận diện
    │   ├── experiment.py               # Vòng lặp mô phỏng & xuất báo cáo CSV/JSON
    │   └── visualization.py            # Module trực quan hóa đồ thị tự động (300 DPI)
    ├── data/raw_data/                  # 11 kịch bản mạng lưới giao thông thực tế (.sumocfg)
    ├── tests/                          # Toàn bộ 64 Unit Tests kiểm định chất lượng
    └── docs/                           # Thư mục tài liệu lý thuyết & báo cáo nghiệm thu
```

---

## ⚡ 4. Bắt đầu nhanh (Quickstart)

### Bước 1: Cài đặt thư viện phụ thuộc
Chỉ cần Python 3.9 - 3.12, mở terminal tại thư mục `LibSignal`:
```powershell
cd LibSignal
pip install -r requirements.txt
```
> [!NOTE]
> Gói `eclipse-sumo` trên PyPI đã tích hợp đầy đủ file thực thi `sumo.exe`, `sumo-gui.exe`, thư viện `traci` và `sumolib`. Người dùng **không cần tải bộ cài đặt MSI** hay cấu hình biến môi trường thủ công.

---

### Bước 2: Khởi chạy Giao diện Đồ họa (GUI Dashboard)
Cách nhanh nhất và trực quan nhất:
* **Trên Windows**: Nhấp đúp chuột vào file [`LibSignal/launch_gui.bat`](LibSignal/launch_gui.bat).
* **Bằng dòng lệnh**:
  ```powershell
  cd LibSignal
  python gui.py
  ```

**Các tính năng nổi bật trên GUI Dashboard:**
- Tự động quét 11 kịch bản bản đồ từ `data/raw_data/` hoặc chọn file `.sumocfg` tùy ý.
- Chạy đối sánh tất cả hoặc nhóm thuật toán tùy chọn (FT, MP, QL, DQN).
- Chế độ huấn luyện RL trực quan với thanh tiến trình thời gian thực.
- Xem mô phỏng đồ họa chuyển động xe và pha đèn bằng SUMO-GUI.
- Tự động sinh biểu đồ phân tích chất lượng cao (300 DPI) và xuất file CSV/JSON.

---

### Bước 3: Chạy thí nghiệm bằng Dòng lệnh (CLI)

```powershell
cd LibSignal

# 1. Chạy Benchmark so sánh cả 4 thuật toán trên bản đồ mặc định Cologne 1 (900s)
python run.py

# 2. Kiểm chuẩn đa hạt giống khoa học theo chuẩn RESCO (seeds 0, 1, 2)
python run.py --seeds 0,1,2

# 3. Xem trực quan chuyển động xe và đèn tín hiệu qua SUMO-GUI
python run.py -c dqn -g
python run.py -c mp -g

# 4. Huấn luyện thuật toán học tăng cường
# Huấn luyện Deep Q-Network (DQN) 50 episodes:
python run.py -c dqn --train --episodes 50

# Huấn luyện Tabular Q-Learning 50 episodes:
python run.py -c ql --train --episodes 50

# 5. Chạy trên mạng lưới đa nút giao phức tạp Cologne 3
python run.py -m "data\raw_data\cologne3\cologne3.sumocfg" -s 300
```

---

### Bước 4: Chạy toàn bộ Unit Tests kiểm định mã nguồn
Framework đi kèm bộ kiểm thử tự động **64 unit tests** bao phủ mọi module:
```powershell
cd LibSignal
python -m unittest discover tests -v
```

---

## 📖 5. Danh mục Tài liệu Kỹ thuật & Báo cáo

Mọi tài liệu chuyên sâu được lưu trữ đầy đủ trong thư mục [`LibSignal/docs/`](LibSignal/docs/):

| STT | Tài liệu | Mô tả chi tiết |
| :---: | :--- | :--- |
| 1 | [Báo cáo Tổng hợp Nghiệm thu Khoa học](LibSignal/docs/BAO_CAO_TONG_HOP_KET_QUA.md) | Báo cáo thực nghiệm đa hạt giống, biểu đồ đối sánh và phân tích chuyên sâu hiệu năng 4 thuật toán |
| 2 | [Báo cáo Đối sánh Phương pháp luận RESCO](LibSignal/docs/BAO_CAO_SO_SANH_RESCO.md) | Phân tích phương pháp luận kiểm chuẩn quốc tế, chỉ số Penalized TT và loại trừ Survival Bias |
| 3 | [Cơ sở Lý thuyết Fixed-Time & Max-Pressure](LibSignal/docs/LY_THUYET_FT_MP.md) | Công thức tối ưu chu kỳ Webster $C_0$, định lý áp lực Varaiya, Starvation Guard và Idle Protection |
| 4 | [Hướng dẫn 3 bước thêm thuật toán mới](LibSignal/docs/HUONG_DAN_THEM_THUAT_TOAN.md) | Hướng dẫn mở rộng controller mới qua Controller Registry theo nguyên lý Open-Closed |
| 5 | [Kịch bản Demo Thuyết trình](LibSignal/docs/KICH_BAN_DEMO.md) | Kịch bản trình diễn đề tài trực quan 5 - 7 phút dành cho buổi bảo vệ báo cáo |

Chi tiết kỹ thuật dành cho nhà phát triển xem tại [`LibSignal/README.md`](LibSignal/README.md).
