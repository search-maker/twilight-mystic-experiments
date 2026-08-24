# Empirical twilight-radiance source admission v1

## Status

`REVIEW_ONLY_PRIMARY_METADATA_CANDIDATE_IDENTIFIED_CALIBRATION_READINESS_BLOCKED_NO_TARGET_RADIANCE_OPENED`

This package advances the next unresolved validation layer after ASIV v1: **physical twilight model vs measured real sky**. It does not reopen ASIV ordinal 39, execute MYSTIC, inspect the selected candidate's target sky-radiance values, fit or retune any model, allocate a scientific ordinal, or authorize production.

The package deliberately freezes candidate identity and admission requirements **before** target radiance is opened. It preserves the existing project distinction:

1. surrogate vs MYSTIC;
2. MYSTIC/atmosphere vs measured real sky;
3. end-to-end prediction vs human first-seeing.

ASIV v1 addressed layer 1 for aerosol transport. This review starts preparation for layer 2 only.

## Frozen prior gate

The authoritative Issue #60 history already froze an observational-source admission rule under `MYSTIC-STATE-0066`, canonical SHA-256:

`da59630cea65410219bf3575376910ccf49f83ac6f5af4b36095d264a315bbfb`

The historical disposition was:

`REVIEW_ONLY_NO_ELIGIBLE_UNTOUCHED_SOURCE_IDENTIFIED`

The present review does not weaken that gate. Strict admission still requires absolute calibrated directional photopic luminance or a sufficient calibrated spectrum; exact UTC/site/pointing; independent AOD550 with uncertainty not fitted from the validation radiance; cloud/glare QC; immutable raw provenance; session-level calibration/validation isolation; source selection before opening target values; and predeclared uncertainty-aware comparison gates.

The existing repository metadata validator remains bound by exact blob identity:

`integration/twilight-observation-v1/observation_validator.py`

Git blob:

`67ffbda4cb20713871ec66b36768c7e1b5cdaa16`

## Primary candidate: Izaña / PGN Pandora209

The primary candidate is the public Pandonia Global Network archive at the Izaña Atmospheric Observatory, specifically the paired archive identities:

- `Pandora209s1`
- `Pandora209s2`

Public archive root:

https://data.hetzner.pandonia-global-network.org/Izana/

PGN data API:

https://api.pandonia-global-network.org/

PGN documentation/data access:

https://www.pandonia-global-network.org/

The paired `s1`/`s2` identity is consistent with a Pandora-2S dual-spectrometer installation, but **this review does not elevate that inference to an exact instrument/calibration binding**. The exact calibration files, applicable dates, radiance units, uncertainty representation, observation type/pointing, and usable twilight session universe must be verified from PGN metadata before target radiance values are read.

Generic Pandora-2S descriptions indicate complementary spectrometers spanning roughly 270–530 nm and 400–900 nm. Spectrometer 1 alone therefore does not cover the full 380–780 nm photopic target; spectrometer 2 evidence is required for the intended full-visible strict validation.

### Critical L1 product-type gate

PGN/NASA documentation describes L0 as raw field spectra and L1 as data after instrument-characteristic corrections. That does **not** imply that every L1 row is an absolute radiance. The Blick file contract explicitly provides a `Level 1 data type` field with these semantics:

- `1` = corrected count rate `[s^-1]`;
- `2` = radiance `[W/m2/nm/sr]`;
- `3` = irradiance `[W/m2/nm]`.

Therefore the strict real-sky directional-radiance validation will admit only selected Pandora209 measurements whose metadata independently states **L1 data type 2**, with radiance units `W/m2/nm/sr` and an acceptable uncertainty/calibration binding. Type 1 corrected-count-rate rows and type 3 irradiance rows are ineligible for this strict target unless a separately reviewed, traceable absolute-radiance conversion is frozen before target values are opened.

This type/units check is metadata-only and may be performed before reading the target spectral value arrays.

References for these semantics:

https://pandora.gsfc.nasa.gov/Data/html/processing.html

https://pandora.gsfc.nasa.gov/Data/html/versions.html

## Current calibration-readiness finding — blocker, not failure

The PGN Calibration Report reviewed for this package was published 2026-08-18 and generated at 2026-08-18 11:54 UTC:

https://reports.hetzner.pandonia-global-network.org/calibrationReport.html

The report surfaces historical finished processing for Pandora209 spectrometer 1 at Izaña with calibration-file identities:

- `20220720, v5` — Blick 1.8.50, processed 2022-12-01;
- `20221111, v4` — Blick 1.8.50, processed 2022-12-01.

The same current report lists open Izaña calibration-analysis sessions for Pandora209:

- s1 session 11 (`ID1796`, AnaFld, Blick 1.9.5);
- s1 session 12 (`ID1804`, AnaFld, Blick 1.9.5);
- s1 session 14 (`ID1805`, AnaFld, Blick 1.9.5);
- **s2 session 4 (`ID1806`, AnaFld, Blick 1.9.5)**.

The visible open-session row for `ID1806` does not show an assigned `NewCF` and still lists `EndDate` among missing documentation. The review also did not surface a finished/current Izaña s2 calibration-file identity elsewhere in that public calibration report.

This does **not** prove that spectrometer 2 is bad or uncalibrated. It proves only that the exact current s2 calibration file and its validity period have not yet been demonstrated from the metadata reviewed so far. Because s2 is needed for the full visible target, strict dual-spectrometer admission is therefore blocked until exact PGN calibration-file metadata resolves this point.

A separate public `calibrationfiles/` directory was also inspected. It did not surface any filename matching `Pandora209` in the indexed listing. That directory is therefore not treated as a complete authoritative inventory for Pandora209; absence there is not evidence that no ICF exists.

### Exact next calibration question

