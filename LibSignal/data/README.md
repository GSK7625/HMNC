# SUMO datasets

Chỉ giữ các thư mục có cấu hình `.sumocfg` và map SUMO đi kèm:

- `atlanta_1x5`
- `cologne1` (mặc định cho Phase 1)
- `cologne3`
- `hangzhou_1x1_bc-tyc_18041610_1h`
- `hangzhou_1x1_kn-hz_18041608_1h`
- `hangzhou_1x1_qc-yn_18041608_1h`
- `hangzhou_1x1_sb-sx_18041607_1h`
- `hangzhou_4x4_gudang_18041610_1h`
- `hangzhou_4x4_hetero`
- `ingolstadt21`
- `manhattan_28x7`

Các dataset chỉ có JSON CityFlow/OpenEngine và hai config SUMO thiếu file mạng/tuyến
đã được loại bỏ. Khi thêm map mới, đặt toàn bộ `.sumocfg`, `.net.xml` và
`.rou.xml` trong cùng một thư mục con.
