# ICOP 2008-09-28 — source admission: morning last-visibility of Canopus and Sirius (NOT P1)
Date of analysis: 2026-11-22, America/New_York Sunday evening (13 Kislev 5787 after sunset).
Classification: ORIGINAL_OBSERVER_STATEMENT_IN_PRIMARY_ARCHIVE_SEARCH_INDEX; RAW_SOURCE_BYTES_UNVERIFIED.
Science verdict: EXPLORATORY / NOT ADMISSIBLE TO BLINDED EVENING FIRST-SIGHTING VALIDATION.

## Original provenance and minimally extracted evidence
International Astronomical Center (ICOP), "Visibility of Shawwal Crescent (1429 AH)", Ramadan Waning (OLD) Crescent Observation Results, Sunday 28 September 2008:
https://astronomycenter.net/icop/shw29.html

Author-observer named in host archive: Ma'rufin Sudibyo.
Reported original site: 7°40′ south, 109°40′ east, elevation 21 m ASL, GMT+7.
Original stated start of lunar observation: 04:57 local.
Eastern sky: clear except low thin clouds to ~1° altitude.
Crescent observation employed both naked eye and 7×35 binoculars. Star observations were used to monitor increasing twilight, but the report **does not unambiguously specify whether the individual star checks were unaided**.
Star loss statements: Canopus was not seen since **05:12** local; Sirius since **05:15** local. Local apparent sunrise reported **05:31**.

This is an author-authored report archived by the observing organization, but this run verified it via **search-indexed text on the original host**. The full raw HTML bytes were not retrieved/hashes could not be verified, and no signed contemporaneous logbook, optical-mode or clock-correction evidence is supplied. Do not promote this to custody-verified raw evidence.

## Reproducible Sun geometry (NOT a model prediction)
The companion executable on this independent science branch is `icop_sudibyo_20080928_star_last_visibility_geometry.py`. It specifies local UTC+7, exact report coordinates (converted from minutes), Swiss Ephemeris/Moshier, Sun equatorial RA/Dec and refraction-off altitude, no atmospheric profile model. Locally executed equivalent code via Python / PySwissEph 2.10.03 on 2026-11-22 with six finite checks PASS (UTC timestamps, solar depression bounds, sunrise comparison). The committed file was fetched and verified in GitHub Contents after writing; the full committed bytes have **not been separately executed through a pinned clone**.

| Reported star | Local clock GMT+7 | Converted UTC | Geometric solar depression at report | Scientific modality |
| --- | --- | --- | --- | --- |
| Canopus | 2008-09-28 05:12 | 2008-09-27 22:12 UTC | **4.682584°** | First reported *not seen since*; no earlier paired star timestamp and optical mode ambiguous |
| Sirius | 2008-09-28 05:15 | 2008-09-27 22:15 UTC | **3.939806°** | First reported *not seen since*; no earlier paired star timestamp and optical mode ambiguous |

At stated 05:31 local apparent sunrise, the same mathematical method yields true Sun-center altitude **+0.022623°**. Near-zero consistency supports clock/geography plausibility but is not an independent clock calibration. True center altitude is not an apparent/refracted solar limb. Site is taken exactly from the report without field survey or local obscuration correction.

## Strict admissibility / limits
- This is **morning loss of visibility** during brightening twilight, **not evening first visibility**; no inverse-time symmetry is authorized. Named stars and time stamps do NOT turn two losses on one site-night into two independent P1 brackets.
- The report does **not** give dated preceding positive naked-eye checks immediately before the two star-negative readings; no quantified clock uncertainty, individual eye adaptation, calibrated directional radiance/SQM bandpass, aerosol AOD/vertical profile, or star-target cloud time series.
- Report is previously published, outcomes known; cannot be a result-blind holdout or preregistered prospective case.
- **0 P1 independent first-NOT_SEEN→first-DIRECT_SEEN cases; 0 quantitative StarsVisibility first-sighting errors.** The observed Sun depths are outside missing (10.5°,16°] and do not validate any precision anywhere. Keep that interval `UNSUPPORTED/null`, >16° v1 OOD.
- Relevant practical lesson: star-target direction and atmospheric effects matter; a global/zenith photometer reading alone is not a human observation or field-direction calibration.
- No observer contact, no new MYSTIC run/ordinal67 or held ordinal68 dispatch, no protected Taylor/Ann Arbor/Jerusalem holdout, no stage4 denied edit/indirect workaround, model modification, or expenditure.

## Required handoff
Coordinator/independent reviewer should classify this as retrospective, exploratory only, and focus on **prospective P1 blinded human per-look original logs**. Outreach owner is currently disabled and its Nov-19 observer inquiries remain Gmail DRAFT/unsent; only the pre-existing authorized outreach owner/Coordinator should resolve its user-action blocker and verify consent/site permissions, not send duplicate unsanctioned messages. Model runnable science SHA, original Hipparcos catalog bytes & digest, ephemeris source, approved site/night/HIP list, outcome-blind predictions, atmosphere input chronology, acceptance threshold and budget still need pre-registration before any results. P1's 24 independent site-night upper bound <30 exploratory numerical screen remains unchanged.

Source executable: https://github.com/search-maker/twilight-mystic-experiments/blob/b853ea4c1841ae921a6b34228f57b00977a9c554/review/source-admission/icop_sudibyo_20080928_star_last_visibility_geometry.py