Before constructing a strict validation session universe, resolve through `/v1/calibrationfiles`, `/v1/operationfiles`, or equivalent PGN metadata:

1. which exact ICF(s) apply to `Pandora209s1` and `Pandora209s2`;
2. each ICF validity start/version and applicable observation dates;
3. the matching IOF/operation configuration;
4. whether selected L1 observations are data type `2 = radiance` rather than corrected counts or irradiance;
5. the radiance uncertainty semantics and wavelength validity/filter ranges.

All of this is metadata/header work. Target sky-radiance arrays remain closed.

## Why Izaña is unusually promising

Izaña provides independent environmental context that can satisfy requirements which blocked earlier historical sources:

- AERONET aerosol optical depth at/near the site;
- GAW-PFR aerosol optical depth as an additional independent reference;
- BSRN radiation observations;
- all-sky SONA imagery / cloud context;
- long-standing high-altitude atmospheric instrumentation and quality-control infrastructure.

Useful public background:

https://izana.aemet.es/

https://aeronet.gsfc.nasa.gov/

https://bsrn.awi.de/

The validation AOD must be taken from an independently frozen external source and timing rule. It may not be inferred by fitting the Pandora twilight radiance being validated.

## Required checks before any target radiance opening

No Pandora209 target twilight radiance is authorized to be read for validation until all of the following are frozen and independently reviewable:

1. **Resolve s2 calibration readiness** — bind an exact PGN ICF/validity period for Pandora209 spectrometer 2; do not infer one merely from the presence of an s2 archive or an open calibration session.
2. **Exact calibration binding** — identify exact PGN ICF and operation files applicable to each selected s1/s2 session.
3. **Absolute-radiance product gate** — prove from metadata that every selected strict-validation measurement is L1 data type `2 = radiance [W/m2/nm/sr]`; reject ordinary corrected-count-rate type 1 and irradiance type 3 for this directional-radiance target.
4. **Uncertainty semantics** — bind the exact uncertainty representation and usable wavelength/filter ranges for each spectrometer.
5. **Metadata-only session universe** — enumerate candidate sessions/files without reading target spectral radiance arrays; confirm the required twilight and pointing coverage.
6. **Dual-spectrometer stitching** — freeze a deterministic overlap/stitch rule for s1/s2 without examining the validation sky values.
7. **Independent AOD contract** — freeze source hierarchy, AOD550 conversion/interpolation, uncertainty propagation, maximum temporal separation and atmospheric-stability rejection criteria.
8. **Cloud/glare QC** — freeze independent QC sources and synchronization rules, including how SONA/BSRN/AERONET or equivalent metadata cause exclusion.
9. **Immutable provenance** — hash raw source files and bind calibration/operation/metadata identities before value opening.
10. **Session isolation** — assign sessions to calibration/validation roles deterministically before outcomes are examined.
11. **Comparison target** — freeze the exact model output to compare (direction, spectral integration, atmosphere inputs, refraction/geometry convention).
12. **Pass/fail metrics** — freeze uncertainty-aware aggregate and worst-case gates before target values are opened.

Until these checks pass, candidate status remains:

`PROMISING_METADATA_ONLY_STRICT_DUAL_SPECTROMETER_ADMISSION_BLOCKED_PENDING_EXACT_CALIBRATION_AND_L1_TYPE2_PROOF`

## Other sources and their role

### ResPan 2025 Greenbelt/Lauder

Reference:

https://doi.org/10.3390/rs17122071

This is a strong methodological benchmark: calibrated zenith twilight spectroradiometry, comparison with independent aerosol products, and detailed radiometric calibration. The paper states that ResPan data are not publicly accessible and that model simulations/experimental data are incomplete or subject to change. Published radiance/model comparisons are already opened. Therefore it is useful for methodology and possibly a future author-supplied dataset, but not as the untouched public strict holdout presently sought.

### Patat et al. 2006, Paranal

Reference:

https://doi.org/10.1051/0004-6361:20064992

Useful absolute UBVRI twilight benchmark with a large archival sample. It remains benchmark-only for the strict gate because the already-published observations are opened and there is no frozen independent per-observation aerosol/QC package matching the present contract.

### Koomen 1952

Reference:

https://opg.optica.org/josa/abstract.cfm?uri=josa-42-5-353

Useful historical absolute directional photopic benchmark, but not a modern strict validation source because independent aerosol characterization and immutable digital raw provenance are unavailable.

### Mateshvili et al. 2005

Reference:

https://doi.org/10.1029/2004JD005512

Useful spectral-shape diagnostic, but the reported experimental data were handled in arbitrary units/reconstruction, so it does not satisfy the absolute-calibration gate.

### TEMPO twilight L1B

Reference:

https://asdc.larc.nasa.gov/project/TEMPO/TEMPO_RADT_L1_V03

Calibrated twilight Earth radiance is valuable for atmospheric science but the satellite line-of-sight geometry is not the ground-based directional sky-radiance geometry needed for the star-visibility model. It is not the primary validation source for this layer.

## Hard boundaries

This review authorizes none of the following:

- reading Pandora209 target radiance arrays for validation;
- MYSTIC or other scientific solver execution;
- a new global scientific ordinal;
- ASIV rerun/retry/resume;
- retuning the ASIV or Level-B model;
- fitting AOD from the target radiance;
- changing the frozen aerosol scenario set;
- production/UI/default activation;
- claiming measured-real-sky or human-first-seeing validation.

## Next safe transition

Perform a **metadata-only exact ICF/IOF and L1-type availability lookup for Pandora209 s1/s2**. Only after the s2 calibration/type-2 radiance blocker is resolved should the project construct a strict Izaña validation session universe and freeze the AOD/QC/stitching/comparison contracts. Target spectral radiance values remain unopened until a separate reviewed transition authorizes them.
