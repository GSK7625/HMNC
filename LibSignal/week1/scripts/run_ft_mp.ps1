param(
    [string]$RepoPath = "",
    [int[]]$Seeds = @(1, 42, 2026),
    [string]$Network = "sumo1x1",
    [string]$Interface = "traci"
)

$ErrorActionPreference = "Stop"
if (-not $RepoPath) {
    $RepoPath = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
}
$RepoPath = [System.IO.Path]::GetFullPath($RepoPath)
$Python = Join-Path $RepoPath ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Không tìm thấy môi trường .venv. Hãy chạy setup_windows.ps1 trước."
}

if (-not $env:SUMO_HOME) {
    $env:SUMO_HOME = @(
        "C:\Program Files (x86)\Eclipse\Sumo",
        "C:\Program Files\Eclipse\Sumo"
    ) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}

if (-not $env:SUMO_HOME) {
    throw "Không tìm thấy SUMO_HOME."
}

$env:PYTHONPATH = Join-Path $env:SUMO_HOME "tools"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONHASHSEED = "0"

Push-Location $RepoPath
try {
    foreach ($Agent in @("fixedtime", "maxpressure")) {
        foreach ($Seed in $Seeds) {
            $Prefix = "week1_seed_$Seed"
            Write-Host "Đang chạy $Agent, seed=$Seed..."

            & $Python run.py `
                --task tsc `
                --agent $Agent `
                --world sumo `
                --network $Network `
                --prefix $Prefix `
                --seed $Seed `
                --ngpu -1 `
                --interface $Interface

            $Meta = Join-Path $RepoPath "data\output_data\tsc\sumo_$Agent\$Network\$Prefix\logger\new_metrics_meta.json"
            if (-not (Test-Path -LiteralPath $Meta)) {
                throw "Lượt chạy $Agent seed=$Seed không tạo new_metrics_meta.json."
            }
        }
    }
}
finally {
    Pop-Location
}

Write-Host "Hoàn tất toàn bộ lượt chạy FT-MP."
