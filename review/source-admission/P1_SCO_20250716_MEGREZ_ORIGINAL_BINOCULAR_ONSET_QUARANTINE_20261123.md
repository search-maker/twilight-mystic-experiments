# P1 original first-onset candidate — 2025-07-16 Megrez at SCO (strict unaided-eye QUARANTINE)

Source inspection and reproducible finite numerical screen: **2026-11-23, Monday 13 Kislev 5787, America/New_York after 05:08 EST**, outside Brooklyn diaspora Shabbat/Yom Tov blackout. Checked current Stars scientific workboard #152, MYSTIC control #60, existing P1 event schema and blinding draft before admission. Search over all #152 comments found **zero** occurrences of "Megrez", "2025-07-16", or "July 16, 2025": this is an original *additional observation source entry*, not a new P1 observation and NOT validation evidence.

## Original first-hand log and independent site authority

- Observer-authored public journal: [ScienceDownEast / All Observations](https://www.sciencedowneast.com/joomla4/index.php/observations/all-observations), exact section **"General Session - July 16, 2025"**, immediately following the separate July 21, 2025 session. Critical: **DO NOT mix the sessions or assign the July 21 Summer Triangle times to July 16.**
- The original dated section says **St. Croix Observatory ("SCO")**, Nova Scotia; date **2025-07-16**, **9:00–11:30 PM ADT**. Official [RASC Halifax observatory page](https://www.halifax.rasc.ca/index.php/observing/14-st-croix-observatory) identifies SCO near St. Croix but does **not** provide verified exact GPS or observing-pad coordinates.
- The log explicitly says **9:55 PM ADT** Arcturus and Big Dipper visible, *"Megrez did not become visible until 10:21 PM"*. This is a human-authored negative-to-positive *narrative*, but **NOT** a time-stamped 9:55 Megrez-specific NOT_SEEN attempt. It gives **10:21 PM ADT on 2025-07-16 = 01:21 UTC on 2025-07-17** as the reported first-positive time.
- Crucial **optical-mode contradiction**: session header "Equipment: Naked eye, Canon 10x42 IS binoculars", immediately followed by author sentence *"I was only using my binoculars on this particular evening at SCO."* A naked-eye Megrez detection **cannot** be assumed. This is a DIRECT disqualifier pending an original observer clarification.
- Temperature 19–17°C; seeing and transparency explicitly **not recorded**. SQM **20.73** reported at **10:23 PM ADT** (2 min after the first-positive time), and 21.886 at 11:16 PM; SQM viewing direction, angular response, uncertainty, and sky conditions at the Megrez ray all **unknown**. No contemporary aerosol/AOD or adaptation/clock-calibration metadata.
- Identifier: **Megrez = delta UMa = HIP 59774**, Johnson-V candidate roughly **3.31** (secondary [Megrez summary](https://en.wikipedia.org/wiki/Megrez); original frozen ESA HIP Johnson-V bytes have NOT been received/hashed). No verified original catalog hash.

## New actual numeric source-linked geometry verification (not model prediction)

Executed offline *twice*, identical JSON output, with Python 3 + **pyswisseph 2.10.03** in Moshier mode and UTC calendar conversion. Source script SHA256 `aa6455a42a1aa0fd07c1959ffbfc43627758dca878355673a917daa99151d818`; exact JSON output SHA256 `1663a8ce73a1e8ee8967af62f0286b585c5506bc8e0cc7a3fc29a5cd92aab011`. The script was **executed in the run container**, **NOT committed or executed in GitHub CI**. Its source/output are retained as local run artifacts.

Because exact SCO coordinates are NOT verified, reference site is **illustrative (45.000°N, -64.000°E, 50 m)**, with **arbitrary screening-only** corners 44.8–45.2°N and -64.2 to -63.8°E; these are NOT site-position confidence intervals. No atmospheric refraction; the star is unpropagated approximate J2000 RA/Dec, not original HIP catalog custody. Angular numerical decimals are algorithm output, **not measurement accuracy**.

| Original log event | Verified clock conversion | Illustrative geometric center-Sun depression | Corner-box scan, not uncertainty | Approximate Megrez true altitude/azimuth | Geometric Moon altitude |
|---|---|---:|---:|---|---:|
| 9:55 PM ADT, Arcturus + Dipper context (NOT a timed Megrez NO) | 2025-07-17 00:55 UTC | **8.762°** | 8.524–9.002° | 51.24° / 310.52° | -19.03° |
| 10:21 PM ADT, Megrez reported first positive, binocular ambiguity | **2025-07-17 01:21 UTC** | **12.029°** | **11.786–12.272°** | **47.76° / 311.58°** | **-15.02°** |
| 10:23 PM ADT, SQM=20.73 (unknown pointing) | 2025-07-17 01:23 UTC | **12.268°** | 12.025–12.511° | 47.50° / 311.68° | -14.71° |

At the first-positive moment the J2000-based Sun/target angular separation is approximately 60.01°, the Moon is computed to be below the horizon, and its illuminated fraction ~0.611. **None** is contemporaneous measured aerosol, sky luminance at 48° elevation, or naked-eye adaptation. This event is in the **10.5–16° solar-depression geometry band** and has a **20–80° target altitude**, but **optical provenance and a real last-NOT_SEEN timestamp are missing**. It cannot support an onset residual or sky-radiance calibration.

## Provenance-checked admission manifest (explicit missingness)

```json
{
  "event_id": "EXTERNAL_CONTEXT_SCO_2025-07-16_MEGREZ",
  "origin": "observer-authored public HTML, exact dated session",
  "source_url": "https://www.sciencedowneast.com/joomla4/index.php/observations/all-observations",
  "original_html_bytes_sha256": null,
  "site": "SCO; exact GPS/elevation/observing pad unverified",
  "reported_local_clock": "2025-07-16 22:21 ADT",
  "converted_utc": "2025-07-17T01:21:00Z",
  "clock_uncertainty_seconds": null,
  "star": "Megrez; HIP 59774",
  "magnitude_original_hip_bytes_sha256": null,
  "last_explicit_same_star_not_seen_utc": null,
  "first_reported_positive_utc": "2025-07-17T01:21:00Z",
  "confirming_direct_eye_seen_utc": null,
  "unaided_eye_mode_verified": false,
  "binoculars_in_session": "10x42; author explicitly says binoculars only",
  "directional_sqm_same_ray_and_time_verified": false,
  "aod_cloud_adaptation_clock_qc": null,
  "site_consent_and_original_private_logs": null,
  "predictions_sealed_before_outcomes": false,
  "eligible_blinded_first_eye_onsets_added": 0,
  "measured_prediction_residual_or_mae": null,
  "late_twilight_model_support_promotion": false,
  "decision": "CONTEXT_ONLY_QUARANTINE"
}
```

### Finite owner handoff; do not contact outside authorized outreach channel

The **pre-existing outreach custodian/Model Closure Coordinator**, once its disabled/user-action-blocked channel is legitimately restored, can *ask*, without assumption or payment: (1) Was the Megrez first positive at 10:21 strictly **unaided eye**, **10x42 binocular**, or both? (2) Is there an independently recorded *Megrez-specific* earlier failed look time, any confirmation time, and original contemporaneous log/audio/photo? (3) Exact SCO pad and horizontal obstruction, clock error/time-zone, cloud and observer adaptation? (4) Was SQM at 10:23 aimed at Megrez (~az 312°, alt 48°), zenith or elsewhere; unit, device model and calibration? (5) Consent/data publication terms. **No message sent.** Even recovered retrospective data could not substitute for pre-registered, blinded prospective P1. Keep Taylor/Jerusalem holdouts sealed. No MYSTIC ordinal67/68/new solver run, release/fit/retrained thresholds, money, or protected data touched.

**Admission:** original new historical source entry **PASS as context only**; **strict unaided-eye first-visibility calibration FAIL**; in 10.5–16° band **0 new eligible brackets**, **no empirical prediction error**, model **UNSUPPORTED/null**.
