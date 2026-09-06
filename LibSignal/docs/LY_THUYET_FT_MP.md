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

FT thực hiện tuần tự theo chu kỳ thời gian đã ấn định:

```text
target_green = max(0, required_duration - yellow_seconds)
if green_elapsed < target_green:
    giữ pha hiện tại
else:
    chuyển sang (current_phase + 1) mod số pha
```

- **Đồng bộ nhịp thời gian & Triệt tiêu trôi do đèn vàng**:
  - Thời gian mỗi pha (`duration`) luôn được cấu hình hoặc làm tròn là **bội số chính xác của chu kỳ hành động** (`action_interval`, ví dụ 10s).
  - Khấu trừ thời gian đèn vàng (`yellow_seconds`, mặc định 3.0s theo chuẩn RESCO/SUMO) vào ngưỡng kích hoạt: `target_green = required_duration - yellow_seconds`.
  - Tại mốc ranh giới bước mô phỏng (ví dụ sau đúng 30s), thời gian xanh thực tế đạt $30 - 3 = 27s$, bộ điều khiển chuyển pha ngay lập tức mà không bị trôi trễ thêm một khoảng `action_interval` (10s) vô ích.

## Max-Pressure

Thuật toán Max-Pressure chuẩn hóa (Varaiya 2013 / RESCO):

1. **Đồng nhất một đại lượng (Dimensional Consistency)**:
   - Cả làn vào và làn thoát đều sử dụng đồng nhất một đại lượng $Q$:
     - Ở chế độ `standard`: $Q$ là số lượng xe (`lane_vehicle_count`).
     - Ở chế độ `density`: $Q$ là mật độ xe (`lane_density` = số xe / chiều dài làn).

2. **Nhân tỷ lệ phân chia luồng rẽ (Turning Split Ratio)**:
   - Nếu làn vào $u$ rẽ ra nhiều nhánh thoát $v \in Out(u)$ (ví dụ: vừa rẽ trái, vừa đi thẳng, vừa rẽ phải với số nhánh $k = |Out(u)|$):
     - Mỗi nhánh thoát được nhân với tỷ lệ rẽ tương ứng $r(u, v) = \frac{1}{k}$ (hoặc tỷ lệ phân chia thực tế).
     - Áp lực hạ lưu ứng với làn vào $u$ là:
       $$Q_{out}(u) = \sum_{v \in Out(u)} r(u, v) \cdot Q(v)$$
     - Áp lực riêng của làn vào $u$:
       $$P(u) = Q(u) - Q_{out}(u) = Q(u) - \sum_{v \in Out(u)} r(u, v) \cdot Q(v)$$
   - Khử triệt để hiện tượng trừ trùng lặp hạ lưu (double/triple-counting) khi một làn vào phân nhánh.

3. **Áp lực của pha $p$**:
   $$P(p) = \sum_{u \in In(p)} P(u)$$
   (Nếu ở chế độ `normalized`, chia cho tổng số làn vào duy nhất của pha: $P(p) / |In(p)|$).

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
