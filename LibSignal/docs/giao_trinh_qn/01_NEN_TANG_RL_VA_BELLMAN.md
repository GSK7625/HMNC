# PHẦN 1: NỀN TẢNG HỌC TĂNG CƯỜNG & PHƯƠNG TRÌNH BELLMAN

---

## 1. Học Tăng Cường (Reinforcement Learning - RL) là gì?

Học máy truyền thống thường được chia thành 3 trường phái chính:
1. **Học có giám sát (Supervised Learning)**: Học từ dữ liệu đã gán nhãn sẵn $(\text{Input } X \rightarrow \text{Nhãn } Y)$. Ví dụ: Cho xem 10.000 bức ảnh mèo và chó đã gắn nhãn.
2. **Học không giám sát (Unsupervised Learning)**: Tự tìm cấu trúc ẩn trong dữ liệu không có nhãn. Ví dụ: Phân cụm khách hàng (Clustering).
3. **Học tăng cường (Reinforcement Learning - RL)**: Không có ai cầm tay chỉ việc, không có nhãn đúng/sai ngay lập tức. Thay vào đó, một **Tác tử (Agent)** tự mình thực hiện các hành động trong một **Môi trường (Environment)**, nhận về tín hiệu **Thưởng/Phạt (Reward/Penalty)**, và học qua cơ chế **Thử và Sai (Trial and Error)** để tìm ra chiến lược hành động tối ưu nhất về lâu dài.

```text
               +-------------------+
               |    Environment    |
               | (Môi trường SUMO) |
               +---------+---------+
                         |
       Trạng thái s_t    |    Phần thưởng r_t
       (Số xe chờ, pha)  |    (Độ dài hàng đợi xe)
                         v
               +---------+---------+
               |       Agent       |
               | (Bộ điều khiển QN)|
               +---------+---------+
                         |
                         | Hành động a_t
                         | (Chọn pha đèn kế tiếp)
                         v
               +---------+---------+
               |    Environment    |
               +-------------------+
```

---

## 2. Quá trình Ra Quyết định Markov (Markov Decision Process - MDP)

Mọi bài toán Học tăng cường đều được hình thức hóa toán học dưới dạng một **Markov Decision Process (MDP)**, bao gồm bộ 5 thành phần $\langle \mathcal{S}, \mathcal{A}, \mathcal{P}, \mathcal{R}, \gamma \rangle$:

1. **$\mathcal{S}$ - Không gian Trạng thái (State Space)**: Tập hợp tất cả các tình huống mà Agent có thể quan sát được.
   - *Trong điều khiển giao thông*: Số lượng xe đang dừng ở mỗi nhánh ngã tư, pha đèn hiện tại đang sáng xanh, thời gian xanh đã trôi qua.
2. **$\mathcal{A}$ - Không gian Hành động (Action Space)**: Tập hợp các quyết định mà Agent có thể thực hiện.
   - *Trong điều khiển giao thông*: Chọn pha đèn tiếp theo sẽ được bật xanh (ví dụ: Pha 0: Bắc - Nam, Pha 1: Đông - Tây).
