param(
    [string]$RepoPath = "",
    [string]$Python = "python",
    [string]$RepositoryUrl = "https://github.com/sal0-h/LibSignal.git"
)

$ErrorActionPreference = "Stop"
$KitRoot = Split-Path -Parent $PSScriptRoot
if (-not $RepoPath) {
    $RepoPath = Split-Path -Parent $KitRoot
}
$RepoPath = [System.IO.Path]::GetFullPath($RepoPath)

if (-not (Test-Path -LiteralPath $RepoPath)) {
    git clone $RepositoryUrl $RepoPath
}

$VenvPath = Join-Path $RepoPath ".venv"
if (-not (Test-Path -LiteralPath $VenvPath)) {
    & $Python -m venv $VenvPath
}

$VenvPython = Join-Path $VenvPath "Scripts\python.exe"
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r (Join-Path $KitRoot "requirements-classical.txt")

if (-not $env:SUMO_HOME) {
    $KnownSumo = @(
        "C:\Program Files (x86)\Eclipse\Sumo",
        "C:\Program Files\Eclipse\Sumo"
    ) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1

    if ($KnownSumo) {
        $env:SUMO_HOME = $KnownSumo
    }
}

if (-not $env:SUMO_HOME -or -not (Test-Path -LiteralPath $env:SUMO_HOME)) {
    throw "Không tìm thấy SUMO. Hãy cài SUMO và đặt biến SUMO_HOME trước khi chạy thí nghiệm."
}

$SumoTools = Join-Path $env:SUMO_HOME "tools"
$env:PYTHONPATH = $SumoTools

& $VenvPython -c "import yaml, gymnasium, numpy, torch, lmdb; print('Python dependencies: OK')"
& (Join-Path $env:SUMO_HOME "bin\sumo.exe") --version | Select-Object -First 1

Write-Host "Thiết lập hoàn tất tại $RepoPath"
