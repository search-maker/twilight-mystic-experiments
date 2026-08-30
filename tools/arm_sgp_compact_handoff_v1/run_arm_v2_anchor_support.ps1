param(
    [Parameter(Mandatory = $true)]
    [string]$ArchiveRoot,
    [string]$OutputRoot = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ArchiveRoot = [System.IO.Path]::GetFullPath($ArchiveRoot)
if (-not (Test-Path -LiteralPath $ArchiveRoot -PathType Container)) {
    throw "ArchiveRoot does not exist or is not a directory: $ArchiveRoot"
}
if ([string]::IsNullOrWhiteSpace($OutputRoot)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputRoot = Join-Path (Get-Location) "ARM_SGP_V2_ANCHOR_SUPPORT_$stamp"
}
$OutputRoot = [System.IO.Path]::GetFullPath($OutputRoot)

$venv = Join-Path ([System.IO.Path]::GetTempPath()) "arm-sgp-v2-anchor-support-venv"
if (Get-Command py -ErrorAction SilentlyContinue) {
    $launcher = "py"; $launcherArgs = @("-3")
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $launcher = "python"; $launcherArgs = @()
} else {
    throw "Python 3 was not found."
}
if (-not (Test-Path -LiteralPath $venv -PathType Container)) {
    & $launcher @launcherArgs -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw "Failed to create Python virtual environment." }
}
$python = Join-Path $venv "Scripts\python.exe"
& $python -m pip install --disable-pip-version-check -r (Join-Path $ScriptRoot "requirements_v2_anchor_support.txt")
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }
& $python -m py_compile (Join-Path $ScriptRoot "audit_sasze_anchor_support_v2.py")
if ($LASTEXITCODE -ne 0) { throw "V2 audit syntax preflight failed." }
New-Item -ItemType Directory -Path $OutputRoot -Force | Out-Null
& $python (Join-Path $ScriptRoot "audit_sasze_anchor_support_v2.py") --archive-root $ArchiveRoot --output-dir $OutputRoot
if ($LASTEXITCODE -ne 0) { throw "V2 anchor-support audit failed with exit code $LASTEXITCODE." }

$manifest = @'
import hashlib, json, pathlib, sys
root = pathlib.Path(sys.argv[1])
rows = []
for path in sorted(root.glob("*")):
    if not path.is_file() or path.name == "manifest.json":
        continue
    h = hashlib.sha256(path.read_bytes()).hexdigest()
    rows.append({"file": path.name, "bytes": path.stat().st_size, "sha256": h})
(root / "manifest.json").write_text(json.dumps({"files": rows}, indent=2, sort_keys=True), encoding="utf-8")
'@
& $python -c $manifest $OutputRoot
if ($LASTEXITCODE -ne 0) { throw "Manifest creation failed." }
$zipPath = "$OutputRoot.zip"
if (Test-Path -LiteralPath $zipPath) { Remove-Item -LiteralPath $zipPath -Force }
Compress-Archive -Path (Join-Path $OutputRoot "*") -DestinationPath $zipPath -CompressionLevel Optimal
$zipHash = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash.ToLowerInvariant()
Write-Host "ARM V2 anchor-support audit complete."
Write-Host "ZIP: $zipPath"
Write-Host "SHA256: $zipHash"
Write-Host "No SASZE radiance magnitudes were emitted."
