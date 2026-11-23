# P1 original human-visual / SQM witness: St. Croix Observatory, 2019-10-28 — context admitted, first-onset validation EXCLUDED

**Audit date**: 2026-11-23, America/New_York, after live Monday 13 Kislev 5787 calendar/time guard. **Status**: SOURCE-QC PASS for separately reported human visual star visibility and numerical SQM readings; P1 first-visibility onset **NO-GO**; no prospective experiment performed. New historical record, not to be counted as model verification or as an independent model-performance sample.

## First-hand originals and cross-source site identity

1. [ScienceDownEast's dated original observer log, *General Session – October 28/29, 2019*](https://www.sciencedowneast.com/joomla4/index.php/observations/all-observations/general-session-october-28-29-2019) — source text lines 64–80, retrieved 2026-11-23. Location **SCO**, night **2019-10-28/29**, log-time zone **ADT**, transparent/seeing both “Very Good (4)”, no early cloud/wind, low humidity qualitatively. Observing kit header says 10x42 binocular, but **the 19:05 Summer Triangle subentry expressly says “Equipment: Visual”**; do not transfer binocular mode from other entries to that subsection.
2. [RASC Halifax Centre's first-party SCO telescope documentation](https://halifax.rasc.ca/index.php/sco-telescopes), near the bottom under “The To Do list”, has specific telescope-controller site settings: **44°56′53.00″ N, 64°02′27.00″ W, 90.00 m**. Decimal = **44.94805556, −64.04083333**, 90 m. The location is the official SCO equipment reference, not independently measured coordinates of the human observer's particular eye position. General [SCO observatory description](https://www.halifax.rasc.ca/index.php/observing/14-st-croix-observatory) corroborates the facility.
3. Source of solar computation: **Swiss Ephemeris** Python module, geocentric solar center ecliptic position and ecliptic-to-horizontal, **true geometric center altitude, no atmospheric refraction**. 2019-10-28 19:00–19:30 **ADT = UTC−03:00** per America/Halifax zone database (22:00–22:30 UTC). These are retrospective computations, **not times/predictions from the StarsVisibility model**. Keep rounded degrees; do not imply source timestamp precision to seconds or atmospheric accuracy.

## Original recorded events (do not conflate instrument and eye)

| ADT 2019-10-28 | UTC | Original report | Recomputed Sun below horizon |
|---|---|---|---:|
| 19:00 | 22:00 | SQM **18.53 mag/arcsec²**, device pointing and calibration unspecified | **9.33°** |
| 19:05 | 22:05 | Summer Triangle subsection “Equipment: Visual”; Vega located, then Altair near zenith; Deneb followed “a while later”. **19:05 is the subsection label, not an independently measured onset time for each star**. | **10.20°** |
| 19:30 | 22:30 | SQM **20.98 mag/arcsec²**, unspecified pointing; no corresponding first-sighting eye event | **14.60°** |
| 22:44 | 01:44 next UTC day | SQM 21.14 mag/arcsec² (source only; solar geometry not computed in this fixture) | — |
| 23:58 | 02:58 next UTC day | SQM 21.18 mag/arcsec² (source only) | — |

The 30-minute **SQM difference = 2.45 mag/arcsec²**, equivalent to **10^(0.4 × 2.45) = 9.5499-fold** lower indicated sky luminance at 19:30 relative to 19:00, **provided** both instrument readings are comparable/valid. This is an actual published instrument observation, **not** a measured directional star background nor eye-onset error; device orientation, angular response, quality/calibration and correction metadata are not given. A 19:05 visual source-subsection and 19:00 SQM are **5 min apart**; assigning a contemporaneous same-ray value is prohibited. 19:30 at Sun depression 14.60° lies within the previously unsupported 10.5–16° range **for instrument context only**, not for human threshold prediction.

## Eligibility and source manifest

- Historical named-site witness: **YES** (original source links above). Date and ADT zone: **YES**. Official named SCO controller coordinate: **YES**; exact human eye-location separately measured: **UNKNOWN**.
- Real human observation: **YES** for a positive visual-labelled star group, **NOT** optical-only camera inference. Exact individual-star first-positive instants: **NO**. Two prior timed genuine **same-star non-detections**: **NO**. Confirmed subsequent detection within 120 s: **NO**. Target V magnitudes verified against frozen HIP catalog: **NO**. Directional stellar alt/az calculated and time-matched: **NOT DONE**. Individual observer protocol/eye adaptation/eyesight or screen history: **UNKNOWN**.
- Cloud: qualitative only. Near-star cloud opacity, directional artificial skyglow, aerosol AOD profile and photometric spectral calibration: **UNKNOWN**. SQM beam pointing: **UNKNOWN**. A photometer reading at zenith, if any, must not be mapped to a <=80° ray without an explicit angular model.
- True first-visibility bracket count **0**; eligible independently scored P1 sample **0**; temporal forecast errors **NOT COMPUTABLE**; qualified forecaster executable/input SHA **NOT FROZEN**; outcome-blind registration or consent **NOT DONE**.
- Raw HTML byte custody **NOT RECOVERED** (download attempt failed); original raw SHA-256 **NULL**, no invented hash. Web reader yielded source passages and line indices. Local reproducible synthetic-free *source-derived calculation* script SHA-256 **15a30afa0372c1abb40e56d77b5fb4399093586462d649699021a5037e44adb1** and output JSON SHA-256 **40e781ef2f5aa6abb3591aeb3f6bd1169e6264cc20e7dd1ac0b6046517abfa36** (conversation artifacts); repeated execution matched byte for byte, but this does **not** authenticate original web-page bytes.
- This is a retrospective external observational **context/exclusion case**, NOT selected as an independent first-onset model-validation case. No Taylor/Ann Arbor/Jerusalem protected data, tuning, solver/MYSTIC dispatch, spent ordinals, paid compute, site contact, consent claim, blocked Stage4 write, merge or deployment.

## Next falsifiable action

Through the **existing authorized outreach owner only**, if legitimately enabled, ask whether the original author has raw time-stamped first-search failures for Vega / Altair / Deneb, recorded individual unaided first-positives, sky meter direction/calibration and raw logs; if any are absent, keep excluded. Independently for prospective P1, select approved weekday sites, consented adults, frozen HIP catalog/qualified model SHA, blind per-look NOT_SEEN → DIRECT_SEEN time receipts, and directional atmospheric/skyglow data **before** opening observations. Existing P1 draft and release gates remain unmodified. Do not silently promote this source or fit on it.
