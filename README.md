# HMNC - Nhom 9

Repository cho de tai dieu khien tin hieu giao thong bang SUMO (LibSignal).

## Noi dung

- Ma nguon tinh gon cho bo dieu khien Fixed-Time va Max-Pressure (`LibSignal/src/traffic_control/`).
- Moi truong mo phong SUMO / TraCI voi xu ly den vang.
- Script khoi tao va chay demo benchmark / GUI (`setup.ps1`, `run_demo.ps1`).
- Tai lieu ly thuyet va kich ban demo huong dan thuyet trinh (`LibSignal/docs/`).

## Bat dau nhanh

Mo PowerShell tai thu muc `LibSignal`, sau do chay:

```powershell
# Kiem tra moi truong
.\setup.ps1

# Chay benchmark ca Fixed-Time va Max-Pressure
.\run_demo.ps1 -Controller all -Steps 900

# Chay demo giao dien SUMO-GUI
.\run_demo.ps1 -Controller maxpressure -Steps 300 -Gui -StepDelay 0.03
```

Huong dan chi tiet nam tai `LibSignal/README.md`.
