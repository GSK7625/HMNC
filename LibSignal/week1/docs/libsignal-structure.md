# Cấu trúc LibSignal cần biết trong tuần 1

## Luồng chạy

```text
run.py
  -> đọc tham số CLI và YAML
  -> tạo TSCTrainer
  -> tạo SUMO World
  -> tạo FixedTimeAgent hoặc MaxPressureAgent
  -> tạo TSCEnv và Metrics
  -> chạy 3600 bước đánh giá
  -> ghi log, new_metrics.csv và new_metrics_meta.json
```

## Các vị trí quan trọng

| Thành phần | Vị trí | Vai trò |
|---|---|---|
| Điểm vào | `run.py` | Nhận `agent`, `world`, `network`, `seed`, `prefix`, `interface` |
| Cấu hình chung | `configs/tsc/base.yml` | Số bước, action interval, metric, thư mục đầu ra |
| Cấu hình FT | `configs/tsc/fixedtime.yml` | `t_fixed = 30`, một episode, chỉ test |
| Cấu hình MP | `configs/tsc/maxpressure.yml` | `t_min = 10`, chỉ test |
| Mạng 1x1 | `configs/sim/sumo1x1.cfg` | Trỏ tới mạng và luồng Cologne một nút giao |
| Fixed-Time | `agent/fixedtime.py` | Giữ pha đủ `t_fixed`, sau đó chuyển tuần tự |
| MaxPressure | `agent/maxpressure.py` | Chọn pha có tổng chênh lệch xe vào-ra lớn nhất |
| SUMO adapter | `world/world_sumo.py` | Giao tiếp SUMO, trạng thái làn xe, throughput và trip records |
| Trainer | `trainer/tsc_trainer.py` | Chạy đánh giá và ghi metric |
| Metrics | `common/metrics.py` | Reward, queue, delay, throughput và travel time |

## Fixed-Time

Với mỗi lần ra quyết định:

1. Nếu thời gian của pha hiện tại nhỏ hơn 30 giây, giữ nguyên pha.
2. Nếu đã đủ 30 giây, chuyển sang pha tiếp theo theo thứ tự vòng tròn.

FT không đọc tình trạng ùn tắc để quyết định pha.

## MaxPressure

MP giữ một pha tối thiểu 10 giây. Sau đó, với từng pha khả dụng, nó tính:

```text
pressure(phase) = tổng [số xe làn vào - số xe làn ra]
```

Pha có pressure lớn nhất được chọn. Vì vậy MP thích nghi với trạng thái xe hiện tại nhưng không huấn luyện mô hình.

## Đầu ra

Mỗi lượt chạy nằm tại:

```text
data/output_data/tsc/sumo_<agent>/sumo1x1/week1_seed_<seed>/logger/
```

Trong đó:

- `*.log`: metric tổng cuối lượt chạy, gồm queue và delay.
- `new_metrics.csv`: dữ liệu theo từng xe.
- `new_metrics_meta.json`: travel time, throughput, completion rate, seed và metadata.
