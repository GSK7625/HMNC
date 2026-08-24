# HMNC - Nhom 9

Repository cho de tai dieu khien tin hieu giao thong bang LibSignal.

## Noi dung hien tai

- Ma nguon LibSignal dung cho thi nghiem SUMO.
- Ket qua tuan 1 cua Fixed-Time va MaxPressure tren mang `sumo1x1`.
- Ba seed thi nghiem: `1`, `42`, `2026`.
- Script cai dat, chay lai va tong hop ket qua.
- Bao cao, bang du lieu va bieu do so sanh.

## Bat dau

Mo PowerShell tai thu muc `LibSignal`, sau do chay:

```powershell
powershell -ExecutionPolicy Bypass -File .\week1\scripts\setup_windows.ps1
powershell -ExecutionPolicy Bypass -File .\week1\scripts\run_ft_mp.ps1 -RepoPath . -Seeds 1,42,2026
```

Huong dan chi tiet nam tai `LibSignal/week1/README.md`.

## Pham vi tuan 1

Tuan 1 chi tap trung vao Fixed-Time va MaxPressure. Chua trien khai AWPC, DQN hoac PressLight.
