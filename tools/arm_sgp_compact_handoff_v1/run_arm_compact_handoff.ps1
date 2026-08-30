param(
    [Parameter(Mandatory = $true)]
    [string]$ArchiveRoot,

    [string]$OutputRoot = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($OutputRoot)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputRoot = Join-Path (Get-Location) "ARM_SGP_COMPACT_HANDOFF_$stamp"
}

$ArchiveRoot = [System.IO.Path]::GetFullPath($ArchiveRoot)
$OutputRoot = [System.IO.Path]::GetFullPath($OutputRoot)

if (-not (Test-Path -LiteralPath $ArchiveRoot -PathType Container)) {
    throw "ArchiveRoot does not exist or is not a directory: $ArchiveRoot"
}

$venv = Join-Path $ScriptRoot ".venv-arm-compact-handoff"
$python = $null

if (Get-Command py -ErrorAction SilentlyContinue) {
    $launcher = "py"
    $launcherArgs = @("-3")
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $launcher = "python"
    $launcherArgs = @()
} else {
    throw "Python 3 was not found. Install Python 3, then rerun this same command."
}

if (-not (Test-Path -LiteralPath $venv -PathType Container)) {
    & $launcher @launcherArgs -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw "Failed to create Python virtual environment." }
}

$python = Join-Path $venv "Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "Virtual-environment Python was not created: $python"
}

& $python -m pip install --disable-pip-version-check -r (Join-Path $ScriptRoot "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }

New-Item -ItemType Directory -Path $OutputRoot -Force | Out-Null

& $python (Join-Path $ScriptRoot "extract_arm_compact_handoff.py") `
    --archive-root $ArchiveRoot `
    --output $OutputRoot `
    --start 2023-12-14 `
    --end 2024-06-02
if ($LASTEXITCODE -ne 0) { throw "ARM compact extraction failed with exit code $LASTEXITCODE." }

$zipPath = "$OutputRoot.zip"
if (Test-Path -LiteralPath $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}
Compress-Archive -Path (Join-Path $OutputRoot "*") -DestinationPath $zipPath -CompressionLevel Optimal
$zipHash = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash.ToLowerInvariant()
$zipSize = (Get-Item -LiteralPath $zipPath).Length

Write-Host ""
Write-Host "ARM compact handoff complete."
Write-Host "Folder: $OutputRoot"
Write-Host "ZIP:    $zipPath"
Write-Host "SHA256: $zipHash"
Write-Host "Bytes:  $zipSize"
Write-Host ""
Write-Host "Upload/share only the ZIP. The original ARM archive was not modified."
