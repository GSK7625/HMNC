# PHẦN 4: DEEP Q-NETWORK (DQN) - KHẮC PHỤC BẤT ỔN ĐỊNH

---

## 1. Tại sao Q-Network Ngây thơ (Naive QN) Thất bại?

Khi kết hợp Học tăng cường với Mạng nơ-ron sâu trong những năm 1990 - 2012, hầu hết các nhà nghiên cứu đều gặp phải hiện tượng: **Mạng nơ-ron không hội tụ, giá trị Q bị nổ tung (phân kỳ) hoặc rớt thảm hại về 0**.

Giáo sư Richard Sutton (cha đẻ ngành RL) gọi đây là hiện tượng **"Tam giác Chết chóc" (The Deadly Triad)**: Khi một hệ thống hội tụ đủ 3 yếu tố sau, sự bất ổn định là điều khó tránh khỏi:
1. **Xấp xỉ hàm (Function Approximation)**: Dùng mạng nơ-ron thay vì bảng tra cứu.
2. **Khởi động tự thân (Bootstrapping)**: Dùng chính ước lượng tương lai để cập nhật ước lượng hiện tại ($r + \gamma \max Q$).
3. **Học ngoài chính sách (Off-Policy Learning)**: Học giá trị tối ưu của chính sách $\pi^*$ dựa trên hành vi sinh ra từ chính sách thăm dò $\epsilon$-greedy.

Cụ thể, có hai nguyên nhân kỹ thuật cốt tử dẫn tới sụp đổ:

---

### Nguyên nhân 1: Dữ liệu Tương quan Chuỗi Thời gian (Correlated Samples)
Trong học máy giám sát, các mẫu dữ liệu $(X_i, Y_i)$ luôn được giả định là **độc lập và đồng phân phối (i.i.d)**.
Tuy nhiên, trong mô phỏng giao thông:
- Trạng thái ngã tư lúc $t=10\text{s}$ gần như giống hệt trạng thái lúc $t=0\text{s}$ (xe chỉ nhích được vài mét).
- Nếu đưa liên tục các trạng thái kế tiếp nhau này vào mạng để huấn luyện theo thời gian thực, mạng nơ-ron sẽ bị hiện tượng **Overfitting cục bộ** (quên sạch quá khứ và chỉ thích nghi với khoảnh khắc hiện tại).

---

