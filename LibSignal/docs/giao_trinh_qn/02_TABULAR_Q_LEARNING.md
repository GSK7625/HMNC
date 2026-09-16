# PHẦN 2: TABULAR Q-LEARNING (BẢNG TRA CỨU Q)

---

## 1. Bản chất của Bảng Q (Q-Table)

Trước khi mạng nơ-ron sâu ra đời, dạng sơ khai và thuần khiết nhất của thuật toán Q-Learning được phát minh bởi Chris Watkins (1989) là **Tabular Q-Learning** (Q-Learning dạng bảng).

Ý tưởng rất đơn giản: Ta xây dựng một bảng tính (ma trận 2 chiều):
- **Các hàng**: Tương ứng với từng trạng thái rời rạc $s \in \mathcal{S}$.
- **Các cột**: Tương ứng với từng hành động có thể chọn $a \in \mathcal{A}$.
- **Giá trị trong ô $Q[s, a]$**: Điểm chất lượng dự đoán của hành động $a$ khi đứng ở trạng thái $s$.

Ví dụ một Bảng Q tại một ngã tư giao thông:

| Trạng thái $s$ (Pha hiện tại, Hàng đợi nhánh Bắc, Đông) | Hành động $a=0$ (Bật xanh Bắc-Nam) | Hành động $a=1$ (Bật xanh Đông-Tây) |
| :--- | :---: | :---: |
| Trạng thái A: `[Pha 0, Nhiều xe, Ít xe]` | **$-2.5$** | $-18.0$ |
| Trạng thái B: `[Pha 0, Ít xe, Nhiều xe]` | $-15.2$ | **$-3.1$** |
| Trạng thái C: `[Pha 1, Ít xe, Nhiều xe]` | $-20.0$ | **$-1.8$** |

Khi Agent cần đưa ra quyết định ở Trạng thái A:
Nó chỉ cần nhìn vào hàng "Trạng thái A" trong bảng, tìm cột có giá trị cao nhất: $\max(-2.5, -18.0) = -2.5$ (ứng với hành động $a=0$). Vậy Agent quyết định bật xanh Bắc-Nam!

---

## 2. Công thức Cập nhật Bảng Q (Q-Learning Update Rule)

Khi mới bắt đầu, Agent chưa biết gì cả, mọi ô trong bảng Q đều được khởi tạo bằng $0$.
Làm thế nào để bảng Q tự điền được các con số chính xác?

Mỗi khi Agent đứng ở trạng thái $s$, thực hiện hành động $a$, nhận được phần thưởng $r$ và quan sát thấy trạng thái mới $s'$, nó cập nhật ô $Q[s, a]$ theo công thức:

