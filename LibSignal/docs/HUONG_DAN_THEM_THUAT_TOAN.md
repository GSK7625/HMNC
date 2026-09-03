# Hướng Dẫn Thêm Thuật Toán Điều Khiển Đèn Giao Thông Mới

Hệ thống được thiết kế theo nguyên lý **Open-Closed Principle (OCP)** và kiến trúc **Plug-and-Play (Controller Registry)**. Bạn có thể thêm bất kỳ thuật toán điều khiển mới nào mà **hoàn toàn không cần sửa code cũ** (không sửa `run.py`, không sửa `__init__.py`, không sửa các controller khác).

---

## 3 Bước Để Thêm Thuật Toán Mới

### Bước 1: Tạo file thuật toán trong thư mục `src/traffic_control/controllers/`

Ví dụ tạo file: `src/traffic_control/controllers/my_algorithm.py`

### Bước 2: Kế thừa `BaseController` và gắn decorator `@register_controller`

```python
from src.traffic_control.controllers.base import BaseController
from src.traffic_control.controllers.registry import register_controller


@register_controller(
    name="my_algorithm",          # Tên định danh gọi từ CLI (-c my_algorithm)
    aliases=["my_algo", "ma"],    # Các tên viết tắt gọi nhanh (-c ma)
    display_name="My Algorithm",  # Tên hiển thị trên bảng so sánh
    description="Mô tả thuật toán của bạn"
)
class MyAlgorithmController(BaseController):
    """Mô tả chi tiết nguyên lý thuật toán."""

    def __init__(self, minimum_green_seconds: float = 10.0, my_param: float = 1.5, **kwargs):
        # BaseController tự động lưu minimum_green_seconds để kích hoạt cơ chế bảo vệ an toàn
        super().__init__(minimum_green_seconds=minimum_green_seconds, **kwargs)
        self.my_param = my_param

    def decide_phase(self, observation) -> int:
        """Logic cốt lõi của thuật toán: Quyết định chọn pha đèn nào tiếp theo (0, 1, ...).

        Dữ liệu observation cung cấp:
        - observation.current_phase: Pha đèn hiện tại (int)
        - observation.green_elapsed: Số giây đèn xanh hiện tại đã sáng (float)
        - observation.lane_vehicle_count: Số xe trên từng làn {'lane_id': count}
        - observation.phase_movements: Danh sách luồng di chuyển cho mỗi pha
        """
        # Ví dụ: tính toán và trả về chỉ số pha đèn tiếp theo
        num_phases = len(observation.phase_movements)
        best_phase = 0  # <--- Thay bằng logic tính toán của bạn ở đây
        return best_phase
```

### Bước 3: Chạy ngay lập tức!

Chỉ cần lưu file lại, hệ thống sẽ tự động quét và nạp thuật toán của bạn:

1. **Xem trợ giúp CLI**:
   ```powershell
   python run.py --help
   ```
   *Thuật toán `my_algorithm` và các alias `ma` sẽ tự động xuất hiện trong danh sách lựa chọn!*

2. **Chạy thử nghiệm thuật toán của bạn**:
   ```powershell
   python run.py -c my_algorithm -s 60
   # hoặc dùng alias:
   python run.py -c ma -s 60
   ```

3. **Truyền tham số riêng cho thuật toán qua CLI**:
   ```powershell
   python run.py -c ma --controller-args "my_param=2.0"
   ```

4. **So sánh trực tiếp thuật toán của bạn với các baseline**:
   ```powershell
   python run.py -c all --controllers ft,mp,ql,ma -s 60
   ```

---

## Tính An Toàn & Chuẩn Hóa So Sánh

### 1. Cơ chế Bảo Vệ An Toàn Giao Thông Tự Động (Safety Guard)
Trong thực tế và mô phỏng giao thông, việc chuyển đổi đèn xanh quá nhanh (chưa đủ thời gian xanh tối thiểu $G_{min}$) là vi phạm an toàn kỹ thuật và tạo ra so sánh thiếu công bằng.

`BaseController` tích hợp sẵn cơ chế **Safety Guard**:
- Khi thuật toán muốn đổi sang pha khác, `BaseController` tự động kiểm tra nếu `observation.green_elapsed < minimum_green_seconds` thì **bắt buộc giữ nguyên pha hiện tại**.
- Bạn chỉ cần tập trung viết logic trong hàm `decide_phase(observation)` mà không lo thuật toán vi phạm thời gian xanh tối thiểu.

### 2. Thống Nhất Tham Số Môi Trường (Benchmark Fairness)
Để so sánh an toàn và công bằng, lệnh so sánh `python run.py -c all` đảm bảo 100% các thuật toán chạy trên cùng một đối tượng cấu hình `BenchmarkConfig`:
- Cùng kịch bản bản đồ (`--scenario`)
- Cùng thời gian mô phỏng (`--steps`)
- Cùng chu kỳ ra quyết định (`--action-interval`)
- Cùng hạt giống ngẫu nhiên (`--seed`)
- Cùng thời gian đèn vàng dọn đường (`--yellow-seconds`)
- Cùng ràng buộc thời gian xanh tối thiểu (`--minimum-green`)

### 3. Thống Nhất Chỉ Số Đo Lường (Standardized Metrics)
Mọi lượt chạy đều xuất ra bảng chuẩn hóa với các chỉ số:
- **Thời gian đi trung bình (Average Travel Time - s)**: Thời gian di chuyển của các xe đã hoàn thành hành trình.
- **Hàng đợi trung bình (Average Queue - xe)**: Số xe dừng chờ trung bình trên mỗi nút giao.
- **Thời gian chờ trung bình (Average Waiting Time - s)**: Thời gian chờ tích lũy của các xe đang di chuyển.
- **Thông lượng (Throughput - xe)**: Số lượng xe đã về đích thành công.
- **Tỷ lệ hoàn thành (Completion Rate - %)**: Thông lượng / Tổng số xe xuất phát.
- **Số lần đổi pha (Phase Switches)**: Đo lường độ ổn định của hệ thống đèn (hạn chế đổi pha lãng phí thời gian đèn vàng).
