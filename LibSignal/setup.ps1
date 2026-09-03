$ErrorActionPreference = "Stop"

$repoRoot = $PSScriptRoot
$venvDir = Join-Path $repoRoot ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"

if (-not (Test-Path -LiteralPath $venvPython)) {
    $python = Get-Command python -ErrorAction SilentlyContinue
    $codexPython = Join-Path $HOME ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

    if ($python) {
        & $python.Source -m venv $venvDir
    }
    elseif (Test-Path -LiteralPath $codexPython) {
        & $codexPython -m venv $venvDir
    }
    else {
        $launcher = Get-Command py -ErrorAction SilentlyContinue
        if (-not $launcher) {
            throw "Không tìm thấy Python 3.10-3.12."
        }
        & $launcher.Source -3 -m venv $venvDir
    }
}

if (-not $env:SUMO_HOME) {
    # 1. Kiểm tra gói eclipse-sumo trong môi trường ảo .venv
    $pipSumo = Join-Path $venvDir "Lib\site-packages\sumo"
    if (Test-Path -LiteralPath (Join-Path $pipSumo "bin\sumo.exe")) {
        $env:SUMO_HOME = $pipSumo
    }
}

if (-not $env:SUMO_HOME) {
    # 2. Kiểm tra thư mục sumo portable nội bộ trong repo
    $localSumo = Join-Path $repoRoot "sumo"
    if (Test-Path -LiteralPath (Join-Path $localSumo "bin\sumo.exe")) {
        $env:SUMO_HOME = $localSumo
    }
}

if (-not $env:SUMO_HOME) {
    # 3. Kiểm tra các đường dẫn cài đặt hệ thống trên Windows
    foreach ($candidate in @(
        "C:\Program Files (x86)\Eclipse\Sumo",
        "C:\Program Files\Eclipse\Sumo",
        "C:\Sumo"
    )) {
        if (Test-Path -LiteralPath (Join-Path $candidate "bin\sumo.exe")) {
            $env:SUMO_HOME = $candidate
            break
        }
    }
}

if (-not $env:SUMO_HOME) {
    # 4. Tự động cài đặt eclipse-sumo qua pip nếu máy chưa có SUMO
    Write-Host "Chưa tìm thấy SUMO. Đang tự động cài đặt eclipse-sumo qua pip..." -ForegroundColor Cyan
    & $venvPython -m pip install eclipse-sumo
    $pipSumo = Join-Path $venvDir "Lib\site-packages\sumo"
    if (Test-Path -LiteralPath (Join-Path $pipSumo "bin\sumo.exe")) {
        $env:SUMO_HOME = $pipSumo
    }
}

if (-not $env:SUMO_HOME) {
    throw "Không tìm thấy SUMO. Hãy thử chạy thủ công: .\.venv\Scripts\python.exe -m pip install eclipse-sumo"
}

if (-not (Test-Path -LiteralPath (Join-Path $env:SUMO_HOME "tools\traci"))) {
    throw "SUMO_HOME không hợp lệ: thiếu tools\traci tại $env:SUMO_HOME"
}

& $venvPython --version
Write-Host "SUMO_HOME: $env:SUMO_HOME" -ForegroundColor Green
Write-Host "Môi trường đã sẵn sàng! Chạy lệnh: .\.venv\Scripts\python.exe run.py" -ForegroundColor Green
