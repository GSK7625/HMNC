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
pressure(i, j) = N(i) - N(j)
```

Với pha `p`:

```text
P(p) = sum(N(i) - N(j)) cho mọi chuyển động thuộc p
```

Sau khi pha hiện tại đủ 10 giây xanh:

```text
selected_phase = argmax P(p)
```

MP ưu tiên hướng có nhiều xe ở đầu vào và ít xe ở đầu ra. Nó thích nghi theo
trạng thái nhưng không phải học máy.

## Pha vàng

Controller chỉ chọn pha xanh. `SumoEnvironment` tự tạo trạng thái vàng khi một
chuyển động đang xanh phải đóng lại. Trong 5 giây vàng, môi trường không nhận
thêm chuyển pha. Sau đó pha xanh mục tiêu được bật và bộ đếm xanh trở về 0.

## Metric

- Average travel time: thời gian của xe đã hoàn thành hành trình.
- Average queue: số xe đang dừng trên các làn vào.
- Average current waiting: thời gian chờ tích lũy của xe đang ở trong mạng.
- Throughput: số xe hoàn thành hành trình.
- Phase switches: số lần action thay đổi giữa hai mốc quyết định.

## Code cần hiểu

1. `controllers.py`: toàn bộ công thức FT/MP.
2. `sumo_env.py::_load_signals`: đọc pha và lane movement từ map.
3. `sumo_env.py::step`: xử lý xanh-vàng-xanh.
4. `experiment.py::run_experiment`: vòng lặp quan sát-quyết định-mô phỏng.

Nền tảng lý thuyết MP: [Varaiya (2013)](https://doi.org/10.1016/j.trc.2013.08.014).
TraCI: [SUMO traffic-light tutorial](https://sumo.dlr.de/docs/Tutorials/TraCI4Traffic_Lights.html).
