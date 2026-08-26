param(
    [ValidateSet("all", "fixedtime", "maxpressure")]
    [string]$Controller = "all",
    [ValidateRange(1, 86400)]
    [int]$Steps = 900,
    [string]$Scenario = "data\raw_data\cologne1\cologne1.sumocfg",
    [switch]$Gui,
    [ValidateRange(0, 10)]
    [double]$StepDelay = 0.0,
    [int]$Seed = 0
)

$ErrorActionPreference = "Stop"
$repoRoot = $PSScriptRoot
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    & (Join-Path $repoRoot "setup.ps1")
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

$arguments = @(
    (Join-Path $repoRoot "run.py"),
    "--controller", $Controller,
    "--steps", $Steps,
    "--scenario", (Join-Path $repoRoot $Scenario),
    "--step-delay", $StepDelay,
    "--seed", $Seed
)
if ($Gui) {
    $arguments += "--gui"
}

Push-Location $repoRoot
try {
    & $python @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Demo kết thúc với mã lỗi $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}
