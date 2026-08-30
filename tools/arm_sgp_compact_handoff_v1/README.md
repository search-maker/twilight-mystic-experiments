# ARM SGP compact local handoff v1

Purpose: make the preserved ~65 GB ARM SGP order scientifically usable from a small, uploadable handoff **without modifying the archive and without opening the held-out SASZE radiance**.

This is a Phase-0 data-provenance tool. It does not run MYSTIC, fit Taylor/Jerusalem, compute validation residuals, choose cases from model agreement, or alter any source byte.

## Current controlling ARM V1 recovery gate — V2 exhaustive anchor support

The historical strict 20-priority-case full-core continuity gate below is now **closed as a historical gate** by authoritative Issue #60 comment `5471264663`: its exact recovered VIS audit found 0 `TWILIGHT_CONTIGUOUS`, 4 `TWILIGHT_DISCONTINUOUS`, and 16 `TWILIGHT_SAMPLES_ABSENT`, with all 20 readable. Do not weaken, reinterpret, or rerun that old rule as if it were the current recovery protocol.

The current project-V1 recovery path is the distinct, pre-result protocol `ARM_SGP_REAL_SKY_VALIDATION_V2_EXHAUSTIVE_ANCHOR_SUPPORT`, also frozen in Issue #60 comment `5471264663`. It audits **all 344 dawn/dusk events** for local civil dates 2023-12-14 through 2024-06-02 using geometric/unrefracted solar-center crossings at -8, -7, and -6 degrees.

For each anchor V2 requires, exactly as frozen:

- at least one native `sgpsaszevisC1.a1` timestamp within +/-5.000 s;
- at least 10 native VIS timestamps within +/-30.000 s;
- after timing passes, at least 5 valid/non-fill samples inside that +/-30 s window at the native VIS pixel nearest 464.020874 nm;
- no interpolation and no full-core max-gap rule;
- no SASZE radiance magnitude may be emitted or inspected during this gate.

`2024-02-08_dusk` is permanently `EXPOSED_DEVELOPMENT_ONLY` under the holdout firewall and can never become a primary held-out case even if its V2 timing/validity support passes.

### The one current local V2 command

From a Windows clone at the latest PR #663 head, run once against the preserved/recovered SASZE VIS source tree:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\arm_sgp_compact_handoff_v1\run_arm_v2_anchor_support.ps1 -ArchiveRoot "<ARM_SOURCE_ROOT>"
```

Return/upload only the generated `ARM_SGP_V2_ANCHOR_SUPPORT_*.zip`.

The wrapper runs a solver-free synthetic self-test first. The hardened executor preserves native time-axis indexing through masked/non-finite time entries, refuses masked/non-finite wavelength coordinates, chooses the nearest 464.020874-nm native pixel independently for each contributing source file, and combines duplicate-timestamp validity by logical OR. Those are mechanical correctness safeguards only; none changes the frozen V2 windows, counts, firewall, ranking, or HALT rule.

If no still-blind event passes all V2 gates, record exactly `HALT_ARM_SASZE_V2_NO_ANCHOR_SUPPORTED_PRIMARY_EVENT` and move primary validation to a genuinely different dataset/instrument/site rather than relaxing the windows.

## Historical full compact-handoff run

The broader Phase-0 inventory/extraction package remains available and useful when a fresh compact inventory is actually needed. From a Windows clone of this repository:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\arm_sgp_compact_handoff_v1\run_arm_compact_handoff.ps1 -ArchiveRoot "<FOLDER_CONTAINING_THE_PRESERVED_ARM_ORDER>"
```

The wrapper keeps its temporary Python environment outside the repository and outside the ARM archive, installs the small reader dependencies, syntax-checks the package, runs a synthetic native-time continuity self-test, scans the archive read-only, compacts structurally equivalent NetCDF headers, captures bounded DQR/DQPR/quality-document excerpts when present, reruns the historical strict SASZE native-time gate, then produces a compact ZIP plus its SHA-256. Upload/share the ZIP only; keep the original ARM order untouched.

## Important SASZE product-semantics correction

Actual local 2024 SASZE file evidence established a distinction that file-envelope metadata alone could not show:

- `sgpsaszevisC1.a1` and `sgpsaszenirC1.a1` contain the calibrated full spectral radiance stream through twilight, with native validity/fill masking that changes with the dual-integration acquisition.
- `sgpsaszefilterbandsC1.a1` keeps timestamps through twilight, but its **derived filterband radiance/transmittance product is daylight gated**. In the inspected 2024-02-09 file every filterband radiance is fill over apparent solar zenith 95.9–97.9 deg, while populated filterband radiance over that day is confined to apparent solar zenith 51.2–89.0 deg.

Therefore the held-out-observable source is the calibrated full VIS stream, not filterband continuity. NIR is a secondary spectral extension. Filterbands remain a useful daylight-derived diagnostic/timing stream but cannot prove that the twilight held-out spectrum exists or does not exist.

The historical 20-case result does not establish the V2 result. V2 is a distinct preregistered all-344 anchor-support audit, and its thresholds must not be changed after seeing its outcome.

## Broad compact-handoff outputs

The compact ZIP produced by `run_arm_compact_handoff.ps1` contains:

- `archive_inventory.csv` — every source filename, inferred datastream/date, size, SHA-256, NetCDF readability, **native decoded** time coverage/sample count, schema signature and error state.
- `netcdf_headers.jsonl` — structurally de-duplicated NetCDF dimensions, global metadata keys/nonvolatile values, variables, units, dimensions and variable attributes. Record/time dimension lengths are summarized as observed ranges rather than duplicating otherwise identical daily schemas. Daily volatile coverage/history attributes are deliberately not used as a sample-continuity proof.
- `quality_metadata.jsonl` — discovered QC/quality/DQR/DQPR/flag metadata from NetCDF global and variable attributes, including flag meanings/masks when present.
- `quality_documents.jsonl` — bounded excerpts from small text-like DQR/DQPR/data-quality/readme/manifest files in the order, retaining source relative path, source SHA-256, size and truncation/read disposition. Binary-looking or large files are noted rather than copied.
- `daily_availability.csv` — day-by-day availability by concrete datastream.
- `family_daily_availability.csv` — explicit available/absent matrix for the science interval 2023-12-14 through 2024-06-02 for SASZE, HSRL, Raman/RLPROF, CSPHOT AOD, MFRSR/NIMFR AOD, ARSCL, ceilometer, sonde and surface/albedo families.
- `issues.csv` — corrupt/unreadable/hash/extract notes; absence is kept distinct from unreadability.
- `representative_extracts.jsonl` — deterministic first/middle/last small samples from relevant datastream families, preserving original values, units, dimensions, QC and coordinate metadata. **SASZE radiance/transmittance values are excluded by default**; SASZE timing, wavelength coordinates and housekeeping remain visible so the radiance holdout stays protected.
- `stageA_sasze_twilight_operability_2024.csv` — historical 60-row audit = 20 frozen cases x three SASZE streams. `sgpsaszevisC1.a1` is `PRIMARY_HELDOUT_SUPPORT`; `sgpsaszenirC1.a1` is `SECONDARY_SPECTRAL_EXTENSION`; `sgpsaszefilterbandsC1.a1` is `DAYLIGHT_DERIVED_DIAGNOSTIC`.
- `summary.json` — compact family/historical-gate summary.
- `handoff_manifest.json` — tool/runtime versions plus SHA-256/size for every handoff output, refreshed after all post-processing.

The V2-specific wrapper instead produces a compact `ARM_SGP_V2_ANCHOR_SUPPORT_*.zip` containing the exact 344-event universe, timing/validity-only audit, summary, and output hashes. It does not emit SASZE radiance magnitudes.

## Historical strict 20-case gate semantics — closed, retained for audit only

Each historical audited stream had five timing dispositions:

- `TWILIGHT_CONTIGUOUS`: native samples bracket the whole chronological -8..-6 degree core and no positive gap in the full bracketing segment, including the two edge gaps, exceeds `2 x median_positive_source_day_cadence`.
- `TWILIGHT_DISCONTINUOUS`: some core samples exist but the bracketing/gap rule fails.
- `TWILIGHT_SAMPLES_ABSENT`: matching readable file(s) exist but no native sample lies in the core.
- `UNREADABLE`: one or more matching source files cannot be opened or do not provide decodable native timestamps; a partially unreadable same-day source set fails closed even if another matching file is readable.
- `SOURCE_FILE_MISSING`: no matching preserved local file exists.

That old gate is immutable historical evidence. Its completed result is `HALT_CURRENT_TARGET_NO_OBSERVATIONAL_SUPPORT` for the original 20-priority target. **Do not use these full-core continuity dispositions as the V2 anchor-support rule.**

## Holdout boundary

Do **not** pass `--include-sasze-radiance-sample` during Phase 0/Stage A. That option exists only for a later explicitly opened Stage-B workflow after exact cases, model inputs, settings and metrics have been frozen.

The extractor never writes to the ARM archive. Its output must be placed outside the archive root; the broad compact-handoff program refuses an output directory inside the source tree.

## What happens after the V2 ZIP is available

1. Read the 344-row V2 timing/validity audit without opening any radiance magnitude.
2. Retain only still-blind `G0_V2_PASS_BLIND_CANDIDATE` events; Feb-08 remains excluded regardless of technical pass.
3. Apply the frozen independent gates/ranking from Issue #60 `5471264663`: corrected HSRL 2.6.7 + independent spectral AOD stratum first, then cloud/Moon/sonde/AOD/surface/ozone completeness, stronger independent AOD temporal support, more valid 464-nm samples, UTC chronology tie-break. Moon must remain at or below -10 deg airless topocentric altitude throughout the -8..-6 core.
4. Freeze approximately 1–3 primary cases, atmosphere-construction rules, uncertainties, MYSTIC settings and comparison metrics before any held-out SASZE radiance is opened.
5. Only then execute the direct spherical MYSTIC prediction and held-out SASZE comparison. No post-result tuning.
6. If no still-blind event passes the complete V2 path, record exactly `HALT_ARM_SASZE_V2_NO_ANCHOR_SUPPORTED_PRIMARY_EVENT` and change dataset/instrument/site rather than changing the preregistered anchor windows.
