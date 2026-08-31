# ARM SGP post-G3 exact-eight minimal data request v1

Status: result-blind acquisition handoff only. This file does **not** select a primary case, does not open SASZE radiance magnitudes, and does not alter any frozen scientific gate.

Authoritative candidate basis: Issue #60 G0-V2 admission `5473411963` + authoritative G3 semantic re-audit `5480629113`. Exactly eight still-blind G3 survivors remain:

| order | case_id | exact -6 UTC | exact -8 UTC | G0 valid 464-nm samples (-8/-7/-6) |
|---:|---|---|---|---|
| 89 | 2024-01-27_dusk | 2024-01-28T00:17:28.689966Z | 2024-01-28T00:27:56.939546Z | 7 / 7 / 5 |
| 99 | 2024-02-01_dusk | 2024-02-02T00:22:33.308189Z | 2024-02-02T00:32:55.905415Z | 6 / 16 / 24 |
| 161 | 2024-03-03_dusk | 2024-03-04T00:52:46.844963Z | 2024-03-04T01:02:45.857405Z | 6 / 6 / 5 |
| 163 | 2024-03-04_dusk | 2024-03-05T00:53:41.973209Z | 2024-03-05T01:03:40.768835Z | 11 / 8 / 5 |
| 167 | 2024-03-06_dusk | 2024-03-07T00:55:31.759900Z | 2024-03-07T01:05:30.248668Z | 21 / 21 / 19 |
| 209 | 2024-03-27_dusk | 2024-03-28T01:14:18.800820Z | 2024-03-28T01:24:24.898437Z | 11 / 11 / 5 |
| 211 | 2024-03-28_dusk | 2024-03-29T01:15:12.205519Z | 2024-03-29T01:25:19.174063Z | 8 / 6 / 12 |
| 339 | 2024-05-31_dusk | 2024-06-01T02:12:47.082575Z | 2024-06-01T02:24:51.346239Z | 14 / 19 / 12 |

## Smallest useful science extraction

For each exact event, extract only the event/core support needed to classify the already-frozen post-G0 gates. For high-cadence event-time streams, a practical transfer window is exact -6 UTC minus 10 minutes through exact -8 UTC plus 10 minutes; preserve **all native timestamps and QC** inside the extracted window so the frozen gate can be applied without interpolation or metadata-only inference.

1. **G2 cloud / clear-sky evidence**
   - KAZR/ARSCL: prefer the current quality-qualified `.c1` product if it exists; use `.c0` only if `.c1` is genuinely unavailable and preserve that downgrade explicitly.
   - CEIL and/or MPL cloud-mask product with native sample times and all relevant QC/flag variables.
   - HSRL/Raman feature/cloud masks when present, with QC.
   - Required output is the native time series/flags, not a precomputed PASS/FAIL.

2. **G4 event-time aerosol profile**
   - Corrected SGP HSRL product with `code_version=2.6.7`, not the known 2.6.5 geometry-pairing version.
   - Preserve native range/height coordinate, 532-nm aerosol extinction/backscatter/depolarization and their uncertainty/QC/feature fields needed to construct the event-time profile over the twilight core.

3. **G5 independent Raman diagnostic**
   - `sgprlprofbeC1.c1` (or exact current equivalent) over the same window, including aerosol extinction/backscatter/depolarization, height/range and matching QC/uncertainty fields.

4. **G6 independent spectral AOD / stability**
   - Contemporary ARM MFRSR AOD VAP, expected stream family `sgpmfrsr7nchaod1michC1.c1`, over the candidate date/daylight period with all spectral AOD, uncertainty/QC/calibration variables.
   - Existing CSPHOT/ARM AERONET AOD stream over the same daylight period if available.
   - Public AERONET V3 Level-2 direct-sun AOD and ALM/HYB availability have already been acquired independently; do not re-download them merely for this handoff.

5. **G7 thermodynamic profile**
   - The two bracketing measured SGP sonde ascents around each event where available, with pressure/temperature/humidity/dewpoint/altitude and QC. Preserve launch times and full measured ascent; any extension above balloon top remains explicit non-measurement provenance.

6. **G8 surface / ground state**
   - Same-day or nearest defensible daylight MFR upwelling + MFRSR downwelling narrowband/broadband irradiance and QC.
   - QCRAD quality-controlled broadband up/down shortwave and relevant ground/surface-state corroboration.
   - Do not form a twilight irradiance ratio at -6..-8; transfer a nearby-daylight surface constraint with explicit temporal/spectral/BRDF uncertainty.

7. **G9 ozone / upper atmosphere**
   - ARM/OMI daily ozone (`gecomiX1.a1` or current equivalent) for each candidate date, including total column/QC and profile information if the product actually contains it. If only total column exists, preserve the column as retrieved and leave vertical shape unresolved/assumed for the later preregistration.

8. **SASZE health/housekeeping only — radiance firewall remains closed**
   - `sgpsaszefilterbandsC1.a1` and SASZE VIS housekeeping/QC/calibration/status variables needed to judge instrument health across the exact event windows.
   - Do **not** include/open full VIS/NIR `zenith_radiance` spectra or radiance magnitudes at this stage. Full selected-case spectra are Stage B only after deterministic non-radiance selection + complete preregistration.

## Provenance requirements

For every transferred source file/extract preserve: original ARM datastream/file name, product/version (`code_version` where applicable), source URL/order identity if available, byte SHA-256, native time support, extracted variable list/units, QC/flag definitions, and extraction method/version. Missing data must remain `MISSING`; do not synthesize, interpolate, or substitute a metadata coverage envelope for native sample evidence.

## Current independent AERONET result already available

The public AERONET acquisition artifact is run `33412493664`, artifact `9765688951`, digest `sha256:681adec27c7d1428b247e74e22dec596f9cff1e59fb0fdfa90c1fdbf0286b61f`. It provides Level-2 direct-sun spectral AOD support for seven of the eight within the preceding ~5.7 h or better, while `2024-03-06_dusk` has no AERONET AOD sample in the preceding six hours. No exact-eight event has a finite Level-2 ALM/HYB SSA440 + real refractive-index record within +/-24 h of the -6 anchor. Under the frozen protocol this does **not** automatically fail those cases; it leaves AERONET primary microphysics unavailable and requires the already-frozen typical-AOD/profile-closure path unless another qualifying source exists.

No case is selected by this request. `radiance_magnitudes_opened=false`; `mystic_result_opened=false`.
