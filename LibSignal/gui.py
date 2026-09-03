"""SUMO Traffic Signal Control - Giao diện đồ họa phong cách Gà Thức Đêm (Sleepy Chicken Theme).

Thiết kế giao diện trực quan lấy cảm hứng từ chú gà cú đêm mất ngủ cày mô phỏng:
- Mascot: Avatar chú gà thức đêm (mắt thâm quầng) với bong bóng thoại sinh động.
- Tông màu: Kem trứng sketch ấm áp (#FFFBF5), thẻ trắng ngà (#FFFFFF), viền cam mật ong (#FDBA74).
- Màu chữ tương phản cao: Mực đen phác thảo (#1C1917) và cam cháy đậm (#C2410C) - sắc nét, không bị nền làm mờ!
- Họa tiết chủ đề: Dấu chân gà bước qua màn hình, hạt thóc, quả trứng, ổ rơm hoạt hình.
- Đầy đủ 100% chức năng: Benchmark, Chạy đơn lẻ, Train QL, Test, Live Log & Bảng thành tích.
"""

from __future__ import annotations

import csv
import os
import queue
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

# Thiết lập đường dẫn gốc
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
RUN_PY = ROOT / "run.py"
RAW_DATA_DIR = ROOT / "data" / "raw_data"
RESULTS_DIR = ROOT / "results"
ASSETS_DIR = ROOT / "assets"
AVATAR_PATH = ASSETS_DIR / "chicken_avatar.png"

# Nạp controller registry
try:
    from src.traffic_control.controllers import CONTROLLER_REGISTRY
except Exception:
    CONTROLLER_REGISTRY = None


def find_available_scenarios() -> list[tuple[str, Path]]:
    """Tự động tìm kiếm tất cả các file kịch bản .sumocfg trong data/raw_data."""
    scenarios: list[tuple[str, Path]] = []
    if RAW_DATA_DIR.is_dir():
        for cfg in sorted(RAW_DATA_DIR.rglob("*.sumocfg")):
            folder_name = cfg.parent.name
            display_name = f"{folder_name} ({cfg.name})"
            if folder_name == "cologne1":
                display_name = f"Cologne 1 (Mặc định) - {cfg.name}"
            elif folder_name == "cologne3":
                display_name = f"Cologne 3 - {cfg.name}"
            elif folder_name == "ingolstadt21":
                display_name = f"Ingolstadt 21 - {cfg.name}"
            elif folder_name == "manhattan_28x7":
                display_name = f"Manhattan (28x7) - {cfg.name}"
            elif "atlanta" in folder_name:
                display_name = f"Atlanta (1x5) - {cfg.name}"
            elif "hangzhou" in folder_name:
                display_name = f"Hangzhou - {cfg.name}"
            scenarios.append((display_name, cfg))

    # Đưa Cologne 1 lên đầu danh sách làm mặc định
    scenarios.sort(key=lambda item: (0 if "cologne1" in item[0].lower() else 1, item[0]))

    if not scenarios:
        default_cfg = RAW_DATA_DIR / "cologne1" / "cologne1.sumocfg"
        scenarios.append(("Cologne 1 (Mặc định)", default_cfg))
    return scenarios


class ChickenTracksCanvas(tk.Canvas):
    """Họa tiết dấu chân gà và hạt thóc chạy ngang phân cách giao diện."""

    def __init__(self, master, height=20, bg="#FFFBF5", **kwargs):
        super().__init__(master, height=height, bg=bg, highlightthickness=0, **kwargs)
        self.bind("<Configure>", self._draw)

    def _draw(self, event=None):
        self.delete("all")
        w = self.winfo_width()
        if w <= 1:
            w = 1100

        # Vẽ các dấu chân gà bước đi zíc zắc
        step = 42
        x = 16
        idx = 0
        while x < w - 20:
            y = 7 if (idx % 2 == 0) else 13
            offset = -1 if (idx % 2 == 0) else 1

            # Dấu chân gà: 3 ngón trước, 1 cựa sau
            color = "#EA580C" if (idx % 3 == 0) else "#D97706"
            self.create_line(x, y, x + 8, y + offset, fill=color, width=2)
            self.create_line(x, y, x + 6, y - 5 + offset, fill=color, width=1.5)
            self.create_line(x, y, x + 6, y + 5 + offset, fill=color, width=1.5)
            self.create_line(x, y, x - 4, y, fill=color, width=1.5)

            # Hạt thóc nhỏ rơi vãi giữa các bước chân
            if idx % 2 == 1:
                gx = x + 20
                gy = y - 2
                self.create_oval(gx - 2, gy - 1, gx + 2, gy + 1, fill="#F59E0B", outline="#D97706")

            x += step
            idx += 1


