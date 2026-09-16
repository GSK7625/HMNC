# 📚 GIÁO TRÌNH TOÀN DIỆN: THUẬT TOÁN QN & DEEP Q-NETWORK (DQN)
## Từ Nền tảng Lý thuyết Cơ bản nhất đến Mã nguồn Thực chiến trong LibSignal

Chào mừng bạn đến với bộ tài liệu tự học toàn diện về thuật toán **Q-Network (QN)** và **Deep Q-Network (DQN)**. Bộ giáo trình này được thiết kế theo cấu trúc mô-đun hóa, dẫn dắt bạn đi từ những khái niệm trực quan ban đầu của Học tăng cường (Reinforcement Learning - RL) cho đến việc tự tay đọc hiểu, vận hành và tùy biến mã nguồn điều khiển giao thông bằng Deep RL trong dự án **LibSignal**.

---

## 🗺️ Bản đồ Lộ trình Học tập (Roadmap)

```text
┌─────────────────────────────────────────────────────────────┐
│  Phần 1: Nền tảng Học tăng cường & Phương trình Bellman     │
│  - Agent, Environment, State, Action, Reward                │
│  - MDP, Discount Factor γ, Hàm giá trị V(s) và Q(s, a)      │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│  Phần 2: Tabular Q-Learning (Bảng tra cứu Q)                │
│  - Bảng ma trận Q[s, a] & Thuật toán cập nhật TD(0)         │
│  - Chiến lược thăm dò ε-greedy                              │
│  - Bài tập tính nhẩm số học từng bước bằng tay             │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│  Phần 3: Bước nhảy vọt: Từ Bảng Q sang Q-Network (QN)       │
│  - Giới hạn bộ nhớ: "Lời nguyền số chiều"                   │
│  - Mạng nơ-ron đóng vai trò xấp xỉ hàm (Function Approximator)│
│  - Hàm mất mát Bellman Regression & Lan truyền ngược         │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│  Phần 4: Deep Q-Network (DQN) - Khắc phục Bất ổn định       │
│  - Vấn đề phân kỳ: "Tam giác chết chóc" (Deadly Triad)       │
│  - Vũ khí 1: Bộ nhớ đệm trải nghiệm (Experience Replay)     │
│  - Vũ khí 2: Mạng mục tiêu đóng băng (Target Network)       │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│  Phần 5: Các Cải tiến Chuyên sâu (Double DQN & Optimization) │
│  - Thổi phồng giá trị (Overestimation Bias) của phép max    │
│  - Thuật toán Double DQN (Tách chọn hành động & định giá)   │
│  - Huber Loss & Gradient Clipping giúp huấn luyện ổn định    │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│  Phần 6: Thực chiến & Mổ xẻ Mã nguồn LibSignal              │
│  - Phân tích chi tiết `q_learning.py` và `dqn.py`            │
│  - Trích xuất đặc trưng ngã tư (Hàng đợi, Mật độ, Pha đèn)  │
│  - Lệnh CLI huấn luyện, phân tích đồ thị Loss / Reward       │
└─────────────────────────────────────────────────────────────┘
```

---

## 📑 Danh mục Tài liệu Chi tiết

| Bài học | Tên tài liệu | Chủ đề cốt lõi | Mục tiêu đầu ra |
| :--- | :--- | :--- | :--- |
| **Phần 1** | [01_NEN_TANG_RL_VA_BELLMAN.md](file:///c:/Users/dotru/HMNC/LibSignal/docs/giao_trinh_qn/01_NEN_TANG_RL_VA_BELLMAN.md) | Khái niệm Agent, Môi trường, MDP, Hàm $Q(s, a)$, Phương trình Bellman | Hiểu được cách mô hình hóa bài toán ra quyết định theo thời gian |
| **Phần 2** | [02_TABULAR_Q_LEARNING.md](file:///c:/Users/dotru/HMNC/LibSignal/docs/giao_trinh_qn/02_TABULAR_Q_LEARNING.md) | Bảng Q-table, Cập nhật sai số TD, Khám phá $\epsilon$-greedy | Tự tính nhẩm được giá trị Q thay đổi qua từng bước thời gian |
| **Phần 3** | [03_TU_BANG_Q_SANG_Q_NETWORK.md](file:///c:/Users/dotru/HMNC/LibSignal/docs/giao_trinh_qn/03_TU_BANG_Q_SANG_Q_NETWORK.md) | Curse of Dimensionality, Mạng nơ-ron Q-Network, Mean Squared Bellman Error | Hiểu lý do và cách mạng nơ-ron thay thế bảng tra cứu |
| **Phần 4** | [04_DEEP_Q_NETWORK_DQN.md](file:///c:/Users/dotru/HMNC/LibSignal/docs/giao_trinh_qn/04_DEEP_Q_NETWORK_DQN.md) | Bất ổn định huấn luyện, Replay Buffer, Target Network, DeepMind 2015 | Nắm trọn vẹn thuật toán DQN nguyên bản đột phá của DeepMind |
| **Phần 5** | [05_CAI_TIEN_DOUBLE_DQN.md](file:///c:/Users/dotru/HMNC/LibSignal/docs/giao_trinh_qn/05_CAI_TIEN_DOUBLE_DQN.md) | Overestimation Bias, Công thức Double DQN, Smooth L1 Loss, Gradient Clip | Làm chủ các kỹ thuật giúp mạng hội tụ ổn định và không lệch giá trị |
| **Phần 6** | [06_THUC_CHIEN_LIBSIGNAL.md](file:///c:/Users/dotru/HMNC/LibSignal/docs/giao_trinh_qn/06_THUC_CHIEN_LIBSIGNAL.md) | Phân tích từng dòng PyTorch trong `dqn.py`, Vector quan sát đèn SUMO | Đọc hiểu và làm chủ hoàn toàn code dự án `LibSignal` |

---

## 💡 Phương pháp Học tập Khuyến nghị

1. **Học tuần tự từng phần**: Không nên nhảy cóc từ Phần 1 sang Phần 6. Toàn bộ logic của Deep Q-Network đều bắt nguồn từ trực giác của Phương trình Bellman và Tabular Q-Learning.
2. **Tự làm bài tập tính nhẩm**: Ở Phần 2, hãy lấy giấy bút tự tính tay theo ví dụ số học được cung cấp. Cảm giác nhìn thấy một con số trong ô bảng $Q[s, a]$ nhích dần theo reward sẽ giúp bạn thấm nhuần thuật toán.
3. **Đối chiếu song song với code**: Khi đọc đến Phần 6, hãy mở đồng thời file [traffic_control/controllers/dqn.py](file:///c:/Users/dotru/HMNC/LibSignal/src/traffic_control/controllers/dqn.py) trong IDE để quan sát sự tương ứng giữa ký hiệu toán học và câu lệnh Python.
4. **Chạy thử nghiệm kiểm chứng**: Thực thi các lệnh huấn luyện được đề xuất trong Phần 6 và theo dõi sự thay đổi của hàm Loss và Reward qua các Episode.
