# NASA LaRC NightBLUE HSRL-2 underflight primary-locator audit — 2026-11-22
**Status: NEW independent measured-atmosphere DATASET LOCATOR ONLY; original data bytes NOT obtained; no human first-sighting validation. Not an experiment or new simulation.**
**Research governance:** StarsVisibility workboard #152; MYSTIC controls #60; no Taylor/Ann Arbor/Jerusalem protected data, no MYSTIC dispatch, no production mutation.

## Sources inspected, separately
1. Original NASA Langley aircraft/ATLID underflight campaign index (web table, last updated 2025-10-27):
   https://www-air.larc.nasa.gov/missions/earthcare-airbornelidar-underflights/
2. Original NASA LaRC *EarthCARE-LaRC Lidar Underflights ReadMe*, dated 2025-10-23 (PDF page 1 describes 10-second gridded profiles and Nav_Data/GPS; pages 2–3 give access stipulations and table):
   https://www-air.larc.nasa.gov/missions/earthcare-airbornelidar-underflights/docs/EarthCARE-LaRC_Lidar_Underflights_README.pdf
   Actual original page images for PDF pp. 1–3 were visually inspected, including the contradictions below (not just search snippets).
3. Corresponding LAS campaign HDF5 references (titles/file names only, NOT downloaded): the NASA HTML index. A login is required to access the NightBLUE processed data files; original README p. 2 says to request archive credentials from NASA HSRL-2 data-management staff. No request or implied permissions/commitment has been made.

## Exact new candidate and two real source disagreements
NASA index lists 24 EarthCARE underflights, of which NightBLUE occupies indices 9–24 (16 flights), with 11 flagged `N` (indices 11–21, night flights). All these are **airborne optical aerosol/cloud-profile measurements**, NOT naked-eye observations, and do not establish model bias or first-visibility. Navigation is aircraft GPS, **not a fixed ground observer's horizon or atmosphere**.

| Index | NASA index date (YYYY-MM-DD) | README date | NASA index UTC hours start–end | README UTC hours start–end | Lidar file name listed by index | Provenance verdict |
| --- | --- | --- | --- | --- | --- | --- |
| 11 | 2025-09-07 | 2025-09-07 | 4.3756–5.5144 | 4.3756–5.5144 | nightblue-HSRL2_G3_20250907_RA.h5 | Index and PDF **metadata match**, raw HDF5 not checked |
| 16 | **2025-09-12** | **2024-09-12** | 4.9953–5.9394 | 4.9953–5.9394 | **nightblue-HSRL2_G3_20250912_RA.h5** | **CONFLICT**: year in original PDF contradicts both original NASA index and filename; do not quietly correct when joining |
| 19 | 2025-09-17 | 2025-09-17 | **5.1619**–6.2258 | **2.1619**–6.2258 | nightblue-HSRL2_G3_20250917_RA.h5 | **CONFLICT**: start UTC differs by exactly 3.0000 h; cannot choose without original HDF5 / ground-truth flight navigation |

The HDF5 **names/URIs are locators, not authenticated file content**. No raw data, global attributes, DOI, NetCDF/HDF5 arrays, checksums, measured aerosol extinction/AOD, profile quality masks or cloud flags were recovered here. `raw_sha256=null`, `raw_access=LOGIN_REQUIRED`, `source_admission=LOCATOR_ONLY`, `direct_human_validation=NO`, `quantitative_model_error=null`.

## Scientific utility, strict limitations
- The official README states 10-second altitude-interpolated aerosol/cloud data with `/Nav_Data/gps_time, gps_lat, gps_lon, gps_alt` and `/State` (pressure/temperature/density interpolated from **GMAO**, which are not themselves in-situ independent soundings). Products carry version/DOI metadata in individual HDF5 files, **not necessarily the PDF**.
- NightBLUE `N` records listed around 02:00–07:00 UTC describe nocturnal aircraft underflights, not individually documented simultaneous **evening solar twilight**, and not a fixed ground star sighting. Any link to a solar depression (10.5,16] requires independent exact GPS timestamps/coordinates, ephemeris and field protocol, and cannot be inferred from campaign name or rounded UTC hours.
- Optical lidar backscatter/airborne profiles cannot be substituted for a directional 20–80° ground-view sky radiance, and cannot substitute for human last-NOT_SEEN to first-confirmed-DIRECT_SEEN. Instrument v2.6.7 ARM claims elsewhere do NOT apply to these NASA aircraft files; do not conflate distinct HSRL instruments.
- Do not promote Level-B support [2,10.5] to field minute accuracy, nor predict the (10.5,16] interval until actual independent validation. No Taylor/Jerusalem refitting.

## Bounded next action, normal authorized surface only
The Coordinator and authorized atmosphere/provenance owner can use the **official NASA source index + original README** to determine whether retrieving one SMALL, non-protected HDF5 file with legitimate archive access would produce an input-quality test without a paid or protected solver run. Request/access must go through a normal permitted owner; no bypass of archive login and no speculative data values. Before any intake, resolve the 2025-09-12 date and 2025-09-17 UTC start conflicts against the HDF5 file's actual `Nav_Data/gps_time`, flight date/global attrs, source SHA256, QC/altitude/nav, licensing and permissions. Then test only an explicitly preselected atmospheric *context* case, separate from P1 human first-sighting outcomes. Do not post private consent or archive credentials.

**Outcome:** new verifiable original NASA measurement-program locator and exact independent pair of metadata conflicts, **NOT recovered original HDF5 bytes or new first-star events**; first-sighting admitted=0; model error=NOT COMPUTABLE; late domain remains UNSUPPORTED/null.