3. **$\mathcal{P}(s' \mid s, a)$ - Xác suất Chuyển trạng thái (Transition Probability)**: Xác suất môi trường chuyển từ trạng thái $s$ sang trạng thái mới $s'$ sau khi Agent thực hiện hành động $a$.
   - *Trong SUMO*: Xe cộ di chuyển, dừng lại hoặc rẽ theo mô hình động lực vi mô của SUMO.
4. **$\mathcal{R}(s, a)$ - Hàm Phần thưởng (Reward Function)**: Giá trị số thực phản hồi ngay lập tức cho biết hành động $a$ tại trạng thái $s$ là tốt hay xấu.
   - *Quy ước*: Reward càng cao càng tốt. Nếu muốn giảm tắc đường, ta đặt Reward bằng **số âm** của độ dài hàng đợi xe: $r = -\sum \text{xe dừng}$. Khi hàng đợi bằng 0, reward đạt cực đại là $0$.
5. **$\gamma$ - Hệ số Chiết khấu (Discount Factor)**: Số thực nằm trong đoạn $[0, 1)$.

### 🌟 Tính chất Markov (The Markov Property)
Một trạng thái $s_t$ được gọi là thỏa mãn tính chất Markov nếu tương lai chỉ phụ thuộc vào hiện tại, **hoàn toàn độc lập với quá khứ**:
$$\mathbb{P}(s_{t+1} \mid s_t, a_t, s_{t-1}, a_{t-1}, \dots, s_0, a_0) = \mathbb{P}(s_{t+1} \mid s_t, a_t)$$
> *Nói nôm na*: Chỉ cần bạn biết hiện tại ngã tư có bao nhiêu xe và đang bật đèn gì, bạn không cần quan tâm 1 tiếng trước ngã tư đó kẹt xe ra sao để đưa ra quyết định tối ưu.

---

## 3. Tổng Lợi nhuận Chiết khấu Tương lai (Discounted Return $G_t$)

Mục tiêu của Agent không phải là tối đa hóa phần thưởng ngay ở bước tiếp theo ($r_{t+1}$), mà là tối đa hóa **tổng phần thưởng tích lũy trong toàn bộ tương lai**, ký hiệu là $G_t$:

$$G_t = r_{t+1} + \gamma r_{t+2} + \gamma^2 r_{t+3} + \dots = \sum_{k=0}^{\infty} \gamma^k r_{t+k+1}$$

### Tại sao lại cần hệ số chiết khấu $\gamma$?
- **Toán học**: Giúp tổng chuỗi vô hạn hội tụ về một con số hữu hạn khi bài toán chạy liên tục không có hồi kết.
- **Thực tế**: "Một con chim trong tay hơn hai con chim trong bụi". Phần thưởng nhận được ngay bây giờ chắc chắn và có giá trị hơn phần thưởng chưa biết trước ở tương lai xa.
- **Hành vi**:
  - $\gamma \to 0$: Agent thiển cận (myopic), chỉ chăm chăm húp trọn reward trước mắt.
  - $\gamma \to 1$: Agent nhìn xa trông rộng (far-sighted), sẵn sàng chịu phạt ngắn hạn để gom reward lớn ở tương lai.

---

## 4. Hàm Giá trị: $V(s)$ và $Q(s, a)$

Để đánh giá một trạng thái hoặc một hành động "tốt đến mức nào", ta định nghĩa hai hàm giá trị:

### 4.1. Hàm Giá trị Trạng thái $V^\pi(s)$ (State-Value Function)
Kỳ vọng của tổng lợi nhuận $G_t$ nếu xuất phát từ trạng thái $s$ và tuân theo chính sách $\pi$:
$$V^\pi(s) = \mathbb{E}_\pi [G_t \mid s_t = s]$$
> *Ý nghĩa*: Đứng ở ngã tư trạng thái $s$, trung bình về sau ta sẽ nhận được bao nhiêu điểm thưởng?

### 4.2. Hàm Giá trị Hành động $Q^\pi(s, a)$ (Action-Value Function / Q-Function)
Đây chính là **chữ "Q"** trong **Q-Learning** và **Q-Network**! Chữ **Q** viết tắt của **Quality (Chất lượng)**.
Hàm $Q^\pi(s, a)$ là kỳ vọng tổng lợi nhuận nếu tại trạng thái $s$, ta chọn hành động $a$, và sau đó tiếp tục tuân theo chính sách $\pi$:
$$Q^\pi(s, a) = \mathbb{E}_\pi [G_t \mid s_t = s, a_t = a]$$
> *Ý nghĩa*: Tại trạng thái $s$, nếu tôi quyết định bật **Pha đèn 1**, thì tổng chất lượng tương lai mà tôi gom được là bao nhiêu?

---

## 5. Đột phá Tư duy: Phương trình Bellman (Bellman Equation)

Nhà toán học Richard Bellman (1957) đã phát minh ra nguyên lý quy hoạch động, chia nhỏ bài toán dài hạn thành hai thành phần: **Thưởng trước mắt** và **Giá trị tương lai kế tiếp**.

Nhận xét:
$$G_t = r_{t+1} + \gamma (r_{t+2} + \gamma r_{t+3} + \dots) = r_{t+1} + \gamma G_{t+1}$$

Lấy kỳ vọng hai vế, ta thu được **Phương trình Bellman cho hàm Q**:
$$Q^\pi(s, a) = \mathbb{E} \left[ r_{t+1} + \gamma Q^\pi(s_{t+1}, a_{t+1}) \;\middle|\; s_t = s, a_t = a \right]$$

### 5.1. Phương trình Tối ưu Bellman (Bellman Optimality Equation)
Nếu Agent hành động hoàn hảo (chính sách tối ưu $\pi^*$), thì ở trạng thái kế tiếp $s'$, nó sẽ luôn chọn hành động $a'$ mang lại giá trị $Q^*(s', a')$ lớn nhất:

$$\mathbf{Q^*(s, a) = r + \gamma \max_{a'} Q^*(s', a')}$$

> [!IMPORTANT]
> **Trực giác cốt lõi**:
> Giá trị thực sự của việc chọn hành động $a$ ở trạng thái $s$ bằng **Phần thưởng nhận ngay lập tức ($r$)** cộng với **Giá trị tối đa có thể đạt được ở trạng thái tiếp theo ($\max_{a'} Q^*(s', a')$)** được chiết khấu bởi $\gamma$.
> 
> Đây chính là "kim chỉ nam" của toàn bộ họ thuật toán Q-Learning, Q-Network, và Deep Q-Network!

---

## 6. Tổng kết Phần 1 & Câu hỏi Tự kiểm tra

| Khái niệm | Ký hiệu | Ý nghĩa trong Điều khiển Đèn Giao thông |
| :--- | :--- | :--- |
| **Agent** | - | Bộ điều khiển đèn tín hiệu (Controller) |
| **Environment** | - | Mạng lưới đường và xe cộ trong SUMO |
| **State** | $s$ | Vector hàng đợi xe, pha đèn hiện tại, thời gian trôi qua |
| **Action** | $a$ | Pha đèn xanh được chọn cho chu kỳ kế tiếp |
| **Reward** | $r$ | Điểm phạt (âm) theo số lượng xe dừng hoặc độ trễ |
| **Q-Value** | $Q(s, a)$ | Điểm số đánh giá độ "sáng suốt" của việc bật pha $a$ khi thấy trạng thái $s$ |

### ❓ Câu hỏi Tự ôn tập:
1. Nếu ngã tư đang có 15 xe dừng, ta chọn pha $a=0$, bước sau còn lại 5 xe dừng ($r = -5$), trạng thái mới $s'$ có giá trị tốt nhất là $\max_{a'} Q(s', a') = -20$, và $\gamma = 0.9$. Giá trị mục tiêu của $Q(s, a)$ theo Bellman là bao nhiêu?
   - *Đáp án*: $r + \gamma \max Q = -5 + 0.9 \times (-20) = -5 - 18 = -23$.

👉 **Bước tiếp theo**: Mời bạn đọc tiếp [PHẦN 2: TABULAR Q-LEARNING](file:///c:/Users/dotru/HMNC/LibSignal/docs/giao_trinh_qn/02_TABULAR_Q_LEARNING.md) để xem cách lưu trữ và cập nhật giá trị Q trong một bảng số cụ thể!
