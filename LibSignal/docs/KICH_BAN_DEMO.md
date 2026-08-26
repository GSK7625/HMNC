# Kịch bản demo 5-7 phút

## 1. Giới thiệu

“Nhóm chỉ giữ SUMO và map có sẵn. Hai controller FT và MP cùng vòng lặp thí
nghiệm đều do nhóm tự code, không dùng agent/trainer của LibSignal.”

## 2. Mở code FT

Mở `src/traffic_control/controllers.py`, chỉ vào `FixedTimeController`:

“FT không đọc lane count. Đủ 30 giây xanh thì chuyển sang pha kế tiếp.”

## 3. Mở code MP

Chỉ vào `calculate_phase_pressures` và `MaxPressureController`:

“Mỗi pha được chấm bằng tổng `N_in - N_out`. Sau minimum green 10 giây, MP chọn
pha có điểm cao nhất.”

## 4. Chạy GUI

```powershell
.\run_demo.ps1 -Controller maxpressure -Steps 300 -Gui -StepDelay 0.03
```

Sau đó chạy FT với đúng tham số:

```powershell
.\run_demo.ps1 -Controller fixedtime -Steps 300 -Gui -StepDelay 0.03
```

## 5. Mở decision trace

Trong trace MP, so sánh `actions` với phần tử lớn nhất trong
`phase_pressures`. Nếu action chưa phải max, kiểm tra
`green_elapsed_before_action_s`: controller đang tôn trọng minimum green.

Trong trace FT, pressure vẫn được ghi để đối chiếu nhưng action chỉ chạy tuần
hoàn theo thời gian.

## 6. Kết luận

“Giai đoạn 1 chứng minh nhóm tự xây được pipeline SUMO, hai baseline hoạt động
và quyết định giải thích được. Giai đoạn sau mới thêm scenario, nhiều seed và
thuật toán nâng cao.”