### Nguyên nhân 2: Bài toán Đích Di Động (The Moving Target Problem)
Hãy nhìn lại công thức cập nhật hàm mất mát của Q-Network:
$$L(\theta) = \Big( \underbrace{r + \gamma \max_{a'} Q(s', a'; \theta)}_{\text{Target (Đích ngắm)}} - \underbrace{Q(s, a; \theta)}_{\text{Dự đoán (Mũi tên)}} \Big)^2$$

Lưu ý rằng: **Cả Target lẫn Dự đoán đều dùng chung một bộ trọng số $\theta$!**
- Khi ta bắn mũi tên $Q(s, a; \theta)$ về phía mục tiêu, việc cập nhật $\theta$ vô tình làm cho mục tiêu $Q(s', a'; \theta)$ cũng bị đẩy sang một vị trí mới!
- Hiện tượng này giống như một thợ săn đang bắn một cái bia di động liên tục né tránh mỗi khi anh ta bóp cò, khiến giải thuật tối ưu hóa Gradient Descent rơi vào vòng xoáy dao động không hồi kết.

---

## 2. Vũ khí Thứ nhất của DeepMind: Experience Replay Buffer

Để phá vỡ tương quan chuỗi thời gian, DeepMind (Mnih et al., 2013, 2015) đã giới thiệu cấu trúc **Experience Replay Buffer (Bộ nhớ đệm tái hiện trải nghiệm)**.

```text
  [ Bước 1: Thu thập ]
  Agent hành động trong môi trường SUMO -> tạo ra bộ 5 phần tử Transition:
                       e_t = (s_t, a_t, r_t, s_{t+1}, done_t)
                                         │
                                         ▼
  [ Bước 2: Lưu vào Buffer ]
  +-------------------------------------------------------------------------+
  |  Replay Buffer (Hàng đợi xoay vòng dung lượng N = 5000)                |
  |  [ e_1 ] [ e_2 ] [ e_3 ] ... [ e_142 ] ... [ e_2800 ] ... [ e_5000 ]   |
  +-------------------------------------------------------------------------+
                                         │
                                         ▼ (Lấy mẫu ngẫu nhiên không hoàn lại)
  [ Bước 3: Lấy Mini-batch ]
  Bốc ngẫu nhiên một lô Mini-batch (ví dụ 32 mẫu):
  { e_12, e_495, e_1204, e_27, e_3411, ... } -> Đưa vào Huấn luyện mạng
```

### Tại sao Replay Buffer giải quyết được vấn đề?
1. **Khử hoàn toàn tương quan chuỗi**: Các mẫu trong một mini-batch được lấy từ nhiều thời điểm, nhiều hoàn cảnh giao thông hoàn toàn khác nhau (đông xe, vắng xe, giờ cao điểm...). Mạng nơ-ron nhận được dữ liệu xấp xỉ chuẩn độc lập i.i.d!
2. **Tối đa hóa hiệu quả sử dụng dữ liệu**: Mỗi trải nghiệm quý giá $(s, a, r, s')$ được lưu lại và tái sử dụng nhiều lần cho các bước cập nhật trọng số sau này, thay vì vứt bỏ ngay lập tức như Q-Learning cũ.

Mã nguồn triển khai trong [traffic_control/controllers/dqn.py](file:///c:/Users/dotru/HMNC/LibSignal/src/traffic_control/controllers/dqn.py):
```python
class ReplayBuffer:
    def __init__(self, capacity: int = 5000):
        self.buffer = collections.deque(maxlen=capacity)

    def push(self, state, action, reward, next_state, done):
        self.buffer.append((state, action, reward, next_state, done))

    def sample(self, batch_size, device):
        batch = random.sample(self.buffer, batch_size)
        # Chuyển đổi thành các PyTorch Tensor đưa vào GPU/CPU
```

---

## 3. Vũ khí Thứ hai của DeepMind: Target Network Độc lập

Để giải quyết triệt để bài toán "Đích di động", giải pháp là: **Nhốt bia ngắm lại một chỗ!**

DeepMind nhân bản kiến trúc mạng thành hai mạng nơ-ron riêng biệt:
1. **Online Network (Mạng chính - tham số $\theta$)**: Được cập nhật gradient liên tục ở mọi bước huấn luyện để đưa ra quyết định hành động.
2. **Target Network (Mạng mục tiêu - tham số $\theta^-$)**: Được giữ nguyên cố định (đóng băng trọng số), chỉ dùng để tính giá trị TD Target:

$$\mathbf{y_t^{\text{DQN}} = r_t + \gamma \max_{a'} Q(s_{t+1}, a'; \theta^-)}$$

Và hàm mất mát trở thành:
$$L(\theta) = \mathbb{E} \left[ \Big( y_t^{\text{DQN}} - Q(s_t, a_t; \theta) \Big)^2 \right]$$

```text
             +---------------------------+
             |    Target Network θ^-     |  (Đóng băng trọng số)
             |   Tính giá trị y_target   |
             +-------------+-------------+
                           │
                           │ y = r + γ max Q(s', a'; θ^-)
                           ▼
             +-------------+-------------+
             |       Loss Function       |
             +-------------+-------------+
                           ▲
                           │ Q(s, a; θ)
             +-------------+-------------+
             |     Online Network θ      |  (Liên tục cập nhật gradient)
             |      Cập nhật qua SGD     |
             +---------------------------+
                           │
                           │ Sau mỗi C bước (ví dụ: 20 bước)
                           ▼ Sao chép trọng số: θ^- <── θ
             +---------------------------+
             |    Target Network θ^-     |
             +---------------------------+
```

### Cơ chế Đồng bộ Hóa Trọng số:
Sau mỗi chu kỳ định kỳ (ví dụ cứ sau mỗi $C = 20$ bước huấn luyện hoặc sau mỗi Episode kết thúc), ta mới sao chép toàn bộ trọng số từ mạng Online sang mạng Target:
$$\theta^- \leftarrow \theta$$

Nhờ vậy, bia ngắm luôn đứng yên trong suốt 20 bước để Online Network thoải mái điều chỉnh gradient bám đuổi, loại bỏ hoàn toàn hiện tượng rung lắc và phân kỳ!

---

## 4. Thuật toán Deep Q-Network (DQN) Toàn diện

Dưới đây là mã giả của thuật toán DQN hoàn chỉnh (theo chuẩn bài báo Nature 2015 của DeepMind):

```text
Khởi tạo Replay Buffer D với dung lượng N
Khởi tạo Online Network Q với trọng số ngẫu nhiên θ
Khởi tạo Target Network Q_target với trọng số θ^- = θ

Lặp lại qua từng Episode huấn luyện:
    Khởi tạo trạng thái s_1 từ môi trường
    Với mỗi bước t từ 1 đến T:
        1. Chọn hành động a_t theo chiến lược ε-greedy:
           - Với xác suất ε: chọn ngẫu nhiên hành động a_t
           - Ngược lại: a_t = argmax_a Q(s_t, a; θ)
           
        2. Thực thi a_t trong môi trường, nhận reward r_t và trạng thái mới s_{t+1}
        
        3. Lưu transition (s_t, a_t, r_t, s_{t+1}, done) vào Replay Buffer D
        
        4. Lấy mẫu ngẫu nhiên một mini-batch gồm B mẫu từ D
        
        5. Với mỗi mẫu j trong mini-batch, tính mục tiêu:
           Nếu done_j == True:
               y_j = r_j
           Nếu done_j == False:
               y_j = r_j + γ * max_{a'} Q_target(s'_{j}, a'; θ^-)
               
        6. Tính Loss = MSE(y_j, Q(s_j, a_j; θ))
        
        7. Cập nhật θ bằng Gradient Descent (Adam optimizer)
        
        8. Định kỳ sau mỗi C bước: sao chép θ^- ‹── θ
```

---

## 5. Tóm lược So sánh 3 Thế hệ: Tabular QL vs. QN vs. DQN

| Đặc tính | Tabular Q-Learning (Phần 2) | Naive Q-Network (Phần 3) | Deep Q-Network DQN (Phần 4) |
| :--- | :--- | :--- | :--- |
| **Cấu trúc dữ liệu** | Ma trận 2 chiều trong RAM | Mạng nơ-ron đa tầng | 2 Mạng nơ-ron riêng biệt (Online + Target) |
| **Không gian trạng thái** | Rời rạc, nhỏ | Liên tục, lớn | Liên tục, cực lớn |
| **Tái sử dụng mẫu** | Không (vứt ngay sau 1 bước) | Không | Có (Replay Buffer đa mẫu ngẫu nhiên) |
| **Độ ổn định huấn luyện** | Hội tụ toán học nếu bảng nhỏ | Rất kém (Dễ phân kỳ do Moving Target) | Cực kỳ ổn định và đã được chứng minh thực nghiệm |

Tuy nhiên, trong thuật toán DQN nguyên bản của DeepMind năm 2015, vẫn còn tồn tại một "căn bệnh ngầm" mang tên **Overestimation Bias (Ước lượng giá trị quá đà)** do phép toán $\max$ gây ra.

Làm thế nào để trị dứt điểm căn bệnh này? Đó là lý do thuật toán **Double DQN** ra đời!

👉 **Mời bạn đón đọc**: [PHẦN 5: CÁC CẢI TIẾN CHUYÊN SÂU - DOUBLE DQN](file:///c:/Users/dotru/HMNC/LibSignal/docs/giao_trinh_qn/05_CAI_TIEN_DOUBLE_DQN.md)
