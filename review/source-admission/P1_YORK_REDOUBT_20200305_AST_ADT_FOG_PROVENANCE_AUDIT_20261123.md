# P1 original log provenance audit: York Redoubt, Capella, 2020-03-05

**Audit date:** 2026-11-23 ~19:05 America/New_York (Monday evening, 14 Kislev 5787, non-blackout).
**Status:** NEW independent source-QC finding; **NO-GO for first-visibility model validation**.
**Scientific governance:** #60; workboard starsvisibility #152. No model tuning, MYSTIC dispatch, protected Taylor/Jerusalem sample, paid action or outreach send.

## Primary and independent corroborating sources
- [Observer-authored original session page](https://sciencedowneast.com/joomla5/index.php/observations/all-observations/general-session-march-5-2020), *General Session – March 5, 2020*, page currently marked created 2020-03-05 and last updated 2024-09-21. **Original raw field notebook not retrieved; original HTML bytes/SHA not secured**.
- [Nova Scotia historical clock transition for 2020](https://www.timeanddate.com/time/change/canada/nova-scotia?year=2020): daylight time began **2020-03-08 02:00**, three days *after* the observation. On 2020-03-05 civil timezone was **AST UTC-04**, not ADT UTC-03.
- [GeoNames site centroid](https://www.geonames.org/6185598/york-redoubt-national-historic-site-of-canada.html): York Redoubt 44.59661 N / -63.55378 W, approximate elevation 60 m; **NOT** observer GPS.

## What the actual observer page states
Session 2020-03-05, York Redoubt, 19:00–21:00 **labeled ADT**. Author describes fog before 19:25, when it cleared, and **Capella noticed around 19:30**, under a separate visual equipment subsection, with the Winter Circle appearing as sky cleared. Moon listed 81% waxing gibbous. Session lists visual/binocular/telescope; transparency, seeing, temperature, SQM unrecorded. **No verified observer-adaptation history, directed NO for Capella, repeat unaided confirmation, instantaneous AOD or star-direction photometry**.

## Quantitative original timestamp conflict (two explicitly conditional cases)
Python + Swiss Ephemeris 2.10.03, Moshier solar RA/Dec + true geometric solar-center altitude, approximate York Redoubt site position, 60 m, no refraction. Computed from the written **clock times**, not established real observation instants:

| Written clock | Interpretation | UTC | True-center solar depression |
|---|---|---|---:|
| 19:25 fog clearance | Correct historical AST UTC-04 | 2020-03-05 23:25 Z | 14.489691° |
| 19:25 | Literal mislabelled ADT UTC-03 | 2020-03-05 22:25 Z | 3.835821° |
| 19:30 Capella | Correct historical AST UTC-04 | 2020-03-05 23:30 Z | **15.372348°** |
| 19:30 | Literal ADT UTC-03 | 2020-03-05 22:30 Z | **4.723303°** |

At 19:30, alternative timezone interpretation shifts computed solar depression by **10.649045°**. Historical tzdata independently confirms 2020-03-05 19:30 America/Halifax = UTC-04. This **does NOT prove the observer's wall clock was set to AST**; the page's ADT label may be a clerical mistake, or the clock-time meaning may need source-author clarification.

The fog cleared about five reported minutes before the Capella appearance. Thus even if the wall clock is resolved, the first-noticed event cannot be isolated from a fast-changing cloud/fog transmission window. If AST is correct, this would be a very late Capella noticing at a computed ~15.37° Sun depression, not a defensible visual contrast threshold; if literal ADT is correct, ~4.72° is still confounded and approximate. **Never treat this as a valid detection at either depression without raw notes.**

## Admission and next action
- Human visual appearance mention: **1** (Capella, approximate); verified first-NO→first-YES→confirm onset bracket: **0**.
- Residuals/errors vs scientific model: **none**, since no approved frozen model SHA/prediction or non-protected independent paired observations.
- Provenance status: `REJECT_FOR_BLIND_FIRST_ONSET`; direction-matched sky radiance: absent; AOD and adaptation: absent; moon: reported 81%, not radiance-calibrated.
- Prospective field protocol decision (before any data): require recorder timezone **IANA zone and UTC with offset**, verify DST at event date, record fog/cloud *at star direction* each attempt; assign one target per observer/window, log explicit naked-eye target-directed NOT_SEEN, YES, independent CONFIRM with dwell and optics-exposure time. Cloud-clearing onsets must be excluded or stratified by a pre-declared rule.
- Only existing authorized outreach owner/Coordinator may ask for the March 2020 raw timestamp basis and observer consent; do not send via substitute paths while outreach is disabled.
- Taylor/Ann Arbor and Jerusalem holdouts protected. No solver or scientific validation campaign dispatched.

**Reproducible local evidence:** `york_redoubt_time_audit.py` and `york_redoubt_time_audit_result.json` were executed once under Python/Swiss Ephemeris with three independent numerical assertions and zero admitted human first-sighting outcomes; SHA256 script `02d33e006f037d0bd6a5ee6ec10129bf1f49b7dd5a9d7cec94a508d5567ea813`; local result SHA256 `ef585b79eccb61674a9deec98d2cf082d90a5500dda16f4397be70a9029bf0b5`. **No raw original-log hash and no science-model prediction hash.**
