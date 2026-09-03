# Báo cáo Nghiệm thu: So sánh với RESCO & Nâng cấp Kiểm chuẩn Công bằng

Tài liệu này tổng kết toàn bộ quá trình đối chiếu với **RESCO** (*NeurIPS 2021 Benchmark Suite*) và các cải tiến kỹ thuật đã thực hiện trên dự án **LibSignal** nhằm bảo đảm **tính công bằng tuyệt đối trong kiểm chuẩn** và **phản ánh trung thực bản chất thuật toán**.

---

## 1. Bảng Đối Chiếu: RESCO vs LibSignal (Trước & Sau Cải Tiến)

| Hạng mục | **RESCO (NeurIPS 2021)** | **LibSignal (Ban đầu)** | **LibSignal (Sau nâng cấp)** |
| :--- | :--- | :--- | :--- |
| **Đo lường thời gian đi lại (Travel Time)** | Tính cả phương tiện chưa hoàn thành (`write-unfinished`, Delay) để loại bỏ **Survival Bias**. | Chỉ tính trên xe đã về đích (`_completed_travel_times`). Thuật toán gây nghẽn xe vẫn có điểm đẹp. | **Penalized Travel Time**: Tính cả thời gian các xe kẹt trong mạng (`now - depart_time`). Thuật toán gây tắc nghẽn lập tức bị phơi bày! |
| **Độ trễ hệ thống (System Delay)** | Báo cáo Time Loss / Delay so với tốc độ tự do. | Chỉ đo hàng đợi và waiting time tích lũy tạm thời. | **Average Delay & Total Time Loss**: Đo lường tổng thời gian các phương tiện bị chậm trễ thực tế từ SUMO. |
| **Max-Pressure (MP)** | $P = \sum (x_{in} - x_{out})$ tính trên **hàng đợi dừng chờ (`queued`)**, không cộng lặp làn. | Dùng tổng xe (kể cả xe chạy 50km/h); làn rẽ 2 hướng bị đếm lặp 2 lần; trừ cả xe đang thoát tự do. | **Chuẩn Varaiya & RESCO**: Khử trùng lặp làn (`unique_in_lanes`), tính áp lực dựa trên số xe dừng chờ (`halting queue`). |
| **Fixed-Time (FT)** | Green Splits tối ưu theo tỷ lệ lưu lượng / số làn (tiệm cận Webster). | Ép cứng 30s/pha cho mọi ngã tư, khiến Fixed-Time bị "dìm hàng" (crippled baseline). | **Proportional Green Splits**: Tự động phân bổ thời gian xanh theo tỷ lệ số làn vào ngã tư (`--proportional-splits`). |
| **Q-Learning (QL)** | **Decentralized Multi-Agent (IDQN)**: Mỗi ngã tư có không gian Q riêng; modular reward (`queue`, `delay`, `pressure`). | Dùng chung 1 Q-table duy nhất cho toàn bộ ngã tư, state không có `tls_id`, gây xung đột dữ liệu trên mạng lớn. | **Decentralized Multi-Agent (IDQL)**: Q-table riêng biệt cho từng ngã tư (`q_tables[tls_id]`); hỗ trợ 3 loại reward: `queue`, `delay`, `pressure`. |
| **Đèn vàng & Chu kỳ an toàn** | Mặc định 3.0s đèn vàng, phần xanh còn lại chạy trong cùng chu kỳ 10s. | Mặc định 5.0s đèn vàng, chiếm 50% interval làm `green_elapsed < G_min` kích hoạt khóa cứng 20s. | **Chuẩn hóa Timing**: Đổi `yellow_seconds = 3.0s`, đồng bộ chu kỳ và cơ chế an toàn `minimum_green_seconds`. |
| **Đánh giá Đa Hạt Giống (Multi-seed)** | Đánh giá trên nhiều seed, báo cáo $\text{Mean} \pm \text{Std}$ để tránh may rủi ngẫu nhiên. | Chỉ hỗ trợ 1 seed đơn lẻ. | **Hỗ trợ Multi-Seed toàn diện**: Cờ `--seeds 0,1,2` tự động tính và xuất bảng thống kê $\text{Mean} \pm \text{Std}$. |

---

## 2. Chi tiết các Thay đổi Mã nguồn