class SumoChickenApp(tk.Tk):
    """Ứng dụng GUI phong cách Chú Gà Thức Đêm (Sleepy Chicken) điều khiển mô phỏng SUMO."""

    def __init__(self):
        super().__init__()
        self.title("SUMO Traffic Control - Giao Diện Gà Cú Đêm 🐔💤")
        self.geometry("1080x800")
        self.minsize(940, 700)

        # Quản lý hình ảnh avatar chú gà thức đêm
        self.avatar_img: tk.PhotoImage | None = None
        if AVATAR_PATH.is_file():
            try:
                self.avatar_img = tk.PhotoImage(file=str(AVATAR_PATH))
            except Exception:
                self.avatar_img = None

        # Bảng màu Sleepy Chicken tương phản cao (chữ cực kỳ sắc nét, không bị mờ)
        self.c_bg = "#FFFBF5"            # Nền kem giấy phác thảo ấm áp
        self.c_card = "#FFFFFF"          # Trắng tinh khôi cho các khối thẻ
        self.c_card_inner = "#FFF8ED"    # Khối con nền vàng kem nhạt
        self.c_border = "#FED7AA"        # Viền cam mật ong ngọt ngào
        self.c_border_dark = "#F97316"   # Viền cam đậm nổi bật

        # Màu chữ mực đen và cam đậm (Độ tương phản cao, chống nhòe mờ hoàn toàn):
        self.c_text = "#1C1917"          # Mực đen phác thảo đậm (contrast > 15:1)
        self.c_text_title = "#9A3412"    # Nâu cam cháy đậm tiêu đề
        self.c_text_muted = "#57534E"    # Xám than ấm áp dễ đọc
        self.c_orange = "#EA580C"        # Cam mào gà tươi tắn
        self.c_orange_hover = "#C2410C"  # Cam đậm khi hover
        self.c_red = "#DC2626"           # Đỏ mào gà (Dừng / Lỗi)
        self.c_red_hover = "#B91C1C"     # Đỏ đậm khi hover
        self.c_yellow_gold = "#D97706"   # Vàng mỏ gà nổi bật
        self.c_green = "#15803D"         # Xanh đèn giao thông lá mạ đậm
        self.c_console = "#1C1917"       # Nền console mực đen cà phê

        self._setup_styles()

        # Quản lý tiến trình chạy
        self.running_process: subprocess.Popen | None = None
        self.log_queue: queue.Queue = queue.Queue()
        self.active_output_dir: Path | None = None

        # Danh sách kịch bản & controllers
        self.scenarios = find_available_scenarios()
        self.scenario_map = {name: path for name, path in self.scenarios}
        self.controllers_info = self._get_controllers_info()

        # Xây dựng các widget giao diện
        self._build_ui()

        # Lắng nghe log luồng ngầm
        self.after(100, self._process_log_queue)

        # Cập nhật xem trước câu lệnh
        self._update_preview_command()

    def _setup_styles(self):
        """Cấu hình phong cách doodle hoạt hình dễ thương & độ tương phản sắc nét."""
        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        self.configure(bg=self.c_bg)

        # Cấu hình chung cho ttk với chữ mực đen đậm sắc nét
        self.style.configure(".", background=self.c_bg, foreground=self.c_text, font=("Segoe UI", 9))
        self.style.configure("TNotebook", background=self.c_bg, borderwidth=0)
        self.style.configure(
            "TNotebook.Tab",
            font=("Segoe UI", 10, "bold"),
            padding=[18, 8],
            background="#FDE68A",
            foreground="#78350F",
        )
        self.style.map(
            "TNotebook.Tab",
            background=[("selected", "#FFFFFF"), ("!selected", "#FDE68A")],
            foreground=[("selected", self.c_orange), ("!selected", "#78350F")],
        )

        self.style.configure(
            "ChickenCard.TLabelframe",
            background=self.c_card,
            bordercolor=self.c_border,
            relief=tk.SOLID,
            borderwidth=1,
            padding=12,
        )
        self.style.configure(
            "ChickenCard.TLabelframe.Label",
            background=self.c_card,
            font=("Segoe UI", 10, "bold"),
            foreground=self.c_text_title,
        )

        # Cấu hình combobox & spinbox rõ chữ
        self.style.configure(
            "Chicken.TCombobox",
            fieldbackground="#FFFFFF",
            background="#FDBA74",
            foreground=self.c_text,
            arrowcolor="#EA580C",
            padding=3,
        )
        self.style.map(
            "Chicken.TCombobox",
            fieldbackground=[("readonly", "#FFFFFF")],
            foreground=[("readonly", self.c_text)],
            selectbackground=[("readonly", "#FED7AA")],
            selectforeground=[("readonly", self.c_text)],
        )

        self.style.configure(
            "Chicken.TSpinbox",
            fieldbackground="#FFFFFF",
            background="#FDBA74",
            foreground=self.c_text,
            arrowcolor="#EA580C",
            padding=3,
        )
        self.style.map(
            "Chicken.TSpinbox",
            fieldbackground=[("readonly", "#FFFFFF")],
            foreground=[("readonly", self.c_text)],
        )

        self.style.configure(
            "Treeview.Heading",
            font=("Segoe UI", 9, "bold"),
            background="#FEF3C7",
            foreground="#78350F",
            padding=6,
        )
        self.style.configure(
            "Treeview",
            font=("Segoe UI", 9),
            rowheight=28,
            background="#FFFFFF",
            fieldbackground="#FFFFFF",
            foreground=self.c_text,
        )
        self.style.map(
            "Treeview",
            background=[("selected", "#FED7AA")],
            foreground=[("selected", "#78350F")],
        )

    def _get_controllers_info(self) -> dict[str, str]:
        info = {}
        if CONTROLLER_REGISTRY:
            for name, meta in CONTROLLER_REGISTRY.get_all().items():
                alias_str = f" ({', '.join(meta.aliases)})" if meta.aliases else ""
                info[name] = f"{meta.display_name}{alias_str}"
        if not info:
            info = {
                "fixedtime": "Fixed-Time (ft)",
                "maxpressure": "Max-Pressure (mp)",
                "qlearning": "Q-Learning (ql)",
            }
        return info

    def _build_ui(self):
        """Khung giao diện với Header Chú Gà Thức Đêm và Bong Bóng Thoại."""
        # =========================================================
        # 1. HEADER CHÚ GÀ THỨC ĐÊM
        # =========================================================
        header_card = tk.Frame(self, bg="#FFFFFF", padx=16, pady=10, relief=tk.SOLID, bd=1, highlightbackground=self.c_border, highlightthickness=1)
        header_card.pack(side=tk.TOP, fill=tk.X, padx=12, pady=(10, 4))

        # Avatar chú gà bên trái (Khung bo viền hoạt hình)
        avatar_frame = tk.Frame(header_card, bg="#FED7AA", padx=3, pady=3, relief=tk.SOLID, bd=1)
        avatar_frame.pack(side=tk.LEFT, padx=(0, 14))

        if self.avatar_img:
            lbl_avatar = tk.Label(avatar_frame, image=self.avatar_img, bg="#FFFFFF", bd=0)
            lbl_avatar.pack()
        else:
            lbl_avatar = tk.Label(avatar_frame, text="🐔\n💤", font=("Segoe UI Emoji", 26), bg="#FFFFFF", fg=self.c_orange)
            lbl_avatar.pack(padx=10, pady=6)

        # Khối tiêu đề và lời nhắn của chú gà thức đêm
        text_box = tk.Frame(header_card, bg="#FFFFFF")
        text_box.pack(side=tk.LEFT, fill=tk.Y, expand=True, anchor="w")

        title_row = tk.Frame(text_box, bg="#FFFFFF")
        title_row.pack(anchor="w")

        title_label = tk.Label(
            title_row,
            text="CHICKEN TRAFFIC CONTROL - GIAO DIỆN GÀ CÚ ĐÊM 🐔💤",
            font=("Segoe UI", 12, "bold"),
            bg="#FFFFFF",
            fg=self.c_text_title,
        )
        title_label.pack(side=tk.LEFT)

        sub_label = tk.Label(
            text_box,
            text="Hệ thống điều phối tín hiệu đèn giao thông thông minh với SUMO & TraCI",
            font=("Segoe UI", 9),
            bg="#FFFFFF",
            fg=self.c_text_muted,
        )
        sub_label.pack(anchor="w", pady=(1, 3))

        # Bong bóng thoại của chú gà (Mascot Speech Bubble với viền cam ấm)
        self.bubble_frame = tk.Frame(
            text_box,
            bg="#FFF7ED",
            padx=12,
            pady=5,
            relief=tk.SOLID,
            bd=1,
            highlightbackground="#FDBA74",
            highlightthickness=1,
        )
        self.bubble_frame.pack(anchor="w", fill=tk.X)

        self.lbl_quote = tk.Label(
            self.bubble_frame,
            text="🐔 Gà tỉnh queo: \"Đêm nay quyết cày xong mô phỏng đèn giao thông, mắt thâm quầng cũng chịu!\"",
            font=("Segoe UI", 9, "italic", "bold"),
            bg="#FFF7ED",
            fg="#9A3412",
        )
        self.lbl_quote.pack(anchor="w")

        # Huy hiệu trạng thái bên phải
        right_box = tk.Frame(header_card, bg="#FFFFFF")
        right_box.pack(side=tk.RIGHT, fill=tk.Y, padx=(8, 0))

        self.status_badge = tk.Label(
            right_box,
            text="● TỈNH TÁO (SẴN SÀNG)",
            font=("Segoe UI", 9, "bold"),
            bg="#DCFCE7",
            fg="#166534",
            padx=14,
            pady=8,
            relief=tk.SOLID,
            bd=1,
        )
        self.status_badge.pack(anchor="e", pady=4)

        # Họa tiết dấu chân gà chạy ngang trang trí
        chicken_tracks = ChickenTracksCanvas(self, height=18, bg=self.c_bg)
        chicken_tracks.pack(fill=tk.X, padx=12, pady=(2, 6))

        # =========================================================
        # 2. NOTEBOOK TABS
        # =========================================================
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 10))

        # Tab 1: Cấu hình & Chạy
        self.tab_config = tk.Frame(self.notebook, bg=self.c_bg)
        self.notebook.add(self.tab_config, text="🐣 Bàn Luyện Gà (Cấu Hình)")

        # Tab 2: Live Log
        self.tab_logs = tk.Frame(self.notebook, bg=self.c_bg)
        self.notebook.add(self.tab_logs, text="📜 Nhật Ký Cày Đêm (Live Log)")

        # Tab 3: Bảng xếp hạng kết quả
        self.tab_results = tk.Frame(self.notebook, bg=self.c_bg)
        self.notebook.add(self.tab_results, text="🏆 Bảng Thành Tích Chuồng Gà (Kết Quả)")

        self._build_config_tab()
        self._build_logs_tab()
        self._build_results_tab()

    # -------------------------------------------------------------
    # TAB 1: CẤU HÌNH & CHẠY MÔ PHỎNG
    # -------------------------------------------------------------
    def _build_config_tab(self):
        canvas = tk.Canvas(self.tab_config, bg=self.c_bg, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.tab_config, orient="vertical", command=canvas.yview)
        scroll_content = tk.Frame(canvas, bg=self.c_bg)

        scroll_content.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas_window = canvas.create_window((0, 0), window=scroll_content, anchor="nw")

        def _on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind("<Configure>", _on_canvas_configure)

        canvas.configure(xscrollcommand=None, yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 1. Khung chọn chế độ thí nghiệm
        mode_frame = ttk.LabelFrame(scroll_content, text=" 🎯 1. CHỌN GÀ RA SÂN (CHẾ ĐỘ THÍ NGHIỆM) ", style="ChickenCard.TLabelframe")
        mode_frame.pack(fill=tk.X, padx=10, pady=6)

        self.var_mode = tk.StringVar(value="benchmark")
        self.var_mode.trace_add("write", lambda *args: self._on_mode_change())

        modes = [
            ("benchmark", "🥊 So sánh Gà Chiến (Benchmark FT vs MP vs Q-Learning đối đầu trực tiếp)", True),
            ("single", "🏃 Cho 1 chú gà ra sân (Solo Evaluation Test)", False),
            ("train_ql", "🧠 Luyện Gà Thông Minh (Huấn luyện Q-Learning cày cuốc qua nhiều Episode)", False),
            ("test", "🧪 Kiểm tra sức khỏe đàn gà (Chạy Unit Tests tự động toàn hệ thống)", False),
        ]
        for val, text, is_bold in modes:
            rb = tk.Radiobutton(
                mode_frame,
                text=text,
                value=val,
                variable=self.var_mode,
                bg=self.c_card,
                activebackground=self.c_card_inner,
                fg=self.c_text,
                selectcolor="#FED7AA",
                font=("Segoe UI", 9, "bold" if is_bold else "normal"),
                padx=4,
                pady=2,
            )
            rb.pack(anchor="w")

        # Khung con chế độ Benchmark
        self.sub_benchmark_frame = tk.Frame(mode_frame, bg=self.c_card_inner, padx=16, pady=6, relief=tk.SOLID, bd=1)
        self.sub_benchmark_frame.pack(fill=tk.X, pady=(4, 2))
        tk.Label(
            self.sub_benchmark_frame,
            text="Chọn các ứng viên gà chiến tham gia so tài:",
            bg=self.c_card_inner,
            fg=self.c_text_muted,
            font=("Segoe UI", 9, "italic", "bold"),
        ).pack(anchor="w")

        self.bench_vars = {}
        bench_btn_row = tk.Frame(self.sub_benchmark_frame, bg=self.c_card_inner)
        bench_btn_row.pack(anchor="w", pady=4)
        for name, label in self.controllers_info.items():
            var = tk.BooleanVar(value=True)
            self.bench_vars[name] = var
            cb = tk.Checkbutton(
                bench_btn_row,
                text=f"🐥 {label}",
                variable=var,
                bg=self.c_card_inner,
                activebackground=self.c_card,
                fg=self.c_text,
                selectcolor="#FED7AA",
                font=("Segoe UI", 9, "bold"),
                command=self._update_preview_command,
            )
            cb.pack(side=tk.LEFT, padx=(0, 16))

        # Khung con chế độ Single
        self.sub_single_frame = tk.Frame(mode_frame, bg=self.c_card_inner, padx=16, pady=6, relief=tk.SOLID, bd=1)
        tk.Label(
            self.sub_single_frame,
            text="Thuật toán gà ra sân:",
            bg=self.c_card_inner,
            fg=self.c_text,
            font=("Segoe UI", 9, "bold"),
        ).pack(side=tk.LEFT, padx=4)
        self.var_single_controller = tk.StringVar(value="fixedtime")
        controller_options = list(self.controllers_info.keys())
        self.cb_single_controller = ttk.Combobox(
            self.sub_single_frame,
            textvariable=self.var_single_controller,
            values=controller_options,
            state="readonly",
            style="Chicken.TCombobox",
            width=24,
        )
        self.cb_single_controller.pack(side=tk.LEFT, padx=6)
        self.cb_single_controller.bind("<<ComboboxSelected>>", lambda e: self._update_preview_command())

        # Khung con chế độ Train QL
        self.sub_train_frame = tk.Frame(mode_frame, bg=self.c_card_inner, padx=16, pady=6, relief=tk.SOLID, bd=1)
        t_grid = tk.Frame(self.sub_train_frame, bg=self.c_card_inner)
        t_grid.pack(anchor="w")

        tk.Label(t_grid, text="Số Episodes:", bg=self.c_card_inner, fg=self.c_text, font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", padx=4, pady=2)
        self.var_episodes = tk.IntVar(value=5)
        ttk.Spinbox(t_grid, from_=1, to=100, textvariable=self.var_episodes, width=8, style="Chicken.TSpinbox", command=self._update_preview_command).grid(row=0, column=1, padx=4, pady=2)

        tk.Label(t_grid, text="Alpha (Học):", bg=self.c_card_inner, fg=self.c_text, font=("Segoe UI", 9, "bold")).grid(row=0, column=2, sticky="w", padx=10, pady=2)
        self.var_alpha = tk.DoubleVar(value=0.1)
        ttk.Entry(t_grid, textvariable=self.var_alpha, width=8).grid(row=0, column=3, padx=4, pady=2)

        tk.Label(t_grid, text="Gamma (Chiết khấu):", bg=self.c_card_inner, fg=self.c_text, font=("Segoe UI", 9, "bold")).grid(row=0, column=4, sticky="w", padx=10, pady=2)
        self.var_gamma = tk.DoubleVar(value=0.9)
        ttk.Entry(t_grid, textvariable=self.var_gamma, width=8).grid(row=0, column=5, padx=4, pady=2)

        tk.Label(t_grid, text="Epsilon (Khám phá):", bg=self.c_card_inner, fg=self.c_text, font=("Segoe UI", 9, "bold")).grid(row=1, column=0, sticky="w", padx=4, pady=4)
        self.var_epsilon = tk.DoubleVar(value=0.05)
        ttk.Entry(t_grid, textvariable=self.var_epsilon, width=8).grid(row=1, column=1, padx=4, pady=4)

        tk.Label(t_grid, text="File lưu Bảng Q:", bg=self.c_card_inner, fg=self.c_text, font=("Segoe UI", 9, "bold")).grid(row=1, column=2, sticky="w", padx=10, pady=4)
        self.var_q_table = tk.StringVar(value="checkpoints/q_table.json")
        ttk.Entry(t_grid, textvariable=self.var_q_table, width=28).grid(row=1, column=3, columnspan=3, sticky="w", padx=4, pady=4)

        # 2. Khung chọn bản đồ
        map_frame = ttk.LabelFrame(scroll_content, text=" 🗺️ 2. ĐỊA BÀN HOẠT ĐỘNG (BẢN ĐỒ / SCENARIO) ", style="ChickenCard.TLabelframe")
        map_frame.pack(fill=tk.X, padx=10, pady=6)

        map_top = tk.Frame(map_frame, bg=self.c_card)
        map_top.pack(fill=tk.X, pady=4)

        tk.Label(map_top, text="Kịch bản mạng lưới:", bg=self.c_card, fg=self.c_text, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=4)
        self.var_scenario_name = tk.StringVar(value=self.scenarios[0][0])
        scenario_display_names = [name for name, _ in self.scenarios]
        self.cb_scenario = ttk.Combobox(
            map_top,
            textvariable=self.var_scenario_name,
            values=scenario_display_names,
            state="readonly",
            style="Chicken.TCombobox",
            width=48,
        )
        self.cb_scenario.pack(side=tk.LEFT, padx=6)
        self.cb_scenario.bind("<<ComboboxSelected>>", lambda e: self._on_scenario_selected())

        btn_browse_map = tk.Button(
            map_top,
            text="🌾 Chọn file .sumocfg khác...",
            bg="#FEF3C7",
            fg="#92400E",
            activebackground="#FDE68A",
            activeforeground="#78350F",
            font=("Segoe UI", 9, "bold"),
            relief=tk.SOLID,
            bd=1,
            padx=10,
            pady=3,
            cursor="hand2",
            command=self._browse_custom_map,
        )
        btn_browse_map.pack(side=tk.LEFT, padx=6)

        self.var_custom_scenario_path = tk.StringVar(value=str(self.scenarios[0][1]))
        lbl_path = tk.Label(
            map_frame,
            textvariable=self.var_custom_scenario_path,
            bg="#FEF3C7",
            fg="#92400E",
            font=("Consolas", 8, "bold"),
            anchor="w",
            padx=8,
            pady=4,
            relief=tk.SOLID,
            bd=1,
        )
        lbl_path.pack(fill=tk.X, padx=6, pady=(2, 4))

        # 3. Khung tham số cày cuốc
        param_frame = ttk.LabelFrame(scroll_content, text=" ⚙️ 3. THỜI GIAN CÀY CUỐC & TỐC ĐỘ (THAM SỐ) ", style="ChickenCard.TLabelframe")
        param_frame.pack(fill=tk.X, padx=10, pady=6)

        grid_p = tk.Frame(param_frame, bg=self.c_card)
        grid_p.pack(fill=tk.X, pady=4)

        # Hàng 1: Thời gian chạy
        tk.Label(grid_p, text="Thời gian chạy (giây):", bg=self.c_card, fg=self.c_text, font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", padx=6, pady=4)
        self.var_steps = tk.IntVar(value=900)
        self.ent_steps = ttk.Spinbox(grid_p, from_=10, to=10000, increment=100, textvariable=self.var_steps, width=10, style="Chicken.TSpinbox", command=self._update_preview_command)
        self.ent_steps.grid(row=0, column=1, sticky="w", padx=4, pady=4)
        self.ent_steps.bind("<KeyRelease>", lambda e: self._update_preview_command())

        # Các nút chọn nhanh thời gian kiểu quả trứng gà
        quick_step_frame = tk.Frame(grid_p, bg=self.c_card)
        quick_step_frame.grid(row=0, column=2, columnspan=3, sticky="w", padx=8)
        for s in [100, 300, 900, 1800]:
            b = tk.Button(
                quick_step_frame,
                text=f"🥚 {s}s",
                bg="#FEF3C7",
                fg="#92400E",
                activebackground="#FDE68A",
                activeforeground="#78350F",
                font=("Consolas", 9, "bold"),
                relief=tk.SOLID,
                bd=1,
                padx=8,
                pady=2,
                cursor="hand2",
                command=lambda val=s: self._set_steps(val)
            )
            b.pack(side=tk.LEFT, padx=3)

        # Hàng 2: Chu kỳ đổi đèn
        tk.Label(grid_p, text="Chu kỳ đổi đèn (action interval s):", bg=self.c_card, fg=self.c_text, font=("Segoe UI", 9, "bold")).grid(row=1, column=0, sticky="w", padx=6, pady=4)
        self.var_action_interval = tk.IntVar(value=10)
        ttk.Spinbox(grid_p, from_=1, to=60, textvariable=self.var_action_interval, width=10, style="Chicken.TSpinbox", command=self._update_preview_command).grid(row=1, column=1, sticky="w", padx=4, pady=4)

        tk.Label(grid_p, text="Xanh tối thiểu an toàn G_min (s):", bg=self.c_card, fg=self.c_text, font=("Segoe UI", 9, "bold")).grid(row=1, column=2, sticky="w", padx=12, pady=4)
        self.var_min_green = tk.DoubleVar(value=10.0)
        ttk.Entry(grid_p, textvariable=self.var_min_green, width=8).grid(row=1, column=3, sticky="w", padx=4, pady=4)

        # Hàng 3: Xanh cố định FT, Vàng, Seed
        tk.Label(grid_p, text="Xanh cố định FT (fixed green s):", bg=self.c_card, fg=self.c_text, font=("Segoe UI", 9, "bold")).grid(row=2, column=0, sticky="w", padx=6, pady=4)
        self.var_fixed_green = tk.DoubleVar(value=30.0)
        ttk.Entry(grid_p, textvariable=self.var_fixed_green, width=10).grid(row=2, column=1, sticky="w", padx=4, pady=4)

        tk.Label(grid_p, text="Thời gian đèn vàng (s):", bg=self.c_card, fg=self.c_text, font=("Segoe UI", 9, "bold")).grid(row=2, column=2, sticky="w", padx=12, pady=4)
        self.var_yellow = tk.DoubleVar(value=5.0)
        ttk.Entry(grid_p, textvariable=self.var_yellow, width=8).grid(row=2, column=3, sticky="w", padx=4, pady=4)

        tk.Label(grid_p, text="Random Seed:", bg=self.c_card, fg=self.c_text, font=("Segoe UI", 9, "bold")).grid(row=2, column=4, sticky="w", padx=12, pady=4)
        self.var_seed = tk.IntVar(value=0)
        ttk.Entry(grid_p, textvariable=self.var_seed, width=8).grid(row=2, column=5, sticky="w", padx=4, pady=4)

        # SUMO GUI Checkbox & Delay
        gui_row = tk.Frame(param_frame, bg=self.c_card)
        gui_row.pack(fill=tk.X, pady=6)

        self.var_gui = tk.BooleanVar(value=False)
        self.cb_gui = tk.Checkbutton(
            gui_row,
            text="🖥️ Mở cửa sổ SUMO-GUI để nhìn xe chạy thực tế (-g)",
            variable=self.var_gui,
            font=("Segoe UI", 9, "bold"),
            bg=self.c_card,
            activebackground=self.c_card_inner,
            fg="#C2410C",
            selectcolor="#FED7AA",
            command=self._on_gui_checkbox_toggled,
        )
        self.cb_gui.pack(side=tk.LEFT, padx=6)

        self.delay_frame = tk.Frame(gui_row, bg=self.c_card)
        tk.Label(self.delay_frame, text="Tốc độ xe chạy (Step Delay s):", bg=self.c_card, fg=self.c_text, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=6)
        self.var_delay = tk.DoubleVar(value=0.03)
        self.sp_delay = ttk.Spinbox(self.delay_frame, from_=0.0, to=1.0, increment=0.01, textvariable=self.var_delay, width=6, style="Chicken.TSpinbox", command=self._update_preview_command)
        self.sp_delay.pack(side=tk.LEFT)

        # 4. Preview CLI command
        preview_frame = ttk.LabelFrame(scroll_content, text=" 💻 4. BẢNG MÃ LỆNH CÀY ĐÊM (CLI PREVIEW) ", style="ChickenCard.TLabelframe")
        preview_frame.pack(fill=tk.X, padx=10, pady=6)

        self.var_preview_cmd = tk.StringVar()
        ent_cmd = tk.Entry(
            preview_frame,
            textvariable=self.var_preview_cmd,
            font=("Consolas", 9, "bold"),
            bg=self.c_console,
            fg="#FDE047",
            relief=tk.SOLID,
            bd=1,
            readonlybackground=self.c_console,
            state="readonly",
        )
        ent_cmd.pack(fill=tk.X, padx=6, pady=6)

        # 5. Thanh nút bấm điều khiển
        btn_bar = tk.Frame(scroll_content, bg=self.c_bg)
        btn_bar.pack(fill=tk.X, padx=10, pady=12)

        self.btn_run = tk.Button(
            btn_bar,
            text="🚀 GÁY LÊN NÀO! BẮT ĐẦU CÀY MÔ PHỎNG",
            font=("Segoe UI", 11, "bold"),
            bg=self.c_orange,
            fg="#FFFFFF",
            activebackground=self.c_orange_hover,
            activeforeground="#FFFFFF",
            padx=22,
            pady=10,
            relief=tk.RAISED,
            bd=2,
            cursor="hand2",
            command=self.start_simulation,
        )
        self.btn_run.pack(side=tk.LEFT, padx=6)

        self.btn_stop = tk.Button(
            btn_bar,
            text="🛑 DỪNG LẠI! CHO GÀ NGHỈ NGƠI",
            font=("Segoe UI", 10, "bold"),
            bg="#E7E5E4",
            fg="#78716C",
            padx=18,
            pady=10,
            relief=tk.FLAT,
            bd=1,
            state=tk.DISABLED,
            command=self.stop_simulation,
        )
        self.btn_stop.pack(side=tk.LEFT, padx=6)

        btn_reset = tk.Button(
            btn_bar,
            text="🔄 Đặt lại từ đầu",
            bg="#FFFFFF",
            fg=self.c_text,
            activebackground="#FEE2E2",
            activeforeground="#991B1B",
            font=("Segoe UI", 9, "bold"),
            relief=tk.SOLID,
            bd=1,
            padx=14,
            pady=8,
            cursor="hand2",
            command=self._reset_defaults,
        )
        btn_reset.pack(side=tk.RIGHT, padx=6)

    # -------------------------------------------------------------
    # TAB 2: LIVE LOGS
    # -------------------------------------------------------------
    def _build_logs_tab(self):
        bar = tk.Frame(self.tab_logs, bg=self.c_bg)
        bar.pack(fill=tk.X, padx=8, pady=6)

        tk.Label(
            bar,
            text="📜 Nhật ký tiến trình cày cuốc trực tiếp từ SUMO:",
            font=("Segoe UI", 9, "bold"),
            bg=self.c_bg,
            fg=self.c_text,
        ).pack(side=tk.LEFT)

        btn_clear = tk.Button(
            bar,
            text="🗑️ Xóa log",
            bg="#FFFFFF",
            fg=self.c_text,
            activebackground="#FEE2E2",
            relief=tk.SOLID,
            bd=1,
            padx=8,
            cursor="hand2",
            command=self._clear_logs,
        )
        btn_clear.pack(side=tk.RIGHT, padx=4)

        btn_copy = tk.Button(
            bar,
            text="📋 Sao chép log",
            bg="#FFFFFF",
            fg=self.c_text,
            activebackground="#FEF3C7",
            relief=tk.SOLID,
            bd=1,
            padx=8,
            cursor="hand2",
            command=self._copy_logs,
        )
        btn_copy.pack(side=tk.RIGHT, padx=4)

        self.log_text = ScrolledText(
            self.tab_logs,
            wrap=tk.WORD,
            font=("Consolas", 10),
            bg=self.c_console,
            fg="#F5F5F4",
            insertbackground="#FDE047",
            relief=tk.SOLID,
            bd=1,
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        self.log_text.tag_config("info", foreground="#38BDF8")
        self.log_text.tag_config("success", foreground="#4ADE80")
        self.log_text.tag_config("warning", foreground="#FBBF24")
        self.log_text.tag_config("error", foreground="#F87171")

    # -------------------------------------------------------------
    # TAB 3: BẢNG KẾT QUẢ SO SÁNH
    # -------------------------------------------------------------
    def _build_results_tab(self):
        top_bar = tk.Frame(self.tab_results, bg=self.c_bg)
        top_bar.pack(fill=tk.X, padx=8, pady=8)

        self.lbl_results_info = tk.Label(
            top_bar,
            text="💤 Gà chưa có số liệu mới. Hãy bấm 'GÁY LÊN NÀO' để lập bảng thành tích!",
            font=("Segoe UI", 10, "italic", "bold"),
            bg=self.c_bg,
            fg=self.c_text_muted,
        )
        self.lbl_results_info.pack(side=tk.LEFT)

        self.btn_open_folder = tk.Button(
            top_bar,
            text="📂 Mở thư mục kết quả",
            bg="#FFFFFF",
            fg=self.c_text,
            activebackground="#FEF3C7",
            relief=tk.SOLID,
            bd=1,
            padx=10,
            command=self._open_results_folder,
            state=tk.DISABLED,
        )
        self.btn_open_folder.pack(side=tk.RIGHT, padx=4)

        self.btn_open_csv = tk.Button(
            top_bar,
            text="📊 Mở comparison.csv",
            bg="#FFFFFF",
            fg=self.c_text,
            activebackground="#FEF3C7",
            relief=tk.SOLID,
            bd=1,
            padx=10,
            command=self._open_comparison_csv,
            state=tk.DISABLED,
        )
        self.btn_open_csv.pack(side=tk.RIGHT, padx=4)

        table_frame = tk.Frame(self.tab_results, bg=self.c_bg)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        columns = (
            "controller",
            "travel_time",
            "penalized_tt",
            "delay",
            "queue",
            "throughput",
            "completion_rate",
            "switches",
        )
        self.results_tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )

        headers = [
            ("controller", "Gà chiến ứng viên", 160),
            ("travel_time", "Thời gian đi (s)", 125),
            ("penalized_tt", "Penalized TT (s)", 135),
            ("delay", "Độ trễ TB (s)", 115),
            ("queue", "Hàng đợi TB (xe)", 120),
            ("throughput", "Thông lượng (xe)", 115),
            ("completion_rate", "Tỷ lệ về đích (%)", 125),
            ("switches", "Số lần đổi pha", 105),
        ]
        for col_id, col_name, width in headers:
            self.results_tree.heading(col_id, text=col_name)
            self.results_tree.column(col_id, width=width, anchor="center")
        self.results_tree.column("controller", anchor="w")

        # Cấu hình màu cho hàng kết quả rõ ràng
        self.results_tree.tag_configure("even", background="#FFFFFF", foreground="#1C1917")
        self.results_tree.tag_configure("odd", background="#FFFBF5", foreground="#1C1917")
        self.results_tree.tag_configure("first", background="#FEF3C7", foreground="#9A3412")

        tree_scroll_y = ttk.Scrollbar(table_frame, orient="vertical", command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=tree_scroll_y.set)

        self.results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

    # -------------------------------------------------------------
    # SỰ KIỆN & CẬP NHẬT
    # -------------------------------------------------------------
    def _on_mode_change(self):
        mode = self.var_mode.get()
        self.sub_benchmark_frame.pack_forget()
        self.sub_single_frame.pack_forget()
        self.sub_train_frame.pack_forget()

        if mode == "benchmark":
            self.sub_benchmark_frame.pack(fill=tk.X, pady=(4, 2))
        elif mode == "single":
            self.sub_single_frame.pack(fill=tk.X, pady=(4, 2))
        elif mode == "train_ql":
            self.sub_train_frame.pack(fill=tk.X, pady=(4, 2))

        self._update_preview_command()

    def _on_scenario_selected(self):
        name = self.var_scenario_name.get()
        if name in self.scenario_map:
            self.var_custom_scenario_path.set(str(self.scenario_map[name]))
        self._update_preview_command()

    def _browse_custom_map(self):
        path = filedialog.askopenfilename(
            title="Chọn file mạng lưới SUMO (.sumocfg)",
            filetypes=[("SUMO Configuration", "*.sumocfg"), ("All Files", "*.*")],
            initialdir=str(RAW_DATA_DIR),
        )
        if path:
            self.var_custom_scenario_path.set(path)
            self.var_scenario_name.set(f"Tùy chọn: {Path(path).name}")
            self._update_preview_command()

    def _on_gui_checkbox_toggled(self):
        if self.var_gui.get():
            self.delay_frame.pack(side=tk.LEFT, padx=12)
        else:
            self.delay_frame.pack_forget()
        self._update_preview_command()

    def _set_steps(self, val: int):
        self.var_steps.set(val)
        self._update_preview_command()

    def _reset_defaults(self):
        self.var_mode.set("benchmark")
        for v in self.bench_vars.values():
            v.set(True)
        self.var_scenario_name.set(self.scenarios[0][0])
        self.var_custom_scenario_path.set(str(self.scenarios[0][1]))
        self.var_steps.set(900)
        self.var_action_interval.set(10)
        self.var_min_green.set(10.0)
        self.var_fixed_green.set(30.0)
        self.var_yellow.set(5.0)
        self.var_seed.set(0)
        self.var_gui.set(False)
        self.delay_frame.pack_forget()
        self._update_preview_command()

    def _build_command_list(self) -> list[str]:
        mode = self.var_mode.get()
        python_exe = sys.executable

        if mode == "test":
            return [python_exe, "-m", "unittest", "discover", "tests", "-v"]

        cmd = [python_exe, "-u", str(RUN_PY)]

        if mode == "benchmark":
            cmd.extend(["-c", "all"])
            selected_controllers = [
                name for name, var in self.bench_vars.items() if var.get()
            ]
            if selected_controllers and len(selected_controllers) < len(self.bench_vars):
                cmd.extend(["--controllers", ",".join(selected_controllers)])

        elif mode == "single":
            cmd.extend(["-c", self.var_single_controller.get()])

        elif mode == "train_ql":
            cmd.extend([
                "-c", "ql",
                "--train",
                "--episodes", str(self.var_episodes.get()),
                "--alpha", str(self.var_alpha.get()),
                "--gamma", str(self.var_gamma.get()),
                "--epsilon", str(self.var_epsilon.get()),
                "--q-table-path", self.var_q_table.get(),
            ])

        cfg_path = Path(self.var_custom_scenario_path.get())
        cmd.extend(["-m", str(cfg_path)])
        cmd.extend(["-s", str(self.var_steps.get())])
        cmd.extend(["--action-interval", str(self.var_action_interval.get())])
        cmd.extend(["--seed", str(self.var_seed.get())])
        cmd.extend(["--yellow-seconds", str(self.var_yellow.get())])
        cmd.extend(["--minimum-green", str(self.var_min_green.get())])
        cmd.extend(["--fixed-green", str(self.var_fixed_green.get())])

        if self.var_gui.get():
            cmd.append("-g")
            cmd.extend(["-d", str(self.var_delay.get())])

        return cmd

    def _update_preview_command(self):
        try:
            cmd = self._build_command_list()
            readable_cmd = ["python"] + cmd[2:] if cmd[1] == "-u" else cmd
            self.var_preview_cmd.set(" ".join(f'"{arg}"' if " " in arg else arg for arg in readable_cmd))
        except Exception:
            pass

    # -------------------------------------------------------------
    # TIẾN TRÌNH & ĐIỀU KHIỂN
    # -------------------------------------------------------------
    def start_simulation(self):
        if self.running_process is not None:
            messagebox.showwarning("Gà Nhắc Nhở", "Gà đang bận cày mô phỏng rồi bạn ơi!")
            return

        cmd = self._build_command_list()
        self._set_running_state(True)
        self.notebook.select(self.tab_logs)
        self._append_log(f"[{datetime.now().strftime('%H:%M:%S')}] 🐔 Gà xuất trận cày đêm:\n{' '.join(cmd)}\n\n", "info")

        def run_thread():
            try:
                env = os.environ.copy()
                env["PYTHONUNBUFFERED"] = "1"

                self.running_process = subprocess.Popen(
                    cmd,
                    cwd=str(ROOT),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    env=env,
                    bufsize=1,
                )

                for line in self.running_process.stdout:
                    self.log_queue.put(("log", line))

                ret_code = self.running_process.wait()
                self.log_queue.put(("finished", ret_code))

            except Exception as ex:
                self.log_queue.put(("error", str(ex)))
            finally:
                self.running_process = None

        thread = threading.Thread(target=run_thread, daemon=True)
        thread.start()

    def stop_simulation(self):
        if self.running_process is None:
            return

        if messagebox.askyesno("Xác nhận dừng", "Bạn có chắc muốn dừng mô phỏng để cho gà đi ngủ không?"):
            self.lbl_quote.config(
                text="🐔 Gà ngáp dài: \"Khò khò... Đã dừng khẩn cấp mô phỏng để gà đi ngủ một giấc!\""
            )
            self._append_log(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🛑 Đang dừng khẩn cấp cho gà nghỉ ngơi...\n", "warning")
            try:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(self.running_process.pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception:
                try:
                    self.running_process.terminate()
                except Exception:
                    pass

    def _process_log_queue(self):
        while not self.log_queue.empty():
            msg_type, content = self.log_queue.get()
            if msg_type == "log":
                self._append_log(content)
            elif msg_type == "finished":
                self._on_simulation_finished(content)
            elif msg_type == "error":
                self._append_log(f"\n[LỖI]: {content}\n", "error")
                self._set_running_state(False)

        self.after(100, self._process_log_queue)

    def _append_log(self, text: str, tag: str | None = None):
        self.log_text.insert(tk.END, text, tag or "")
        self.log_text.see(tk.END)

    def _clear_logs(self):
        self.log_text.delete("1.0", tk.END)

    def _copy_logs(self):
        self.clipboard_clear()
        self.clipboard_append(self.log_text.get("1.0", tk.END))
        messagebox.showinfo("Thành công", "Đã sao chép toàn bộ nhật ký vào Clipboard!")

    def _set_running_state(self, is_running: bool):
        if is_running:
            self.lbl_quote.config(
                text="🐔 Gà bơ phờ: \"Đang cày mô phỏng đêm khuya... mắt thâm quầng rồi đừng tắt nha đại ca!\""
            )
            self.status_badge.config(text="⏳ ĐANG CÀY CUỐC...", bg="#FEF3C7", fg="#B45309")
            self.btn_run.config(state=tk.DISABLED, bg="#D6D3D1", fg="#78716C", cursor="arrow")
            self.btn_stop.config(state=tk.NORMAL, bg=self.c_red, fg="#FFFFFF", cursor="hand2")
        else:
            self.lbl_quote.config(
                text="🐔 Gà tỉnh queo: \"Đêm nay quyết cày xong mô phỏng đèn giao thông, mắt thâm quầng cũng chịu!\""
            )
            self.status_badge.config(text="● TỈNH TÁO (SẴN SÀNG)", bg="#DCFCE7", fg="#166534")
            self.btn_run.config(state=tk.NORMAL, bg=self.c_orange, fg="#FFFFFF", cursor="hand2")
            self.btn_stop.config(state=tk.DISABLED, bg="#E7E5E4", fg="#78716C", cursor="arrow")

    def _on_simulation_finished(self, return_code: int):
        self._set_running_state(False)
        if return_code == 0:
            self.lbl_quote.config(
                text="🐔 Gà hớn hở: \"Ò ó o o! Xong rồi! Kết quả mượt như lông gà, qua Tab Kết quả xem bảng thành tích nhé!\""
            )
            self._append_log(f"\n[{datetime.now().strftime('%H:%M:%S')}] ✅ Gà đã cày xong mô phỏng thành công rực rỡ!\n", "success")
            self._load_latest_results()
        else:
            self.lbl_quote.config(
                text="🐔 Gà tá hỏa: \"Toang rồi! Có lỗi xảy ra trong quá trình mô phỏng kìa!\""
            )
            self._append_log(f"\n[{datetime.now().strftime('%H:%M:%S')}] ❌ Kết thúc với mã lỗi: {return_code}\n", "error")

    # -------------------------------------------------------------
    # KẾT QUẢ & THÀNH TÍCH
    # -------------------------------------------------------------
    def _load_latest_results(self):
        latest_file = RESULTS_DIR / "latest.txt"
        if not latest_file.is_file():
            return

        try:
            output_dir_str = latest_file.read_text(encoding="utf-8").strip()
            output_dir = Path(output_dir_str)
            if not output_dir.is_dir():
                return

            self.active_output_dir = output_dir
            comparison_file = output_dir / "comparison.csv"

            for item in self.results_tree.get_children():
                self.results_tree.delete(item)

            if comparison_file.is_file():
                with open(comparison_file, mode="r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for idx, row in enumerate(reader):
                        c_name = row.get("controller_name") or row.get("controller") or "Unknown"
                        travel_time = f"{float(row.get('average_travel_time_s', 0.0)):.2f}"
                        penalized_tt = f"{float(row.get('penalized_travel_time_s', row.get('average_travel_time_s', 0.0))):.2f}"
                        delay = f"{float(row.get('average_delay_s', 0.0)):.2f}"
                        queue = f"{float(row.get('average_queue_vehicles', 0.0)):.2f}"
                        throughput = str(row.get("throughput", 0))
                        comp_rate = f"{float(row.get('completion_rate', 0.0)) * 100:.1f}%"
                        switches = str(row.get("phase_switches", 0))

                        # Đặt huy hiệu cho hàng đầu tiên
                        badge = "🥇 " if idx == 0 else "▫️ "
                        tag = "first" if idx == 0 else ("even" if idx % 2 == 0 else "odd")
                        self.results_tree.insert(
                            "",
                            tk.END,
                            values=(f"{badge}{c_name}", travel_time, penalized_tt, delay, queue, throughput, comp_rate, switches),
                            tags=(tag,),
                        )

                self.lbl_results_info.config(
                    text=f"🎉 Bảng thành tích lưu tại: {output_dir.name}",
                    font=("Segoe UI", 9, "bold"),
                    fg=self.c_green,
                )
                self.btn_open_folder.config(state=tk.NORMAL)
                self.btn_open_csv.config(state=tk.NORMAL)
                self.notebook.select(self.tab_results)

        except Exception as e:
            self._append_log(f"Không thể tải bảng kết quả: {e}\n", "warning")

    def _open_results_folder(self):
        if self.active_output_dir and self.active_output_dir.is_dir():
            os.startfile(str(self.active_output_dir))

    def _open_comparison_csv(self):
        if self.active_output_dir:
            csv_path = self.active_output_dir / "comparison.csv"
            if csv_path.is_file():
                os.startfile(str(csv_path))


def main():
    app = SumoChickenApp()
    app.mainloop()


if __name__ == "__main__":
    main()
