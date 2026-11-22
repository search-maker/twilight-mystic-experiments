# Tousey & Koomen (1953), published Table III: HUMAN sighting status series — OPEN diagnostic only

**Prepared 2026-11-21 EST, post-blackout.** Published source: R. Tousey & M. J. Koomen, *The Visibility of Stars and Planets During Twilight*, Journal of the Optical Society of America **43** (1953), pp. 177–183, published 1953-03-01, DOI [10.1364/JOSA.43.000177](https://doi.org/10.1364/JOSA.43.000177). First-party publisher HTML: https://opg.optica.org/josa/abstract.cfm?uri=josa-43-3-177 , **Table III**, “Star visibility observations, Washington, D. C, January 11, 1952.” The 10 table entries, grouped by four named stars, were individually transcribed from that publisher HTML; original scan/PDF page pixels and original 1952 logbook **NOT** inspected. Repository default-branch code search 2026-11-21 found references to Tousey/Koomen 1953 as already-open diagnostic but no matching Capella/1952 event rows; do not claim this is a new blind observational cohort.

## Bounded factual row fixture

Table fields are *as printed* (not model-calculated). The column headed `Z-Z_sun` is preserved literally; **do not infer its exact coordinate convention** without full text. The source gives star altitude H as a single reported value per star, not a measured per-event trace. Original clock zone, seconds, clock calibration and precise observer coordinates are not confirmed; printed local clock strings are **not** independently verified UTC times. Visibility phrases `To 1°` etc. are retained literally without reinterpretation as threshold, pointer tolerance, or NOT_SEEN.

```csv
target,source_magnitude,source_star_altitude_deg,source_Z_minus_Zsun_deg,source_clock_local_unverified,sun_altitude_deg,source_visibility_phrase
"Capella","0.2","40","171","17:23","-3.8","Very difficult"
"Capella","0.2","40","171","17:28","-4.7","To 3°"
"Capella","0.2","40","171","17:34","-5.7","Easy"
"Aldebaran","1.1","35","150","17:26","-4.4","To 1°"
"Aldebaran","1.1","35","150","17:29","-4.8","To 2°"
"Aldebaran","1.1","35","150","17:34","-5.7","Easy"
"Polaris","2.1","39","113","17:36","-6.1","Very difficult"
"Polaris","2.1","39","113","17:40","-6.9","To 1.5°"
"Vega","0.1","22","57","17:29","-4.8","To 2°"
"Vega","0.1","22","57","17:36","-6.1","Easy"
```

**Source-admission test (computed from these 10 transcribed rows only, not from a model):** ten status entries, four named stars, 1952-01-11 Washington DC; published solar altitudes -3.8 through -6.9 degrees. For each star, printed clock is strictly later and solar altitude strictly lower at the successive listed entries. First-to-last listed **status** separation (NOT first-appearance error):

| Target | Entries | First–last printed time | Duration (minutes) | Solar-altitude change (degrees) | Last published label |
|---|---:|---|---:|---:|---|
| Capella | 3 | 17:23–17:34 | 11 | 1.9 | Easy |
| Aldebaran | 3 | 17:26–17:34 | 8 | 1.3 | Easy |
| Polaris | 2 | 17:36–17:40 | 4 | 0.8 | To 1.5° |
| Vega | 2 | 17:29–17:36 | 7 | 1.3 | Easy |

The positive progression from reported difficult/bounded visibility to “Easy” spans **11 min (Capella), 8 min (Aldebaran), and 7 min (Vega)** on their printed observation rows. Polaris's last row has no “Easy” label. These are merely within-session differences between documented detections/status descriptions; they are not observer first-sight times, prediction residuals, or solar-depression thresholds.

## Mandatory fail-closed admission and blinding

- **PASS source authenticity (bounded):** original publisher-hosted 1953 article metadata and a readable Table III; explicit target identity, tabulated stellar magnitude, reported solar altitude, star altitude, direction field, city, civil date and clock readings for 10 actual human visibility-status observations.
- **FAIL first-visibility interval:** no explicit same-star *prior not-seen* with its timestamp, hence **zero valid last-NO → first-direct-YES brackets**. Earliest published listed sighting **is not** demonstrably earliest possible visibility.
- **FAIL complete matched atmosphere:** no simultaneously acquired event-level cloud/haze, aerosol optical depth/profile, absolute directional skyglow, observer identity/height, visual adaptation, clock calibration or fixed search cadence in the exposed Table III.
- **FAIL late-twilight support:** no row in solar depression (10.5,16] degrees; this source spans only 3.8–6.9 degrees. It cannot validate deep twilight and supplies no externally measured error bars.
- **FAIL blind holdout:** the paper and its values were public and were already identified as an open Tousey/Koomen diagnostic in project precontract. Use only for **descriptive, non-independent checks**; do NOT preregister these exposed entries as new unseen validation, refit a model after seeing them, or open Taylor/Jerusalem holdouts.
- **No computed prediction residual:** no frozen scientifically qualified model SHA/prediction file was used here; empirical minute error, bias/MAE/coverage are **NOT COMPUTABLE**.
- **Historical provenance status:** stable publisher URL, title/date/table/row transcription available; raw 1952 observing notebook and PDF page image hash NOT acquired.

**Priority handoff:** authenticated outreach owner is reenabled after the scheduled Brooklyn blackout but must still obtain *new* independent human observer opt-ins / raw dated same-target NO→YES records with matched directional atmosphere, and Coordinator must lock one V0/R1 protocol, model/input SHA, nonprotected cases and acceptance/stopping rules before exposing outcomes. These 1952 open entries are supplemental background and **do not** settle that priority. No new MYSTIC execution, paid action, protected holdout, denied Stage4 edit, or claim of model release.
