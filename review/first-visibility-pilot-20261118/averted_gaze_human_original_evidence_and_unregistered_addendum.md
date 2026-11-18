# 2026-11-18 — Original controlled human star-detection evidence; first-visibility gaze-method preregistration amendment (PROPOSAL ONLY)

**Science classification:** VERIFIED PRIMARY PUBLISHED PSYCHOPHYSICS; NOT an outdoor twilight first-sighting record, NOT actual star detection, NOT an empirical timing validation, NOT a registered/enrolled field study.

## Original evidence and provenance

- Alexander, R. G., Mintz, R. J., Custodio, P. J., Macknik, S. L., Vaziri, A., Venkatakrishnan, A., Gindina, S., and Martinez-Conde, S. (2021), *Gaze mechanisms enabling the detection of faint stars in the night sky*, European Journal of Neuroscience **54**(4):5357–5367, DOI https://doi.org/10.1111/ejn.15335 .
- Public full original research report and methods: https://pmc.ncbi.nlm.nih.gov/articles/PMC8389526/ (PMCID PMC8389526; PMID 34160864).
- Original paper's data-sharing statement names https://doi.org/10.6084/m9.figshare.14668722 ; **the actual individual-level data files and their byte hashes were NOT retrieved or verified in this pass**. Thus do not infer individual trial measurements from a DOI, or call this a raw-data replication.
- Experiment 1: **12 included participants**, human yes/no detection of a monitor-simulated star of apparent magnitude **3.3**, with 20-minute complete-dark adaptation, eye position recorded at **500 Hz**.
- Experiment 2: **14 included participants**, simulated apparent magnitude **3.5**, 20-minute dark adaptation, eye tracker, distinct range of tested eccentricities. **Do not add 12+14 as if 26 independent people**: participant overlap is not established here.
- Published finding: peak accuracy is first reached at about **8°** of gaze eccentricity, with a high-performance range **8°–14°**; performance generally declines beyond ~15° and the farthest (~30°) conditions approached chance. The **20°–25°** rod-density maximum alone is NOT an empirically verified optimum for seeing a faint star.
- This study used **indoor simulated light sources, not actual stars seen outdoors at sunset**. It reports **human detection** under controlled conditions, but does NOT report a physical star identity, site/time, solar depression, azimuth/altitude, cloud, aerosol, moon, skyglow, or human **first after-sunset** timing. It is therefore **INELIGIBLE** as a first-visibility model test or 10.5°–16° timing validation.

## New material observation-protocol confound identified

The pre-existing unregistered field V0 at
https://github.com/search-maker/twilight-mystic-experiments/blob/science/first-visibility-blank-field-schema-20261109/review/first-visibility-pilot-20261109/PREREGISTRATION_PREPARATION.md
separates direct and averted gaze with a `mode` enum but does **not** specify the approximate magnitude of gaze eccentricity or explicitly define whether first-sighting brackets may cross method changes. Because visual detection depends materially on gaze technique, a late transition from foveal to averted viewing can change the observed first-YES even at unchanged solar geometry and atmosphere. This is a methodological confound, **not a quantified shift in minutes**.

**Bounded proposed amendment before study registration / predictions / observations; not automatically applied to V0:**

1. Coordinator must choose, publish and freeze ONE `gaze_policy` for the principal first-visibility estimand **before** participants are enrolled and model predictions are revealed: e.g. `NATURAL_UNAIDED_GAZE` (free eye movements but method recorded at every check) or a standardized explicit protocol. Do **not** retroactively select the favorable definition after seeing first-YES times.
2. In the private original `CHECK` event, add self-reported `gaze_actual` = `direct | averted | mixed | unknown`, `gaze_offset_band` = `0-5 | 5-15 | over15 | unknown` degrees **only if reasonably self-estimable**, and `gaze_reliability` = `self_report | externally_observed | unknown`. Do not describe self-estimated offset as eye-tracker-calibrated.
3. In `SESSION` and changes of `CONDITION`, document prior bright-screen exposure and elapsed adaptation time; **20 minutes in a laboratory dark room must not be presumed achievable or required at sunset**. At a minimum retain `UNKNOWN` and do not silently label a novice dark-adapted.
4. Continue all scheduled `NOT_SEEN`, `POSSIBLE`, `CONFIRMED`, `OBSCURED` and missed reports for each fixed target; confirmation must be within the previously registered window, and first YES must not be backdated. For **method-specific** analysis, method change between last-NO/first-YES causes censoring or an explicitly predeclared separate analysis. For the **natural-any-method** estimand, retain the event but report method change as a covariate/confound.
5. Predeclare reporting by direct vs averted/mixed/unknown, experience and recorded screen/adaptation history. The result-blinded observer must never see predicted timing, solar-depression cutoffs, or performance feedback during checks. The paper's 8–14° lab result must not be promoted to a universal outdoor twilight optimum.
6. Retain existing pre-registration requirements: two lawful consenting sites, two independently logging adults/site, preselected HIP targets and catalog bytes/hashes, fixed prediction model exact runnable 40-hex SHA/config, encrypted pre-event predictions and metric hashes, observer/prediction separation, capped 12 evenings/30 days, original timestamps/log hashes, independent AOD or UNKNOWN, Taylor/Jerusalem holdouts untouched. This source does not waive any gate.

## Current decision / bounded handoff

- **Scientific timing validation:** `NO_NEW_FIRST_SIGHTING_RESULTS`; sample of authenticated prospective `last_NOT_SEEN→first_CONFIRMED` intervals is still **0 verified** at this review; no new consent found in the targeted outreach mailbox search after 2026-11-08.
- **New evidence state:** `LAB_HUMAN_DETECTION_METHOD_VERIFIED`; original article has genuine human yes/no trials (not an SQM/SG_088 instrument proxy), but original per-trial data remain unverified.
- **Suggested Coordinator action, not performed:** review this short gaze-method addendum and seal an approved version of the field instructions/event schema **before** actual study registration. Existing Outreach Replies owner can confirm willingness and privacy/consent by the historically authorized contact threads; no duplicate personal requests, payments or false enrollment. If not enough volunteers, leave scientific output `UNSUPPORTED`.
- No MYSTIC dispatch; ordinal67 remains spent; ordinal68 remains **NEVER DISPATCH**. No scientific fitting or holdout opening; no changes to production or the original V0 protocol.
- The conditional 2°–10.5° evidence **does not** establish minute-level accuracy. First-visibility timing at 10.5°–16° is **UNSUPPORTED/null**, and >16° is out-of-domain.

**Status:** ORIGINAL PUBLICATION SOURCE VERIFIED / SUPPLEMENTARY RAW FILES NOT VERIFIED / FIELD AMENDMENT DRAFT ONLY / NOT A NEW TIMING RESULT.
