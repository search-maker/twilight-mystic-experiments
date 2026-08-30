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

# Keep helper dependencies outside the repository and outside the preserved ARM archive.
$venv = Join-Path ([System.IO.Path]::GetTempPath()) "arm-sgp-compact-handoff-v1-venv"
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
    (Join-Path $ScriptRoot "repair_cdf_netcdf_inventory.py") `
    (Join-Path $ScriptRoot "compact_netcdf_headers.py") `
    (Join-Path $ScriptRoot "extract_quality_documents.py") `
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

# ARM still uses .cdf filenames for scientifically essential NetCDF streams
# such as SGP radiosondes. The broad extractor deliberately keeps its original
# .nc classification stable; this additive post-pass decodes .cdf NetCDF files
# into the compact inventory/headers/QC/representative extracts without changing
# any source byte or opening protected SASZE radiance.
& $python (Join-Path $ScriptRoot "repair_cdf_netcdf_inventory.py") `
    --archive-root $ArchiveRoot `
    --output $OutputRoot
if ($LASTEXITCODE -ne 0) { throw "ARM .cdf NetCDF compatibility pass failed with exit code $LASTEXITCODE." }

# Collapse daily NetCDF headers to structural schemas. Record/time dimension
# lengths are observed ranges, not reasons to duplicate an otherwise identical schema.
& $python (Join-Path $ScriptRoot "compact_netcdf_headers.py") `
    --headers (Join-Path $OutputRoot "netcdf_headers.jsonl")
if ($LASTEXITCODE -ne 0) { throw "NetCDF header compaction failed with exit code $LASTEXITCODE." }

# Preserve small DQR/DQPR/quality/readme/manifest text excerpts when such files
# exist in the order, while leaving all original documents untouched.
& $python (Join-Path $ScriptRoot "extract_quality_documents.py") `
    --archive-root $ArchiveRoot `
    --inventory (Join-Path $OutputRoot "archive_inventory.csv") `
    --output (Join-Path $OutputRoot "quality_documents.jsonl")
if ($LASTEXITCODE -ne 0) { throw "Quality-document extraction failed with exit code $LASTEXITCODE." }

# Recompute the authoritative SASZE gate with source-day cadence and explicit
# edge-gap checking. This overwrites the provisional gate emitted by the broad
# inventory script and refreshes the gate fields in summary.json.
& $python (Join-Path $ScriptRoot "audit_sasze_native_time.py") `
    --archive-root $ArchiveRoot `
    --priority-csv (Join-Path $ScriptRoot "priority20_sasze_gate.csv") `
    --output (Join-Path $OutputRoot "stageA_sasze_twilight_operability_2024.csv") `
    --update-summary (Join-Path $OutputRoot "summary.json")
if ($LASTEXITCODE -ne 0) { throw "Strict SASZE native-time audit failed with exit code $LASTEXITCODE." }

# Refresh handoff file hashes after .cdf repair, header compaction,
# quality-document extraction, and the strict SASZE gate. Redact the absolute
# local archive path before upload.
$manifestRefresh = @'
import hashlib
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
archive_root = pathlib.Path(sys.argv[2])
manifest_path = root / "handoff_manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
manifest.pop("archive_root", None)
manifest["archive_root_name"] = archive_root.name
manifest["archive_root_path_redacted"] = True
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
& $python -c $manifestRefresh $OutputRoot $ArchiveRoot
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
