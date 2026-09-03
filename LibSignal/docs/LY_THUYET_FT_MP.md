# Lý thuyết FT và MP

## Luồng chung

Mỗi 10 giây, chương trình đọc số xe trên các làn, controller chọn một pha xanh,
môi trường xử lý pha vàng rồi yêu cầu SUMO chạy tiếp.

```text
SUMO -> IntersectionObservation -> Controller -> phase index -> SUMO
```

`IntersectionObservation` gồm pha hiện tại, số giây xanh, số xe trên làn và
danh sách chuyển động được phép của từng pha.

## Fixed-Time

FT không sử dụng số xe để quyết định:

```text
if green_elapsed < 30 giây:
    giữ pha hiện tại
else:
    chuyển sang (current_phase + 1) mod số pha
```

Ưu điểm: đơn giản, xác định, không cần cảm biến. Hạn chế: không thích nghi khi
lưu lượng lệch hướng hoặc thay đổi.

## Max-Pressure

Với chuyển động từ làn vào `i` sang làn ra `j`:

```text
pressure(i, j) = N_in(i) - N_out(j)
```

- `N_in(i)`: Số xe dừng chờ (halting queue) ở làn vào ngã tư cần giải tỏa.
- `N_out(j)`: Tổng số xe trên làn thoát (downstream) để đo lường mật độ/nguy cơ tắc nghẽn hạ lưu.

Với pha `p` (sau khi khử trùng lặp làn):

```text
P(p) = sum(N_in) - sum(N_out) cho mọi làn thuộc pha p
```

Sau khi pha hiện tại đủ thời gian xanh tối thiểu an toàn (`minimum_green_seconds`):

1. **Starvation Guard**: Nếu pha hiện tại đã xanh quá `max_green_seconds` (nếu cấu hình), ưu tiên nhường cho pha khác có áp lực lớn nhất.
2. **Idle Protection**: Nếu không có pha nào có áp lực dương ($P(p) \le 0$, ngã tư vắng xe), giữ nguyên pha hiện tại để tránh kích hoạt đèn vàng lãng phí.
3. **Tie-breaking Hysteresis**: Nếu pha hiện tại cũng đạt áp lực tối đa, giữ nguyên pha hiện tại để tối ưu thông lượng, tránh chuyển pha liên tục.
4. **Argmax**: Bật pha có áp lực lớn nhất: `selected_phase = argmax P(p)`.

## Pha vàng

Controller chỉ chọn pha xanh. `SumoEnvironment` tự tạo trạng thái vàng khi một
chuyển động đang xanh phải đóng lại. Trong thời gian đèn vàng (mặc định 3.0 giây theo chuẩn RESCO/SUMO, có thể tùy biến qua `yellow_seconds`), môi trường không nhận
thêm chuyển pha. Sau đó pha xanh mục tiêu được bật và bộ đếm xanh trở về 0.

## Metric

- Average travel time: thời gian của xe đã hoàn thành hành trình.
- Average queue: số xe đang dừng trên các làn vào.
- Average current waiting: thời gian chờ tích lũy của xe đang ở trong mạng.
- Throughput: số xe hoàn thành hành trình.
- Phase switches: số lần action thay đổi giữa hai mốc quyết định.

## Code cần hiểu

1. `controllers/base.py`: base protocol và công thức tính $P(p)$.
2. `controllers/fixed_time.py`: toàn bộ thuật toán Fixed-Time.
3. `controllers/max_pressure.py`: toàn bộ thuật toán Max-Pressure.
4. `sumo_env.py::_load_signals`: đọc pha và lane movement từ map.
5. `sumo_env.py::step`: xử lý xanh-vàng-xanh.
6. `experiment.py::run_experiment`: vòng lặp quan sát-quyết định-mô phỏng.

Nền tảng lý thuyết MP: [Varaiya (2013)](https://doi.org/10.1016/j.trc.2013.08.014).
TraCI: [SUMO traffic-light tutorial](https://sumo.dlr.de/docs/Tutorials/TraCI4Traffic_Lights.html).
