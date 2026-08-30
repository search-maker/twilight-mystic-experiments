# ARM SGP compact local handoff v1

Purpose: make the preserved ~65 GB ARM SGP order scientifically usable from a small, uploadable handoff **without modifying the archive and without opening the held-out SASZE radiance**.

This is a Phase-0 data-provenance tool. It does not run MYSTIC, fit Taylor/Jerusalem, compute validation residuals, choose cases from model agreement, or alter any source byte.

## One local run

From a Windows clone of this repository, run once:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\arm_sgp_compact_handoff_v1\run_arm_compact_handoff.ps1 -ArchiveRoot "<FOLDER_CONTAINING_THE_PRESERVED_ARM_ORDER>"
```

The wrapper keeps its temporary Python environment outside the repository and outside the ARM archive, installs the small reader dependencies, syntax-checks the package, runs a synthetic native-time continuity self-test, scans the archive read-only, compacts structurally equivalent NetCDF headers, captures bounded DQR/DQPR/quality-document excerpts when present, reruns the strict SASZE native-time gate, then produces a compact ZIP plus its SHA-256. Upload/share the ZIP only; keep the original ARM order untouched.

## Important SASZE product-semantics correction

Actual local 2024 SASZE file evidence established a distinction that file-envelope metadata alone could not show:

- `sgpsaszevisC1.a1` and `sgpsaszenirC1.a1` contain the calibrated full spectral radiance stream through twilight, with native validity/fill masking that changes with the dual-integration acquisition.
- `sgpsaszefilterbandsC1.a1` keeps timestamps through twilight, but its **derived filterband radiance/transmittance product is daylight gated**. In the inspected 2024-02-09 file every filterband radiance is fill over apparent solar zenith 95.9–97.9 deg, while populated filterband radiance over that day is confined to apparent solar zenith 51.2–89.0 deg.

Therefore the primary Phase-0 held-out-observable gate is now **full VIS native-time continuity**, not filterband continuity. NIR is audited as a secondary spectral extension. Filterbands remain a useful daylight-derived diagnostic/timing stream but cannot prove that the twilight held-out spectrum exists or does not exist.

This correction does not relax the previously frozen strict continuity criterion and does not promote any observed case. In particular, an event with a VIS gap larger than `2 x` its source-day median positive cadence remains `TWILIGHT_DISCONTINUOUS` even when its filterband timestamps are continuous.

## Outputs

The compact ZIP contains:

- `archive_inventory.csv` — every source filename, inferred datastream/date, size, SHA-256, NetCDF readability, **native decoded** time coverage/sample count, schema signature and error state.
- `netcdf_headers.jsonl` — structurally de-duplicated NetCDF dimensions, global metadata keys/nonvolatile values, variables, units, dimensions and variable attributes. Record/time dimension lengths are summarized as observed ranges rather than duplicating otherwise identical daily schemas. Daily volatile coverage/history attributes are deliberately not used as a sample-continuity proof.
- `quality_metadata.jsonl` — discovered QC/quality/DQR/DQPR/flag metadata from NetCDF global and variable attributes, including flag meanings/masks when present.
- `quality_documents.jsonl` — bounded excerpts from small text-like DQR/DQPR/data-quality/readme/manifest files in the order, retaining source relative path, source SHA-256, size and truncation/read disposition. Binary-looking or large files are noted rather than copied.
- `daily_availability.csv` — day-by-day availability by concrete datastream.
- `family_daily_availability.csv` — explicit available/absent matrix for the science interval 2023-12-14 through 2024-06-02 for SASZE, HSRL, Raman/RLPROF, CSPHOT AOD, MFRSR/NIMFR AOD, ARSCL, ceilometer, sonde and surface/albedo families.
- `issues.csv` — corrupt/unreadable/hash/extract notes; absence is kept distinct from unreadability.
- `representative_extracts.jsonl` — deterministic first/middle/last small samples from relevant datastream families, preserving original values, units, dimensions, QC and coordinate metadata. **SASZE radiance/transmittance values are excluded by default**; SASZE timing, wavelength coordinates and housekeeping remain visible so the radiance holdout stays protected.
- `stageA_sasze_twilight_operability_2024.csv` — 60 rows = 20 frozen cases x three SASZE streams. `sgpsaszevisC1.a1` is marked `PRIMARY_HELDOUT_SUPPORT`; `sgpsaszenirC1.a1` is `SECONDARY_SPECTRAL_EXTENSION`; `sgpsaszefilterbandsC1.a1` is `DAYLIGHT_DERIVED_DIAGNOSTIC`. All use actual sample timestamps rather than global `time_coverage_*` attributes.
- `summary.json` — compact family/gate summary. Primary survivor IDs and the all-20 observational-support decision are derived **only from `sgpsaszevisC1.a1`**, with the exact strict-gate algorithm identity recorded.
- `handoff_manifest.json` — tool/runtime versions plus SHA-256/size for every handoff output, refreshed after all post-processing.

## SASZE gate semantics

Each audited stream has five timing dispositions:

- `TWILIGHT_CONTIGUOUS`: native samples bracket the whole chronological -8..-6 degree core and no positive gap in the full bracketing segment, including the two edge gaps, exceeds `2 x median_positive_source_day_cadence`.
- `TWILIGHT_DISCONTINUOUS`: some core samples exist but the bracketing/gap rule fails.
- `TWILIGHT_SAMPLES_ABSENT`: matching readable file(s) exist but no native sample lies in the core.
- `UNREADABLE`: one or more matching source files cannot be opened or do not provide decodable native timestamps; a partially unreadable same-day source set fails closed even if another matching file is readable.
- `SOURCE_FILE_MISSING`: no matching preserved local file exists.

Only `TWILIGHT_CONTIGUOUS` on **VIS** can advance a primary case. A filterband `TWILIGHT_CONTIGUOUS` row is diagnostic only. `SOURCE_FILE_MISSING` or `UNREADABLE` on VIS is a local-data blocker and cannot be misreported as evidence that SASZE did not observe.

The strict gate is independently exercised before the archive scan with synthetic NetCDF cases for continuous sampling, an internal gap, readable source-day data with no twilight samples, a partially unreadable same-day source set, an openable NetCDF file lacking decodable native-time coordinates, and a genuinely missing VIS source. The self-test also proves that continuous filterband timestamps cannot rescue a discontinuous or missing primary VIS stream. The audit records integration-time/scan modes and native health/saturation/high-SZA flag names if they exist. Multiple integration times are not themselves a failure; SASZE intentionally used multiple integration modes to improve low-signal SNR while protecting intense spectral regions.

## Holdout boundary

Do **not** pass `--include-sasze-radiance-sample` during Phase 0/Stage A. That option exists only for a later explicitly opened Stage-B workflow after exact cases, model inputs, settings and metrics have been frozen.

The extractor never writes to the ARM archive. Its output must be placed outside the archive root; the program refuses an output directory inside the source tree.

## What happens after the ZIP is available

1. Read the **VIS** rows of `stageA_sasze_twilight_operability_2024.csv` first. NIR/filterband rows are supporting diagnostics.
2. If at least one VIS case is `TWILIGHT_CONTIGUOUS`, apply the already-preregistered independent atmosphere/QC gates only to those primary survivors.
3. If all 20 VIS rows are readably `TWILIGHT_SAMPLES_ABSENT`/`TWILIGHT_DISCONTINUOUS`, record `HALT_CURRENT_TARGET_NO_OBSERVATIONAL_SUPPORT`; do not move the solar-depth target or substitute a different observable after seeing that outcome.
4. If any VIS row is `SOURCE_FILE_MISSING`/`UNREADABLE`, resolve that preserved-archive integrity/access gap before any all-20 HALT decision.
5. Filterband twilight fill values are expected product semantics and are not an observational HALT condition. Full VIS/NIR radiance remains unopened until Stage B.

No full SASZE VIS/NIR radiance spectrum is required to resolve Phase 0.
