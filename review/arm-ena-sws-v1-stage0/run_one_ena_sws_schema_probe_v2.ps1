# Result-blind one-event ARM ENA/SWS E0 v2 schema probe for Windows.
# No protected SWS radiance values are read. Raw SWS files are confined to the
# Python collector's TemporaryDirectory and must not appear in the output ZIP.

[CmdletBinding()]
param(
    [string]$OutputParent = "",
    [switch]$RebuildVenv
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Req = Join-Path $Here "requirements-ena-sws-e0.txt"
$Runner = Join-Path $Here "run_ena_sws_e0_frozen_v2.py"
$Venv = Join-Path $Here ".venv-ena-sws-e0"
$VenvPython = Join-Path $Venv "Scripts\python.exe"

if (-not (Test-Path -LiteralPath $Req)) { throw "Missing requirements file: $Req" }
if (-not (Test-Path -LiteralPath $Runner)) { throw "Missing frozen E0 v2 runner: $Runner" }

if ([string]::IsNullOrWhiteSpace($OutputParent)) {
    $OutputParent = Join-Path $Here "outputs"
}
New-Item -ItemType Directory -Force -Path $OutputParent | Out-Null

function New-EnaVenv {
    if (Test-Path -LiteralPath $Venv) {
        Remove-Item -LiteralPath $Venv -Recurse -Force
    }
    $created = $false
    if (Get-Command py -ErrorAction SilentlyContinue) {
        try {
            & py -3.12 -m venv $Venv
            if ($LASTEXITCODE -eq 0) { $created = $true }
        } catch { }
    }
    if (-not $created -and (Get-Command python -ErrorAction SilentlyContinue)) {
        & python -m venv $Venv
        if ($LASTEXITCODE -eq 0) { $created = $true }
    }
    if (-not $created -or -not (Test-Path -LiteralPath $VenvPython)) {
        throw "Could not create a Python virtual environment. Install Python 3.12 and retry."
    }
}

if ($RebuildVenv -or -not (Test-Path -LiteralPath $VenvPython)) {
    New-EnaVenv
}

$ReqHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $Req).Hash.ToLowerInvariant()
$Stamp = Join-Path $Venv ".ena-e0-requirements-sha256"
$InstalledHash = if (Test-Path -LiteralPath $Stamp) { (Get-Content -Raw -LiteralPath $Stamp).Trim() } else { "" }
if ($InstalledHash -ne $ReqHash) {
    & $VenvPython -m pip install --disable-pip-version-check -r $Req
    if ($LASTEXITCODE -ne 0) { throw "Python dependency installation failed." }
    [IO.File]::WriteAllText($Stamp, $ReqHash + [Environment]::NewLine, [Text.UTF8Encoding]::new($false))
}

$uid = $env:ARM_USER_ID
if ([string]::IsNullOrWhiteSpace($uid)) {
    $uid = (Read-Host "ARM user ID").Trim()
}
if ([string]::IsNullOrWhiteSpace($uid)) { throw "ARM user ID is required." }

$token = $env:ARM_ACCESS_TOKEN
if ([string]::IsNullOrWhiteSpace($token)) {
    $secureToken = Read-Host "ARM access token (input hidden)" -AsSecureString
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureToken)
    try {
        $token = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
    } finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
}
if ([string]::IsNullOrWhiteSpace($token)) { throw "ARM access token is required." }

$timestamp = [DateTime]::UtcNow.ToString("yyyyMMdd-HHmmssZ")
$OutDir = Join-Path $OutputParent ("ARM_ENA_SWS_E0_V2_SCHEMA_PROBE_" + $timestamp)
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$oldUid = $env:ARM_USER_ID
$oldToken = $env:ARM_ACCESS_TOKEN
try {
    $env:ARM_USER_ID = $uid
    $env:ARM_ACCESS_TOKEN = $token

    & $VenvPython $Runner --output-dir $OutDir --stop-after 1 --probe-aux-schema
    if ($LASTEXITCODE -ne 0) { throw "ENA/SWS E0 v2 schema probe failed with exit code $LASTEXITCODE." }
} finally {
    $env:ARM_USER_ID = $oldUid
    $env:ARM_ACCESS_TOKEN = $oldToken
    $token = $null
    $secureToken = $null
}

$rawPayloads = @(Get-ChildItem -LiteralPath $OutDir -Recurse -File | Where-Object { $_.Extension -in ".nc", ".cdf" })
if ($rawPayloads.Count -ne 0) {
    throw "HOLDOUT FIREWALL: raw SWS NetCDF/CDF unexpectedly persisted in output directory."
}

$Summary = Join-Path $OutDir "ena_sws_e0_stream_summary.json"
if (-not (Test-Path -LiteralPath $Summary)) { throw "Probe summary was not produced." }
$summaryObject = Get-Content -Raw -LiteralPath $Summary | ConvertFrom-Json
if ($summaryObject.protocol -ne "ARM_ENA_SWS_V1_STAGE0_E0_RESULT_BLIND_V2") {
    throw "Expected E0 v2 protocol attestation in summary."
}
if ($summaryObject.protected_variable_values_read -ne $false) {
    throw "HOLDOUT FIREWALL: summary does not attest protected_variable_values_read=false."
}
if ($summaryObject.raw_sws_files_retained -ne $false) {
    throw "HOLDOUT FIREWALL: summary does not attest raw_sws_files_retained=false."
}
if ([int]$summaryObject.processed_event_count -ne 1) {
    throw "Expected exactly one processed frozen event in schema probe."
}

$files = @(Get-ChildItem -LiteralPath $OutDir -File | Sort-Object Name)
$manifest = foreach ($file in $files) {
    [ordered]@{
        name = $file.Name
        size_bytes = $file.Length
        sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $file.FullName).Hash.ToLowerInvariant()
    }
}
$receipt = [ordered]@{
    schema = 2
    purpose = "ARM_ENA_SWS_V1_E0_V2_ONE_EVENT_SCHEMA_PROBE"
    created_utc = [DateTime]::UtcNow.ToString("o")
    frozen_event_universe_sha256 = "87933189ff56322ce2b5d2821a1c2ab8094d0a472ef6c690cfbd90cd0451fa41"
    processed_event_count = 1
    protected_variable_values_read = $false
    raw_sws_files_retained = $false
    credentials_persisted = $false
    files = @($manifest)
}
$ReceiptPath = Join-Path $OutDir "probe_receipt.json"
$receipt | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $ReceiptPath -Encoding utf8

$ZipPath = $OutDir + ".zip"
if (Test-Path -LiteralPath $ZipPath) { Remove-Item -LiteralPath $ZipPath -Force }
Compress-Archive -LiteralPath (Join-Path $OutDir "*") -DestinationPath $ZipPath -CompressionLevel Optimal
$ZipSha = (Get-FileHash -Algorithm SHA256 -LiteralPath $ZipPath).Hash.ToLowerInvariant()
[IO.File]::WriteAllText($ZipPath + ".sha256", $ZipSha + "  " + [IO.Path]::GetFileName($ZipPath) + [Environment]::NewLine, [Text.UTF8Encoding]::new($false))

Write-Host ""
Write-Host "ENA/SWS one-event E0 v2 schema probe complete."
Write-Host ("Output ZIP: " + $ZipPath)
Write-Host ("SHA-256:   " + $ZipSha)
Write-Host "The ZIP contains only non-photometric schema/QC/provenance outputs; no raw SWS file is retained."
