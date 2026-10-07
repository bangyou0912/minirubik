# Run from the repository root after reproduce.sh has built the target ELFs.
param([switch]$FullSweep)
$ErrorActionPreference = 'Stop'
$taskStage4 = Join-Path $PSScriptRoot '.'
function Invoke-Check([string]$Script, [string[]]$Arguments) {
    python (Join-Path $taskStage4 $Script) @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Failed: $Script" }
}
foreach ($taskKind in @('reference', 'asm-r0', 'asm-r1', 'asm-r2')) {
    Invoke-Check 'measure.py' -Arguments @('--kind', $taskKind)
}
Invoke-Check 'measure.py' -Arguments @('--kind', 'asm-r2', '--native')
Invoke-Check 'test_generic.py' -Arguments @()
Invoke-Check 'test_extra.py' -Arguments @()
Invoke-Check 'measure.py' -Arguments @('--kind', 'asm-r2-render-test')
Invoke-Check 'test_native_renderer.py' -Arguments @()
Invoke-Check 'capture_pipeline.py' -Arguments @()
Invoke-Check 'summarize_pipeline.py' -Arguments @()
if ($FullSweep) { Invoke-Check 'sweep.py' -Arguments @('--revision', '2', '--workers', '4') }
Invoke-Check 'check_evidence.py' -Arguments @()
Invoke-Check 'check_renderer_evidence.py' -Arguments @()
Invoke-Check 'audit_tables.py' -Arguments @()
Invoke-Check 'check_rebuilt_sections.py' -Arguments @()
Write-Host 'CLI checks complete. Real LED and wire-signal screenshots still require the GUI procedure in visualization.md.'
