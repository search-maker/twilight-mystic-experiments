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

# Fail before touching the archive if any package Python file has a syntax error
# or if the frozen synthetic SASZE gate semantics do not reproduce exactly.
& $python -m py_compile `
    (Join-Path $ScriptRoot "extract_arm_compact_handoff.py") `
    (Join-Path $ScriptRoot "audit_sasze_native_time.py") `
    (Join-Path $ScriptRoot "selftest_arm_compact_handoff.py")
if ($LASTEXITCODE -ne 0) { throw "Python syntax preflight failed." }

Push-Location $ScriptRoot
try {
    & $python (Join-Path $ScriptRoot "selftest_arm_compact_handoff.py")
    if ($LASTEXITCODE -ne 0) { throw "ARM compact-handoff self-test failed with exit code $LASTEXITCODE." }
} finally {
    Pop-Location
}

New-Item -ItemType Directory -Path $OutputRoot -Force | Out-Null

& $python (Join-Path $ScriptRoot "extract_arm_compact_handoff.py") `
    --archive-root $ArchiveRoot `
    --output $OutputRoot `
    --start 2023-12-14 `
    --end 2024-06-02
if ($LASTEXITCODE -ne 0) { throw "ARM compact extraction failed with exit code $LASTEXITCODE." }

# Recompute the authoritative SASZE gate with source-day cadence and explicit
# edge-gap checking. This overwrites the provisional gate emitted by the broad
# inventory script and refreshes the gate fields in summary.json.
& $python (Join-Path $ScriptRoot "audit_sasze_native_time.py") `
    --archive-root $ArchiveRoot `
    --priority-csv (Join-Path $ScriptRoot "priority20_sasze_gate.csv") `
    --output (Join-Path $OutputRoot "stageA_sasze_twilight_operability_2024.csv") `
    --update-summary (Join-Path $OutputRoot "summary.json")
if ($LASTEXITCODE -ne 0) { throw "Strict SASZE native-time audit failed with exit code $LASTEXITCODE." }

# Refresh handoff file hashes after the strict gate overwrote gate/summary files.
$manifestRefresh = @'
import hashlib
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
manifest_path = root / "handoff_manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
files = []
for path in sorted(root.rglob("*")):
    if not path.is_file() or path.name == "handoff_manifest.json":
        continue
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    files.append({
        "relative_path": str(path.relative_to(root)).replace("\\", "/"),
        "size_bytes": path.stat().st_size,
        "sha256": digest.hexdigest(),
    })
manifest["files"] = files
manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
'@
& $python -c $manifestRefresh $OutputRoot
if ($LASTEXITCODE -ne 0) { throw "Failed to refresh handoff manifest hashes." }

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
