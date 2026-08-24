# Báo cáo kết quả tuần 1

## 1. Mục tiêu

Tuần 1 chỉ thực hiện hai baseline cơ bản:

- Fixed-Time (FT).
- MaxPressure (MP).

Mục tiêu là xác nhận LibSignal và SUMO hoạt động, tạo quy trình chạy công bằng, thu metric và kiểm tra khả năng tái lập. Tuần này không thiết kế AWPC và không chạy DQN hoặc PressLight.

## 2. Môi trường thực nghiệm

| Thuộc tính | Giá trị |
|---|---|
| LibSignal | commit `e0c113e92668c19410208434129ca87d598beece` |
| Simulator | SUMO 1.27.1 |
| Giao diện | TraCI |
| Python | 3.12.13 |
| Thiết bị | CPU |
| Network | `sumo1x1` |
| Thời gian đánh giá | 3600 bước, interval 1 giây |
| Action interval | 10 giây |
| Seed | 1, 42, 2026 |
| Fixed-Time | `t_fixed = 30` giây |
| MaxPressure | `t_min = 10` giây |

Hai phương pháp sử dụng cùng network, traffic flow, thời lượng, seed, metric và phiên bản mã nguồn.

## 3. Kết quả từng lượt chạy

| Phương pháp | Seed | Travel time (s) | Waiting time (s) | Queue | Delay | Throughput | Completion |
|---|---:|---:|---:|---:|---:|---:|---:|
| Fixed-Time | 1 | 76.40 | 32.68 | 25.15 | 3.89 | 1983 | 98.51% |
| Fixed-Time | 42 | 75.95 | 32.44 | 24.97 | 3.85 | 1984 | 98.51% |
| Fixed-Time | 2026 | 76.80 | 32.94 | 25.05 | 3.91 | 1981 | 98.36% |
| MaxPressure | 1 | 35.78 | 4.80 | 3.42 | 1.98 | 1999 | 99.21% |
| MaxPressure | 42 | 35.82 | 4.68 | 3.25 | 1.88 | 1999 | 99.21% |
| MaxPressure | 2026 | 36.17 | 5.05 | 3.46 | 1.96 | 1999 | 99.26% |

Waiting time trong bảng là trung bình `custom_wait_s` của các chuyến đã hoàn thành. Queue và delay lấy từ metric tổng cuối lượt chạy của LibSignal.

## 4. Kết quả tổng hợp

Giá trị trình bày dưới dạng trung bình ± độ lệch chuẩn của ba seed.

| Metric | Fixed-Time | MaxPressure | Thay đổi của MP |
|---|---:|---:|---:|
| Average travel time | 76.39 ± 0.43 s | 35.92 ± 0.21 s | giảm 52.97% |
| Average waiting time | 32.69 ± 0.25 s | 4.84 ± 0.19 s | giảm 85.18% |
| Average queue length | 25.06 ± 0.09 | 3.38 ± 0.11 | giảm 86.52% |
| Average delay | 3.89 ± 0.03 | 1.94 ± 0.06 | giảm 50.09% |
| Throughput | 1982.67 ± 1.53 | 1999.00 ± 0.00 | tăng 0.82% |
| Completion rate | 98.46% | 99.22% | tăng 0.76 điểm phần trăm |

## 5. Nhận xét

Trên kịch bản `sumo1x1` đã chạy, MaxPressure tốt hơn Fixed-Time ở cả bốn nhóm chỉ số chính. Chênh lệch lớn nhất nằm ở waiting time và queue length. Điều này phù hợp với cơ chế của MP: pha đèn được chọn từ trạng thái số xe trên làn vào và làn ra, trong khi FT chuyển pha theo lịch cố định.

Kết quả giữa ba seed khá ổn định. Độ lệch chuẩn thấp cho thấy kết quả tuần 1 không phụ thuộc mạnh vào một seed riêng lẻ trong kịch bản này.

Tuy nhiên, chưa thể kết luận MaxPressure luôn tốt hơn trong mọi điều kiện. Bộ thử nghiệm hiện chỉ có:

- một mạng một nút giao;
- một traffic flow;
- ba seed;
- một bộ tham số FT và MP.

## 6. Công việc đã hoàn thành

- Cài và kiểm tra môi trường LibSignal–SUMO trên Windows.
- Xác định cấu trúc `run.py`, config, agent, world, trainer và metric.
- Chạy thành công FT và MP trên cùng mạng.
- Chạy đủ ba seed cho mỗi phương pháp.
- Lưu dữ liệu theo từng xe, metadata và log.
- Tạo script chạy lại và script tổng hợp tự động.
- Tạo bảng, biểu đồ và báo cáo kết quả.

## 7. Vấn đề kỹ thuật đã xử lý

- Dùng `--interface traci` vì môi trường Windows không có module `libsumo`.
- Đặt `PYTHONHASHSEED=0` trước khi chạy để tiến trình Windows không tự khởi động lại ngoài sự kiểm soát của script.
- Cảnh báo thiếu `torch_scatter` không ảnh hưởng, vì dependency này chỉ cần cho CoLight.
- Dòng SUMO `peer shutdown` xuất hiện sau bước cuối khi LibSignal đóng kết nối; metadata, CSV và log vẫn được ghi đầy đủ nên lượt chạy được xác nhận thành công bằng sự tồn tại của `new_metrics_meta.json`.

## 8. Đề xuất tuần 2

Giữ nguyên FT và MP, sau đó mở rộng kiểm thử theo thứ tự:

1. Tạo ba mức traffic flow: Low, Medium, High.
2. Chạy cùng danh sách seed trên từng mức lưu lượng.
3. Kiểm tra ảnh hưởng của `t_fixed` và `t_min` bằng một số giá trị định trước.
4. Chỉ sau khi pipeline FT–MP ổn định trên nhiều lưu lượng mới xem xét thêm baseline khác.
