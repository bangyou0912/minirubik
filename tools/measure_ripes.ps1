# Measures retired-instruction count (and cycles) for an RV32I assembly file
# on Ripes's RV32_SS model, the single-cycle ISS the homework calls
# "RV32_ISS". Run from Windows PowerShell (Ripes is a native GUI app, not a
# WSL binary); point -Src at a path reachable from Windows, e.g. the
# \\wsl.localhost\... UNC path into this repo.
#
# Usage:
#   pwsh tools/measure_ripes.ps1 -Src path\to\program.s
#   pwsh tools/measure_ripes.ps1 -Src path\to\program.s -RipesExe D:\Ripes\Ripes.exe
#
# Smoke-test target (should report 5 cycles / 5 instructions retired):
#   pwsh tools/measure_ripes.ps1 -Src tools\ripes_smoke_test.s
param(
    [Parameter(Mandatory = $true)][string]$Src,
    [string]$RipesExe = "$env:USERPROFILE\Apps\Ripes\Ripes.exe",
    [string]$Proc = "RV32_SS",
    [int]$TimeoutMs = 10000
)
if (-not (Test-Path $RipesExe)) {
    throw "Ripes.exe not found at $RipesExe -- pass -RipesExe explicitly"
}
& $RipesExe --mode cli --src $Src -t asm --proc $Proc --timeout $TimeoutMs `
    --iret --cycles --runinfo -v
