# PHẦN 3: TỪ BẢNG Q SANG Q-NETWORK (QN)

---

## 1. "Lời nguyền số chiều" và Nhu cầu Khái quát hóa

Ở [Phần 2](file:///c:/Users/dotru/HMNC/LibSignal/docs/giao_trinh_qn/02_TABULAR_Q_LEARNING.md), chúng ta đã thấy Tabular Q-Learning lưu trữ giá trị trong một bảng ma trận $Q[s, a]$. Cách tiếp cận này vấp phải hai rào cản chí mạng khi áp dụng vào thực tế:

### 1.1. Lời nguyền số chiều (Curse of Dimensionality)
Giả sử ta điều khiển một ngã tư 4 hướng trong thành phố:
- Mỗi hướng có số xe dừng từ $0$ đến $30$ (31 khả năng).
- Thời gian đèn xanh đã trôi qua từ $0$ đến $60$ giây (61 khả năng).
- Vận tốc trung bình của dòng xe (liên tục).
- Tổng số trạng thái rời rạc kết hợp: $31^4 \times 61 \approx \mathbf{56.334.661}$ trạng thái!
- Nếu lưu bảng này trong bộ nhớ với số thực `float32`, ta cần hàng trăm Megabytes chỉ cho một ngã tư đơn giản. Nếu mạng lưới có 100 ngã tư liên thông nhau, số trạng thái lớn hơn số nguyên tử trong vũ trụ!

### 1.2. Sự thiếu hụt khả năng Khái quát hóa (Generalization)
Trong bảng Q, mỗi ô nhớ là hoàn toàn độc lập:
- Nếu trạng thái $s_1 = [10 \text{ xe}, 5 \text{ xe}]$ đã được học rất tốt.
- Khi môi trường xuất hiện trạng thái $s_2 = [11 \text{ xe}, 5 \text{ xe}]$, bảng Q coi đây là một trạng thái mới tinh $100\%$ và không thể suy luận từ $s_1$.
- Trong khi đó, bộ não con người hiểu ngay rằng: 10 xe hay 11 xe thì mật độ tắc nghẽn là gần như tương đương nhau!

---

## 2. Ý tưởng Đột phá: Mạng Nơ-ron Xấp xỉ Hàm (Function Approximator)

Thay vì dùng một bảng tra cứu tĩnh khổng lồ, ta sử dụng một **Mạng Nơ-ron Nhân tạo (Artificial Neural Network)** với bộ trọng số $\theta$ để mô hình hóa hàm Q:

$$Q(s, a) \approx Q(s, a; \theta)$$

```text
  [Bảng Q Truyền thống]                     [Mạng Q-Network (QN)]
  
    State s ──┐                              State s ──┐
              ├──► [ Lookup Table ] ──► Q              ├──► [ Mạng Nơ-ron MLP ] ──► Q(s, a)
    Action a ─┘                                        │    (Trọng số θ)
                                                       │
  (Nhược điểm: Tốn RAM, không suy luận)     (Ưu điểm: Gọn nhẹ, tự suy luận/khái quát hóa)
```

### Lợi ích to lớn của Mạng Nơ-ron:
1. **Bộ nhớ cực nhỏ**: Dù không gian trạng thái là liên tục và vô hạn, mạng nơ-ron chỉ cần lưu vài nghìn đến vài trăm nghìn trọng số $\theta$ (vài chục Kilobytes).
2. **Khả năng khái quát hóa**: Nhờ các hàm kích hoạt phi tuyến (ReLU) và các lớp ẩn (Hidden Layers), khi mạng đã học trạng thái "10 xe", nó sẽ tự động ngoại suy chính xác hành vi khi gặp "11 xe" hoặc "10.5 xe".

---

## 3. Kiến trúc Đầu ra của Q-Network

Có hai cách để thiết kế mạng nơ-ron dự đoán Q-value:

```text
Cách 1: Input cả State và Action                Cách 2: Input State, Output tất cả Actions
                                                (Chuẩn công nghiệp & DeepMind)

       State s ──┐                                             ┌──► Q(s, a_0)
                 ├──► [ Neural Net ] ──► Q(s, a)   State s ──► [ Neural Net ] ──┼──► Q(s, a_1)
      Action a ──┘                                             └──► Q(s, a_2)
```

- **Tại sao Cách 2 vượt trội hoàn toàn?**
  - Trong thuật toán Q-Learning, tại mỗi bước ta cần tìm hành động tốt nhất:
    $$a^* = \arg\max_{a'} Q(s, a')$$
  - Với **Cách 1**: Nếu ngã tư có 4 pha đèn, ta phải chạy Forward Pass qua mạng nơ-ron **4 lần** riêng biệt cho từng hành động.
  - Với **Cách 2**: Ta chỉ cần Forward Pass qua mạng **đúng 1 lần duy nhất**! Vector đầu ra sẽ chứa đồng thời toàn bộ giá trị $Q(s, a)$ của tất cả các hành động. Sau đó ta chỉ cần lấy `torch.argmax()` trong tích tắc!

Đây chính là kiến trúc được triển khai trong file [traffic_control/controllers/dqn.py](file:///c:/Users/dotru/HMNC/LibSignal/src/traffic_control/controllers/dqn.py) của dự án:
```python
class QNetwork(nn.Module):
    def __init__(self, state_dim: int, action_dim: int, hidden_dims=(64, 64)):
        super().__init__()
        # Input: state_dim (vector số thực)
        # Output: action_dim (giá trị Q cho từng pha đèn)
```

---

## 4. Huấn luyện Q-Network: Hàm Mất mát (Loss Function)

Mạng nơ-ron học bằng cách giảm thiểu một **Hàm mất mát (Loss Function)** thông qua giải thuật Lan truyền ngược (Backpropagation).

Nhắc lại phương trình Bellman:
$$Q^*(s, a) = r + \gamma \max_{a'} Q^*(s', a')$$

Ta định nghĩa **Mục tiêu học (TD Target)** đóng vai trò như nhãn thực tế $y$:
$$y = r + \gamma \max_{a'} Q(s', a'; \theta)$$

Và giá trị mạng nơ-ron hiện tại đang dự đoán là:
$$\hat{y} = Q(s, a; \theta)$$

### Hàm Mất mát Bình phương Sai số Bellman (Mean Squared Bellman Error - MSBE):
$$L(\theta) = \mathbb{E} \left[ \Big( \underbrace{r + \gamma \max_{a'} Q(s', a'; \theta)}_{\text{Target } y} - \underbrace{Q(s, a; \theta)}_{\text{Dự đoán}} \Big)^2 \right]$$

---

## 5. Lan truyền Ngược (Backpropagation) và Gradient Descent

Để cập nhật trọng số $\theta$ của mạng nơ-ron, ta tính đạo hàm của hàm mất mát theo $\theta$:

$$\nabla_\theta L(\theta) = \mathbb{E} \left[ -2 \Big( y - Q(s, a; \theta) \Big) \nabla_\theta Q(s, a; \theta) \right]$$

Quy tắc cập nhật trọng số theo giải thuật Gradient Descent (với tốc độ học $\eta$ / learning rate):
$$\theta \leftarrow \theta - \eta \nabla_\theta L(\theta)$$

Trong PyTorch, toàn bộ quá trình phức tạp này được thực hiện gọn gàng chỉ với 3 dòng code:
```python
optimizer.zero_grad()    # Xóa gradient cũ
loss.backward()          # Tính gradient tự động (Autograd)
optimizer.step()         # Cập nhật trọng số theta mới
```

---

## 6. So sánh: Học có Giám sát vs. Q-Network

| Tiêu chí | Học có Giám sát (Supervised Learning) | Q-Network (QN) |
| :--- | :--- | :--- |
| **Nhãn mục tiêu ($y$)** | Cố định từ đầu (ví dụ ảnh nhãn là "Chó" thì mãi là "Chó") | **Biến thiên liên tục!** Target $y = r + \gamma \max Q(s', a'; \theta)$ thay đổi mỗi khi $\theta$ thay đổi! |
| **Phân phối dữ liệu** | Độc lập và đồng phân phối (i.i.d) | Các trạng thái kế tiếp phụ thuộc chặt chẽ theo thời gian ($s_{t+1}$ bắt nguồn từ $s_t$) |
| **Độ ổn định** | Hội tụ rất ổn định và chắc chắn | Dễ bị dao động, phân kỳ hoặc sụp đổ nếu huấn luyện trực tiếp |

> [!CAUTION]
> **Cảnh báo cốt tử**:
> Việc áp dụng trực tiếp mạng nơ-ron sâu vào Q-Learning theo cách ngây thơ ở trên sẽ khiến quá trình huấn luyện **bị nổ hàm mất mát (phân kỳ)** hoặc rơi vào vòng lặp vô tận!
> Hiện tượng này được gọi là "Đích di động" (Moving Target) và "Dữ liệu tương quan chuỗi" (Correlated Data).

Làm thế nào các nhà khoa học của Google DeepMind giải quyết triệt để vấn đề này vào năm 2013-2015 để khai sinh ra **Deep Q-Network (DQN)**?

👉 **Mời bạn khám phá ngay trong**: [PHẦN 4: DEEP Q-NETWORK (DQN) - VƯỢT QUA BẤT ỔN ĐỊNH](file:///c:/Users/dotru/HMNC/LibSignal/docs/giao_trinh_qn/04_DEEP_Q_NETWORK_DQN.md)
