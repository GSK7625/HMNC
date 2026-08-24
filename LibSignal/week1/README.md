# Bộ công việc tuần 1 - LibSignal Fixed-Time và MaxPressure

Bộ bàn giao này giúp nhóm hoàn tất phạm vi tuần 1: cài đặt môi trường, chạy hai baseline cổ điển trên mạng SUMO `sumo1x1`, lặp lại với nhiều seed, tổng hợp metric và lưu bằng chứng tái lập.

## Phạm vi

- Có: Fixed-Time, MaxPressure, SUMO `1x1`, seed `1`, `42`, `2026`.
- Không có: AWPC, DQN, PressLight, huấn luyện mô hình hoặc mạng lớn.

## Kết quả đã kiểm thử

Môi trường kiểm thử:

- LibSignal fork được duy trì: commit `e0c113e92668c19410208434129ca87d598beece`.
- Python `3.12.13`.
- SUMO `1.27.1`.
- Windows, giao diện TraCI, CPU.
- Network: `sumo1x1` (dữ liệu Cologne một nút giao).
- Mỗi lượt đánh giá: `3600` bước mô phỏng; `action_interval = 10` giây.
- Fixed-Time: `t_fixed = 30` giây.
- MaxPressure: `t_min = 10` giây.

Kết quả tổng hợp nằm trong:

- `results/summary.csv`: từng phương pháp và từng seed.
- `results/aggregate.csv`: trung bình, độ lệch chuẩn và số lần chạy.
- `results/ft_vs_mp.png`: biểu đồ so sánh.
- `docs/week-1-report.md`: báo cáo và diễn giải kết quả.

## Vị trí dự án

Bộ tuần 1 được đặt trong thư mục `week1` của repository LibSignal:

```text
HMNC/
|-- Đề Xuất Đề Tài Nhóm 9.docx
`-- LibSignal/
    |-- run.py
    |-- .venv/
    `-- week1/
```

Các lệnh dưới đây được chạy từ thư mục gốc `LibSignal`.

## Chạy lại trên Windows

Yêu cầu trước:

1. Git.
2. Python 3.10 trở lên.
3. SUMO đã được cài đặt; biến `SUMO_HOME` trỏ tới thư mục cài SUMO.

Thiết lập mã nguồn và môi trường:

```powershell
powershell -ExecutionPolicy Bypass -File .\week1\scripts\setup_windows.ps1
```

Chạy FT và MP với ba seed:

```powershell
powershell -ExecutionPolicy Bypass -File .\week1\scripts\run_ft_mp.ps1 `
  -RepoPath . `
  -Seeds 1,42,2026
```

Tổng hợp kết quả:

```powershell
.\.venv\Scripts\python.exe .\week1\scripts\summarize_results.py `
  --repo . `
  --output .\week1\results
```

## Quy tắc công bằng

Hai baseline phải dùng cùng:

- network và traffic flow;
- số bước mô phỏng;
- danh sách seed;
- giao diện SUMO;
- metric và cách tổng hợp;
- commit LibSignal.

Không chỉnh riêng traffic flow hoặc thời lượng mô phỏng để làm một phương pháp trông tốt hơn.

## Cấu trúc bàn giao

```text
libsignal-week1/
|-- README.md
|-- requirements-classical.txt
|-- scripts/
|   |-- setup_windows.ps1
|   |-- run_ft_mp.ps1
|   `-- summarize_results.py
|-- docs/
|   |-- libsignal-structure.md
|   `-- week-1-report.md
`-- results/
    |-- summary.csv
    |-- aggregate.csv
    |-- ft_vs_mp.png
    `-- raw/
```

## Tiêu chí nghiệm thu

- [x] Fixed-Time chạy thành công trên `sumo1x1`.
- [x] MaxPressure chạy thành công trên cùng cấu hình.
- [x] Có ít nhất ba seed cho mỗi phương pháp.
- [x] Có dữ liệu theo từng xe, metadata và log cho từng lượt chạy.
- [x] Có bảng tổng hợp và biểu đồ.
- [x] Có script thiết lập, chạy và tổng hợp lại.
- [x] Có tài liệu cấu trúc LibSignal và báo cáo tuần 1.

Lưu ý: cảnh báo thiếu `torch_scatter` có thể xuất hiện khi khởi động. Nó thuộc CoLight và không ảnh hưởng tới Fixed-Time hoặc MaxPressure.
