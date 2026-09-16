# PHẦN 5: CÁC CẢI TIẾN CHUYÊN SÂU - DOUBLE DQN & KỸ THUẬT TỐI ƯU HÓA

---

## 1. Căn bệnh "Ước lượng Quá đà" (Overestimation Bias)

Mặc dù thuật toán DQN của DeepMind (2015) đạt thành tựu rực rỡ trên các trò chơi Atari, các nhà nghiên cứu nhanh chóng phát hiện ra một khiếm khuyết toán học nghiêm trọng: **Giá trị Q ước lượng bởi mạng nơ-ron luôn bị thổi phồng cao hơn rất nhiều so với giá trị thực tế**.

### 🔍 Nguồn gốc Toán học của Sai lệch
Hãy nhìn vào biểu thức tính TD Target của DQN chuẩn:
$$y = r + \gamma \max_{a'} Q(s', a'; \theta^-)$$

Phép toán $\max$ có một đặc tính nguy hiểm khi có sự hiện diện của sai số hoặc nhiễu ngẫu nhiên.
Giả sử tại trạng thái $s'$, giá trị thực sự của tất cả các hành động là như nhau: $Q^*(s', a) = 0$.
Tuy nhiên, do mạng nơ-ron chưa học hoàn hảo, các giá trị dự đoán có kèm sai số ngẫu nhiên $\epsilon_a$:
- Hành động 0: Dự đoán $= -0.5$
- Hành động 1: Dự đoán $= +1.2$  $\leftarrow$ Nhiễu dương ngẫu nhiên
- Hành động 2: Dự đoán $= -0.8$

Khi ta lấy $\max(-0.5, +1.2, -0.8) = \mathbf{+1.2}$, ta đã vô tình chọn đúng phần tử có nhiễu dương lớn nhất!
Toán học xác suất đã chứng minh:
$$\mathbb{E}\left[ \max_a \big( Q^*(s, a) + \epsilon_a \big) \right] \ge \max_a Q^*(s, a)$$

Khi quá trình này lặp đi lặp lại qua hàng nghìn bước cập nhật Bellman, sự thổi phồng tích lũy theo cấp số nhân. Agent sẽ lầm tưởng rằng một hành động là "cực kỳ tuyệt vời" chỉ vì nhiễu ngẫu nhiên, dẫn tới việc đưa ra các quyết định điều khiển đèn giao thông sai lầm.

---

## 2. Giải pháp Đột phá: Double DQN (DDQN)

Hado van Hasselt cùng nhóm nghiên cứu DeepMind (2015) đã đưa ra giải pháp thanh lịch: **Tách rời việc "Chọn hành động" và "Định giá hành động"**.

Trong DQN chuẩn:
- Mạng Target $\theta^-$ vừa làm nhiệm vụ **chọn** hành động tốt nhất (qua $\max$), vừa làm nhiệm vụ **tính** giá trị của hành động đó. "Vừa đá bóng vừa thổi còi"!

