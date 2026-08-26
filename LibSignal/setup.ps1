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
    foreach ($candidate in @(
        "C:\Program Files (x86)\Eclipse\Sumo",
        "C:\Program Files\Eclipse\Sumo"
    )) {
        if (Test-Path -LiteralPath (Join-Path $candidate "bin\sumo.exe")) {
            $env:SUMO_HOME = $candidate
            break
        }
    }
}

if (-not $env:SUMO_HOME) {
    throw "Không tìm thấy SUMO. Hãy cài SUMO và đặt biến SUMO_HOME."
}
if (-not (Test-Path -LiteralPath (Join-Path $env:SUMO_HOME "tools\traci"))) {
    throw "SUMO_HOME không hợp lệ: thiếu tools\traci."
}

& $venvPython --version
Write-Host "SUMO_HOME: $env:SUMO_HOME"
Write-Host "Môi trường đã sẵn sàng. Chạy .\run_demo.ps1"
