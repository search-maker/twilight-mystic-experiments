# OPEN diagnostic: Rumen Kolev 2013, first-hand Sirius heliacal-phase entries (11)

**Custody/decision as of 2026-11-22 EST:** a newly identified *author-posted* original observational narrative and printed table transcription, **NOT** a blind first-evening-star-onset validation dataset. No Taylor/Ann Arbor/Jerusalem protected inputs read; no model fit, forecast, solver run, new field observation or consent.

## Primary document and identity

Rumen Kolev, *The Babylonian Astrolabe: The Calendar of Creation* (2013), SAAS vol. XXII, Appendix F “Heliacal Practice,” pp. 237–246, author-posted excerpt [“11 Sirius Heliacal Phases Observations”](https://www.academia.edu/181494239/11_Sirius_Heliacal_Phases_Observations_Excerpt_pp_237_246_from_the_book_The_Babylonian_Astrolabe) and duplicate [“ELEVEN OBSERVATION of HELIACAL PHASES of SIRIUS”](https://www.academia.edu/180354906/ELEVEN_OBSERVATION_of_HELIACAL_PHASES_of_SIRIUS). HTML transcription publicly accessible. **Original 2013 printed-page pixels, raw 1998–2012 observer logbooks, original clock/UTC, original camera/optical instrument files and hashes NOT verified.** The author describes his own observations, some separately attributed to others, in Seattle and Bulgaria. This is observer testimony, not a calibrated photometer dataset.

Source defines `First` as a pair **sun altitude / Sirius altitude in degrees** at the first sighting of the given astronomical phase, NOT a clock time and NOT a same-star earlier NOT_SEEN -> first_DIRECT_SEEN transition. The 2013 author says 270 collected, 255 selected historical phase observations (48 planets/207 stars), and constructs an algorithm from those data: these are **training/exposed observations for the author's theory**, not independent holdouts.

## Finite transcription of the displayed Sirius “First” pairs

The below **11 individual author-printed first-phase entries** are transcribed as reported; `mag=-1.5` is the source's fixed Sirius magnitude. Other columns (Best/Last, Min/dAZ/Stand) are not transcribed and are NOT inferred. Site codes `Bl` and `Brg` are retained verbatim. Phase codes retained verbatim; source distinguishes Morning First (MF), Evening Last (EL) and Acronychal Rise (AR). `first_sun_alt_deg` is negative when Sun below horizon. Atmospheric `source_extinction_mag_per_airmass` is an author's observational extinction estimate; **not an independently measured aerosol/AOD profile**.

| id | date | site | phase | source extinction mag/airmass | first Sun alt (deg) | first Sirius alt (deg) |
|---|---|---|---|---:|---:|---:|
| 1 | 2003-08-18 | QA | MF0 | 0.16 | -6.0 | 1.4 |
| 2 | 2003-08-19 | QA | MF1 | 0.16 | -7.2 | 0.9 |
| 3 | 2005-08-19 | QA | MF1 | 0.20 | -7.0 | 1.5 |
| 4 | 2000-05-10 | VM | EL1 | 0.42 | -4.8 | 7.7 |
| 5 | 2000-08-17 | VT | MF1 | 0.36 | -8.2 | 2.7 |
| 6 | 2006-08-19 | VM | MF1 | 0.42 | -9.8 | 2.3 |
| 7 | 2004-08-16 | RL | MF1 | 0.36 | -6.2 | 4.7 |
| 8 | 2000-01-28 | VC | AR1 | 0.36 | -5.8 | 2.2 |
| 9 | 2009-08-18 | VC | MF1 | 0.36 | -9.2 | 2.3 |
| 10 | 2011-05-13 | Bl | EL1 | 0.32 | -4.8 | 6.0 |
| 11 | 2011-08-17 | Brg | MF1 | 0.32 | -8.2 | 2.9 |

**Independently counted directly from these 11 exposed source rows, not a prediction/model comparison:** 8 Morning First (1 MF0, 7 MF1), 2 Evening Last (EL1), 1 Acronychal Rise (AR1); 7 different site codes; 5 printed extinction levels (0.16, 0.20, 0.32, 0.36, 0.42); printed Sun depression from **4.8° to 9.8°**, star altitude **0.9° to 7.7°**; **zero entries** in the missing 10.5°–16° range, **zero entries** with target altitude >=20° required by P1, **zero** documented prior NONSEEN for the same star, and **zero** printed verified first-visibility clock instants. Source attributes some entries to other observers; those are not independent *site-night* clusters without further raw provenance.

**User-relevant observational variance, only as anecdote:** The author recounts co-observation groups of 4–7 people, with some seeing objects **2–8 min before** the author, and an observer occasionally seeing an object none of the others could. No paired raw time-stamped dataset or error bars are shown; do NOT turn 2–8 minutes into a model error, a general population range, or a formal uncertainty distribution. It is a prospective reason to record separate observer IDs, independent looks and adaptation/screen exposure.

## Strict source-admission decision

- **PASS**: historical human observational phase table with individual Sirius identification, source visual magnitude, author-provided Sun/star altitudes, date, site code, and estimated extinction context. Exact excerpt source link and an auditable 11-row limited transcription are preserved.
- **FAIL** for REAL FIRST EVENING NAKED-EYE onset: MF phase is morning heliacal first and EL phase is evening **last**, not the first star seen as the sunset sky darkens. No bracketed earlier same-star true NOT_SEEN; no reliable per-event UTC timestamp, fixed cadence or standardized visual adaptation; **no P1-qualified target altitude**.
- **FAIL** as independent measured atmosphere: estimated extinction partly obtained from human night-rise/star limiting-magnitude observations, not independently measured at the listed event with optical aerosol profile. If computed from observed brightness/appearance it must NOT be reused as if prospective independent ex-ante physical input (outcome leakage).
- **FAIL** for blind model error/late domain: historical exposed source, author's internal algorithm training, zero 10.5°–16° entries, no locked qualified StarsVisibility scientific model SHA or sealed forecast, no simultaneous directional radiance/skyglow, no original photometric data. **Empirical residual, MAE, bias, coverage: NOT COMPUTABLE; first-star-onset qualified brackets: 0.**
- **Usable only** as qualitative/contextual open diagnostic, design caution for independent observer pairing and transparency. Do NOT silently count 11 as 11 test cases, generalize observational minutes, retune a model to these open values, use as a protected holdout, or imply success in deep twilight.

## Operational handoff

On 2026-11-22 the project's already-authorized `Twilight Outreach Replies` automation was freshly inspected: **disabled**, last completed run 2026-11-22T16:13:41Z marked `requires_user_action=true`, without a supplied reason. Gmail fresh search found two existing research requests to Halifax RASC secretary and M. Nickiforov still carrying `DRAFT` labels on 2026-11-22, and no new written individual P1 participant consent in the specifically searched post-2026-11-18 research mail results. Those drafts are NOT sent and are not proof of consent. This note performs **NO new observer contact or dispatch**. Coordinator/authorized outreach owner needs to inspect the permission/action gate, avoid duplicate solicitations, obtain original optical/time metadata and explicit consent+weekday site approval. Pre-outcome P1 template already exists at blob `be0f827e680c029aeee349cc203c16290f53d32f`; it remains review-only with `qualified_runnable_first_visibility_model_commit_sha=null`, zero consent, zero original events, `P1_START_AUTHORIZED=false`. Only a qualified frozen executable model + source hashes + independent reviewer/Coordinator signatures + privately sealed forecasts (or separately prespecified outcome-blind hindcast) can precede actual trial results. No new MYSTIC ordinal permitted without issue #60 prerequisites; ordinal67 spent, ordinal68 frozen.
