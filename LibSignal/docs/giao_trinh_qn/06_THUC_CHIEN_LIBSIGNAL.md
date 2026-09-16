# PHẦN 6: THỰC CHIẾN & MỔ XẺ MÃ NGUỒN LIBSIGNAL

---

## 1. Bản đồ Ánh xạ Lý thuyết ➔ Mã nguồn Thực tế

Mọi kiến thức lý thuyết về **Q-Network**, **DQN** và **Double DQN** mà chúng ta đã học ở các phần trước đều được hiện thực hóa một cách mạch lạc, chuẩn mực trong hai file mã nguồn chính của dự án:
- [traffic_control/controllers/q_learning.py](file:///c:/Users/dotru/HMNC/LibSignal/src/traffic_control/controllers/q_learning.py): Triển khai Tabular Q-Learning dạng bảng rời rạc.
- [traffic_control/controllers/dqn.py](file:///c:/Users/dotru/HMNC/LibSignal/src/traffic_control/controllers/dqn.py): Triển khai Deep Q-Network liên tục với PyTorch.

Dưới đây là bảng đối chiếu giữa khái niệm toán học và class / hàm tương ứng trong code:

| Khái niệm Toán học | Mã nguồn trong `dqn.py` | Vai trò và Nhiệm vụ |
| :--- | :--- | :--- |
| **Mạng nơ-ron xấp xỉ** $Q(s, a; \theta)$ | `class QNetwork(nn.Module)` | Mô hình MLP 3 tầng nhận vector trạng thái và xuất ra vector Q-value |
| **Bộ nhớ đệm** $\mathcal{D}$ | `class ReplayBuffer` | Lưu trữ bộ năm `(state, action, reward, next_state, done)` bằng `collections.deque` |
| **Online & Target Network** | `class DQNAgent` | Quản lý `self.q_network` ($\theta$) và `self.target_network` ($\theta^-$) |
| **Mục tiêu Double DQN** | `DQNAgent.train_step()` | `next_q = target_net.gather(1, online_net.argmax())` |
| **Cập nhật Trọng số SGD** | `DQNAgent.train_step()` | Tối ưu hóa bằng `torch.optim.Adam`, tính Smooth L1 Loss và Clip Gradient |
| **Bộ điều khiển ngã tư** | `class DQNController` | Kết nối dữ liệu quan sát từ môi trường SUMO và đưa ra quyết định đổi đèn |

---

## 2. Kỹ thuật Biến đổi Trạng thái Giao thông thành Vector Số thực

Một mạng nơ-ron không thể trực tiếp hiểu được hình ảnh xe cộ hay các làn đường SUMO nếu không được mã hóa thành một **Vector Quan sát Liên tục (Continuous State Vector)**.

Trong hàm `_extract_state_vector()` của `dqn.py`, ngã tư được chuyển hóa thành một vector toán học $\mathbf{s} \in \mathbb{R}^d$ bao gồm các thành phần sau:

```text
               Vector Quan sát s của Ngã tư
┌─────────────────────────────────────────────────────────────┐
│  Với mỗi pha đèn p = 0, 1, ..., P-1:                         │
│  1. Tỷ lệ hàng đợi xe dừng:      min(Q_p / 20.0, 1.0)       │
│  2. Tỷ lệ mật độ xe lưu thông:   min(V_p / 30.0, 1.0)       │
│  3. Thời gian chờ chuẩn hóa:     min(W_p / 120.0, 1.0)      │
│  4. Áp lực chênh lệch (Varaiya): tanh(P_p / 10.0)           │
│                                                             │
│  Thông tin toàn cục ngã tư:                                │
│  5. One-hot encoding của pha hiện tại: [0, 1, 0, ...]       │
│  6. Thời gian xanh đã trôi qua:   min(t_green / 60.0, 1.0)  │
└─────────────────────────────────────────────────────────────┘
```

### Tại sao cần phải chuẩn hóa (Normalization)?
- Các giá trị như thời gian chờ có thể lên tới $300\text{s}$, trong khi tỷ lệ hàng đợi chỉ từ $0$ đến $1$.
- Nếu không chuẩn hóa, các đặc trưng có giá trị số học lớn sẽ lấn át hoàn toàn gradient của mạng nơ-ron, khiến mạng khó hội tụ.
- Mọi giá trị đầu vào đều được ép về thang đo $[0, 1]$ hoặc $[-1, 1]$ (thông qua hàm $\tanh$).

---

## 3. Quy trình Ra Quyết định & Rào chắn An toàn (Safety Guard)

Trong giao thông thực tế, ta không thể đổi đèn tín hiệu liên tục từng giây vì sẽ gây tai nạn hoặc ùn ứ xe trong lòng nút giao.
Hệ thống tuân thủ chặt chẽ quy chuẩn quốc tế **RESCO**:

```python
def select_phase(self, observation: IntersectionObservation) -> int:
    # 1. RÀO CHẮN AN TOÀN (Safety Guard)
    # Nếu pha hiện tại chưa sáng đủ thời gian xanh tối thiểu G_min (10s):
    if observation.green_seconds < self.minimum_green_seconds:
        # Bắt buộc giữ nguyên pha hiện tại
        return observation.current_phase

    # 2. HỌC TĂNG CƯỜNG (Sau khi đã đủ G_min)
    state = self._extract_state_vector(observation)
    
    # 3. LỰA CHỌN THEO CHIẾN LƯỢC ε-GREEDY
    action = agent.select_action(state, epsilon=self.epsilon)
    return action
```

---

## 4. Hướng dẫn Chạy Huấn luyện & Đánh giá trên Terminal

Dự án đã tích hợp sẵn toàn bộ các lệnh CLI tiện lợi trong file [run.py](file:///c:/Users/dotru/HMNC/LibSignal/run.py).

### 4.1. Huấn luyện Tabular Q-Learning
Chạy huấn luyện thuật toán Q-Learning dạng bảng trên kịch bản ngã tư Cologne trong 50 episodes:
```powershell
python run.py --controller qlearning --scenario cologne1 --train --episodes 50
```
- Bảng Q sau khi học sẽ tự động được lưu tại: `checkpoints/q_table.json`.

---

### 4.2. Huấn luyện Deep Q-Network (DQN)
Chạy huấn luyện mạng nơ-ron sâu Double DQN trên GPU/CPU:
```powershell
python run.py --controller dqn --scenario cologne1 --train --episodes 50 --lr 0.001 --gamma 0.95
```
- Trọng số mạng sau khi tối ưu sẽ được lưu tại: `checkpoints/dqn_model.pt`.

---

### 4.3. Kiểm chuẩn So sánh (Benchmark) với Thuật toán Heuristic
Sau khi đã có mô hình được huấn luyện, bạn có thể chạy so sánh khoa học giữa **DQN**, **Max-Pressure (MP)** và **Fixed-Time (FT)**:
```powershell
python run.py --scenario cologne1 --controllers fixed_time max_pressure dqn --seeds 1 2 3
```

---

## 5. Đọc hiểu Đồ thị Huấn luyện & Tiêu chí Đánh giá

Khi mở giao diện Sleepy Chicken Dashboard (`python gui.py`) hoặc xem các biểu đồ xuất ra tại thư mục `results/`, bạn cần chú ý 3 đường cong quan trọng:

```text
    Hàm Mất mát (Loss)                      Tổng Phần thưởng (Reward)
   │                                       │
   │ ──╮                                   │             ╭─────────── (Tiệm cận 0)
   │    ╰──╮                               │       ╭─────╯
   │       ╰──────────────                 │ ──────╯
   │                       (Hội tụ)        │ (Bắt đầu âm sâu)
   └──────────────────────► Episode        └──────────────────────────► Episode
```

1. **Loss Curve (Đường cong Loss)**:
   - Ban đầu Loss có thể cao và trồi sụt do Agent đang khám phá ($\epsilon$ lớn).
   - Về sau, Loss phải giảm dần và dao động quanh một mức sàn ổn định.
2. **Reward Curve (Đường cong Phần thưởng)**:
   - Vì Reward được định nghĩa bằng số âm của hàng đợi xe ($r = -\sum \text{xe dừng}$), đường cong sẽ bắt đầu từ giá trị âm sâu (ví dụ: $-800$) và tăng dần hướng về $0$ (ví dụ: đạt $-50$).
   - Điều này chứng minh Agent đã học được cách giải tỏa ách tắc giao thông!
3. **Average Travel Time & Penalized Travel Time**:
   - Thời gian di chuyển trung bình của xe hoàn thành hành trình càng thấp càng tốt.
   - Chỉ số **Penalized Travel Time** (chuẩn RESCO) phạt nặng các xe bị bỏ đói kẹt lại trong mạng lưới, giúp đánh giá công tâm nhất chất lượng của bộ điều khiển.

---

## 6. Bảng Tra cứu Lỗi Thường gặp (Troubleshooting Guide)

| Hiện tượng | Nguyên nhân Khả dĩ | Cách Khắc phục |
| :--- | :--- | :--- |
| **Loss không giảm hoặc nổ NaN** | Learning rate $\alpha$ quá lớn hoặc dữ liệu có số âm/dương cực đoan | Giảm learning rate (`--lr 1e-4`), kiểm tra lại hàm chuẩn hóa đặc trưng, bật Huber Loss (`SmoothL1Loss`) |
| **Đèn chuyển pha liên tục sau mỗi 10s** | Reward phạt chuyển pha chưa đủ lớn hoặc thiếu cơ chế Tie-Breaking Hysteresis | Bổ sung `--switch-penalty 2.0` để phạt hành vi đổi pha không cần thiết |
| **Xe ở một nhánh bị chờ quá lâu (bỏ đói)** | Agent quá tập trung vào nhánh đông xe mà bỏ quên nhánh phụ | Bật tính năng phạt thời gian chờ tích lũy (`--reward-type delay`) hoặc kết hợp Starvation Guard |
| **Mô hình học tốt trên kịch bản A nhưng chạy tệ trên kịch bản B** | Số làn hoặc số pha đèn giữa hai bản đồ khác nhau (State Dimension Mismatch) | Sử dụng cơ chế tự động nhận diện chiều đặc trưng hoặc huấn luyện mô hình riêng cho từng kịch bản |

---

🎉 **Chúc mừng bạn đã hoàn thành trọn bộ 6 phần Giáo trình Thuật toán QN & DQN!**
Bây giờ bạn đã sẵn sàng tự tay chỉnh sửa, phát triển các kiến trúc học tăng cường mới hoặc áp dụng vào các bài toán điều khiển giao thông nâng cao.
