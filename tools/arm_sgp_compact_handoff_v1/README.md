# ARM SGP compact local handoff v1

Purpose: make the preserved ~65 GB ARM SGP order scientifically usable from a small, uploadable handoff **without modifying the archive and without opening the held-out SASZE radiance**.

This is a Phase-0 data-provenance tool. It does not run MYSTIC, fit Taylor/Jerusalem, compute validation residuals, choose cases from model agreement, or alter any source byte.

## One local run

From a Windows clone of this repository, run once:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\arm_sgp_compact_handoff_v1\run_arm_compact_handoff.ps1 -ArchiveRoot "<FOLDER_CONTAINING_THE_PRESERVED_ARM_ORDER>"
```

The wrapper creates an isolated Python venv beside the script, installs the pinned reader dependencies, scans the archive read-only, creates a compact folder, and produces a ZIP plus its SHA-256. Upload/share the ZIP only; keep the original ARM order untouched.

## Outputs

The compact ZIP contains:

- `archive_inventory.csv` — every source filename, inferred datastream/date, size, SHA-256, NetCDF readability, **native decoded** time coverage/sample count, schema signature and error state.
- `netcdf_headers.jsonl` — de-duplicated NetCDF dimensions, global metadata keys/nonvolatile values, variables, units, dimensions and variable attributes. Daily volatile coverage/history attributes are deliberately not used as a sample-continuity proof.
- `quality_metadata.jsonl` — discovered QC/quality/DQR/DQPR/flag metadata from global and variable attributes, including flag meanings/masks when present.
- `daily_availability.csv` — day-by-day availability by concrete datastream.
- `family_daily_availability.csv` — explicit available/absent matrix for the science interval 2023-12-14 through 2024-06-02 for SASZE, HSRL, Raman/RLPROF, CSPHOT AOD, MFRSR/NIMFR AOD, ARSCL, ceilometer, sonde and surface/albedo families.
- `issues.csv` — corrupt/unreadable/hash/extract notes; absence is kept distinct from unreadability.
- `representative_extracts.jsonl` — deterministic first/middle/last small samples from relevant datastream families, preserving original values, units, dimensions, QC and coordinate metadata. **SASZE radiance/transmittance values are excluded by default**; SASZE timing, wavelength coordinates and housekeeping remain visible so the radiance holdout stays protected.
- `stageA_sasze_twilight_operability_2024.csv` — the frozen 20-case native-time gate for `sgpsaszefilterbandsC1.a1`, using actual sample timestamps rather than global `time_coverage_*` attributes.
- `summary.json` — compact family/gate summary, including any `TWILIGHT_CONTIGUOUS` survivor IDs.
- `handoff_manifest.json` — tool/runtime versions plus SHA-256/size for every handoff output.

## SASZE gate semantics

The mandatory filterband gate has five dispositions:

- `TWILIGHT_CONTIGUOUS`: native samples bracket the whole chronological -8..-6 degree core and no positive internal gap exceeds `2 x median_positive_cadence`.
- `TWILIGHT_DISCONTINUOUS`: some core samples exist but the bracketing/gap rule fails.
- `TWILIGHT_SAMPLES_ABSENT`: matching readable file(s) exist but no native sample lies in the core.
- `UNREADABLE`: matching source file(s) exist but native timestamps cannot be decoded.
- `SOURCE_FILE_MISSING`: no matching preserved local file exists.

Only the first disposition can advance a case. `SOURCE_FILE_MISSING` or `UNREADABLE` is a local-data blocker and cannot be misreported as evidence that SASZE did not observe.

The filterband audit records integration-time/scan modes and native health/saturation/high-SZA flag names if they exist. Multiple integration times are not themselves a failure; SASZE intentionally used multiple integration modes to improve low-signal SNR while protecting intense spectral regions.

## Holdout boundary

Do **not** pass `--include-sasze-radiance-sample` during Phase 0/Stage A. That option exists only for a later explicitly opened Stage-B workflow after exact cases, model inputs, settings and metrics have been frozen.

The extractor never writes to the ARM archive. Its output must be placed outside the archive root; the program refuses an output directory inside the source tree.

## What happens after the ZIP is available

1. Read `stageA_sasze_twilight_operability_2024.csv` first.
2. If at least one case is `TWILIGHT_CONTIGUOUS`, apply the already-preregistered independent atmosphere/QC gates only to those survivors.
3. If all 20 are readably `TWILIGHT_SAMPLES_ABSENT`/`TWILIGHT_DISCONTINUOUS`, record `HALT_CURRENT_TARGET_NO_OBSERVATIONAL_SUPPORT`; do not move the solar-depth target or substitute a different observable after seeing that outcome.
4. If any row is `SOURCE_FILE_MISSING`/`UNREADABLE`, resolve that preserved-archive integrity/access gap before any all-20 HALT decision.

No full SASZE VIS/NIR radiance spectrum is required to resolve Phase 0.