### A. Tầng Môi trường & Đo lường Chỉ số (`sumo_env.py`, `observation.py`, `metrics.py`)
- [`observation.py`](file:///c:/Users/dotru/HMNC/LibSignal/src/traffic_control/core/observation.py):
  - Bổ sung `lane_halting_count` (xe dừng chờ) và `lane_waiting_time` vào [`IntersectionObservation`](file:///c:/Users/dotru/HMNC/LibSignal/src/traffic_control/core/observation.py#L9).
  - Bổ sung `penalized_travel_time`, `average_delay`, `total_time_loss` vào [`TrafficSnapshot`](file:///c:/Users/dotru/HMNC/LibSignal/src/traffic_control/core/observation.py#L31).
- [`metrics.py`](file:///c:/Users/dotru/HMNC/LibSignal/src/traffic_control/core/metrics.py):
  - Mở rộng [`EvaluationMetrics`](file:///c:/Users/dotru/HMNC/LibSignal/src/traffic_control/core/metrics.py#L14) với `penalized_travel_time_s`, `average_delay_s`, `total_time_loss_s`.
  - Cập nhật [`MetricsCollector`](file:///c:/Users/dotru/HMNC/LibSignal/src/traffic_control/core/metrics.py#L42) ghi nhận chi tiết từng bước quyết định.
- [`sumo_env.py`](file:///c:/Users/dotru/HMNC/LibSignal/src/traffic_control/sumo_env.py):
  - Theo dõi `_active_time_losses` và `_completed_time_losses` từ TraCI.
  - Thu thập `getLastStepHaltingNumber` trong [`observe()`](file:///c:/Users/dotru/HMNC/LibSignal/src/traffic_control/sumo_env.py#L202).
  - Tính toán Penalized Travel Time trên toàn bộ xe xuất phát trong [`snapshot()`](file:///c:/Users/dotru/HMNC/LibSignal/src/traffic_control/sumo_env.py#L279).
  - Đổi giá trị mặc định của `yellow_seconds` thành `3.0s`.

### B. Tầng Thuật toán (`controllers/`)
- [`base.py`](file:///c:/Users/dotru/HMNC/LibSignal/src/traffic_control/controllers/base.py):
  - Khử trùng lặp làn trong [`calculate_phase_pressures`](file:///c:/Users/dotru/HMNC/LibSignal/src/traffic_control/controllers/base.py#L66) (`unique_in_lanes`, `unique_out_lanes`).
  - Hỗ trợ tham số `use_halting=True` để đo áp lực theo hàng đợi xe dừng chờ thực tế.
- [`max_pressure.py`](file:///c:/Users/dotru/HMNC/LibSignal/src/traffic_control/controllers/max_pressure.py):
  - Tích hợp `use_halting=True` để đưa Max-Pressure về đúng nguyên lý Varaiya (2013) & RESCO.
- [`fixed_time.py`](file:///c:/Users/dotru/HMNC/LibSignal/src/traffic_control/controllers/fixed_time.py):
  - Bổ sung phương thức [`get_phase_duration`](file:///c:/Users/dotru/HMNC/LibSignal/src/traffic_control/controllers/fixed_time.py#L32) hỗ trợ chia thời gian xanh tỷ lệ theo số làn vào (`proportional_splits`) hoặc theo danh sách tùy biến (`phase_splits`).
- [`q_learning.py`](file:///c:/Users/dotru/HMNC/LibSignal/src/traffic_control/controllers/q_learning.py):
  - Tái cấu trúc thành **Decentralized Independent Q-Learning (IDQL)**: [`get_tls_table(tls_id)`](file:///c:/Users/dotru/HMNC/LibSignal/src/traffic_control/controllers/q_learning.py#L88) bảo đảm tính độc lập giữa các ngã tư, không làm đè dữ liệu trạng thái khi chạy mạng lưới nhiều nút giao.
  - Hỗ trợ 3 hàm phần thưởng chuẩn hóa: `"queue"` (hàng đợi dừng), `"delay"` (thời gian chờ), `"pressure"` (áp lực).
  - Duy trì thuộc tính `q_table` để bảo đảm tính tương thích ngược 100% với các mã kiểm thử cũ.

### C. Tầng CLI & Benchmark (`run.py`, `gui.py`, `experiment.py`)
- [`run.py`](file:///c:/Users/dotru/HMNC/LibSignal/run.py):
  - Bổ sung cờ `--seeds` (chạy đa hạt giống), `--proportional-splits` (Fixed-Time Webster), `--reward-type` (Q-Learning).
  - Tích hợp hàm [`aggregate_multi_seed_results`](file:///c:/Users/dotru/HMNC/LibSignal/run.py#L210) và [`print_multi_seed_summary`](file:///c:/Users/dotru/HMNC/LibSignal/run.py#L265) in bảng $\text{Mean} \pm \text{Std}$ và xuất file `multi_seed_summary.csv/json`.
- [`gui.py`](file:///c:/Users/dotru/HMNC/LibSignal/gui.py):
  - Mở rộng bảng kết quả đồ họa (Treeview) hiển thị trực tiếp 2 cột: `Penalized TT (s)` và `Độ trễ TB (s)`.

---

## 3. Kết Quả Xác Minh & Kiểm Thử Thực Tế

### A. Kiểm thử Tự động (Unit Tests)
Chạy toàn bộ test suite:
```powershell
python -m unittest discover tests -v
```
**Kết quả**: `21/21 tests passed` (100% thành công).

### B. Kiểm chuẩn Thực nghiệm Đơn Hạt Giống (Cologne 1 - 300s)
Lệnh chạy: `python run.py -c all -s 300`

| Thuật toán | Thời gian đi (s) | Penalized TT (s) | Độ trễ TB (s) | Hàng đợi (xe) | Thông lượng | Tỷ lệ xong | Đổi pha |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Max-Pressure** | **36.96** | **33.25** | **14.57** | **3.97** | **151** | **79.1%** | 14 |
| **Q-Learning** | 80.60 | 68.06 | 49.84 | 23.00 | 114 | 65.5% | 13 |
| **Fixed-Time** | 88.41 | 75.16 | 58.32 | 30.00 | 103 | 56.9% | 7 |

### C. Kiểm chuẩn Đa Hạt Giống Khoa học (Multi-Seed: Seeds = 0, 1)
Lệnh chạy: `python run.py -c all --seeds 0,1 -s 150`

```text
=== BÁO CÁO KIỂM CHUẨN ĐA HẠT GIỐNG (MULTI-SEED BENCHMARK: Mean ± Std) ===
Thuật toán     | Penalized TT (s)     | Thời gian đi (s)     | Độ trễ TB (s)      | Hàng đợi (xe)    | Thông lượng     | Tỷ lệ xong     
----------------------------------------------------------------------------------------------------------------------------------------
Fixed-Time     |         61.41 ± 0.35 |         47.45 ± 0.37 |       49.40 ± 0.42 |     21.44 ± 0.23 |      17.0 ± 0.0 |    24.6% ± 0.0%
Max-Pressure   |         31.18 ± 3.06 |         34.24 ± 3.05 |       14.98 ± 2.85 |      3.06 ± 0.94 |      61.0 ± 1.4 |    79.7% ± 1.1%
Q-Learning     |        54.02 ± 14.73 |         38.11 ± 5.18 |      41.39 ± 16.43 |     17.04 ± 8.25 |     25.0 ± 19.8 |   33.4% ± 24.4%
```

> [!IMPORTANT]
> **Chứng minh tác dụng chống Survival Bias**:
> Khi Q-Learning ở Seed 1 gặp bất lợi dẫn đến tỷ lệ hoàn thành thấp (16.2%), thời gian đi của vài xe thoát ra chỉ là 34.45s (ngụy tạo thành tích). Tuy nhiên, chỉ số **Penalized TT đã nhảy vọt lên 64.44s** và **Độ trễ TB là 53.01s**, vạch trần ngay lập tức hiện tượng kẹt xe mà các metric cũ không thể hiện được!

### D. Kiểm tra Fixed-Time với Proportional Green Splits
- Chạy mặc định 30s/pha: Thông lượng = 17 xe (24.6%), Thời gian đi = 47.18s.
- Bật `--proportional-splits` (chia thời gian xanh theo tỷ lệ số làn): Thông lượng tăng lên **21 xe (30.4%)**, Thời gian đi giảm xuống **44.90s**. Phản ánh đúng bản chất kỹ thuật giao thông của Fixed-Time!