$$\mathbf{Q(s, a) \leftarrow Q(s, a) + \alpha \Big[ \underbrace{r + \gamma \max_{a'} Q(s', a')}_{\text{TD Target}} - \underbrace{Q(s, a)}_{\text{Giá trị cũ}} \Big]}$$

### 🔍 Mổ xẻ từng thành phần:

1. **$Q(s, a)$ cũ**: Ước lượng hiện tại trong bảng mà Agent đang có.
2. **$\text{TD Target} = r + \gamma \max_{a'} Q(s', a')$**: Mục tiêu thực tế mới được cập nhật nhờ trải nghiệm vừa xảy ra.
   - $r$: Phần thưởng thực tế vừa cầm trong tay.
   - $\gamma \max_{a'} Q(s', a')$: Giá trị tốt nhất của trạng thái mới bước tới.
3. **$\text{TD Error} = \text{TD Target} - Q(s, a)$**: Độ sai lệch giữa "thực tế mới biết" và "dự đoán cũ".
   - Nếu $\text{TD Error} > 0$: Hành động mang lại kết quả tốt hơn dự đoán $\rightarrow$ Tăng giá trị $Q(s, a)$.
   - Nếu $\text{TD Error} < 0$: Hành động mang lại kết quả tệ hơn dự đoán $\rightarrow$ Giảm giá trị $Q(s, a)$.
4. **$\alpha \in (0, 1]$ - Tốc độ học (Learning Rate)**:
   - Quyết định ta tiếp thu thông tin mới nhanh hay chậm.
   - $\alpha = 0.1$: Chỉ cập nhật 10% sai số mới, giữ lại 90% ký ức cũ.

---

## 3. Cân bằng Thăm dò và Khai thác ($\epsilon$-greedy Policy)

Nếu Agent chỉ luôn chọn hành động có $Q(s, a)$ cao nhất hiện có (Khai thác - Exploitation), nó có thể bị kẹt vào các lựa chọn cục bộ và không bao giờ phát hiện ra những hành động khác còn tốt hơn nhiều (Thăm dò - Exploration).

Để cân bằng, ta dùng chiến lược **$\epsilon$-greedy**:
- Với xác suất $1 - \epsilon$: **Khai thác** (chọn hành động $a = \arg\max_a Q(s, a)$).
- Với xác suất $\epsilon$: **Thăm dò** (chọn ngẫu nhiên một hành động bất kỳ).

Thông thường trong huấn luyện:
- Ban đầu: $\epsilon = 1.0$ (chọn 100% ngẫu nhiên để khám phá môi trường).
- Sau đó giảm dần: $\epsilon \leftarrow \max(\epsilon_{min}, \epsilon \times \text{decay})$ (Agent tích lũy tri thức và chuyển dần sang hành động thông minh).

---

## 4. 🧮 Ví dụ Tính tay Từng bước (Step-by-step Walkthrough)

Giả sử ta điều khiển một ngã tư đơn giản:
- 2 hành động: $a=0$ (Xanh Bắc-Nam), $a=1$ (Xanh Đông-Tây).
- Siêu tham số: Tốc độ học $\alpha = 0.5$, Hệ số chiết khấu $\gamma = 0.9$.
- Bảng Q ban đầu khởi tạo toàn bộ bằng $0$:

| Trạng thái | $a=0$ | $a=1$ |
| :--- | :---: | :---: |
| $s_1$ (Kẹt Bắc-Nam) | $0.0$ | $0.0$ |
| $s_2$ (Kẹt Đông-Tây) | $0.0$ | $0.0$ |

### 📍 Bước 1:
- Đang ở trạng thái $s_1$.
- Agent chọn hành động $a=0$ (Bật xanh Bắc-Nam).
- Kết quả: Xe Bắc-Nam thoát bớt, nhưng vẫn còn 4 xe $\rightarrow$ Reward $r = -4$.
- Trạng thái mới chuyển thành $s_2$ (xe dồn sang Đông-Tây).
- Ở $s_2$, các giá trị hiện tại là: $Q(s_2, 0) = 0.0$, $Q(s_2, 1) = 0.0 \Rightarrow \max_{a'} Q(s_2, a') = 0.0$.

**Tính toán cập nhật $Q(s_1, 0)$:**
$$\text{TD Target} = r + \gamma \max_{a'} Q(s_2, a') = -4 + 0.9 \times 0.0 = -4.0$$
$$\text{TD Error} = \text{TD Target} - Q(s_1, 0) = -4.0 - 0.0 = -4.0$$
$$Q(s_1, 0) \leftarrow 0.0 + 0.5 \times (-4.0) = \mathbf{-2.0}$$

*Bảng Q sau Bước 1:*
| Trạng thái | $a=0$ | $a=1$ |
| :--- | :---: | :---: |
| $s_1$ | **-2.0** | $0.0$ |
| $s_2$ | $0.0$ | $0.0$ |

---

### 📍 Bước 2:
- Hiện tại đang ở $s_2$.
- Agent chọn hành động $a=1$ (Bật xanh Đông-Tây).
- Kết quả: Thông thoáng Đông-Tây, chỉ còn 2 xe dừng $\rightarrow$ Reward $r = -2$.
- Trạng thái mới quay lại $s_1$.
- Ở $s_1$, các giá trị hiện có: $Q(s_1, 0) = -2.0$, $Q(s_1, 1) = 0.0 \Rightarrow \max_{a'} Q(s_1, a') = 0.0$.

**Tính toán cập nhật $Q(s_2, 1)$:**
$$\text{TD Target} = -2 + 0.9 \times 0.0 = -2.0$$
$$\text{TD Error} = -2.0 - 0.0 = -2.0$$
$$Q(s_2, 1) \leftarrow 0.0 + 0.5 \times (-2.0) = \mathbf{-1.0}$$

*Bảng Q sau Bước 2:*
| Trạng thái | $a=0$ | $a=1$ |
| :--- | :---: | :---: |
| $s_1$ | $-2.0$ | $0.0$ |
| $s_2$ | $0.0$ | **-1.0** |

---

### 📍 Bước 3 (Kỳ diệu của Bellman: Lan truyền giá trị tương lai):
- Giả sử Agent lại gặp lại trạng thái $s_1$, và tiếp tục chọn $a=0$.
- Nhận được reward $r = -4$ và rơi vào trạng thái $s_2$.
- **Lần này, ở $s_2$ đã có dữ liệu**: $Q(s_2, 0) = 0.0$, $Q(s_2, 1) = -1.0 \Rightarrow \max_{a'} Q(s_2, a') = 0.0$.
- Nếu bước kế tiếp Agent đến một trạng thái có giá trị khác, thông tin tương lai sẽ được kéo ngược về quá khứ!

---

## 5. Code Python Độc lập Mô phỏng Tabular Q-Learning

Bạn có thể chạy thử đoạn code ngắn gọn sau đây bằng lệnh `python` để thấy bảng Q hội tụ:

```python
import numpy as np

# Định nghĩa môi trường đơn giản 2 trạng thái, 2 hành động
# State 0: Xe Bắc đông | State 1: Xe Đông đông
# Action 0: Xanh Bắc  | Action 1: Xanh Đông

Q_table = np.zeros((2, 2))
alpha = 0.2
gamma = 0.9
epsilon = 0.2

def step(state, action):
    # Nếu chọn đúng pha giải tỏa kẹt: reward = -1, đổi trạng thái
    # Nếu chọn sai pha: reward = -10, giữ nguyên trạng thái
    if state == action:
        reward = -1.0
        next_state = 1 - state
    else:
        reward = -10.0
        next_state = state
    return next_state, reward

# Huấn luyện 500 bước
state = 0
for _ in range(500):
    # Epsilon-greedy
    if np.random.rand() < epsilon:
        action = np.random.choice([0, 1])
    else:
        action = np.argmax(Q_table[state])
    
    next_state, reward = step(state, action)
    
    # Cập nhật Bellman TD
    best_next_q = np.max(Q_table[next_state])
    td_target = reward + gamma * best_next_q
    td_error = td_target - Q_table[state, action]
    Q_table[state, action] += alpha * td_error
    
    state = next_state

print("Bảng Q sau khi học:")
print(Q_table)
# Kết quả sẽ cho thấy Q[0, 0] > Q[0, 1] và Q[1, 1] > Q[1, 0]
```

---

## 6. Tại sao Tabular Q-Learning gặp Giới hạn?

Tabular Q-Learning hoạt động rất tốt trong các bài toán đồ chơi (nhỏ hơn vài trăm trạng thái). Nhưng trong thế giới thực:
1. **Số lượng xe liên tục**: Một ngã tư 4 nhánh, mỗi nhánh có từ $0$ đến $50$ xe $\rightarrow 50^4 = 6.250.000$ trạng thái!
2. Nếu có thêm vận tốc xe, thời gian chờ, góc rẽ... số trạng thái là **vô hạn (liên tục)**.
3. Bảng Q không thể chứa nổi hàng tỷ tỷ ô nhớ trong RAM.
4. **Không có khả năng khái quát hóa (Generalization)**: Nếu Bảng Q đã học được cách xử lý khi có đúng 10 xe ở nhánh Bắc, nhưng khi gặp 11 xe, nó coi như một trạng thái hoàn toàn xa lạ và phải học lại từ đầu!

> Đây chính là lúc chúng ta cần bước nhảy vọt: **Q-Network (QN)**!

👉 **Mời bạn đọc tiếp**: [PHẦN 3: TỪ BẢNG Q SANG Q-NETWORK (QN)](file:///c:/Users/dotru/HMNC/LibSignal/docs/giao_trinh_qn/03_TU_BANG_Q_SANG_Q_NETWORK.md)
