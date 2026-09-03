# 🚦 Học Máy Nâng Cao - Đề Tài Nhóm 9

**Đề tài**: Nghiên cứu, cài đặt và đánh giá so sánh các thuật toán điều khiển đèn tín hiệu giao thông thông minh (Traffic Signal Control) trên nền tảng **SUMO (Simulation of Urban MObility)** và **TraCI**.

---

## 📌 Tổng quan đề tài

Dự án triển khai và đối sánh khoa học giữa các trường phái điều khiển đèn tín hiệu giao thông theo chuẩn kiểm chuẩn quốc tế **RESCO (Reinforcement Learning Benchmarks for Traffic Signal Control)**:
1. **Fixed-Time (FT)**: Điều khiển truyền thống theo chu kỳ thời gian cố định và chia pha theo tỉ lệ số làn (xấp xỉ công thức Webster).
2. **Max-Pressure (MP)**: Thuật toán điều khiển thích nghi phân tán theo áp lực luồng xe (Varaiya, 2013), tích hợp cơ chế chống bỏ đói pha (Starvation Guard) và giữ pha khi vắng xe (Idle Protection).
3. **Tabular Q-Learning (QL)**: Thuật toán học máy tăng cường phi tập trung (Decentralized Independent Q-Learning - IDQL) tối ưu theo độ dài hàng đợi xe dừng chờ và phạt đổi pha.

---

## 📂 Cấu trúc Repository

```text
HMNC/
├── LibSignal/                     # Mã nguồn chính của framework điều khiển giao thông
│   ├── run.py                     # CLI chạy thí nghiệm, benchmark đơn/đa seed, huấn luyện QL
│   ├── gui.py                     # Giao diện đồ họa tương tác (Sleepy Chicken Dashboard)
│   ├── launch_gui.bat             # File khởi chạy GUI 1-click trên Windows
│   ├── setup.ps1                  # Script tự động khởi tạo môi trường Python & kiểm tra SUMO
│   ├── requirements.txt           # Danh sách thư viện phụ thuộc (eclipse-sumo)
│   ├── assets/                    # Tài nguyên hình ảnh giao diện
│   ├── checkpoints/               # Lưu trữ bảng Q-table đã huấn luyện
│   ├── src/traffic_control/       # Bộ điều khiển (controllers), môi trường (sumo_env) & metrics
│   ├── data/raw_data/             # 11 bộ kịch bản mạng lưới giao thông thực tế (.sumocfg)
│   ├── tests/                     # 30 unit tests kiểm định chất lượng mã nguồn
│   └── docs/                      # Tài liệu lý thuyết, báo cáo RESCO và hướng dẫn thuyết trình
├── Đề Xuất Đề Tài Nhóm 9.docx     # Đề cương chi tiết đề tài nghiên cứu của nhóm
└── s10994-023-06412-y.pdf         # Bài báo nghiên cứu khoa học tham chiếu chính (LibSignal)
```

---

## ⚡ Bắt đầu nhanh

### 1. Khởi chạy Giao diện Đồ họa (GUI)
Cách nhanh nhất và trực quan nhất trên Windows:
* Nhấp đúp chuột vào file [`LibSignal/launch_gui.bat`](LibSignal/launch_gui.bat)
* Hoặc chạy lệnh:
  ```powershell
  cd LibSignal
  python gui.py
  ```

### 2. Chạy thử nghiệm bằng Dòng lệnh (CLI)
Mở terminal PowerShell tại thư mục `LibSignal`:
```powershell
cd LibSignal

# Cài đặt môi trường siêu tốc (nếu chưa cài)
pip install -r requirements.txt

# Chạy Benchmark so sánh cả 3 thuật toán FT, MP, QL (900s)
python run.py

# Chạy mô phỏng có đồ họa quan sát chuyển động xe
python run.py -c mp -g

# Chạy kiểm chuẩn khoa học đa hạt giống (Multi-Seed RESCO: seeds 0, 1, 2)
python run.py --seeds 0,1,2
```

### 3. Chạy toàn bộ Unit Tests
```powershell
cd LibSignal
python -m unittest discover tests -v
```

---

## 📖 Tài liệu chi tiết

Vui lòng tham khảo tài liệu đầy đủ tại [`LibSignal/README.md`](LibSignal/README.md) cùng thư mục [`LibSignal/docs/`](LibSignal/docs/):
- [Lý thuyết chi tiết Fixed-Time & Max-Pressure](LibSignal/docs/LY_THUYET_FT_MP.md)
- [Kịch bản Demo thuyết trình 5-7 phút](LibSignal/docs/KICH_BAN_DEMO.md)
- [Báo cáo đối sánh phương pháp luận theo chuẩn RESCO](LibSignal/docs/BAO_CAO_SO_SANH_RESCO.md)
- [Hướng dẫn 3 bước thêm thuật toán mới](LibSignal/docs/HUONG_DAN_THEM_THUAT_TOAN.md)