Trong **Double DQN (DDQN)**:
- **Mạng Online $\theta$** (mạng liên tục học) được giao nhiệm vụ **Chọn hành động tốt nhất**:
  $$a^* = \arg\max_{a'} Q(s', a'; \theta)$$
- **Mạng Target $\theta^-$** (mạng đóng băng) được giao nhiệm vụ **Định giá xem hành động $a^*$ đó thực sự đáng giá bao nhiêu**:
  $$\text{Value} = Q(s', a^*; \theta^-)$$

### 🌟 Công thức TD Target của Double DQN:

$$\mathbf{y_t^{\text{Double DQN}} = r_t + \gamma \, Q_{\text{target}}\Big(s_{t+1}, \underbrace{\arg\max_{a'} Q_{\text{online}}(s_{t+1}, a'; \theta_t)}_{\text{Mạng Online chọn hành động}}; \; \theta_t^-\Big)}$$

```text
               Trạng thái mới s'
                 │           │
                 │           │
        ┌────────┴──────┐    │
        │ Online Net θ  │    │
        └───────┬───────┘    │
                │            │
       argmax_a Q(s', a; θ)  │
        (Hành động a*)       │
                │            │
                └─────►┌─────┴──────────┐
                       │ Target Net θ^- │
                       └─────┬──────────┘
                             │
                             ▼
                    Q_target(s', a*; θ^-)
                             │
                             ▼
              y = r + γ * Q_target(s', a*; θ^-)
```

> [!TIP]
> **Tại sao việc tách rời này loại bỏ được Overestimation Bias?**
> Nếu mạng Online vô tình ước lượng quá cao một hành động do nhiễu, nhưng mạng Target (với bộ trọng số khác) không có cùng nhiễu đó, giá trị ước lượng tổng thể sẽ được kéo về mức trung thực và khách quan.

Trong file [traffic_control/controllers/dqn.py](file:///c:/Users/dotru/HMNC/LibSignal/src/traffic_control/controllers/dqn.py) của dự án `LibSignal`, Double DQN được bật mặc định (`double_dqn: bool = True`):
```python
if self.double_dqn:
    # 1. Mạng Online chọn hành động tốt nhất:
    best_actions = self.q_network(next_states).argmax(dim=1, keepdim=True)
    # 2. Mạng Target đánh giá giá trị của hành động đó:
    next_q = self.target_network(next_states).gather(1, best_actions).squeeze(1)
else:
    # DQN chuẩn: Target tự làm cả hai
    next_q = self.target_network(next_states).max(dim=1)[0]
```

---

## 3. Các Kỹ thuật Tối ưu Hóa Giúp Hội tụ Ổn định

Bên cạnh Double DQN, trong mã nguồn `LibSignal` còn tích hợp 3 kỹ thuật công nghiệp quan trọng giúp mạng nơ-ron học êm và không bao giờ bị nổ gradient:

### 3.1. Hàm mất mát Huber Loss (Smooth L1 Loss)
Thay vì sử dụng hàm mất mát bình phương sai số thông thường (MSE):
$$L_{\text{MSE}} = (y - \hat{y})^2 \implies \frac{\partial L}{\partial \hat{y}} = -2(y - \hat{y})$$

Khi ngã tư gặp tình huống bất ngờ (ví dụ: lượng xe ùn tắc đột biến hoặc chuyển pha đột ngột), sai số $|y - \hat{y}|$ có thể rất lớn (ví dụ: $100$). Gradient của MSE sẽ lên tới $200$, làm các trọng số mạng nơ-ron bị "giật" mạnh và phá vỡ toàn bộ cấu trúc đã học!

**Hàm mất mát Huber Loss (Smooth L1)** dung hòa hoàn hảo giữa MSE và L1:
$$L_\delta(e) = \begin{cases} 
\frac{1}{2} e^2 & \text{khi } |e| \le 1.0 \quad (\text{Mượt mà như MSE khi sai số nhỏ}) \\
|e| - \frac{1}{2} & \text{khi } |e| > 1.0 \quad (\text{Tuyến tính như L1 khi sai số lớn})
\end{cases}$$

Gradient khi sai số lớn được khống chế tối đa là $\pm 1$, triệt tiêu hoàn toàn hiện tượng nổ gradient.
Trong PyTorch:
```python
loss = nn.functional.smooth_l1_loss(current_q, target_q)
```

---

### 3.2. Cắt xén Gradient (Gradient Clipping)
Để đảm bảo mạng nơ-ron không bao giờ bước những bước quá dài trong không gian tham số, chuẩn Euclidean của toàn bộ vector gradient được giới hạn không vượt quá một ngưỡng an toàn ($1.0$):

```python
torch.nn.utils.clip_grad_norm_(self.q_network.parameters(), max_norm=1.0)
```
Nếu $\|\nabla_\theta\| > 1.0$, vector gradient sẽ được chuẩn hóa thu nhỏ lại:
$$\nabla_\theta \leftarrow \nabla_\theta \times \frac{1.0}{\|\nabla_\theta\|}$$

---

### 3.3. Cơ chế Khử Rung Lắc (Tie-Breaking Hysteresis)
Khi Agent đã học tốt, đôi khi giá trị Q của hai pha đèn là gần như bằng nhau (ví dụ: Pha 0 có $Q = -5.001$, Pha 1 có $Q = -5.000$).
Nếu cứ máy móc chọn $\arg\max$, Agent sẽ liên tục đổi đèn qua lại sau mỗi chu kỳ, kích hoạt đèn vàng $3$ giây liên tục gây lãng phí nghiêm trọng thời gian lưu thông!

**Giải pháp Hysteresis**:
Nếu pha hiện tại đang có giá trị $Q$ xấp xỉ bằng giá trị $Q$ lớn nhất (chênh lệch trong ngưỡng $\text{tol} = 10^{-4}$), bộ điều khiển sẽ **ưu tiên giữ nguyên pha hiện tại**, giữ cho luồng giao thông được lưu thông liên tục.

---

## 4. Mở rộng Kiến thức: Dueling DQN & Prioritized Replay

Dù chưa bắt buộc phải có trong phiên bản cơ bản, đây là hai cải tiến nổi tiếng khác bạn nên biết:

### 4.1. Dueling DQN (Wang et al., 2016)
Mạng nơ-ron được chia thành hai nhánh độc lập ở tầng cuối:
- Nhánh 1: Dự đoán giá trị trạng thái $V(s)$ (Ngã tư này nhìn chung thông thoáng hay kẹt xe).
- Nhánh 2: Dự đoán lợi thế riêng của từng hành động $A(s, a)$ (Bật pha này có hơn gì các pha khác không).
$$Q(s, a) = V(s) + \left( A(s, a) - \frac{1}{|\mathcal{A}|} \sum_{a'} A(s, a') \right)$$

### 4.2. Prioritized Experience Replay (PER - Schaul et al., 2015)
Thay vì bốc ngẫu nhiên bình đẳng trong Replay Buffer, ta ưu tiên bốc lại những trải nghiệm có sai số TD Error cao ($|\delta| = |y - Q|$ lớn). Những pha xử lý mà Agent còn lúng túng và sai lệch nhiều sẽ được đưa vào "ôn luyện" thường xuyên hơn.

---

Giờ đây, bạn đã nắm vững toàn bộ lý thuyết từ nền tảng Bellman đến các kỹ thuật Deep Q-Network hiện đại nhất.
Hãy cùng bước vào phần cuối cùng: **Thực chiến và làm chủ mã nguồn dự án LibSignal!**

👉 **Mời bạn đón đọc**: [PHẦN 6: THỰC CHIẾN & MỔ XẺ MÃ NGUỒN LIBSIGNAL](file:///c:/Users/dotru/HMNC/LibSignal/docs/giao_trinh_qn/06_THUC_CHIEN_LIBSIGNAL.md)
