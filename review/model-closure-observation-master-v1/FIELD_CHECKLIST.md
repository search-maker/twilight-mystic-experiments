# Exact field-observation checklist for star-visibility model validation

Status: **review-only acquisition contract.** This checklist defines what must be measured before observations may be used for model calibration/validation. It does not set model parameters or authorize a final holdout.

## A. Core rule: one observation must link four independent things

Every calibration-grade star-seeing record must make it possible to reconstruct, independently:

1. **what the sky/atmosphere was doing**;
2. **what exact star geometry and predicted signal were present**;
3. **what the observer had been exposed to / where they were looking**;
4. **when and under what criterion the star was first suspected and confirmed**.

If one of these four blocks is missing, the record may remain descriptive but must not silently be upgraded to a validation row.

---

# H1 — Human first-seeing campaign

## H1.1 Mandatory session identity

Record once per session:

- session UUID;
- observer pseudonymous ID;
- date and timezone;
- latitude, longitude, observer elevation, source and uncertainty;
- site/horizon description and any obstruction map;
- optical aid: must be `none` for naked-eye validation;
- corrective lenses/contact lenses and whether worn;
- observer's prior familiarity with the target/star field;
- weather notes independent of the model result.

Do not store identifying personal information unnecessary for the science.

## H1.2 Time integrity

Required:

- device clock synchronized to a traceable time source before session;
- target clock error goal **<=1 s**;
- record measured synchronization offset/uncertainty, not merely “automatic time enabled”;
- event capture must be hands-free or low-distraction, preferably timestamped audio/button capture;
- retain raw event timestamp and any later corrected timestamp separately; never overwrite raw time.

Visual search cadence:

- structured check opportunity **at least every 10 s** in the critical interval;
- do not infer exact first-seeing from a 1–2 minute cadence;
- continue observation for at least **60 s after first SEEN/CONFIRMED** so stability/re-loss is recorded.

## H1.3 Blinding / target cueing

For a first-seeing validation trial:

- observer must not see model-predicted first-visible time during the trial;
- do not display a countdown to prediction;
- do not reveal the model's limiting magnitude/margin;
- predefine target identity and search region before the critical interval;
- record whether star position was `exactly_known`, `small_search_region`, or `blind_field_search`;
- if another person cues the observer, record cue timing/type; cued trials must be stratified separately.

## H1.4 Observation-state vocabulary

Every check should support at least:

- `NOT_SEEN` — actively checked, no detection;
- `SUSPECTED` — possible target but not confidently identified;
- `CONFIRMED` — target confidently identified under the predefined rule;
- `LOST` — previously seen but no longer detected;
- `NOT_CHECKED` — no valid check at this time.

Never encode absence of an event as `NOT_SEEN`; explicit non-detections are required.

For each event record:

- raw timestamp;
- event state;
- target ID;
- viewing mode (`direct`, `averted`, `mixed`);
- current search mode/location certainty;
- optional spoken confidence on a frozen ordinal scale;
- reason for invalidation if trial interrupted.

## H1.5 Confirmation criterion must be frozen before holdout

Examples of admissible rules:

- `CONFIRMED` requires target indicated correctly on a blind star-field map after detection;
- or repeated detection in N of M checks within a frozen window;
- or a preregistered forced-choice identification rule.

The project may compare more than one criterion during calibration, but the criterion used for final validation must be fixed before opening the final holdout.

## H1.6 Search / gaze metadata

At minimum record:

- `viewingMode`: direct / averted / mixed;
- `targetLocationKnowledge`: exact / bounded / field-search;
- `searchRadiusDeg` or equivalent bounded region if known;
- `searchDurationSec` before each detection state when practical;
- `locationUncertaintyDeg` if the observer is using a memorized/indicated position;
- `searchEase` on a frozen ordinal scale if retained as a diagnostic.

Do not mix a known-location stare task with an unguided sky search and call both one threshold population.

---

# S1 — Early-twilight sky / atmosphere campaign

S1 is required alongside H1 if the purpose is to validate the **model**, rather than only human repeatability.

## S1.1 Directional sky measurement

For every target trial in the critical period, obtain calibrated sky brightness near the target direction.

Preferred:

- calibrated imaging photometer/spectroradiometer with the target direction identifiable;

Acceptable minimum:

- calibrated SQM/SQM-L directional measurements if instrument FOV/operator is recorded accurately and the model forward operator can reproduce it.

Record:

- instrument make/model/serial or stable instrument ID;
- detector/FOV response description;
- calibration source/date/version;
- timestamp;
- pointing altitude/azimuth and pointing uncertainty;
- raw measurement and units;
- any temperature correction or preprocessing, versioned and reversible.

Do not silently equate a zenith SQM reading with the local background behind a low-altitude target.

## S1.2 All-sky adaptation context

For adaptation analysis obtain full-sky or wide-field calibrated context at **<=30 s cadence** through the critical interval when feasible.

Minimum useful product:

- calibrated luminance/radiance map with timestamp and sky coordinates;
- enough field coverage to reconstruct local target-centered annuli plus wider surround;
- raw or losslessly preserved source frames and calibration metadata.

This is specifically needed because the adaptation field is not justified as either one target ray or one hemisphere-wide scalar.

## S1.3 Spectral sky information

Strongly preferred for A1/C1:

- spectral radiance or calibrated multi-band sky data near target and surrounding field;
- enough wavelength information to derive photopic/scotopic and candidate mesopic quantities independently.

If only broadband SQM is available, mark spectral adaptation/color conclusions as unsupported rather than inferring them from the star color alone.

## S1.4 Atmosphere

Mandatory minimum:

- independent AOD estimate with timestamp/provenance and uncertainty;
- surface pressure;
- temperature;
- relative humidity;
- visibility/haze/cloud notes;
- cloud fraction/type if any;
- wind optional but useful for changing smoke/aerosol conditions.

Preferred:

- AERONET or calibrated sun/sky photometer when available;
- independent aerosol profile/lidar/ceilometer or validated model profile if available;
- aerosol type indicators from independent measurement/product.

Fail-closed rule:

- if atmosphere is outside the model's validated support, classify the row OOD rather than clipping it into support.

## S1.5 Geometry reconstruction

Store enough information to recompute rather than merely copy:

- UTC timestamp;
- site coordinates/elevation;
- target catalog identity;
- apparent/topocentric star altitude/azimuth convention;
- unrefracted geometric topocentric solar-center altitude for direct-MYSTIC comparison;
- if an instrument/notebook gives apparent/refracted Sun altitude, store it under a separate named field.

Never silently compare an apparent/refracted H value with geometric solar depression.

---

# A1 — Adaptation-specific experiment

A1 is not simply “record the same star many times.” It must manipulate or measure adaptation history independently enough to identify the transient component.

## A1.1 Conditions to randomize/compare

At minimum design matched trials around one or more of:

- `natural_continuous_twilight` — ordinary outdoor exposure;
- `controlled_brighter_preexposure` — frozen luminance/duration before the search interval;
- `controlled_dimmer_preexposure` or shielded exposure;
- `target_local_field` versus a broader brighter/darker surrounding-field condition when practical and safe;
- direct vs averted viewing as separate conditions.

Order should be randomized/counterbalanced where feasible. Do not let the model prediction choose which condition occurs on a given trial.

## A1.2 Pre-exposure log

From at least **30 min before expected first-seeing** through the event, record all meaningful exposure changes:

- outdoor sky exposure start/end;
- indoor/artificial light exposure;
- phone/screen/flashlight exposure;
- luminance/intensity if controlled;
- spectral character if controlled;
- duration;
- whether the observer closed/covered eyes;
- gaze direction/field if controlled.

An unrecorded bright screen exposure can invalidate a transient-adaptation inference even if the star timestamp itself is perfect.

## A1.3 Pupil/gaze requirement for physical bleach-state claims

If the analysis intends to map pre-exposure physically into retinal illuminance/bleach state, record or constrain:

- pupil diameter or validated proxy;
- gaze direction over the relevant exposure interval;
- field luminance/spectrum seen by the eye.

Without those, the condition may still support **empirical condition-specific adaptation calibration**, but not a precise physiological bleach-state reconstruction.

## A1.4 Adaptation-field estimation

From all-sky/wide-field data compute candidate fields only after the spatial model family is preregistered, for example:

- target-local disk/annulus summaries;
- several fixed angular radii;
- local + angularly decaying surround families.

Do not select the radius/kernel that best moves the final star event. Select/calibrate it on separate adaptation calibration data, then freeze it before H1 holdout scoring.

## A1.5 Temporal model fitting

External psychophysics should constrain candidate temporal/history models first.

Project A1 calibration may then estimate any remaining open-sky mapping parameters, but:

- `tau` or equivalent history parameter cannot be fit on final holdout;
- one universal tau must not be assumed unless data support it;
- rate, luminance level, pre-exposure and observer dependence should be tested explicitly.

---

# C1 — Color / mesopic star experiment

Only necessary if the project wants empirical validation of spectral weighting beyond the already-small MES2 event sensitivity.

Design:

- choose stars/conditions that produce contrast in spectral type while approximately matching catalog/apparent magnitude, altitude, sky direction and timing as closely as practical;
- record actual stellar SED/template identity and wavelength-resolved atmospheric attenuation used by the model;
- measure local sky spectrum/multi-band radiance;
- separate direct/averted viewing;
- blind observer to predicted color correction.

Primary question:

- after controlling local photometric background and geometric/atmospheric variables, is there a repeatable residual by star SED/color consistent with or inconsistent with the candidate mesopic weighting?

Do not use C1 to refit the achromatic threshold curve simultaneously.

---

# S2 — Late twilight / total-sky campaign

Run separately when Sun depression enters the regime where non-solar backgrounds become material.

Record/model independently:

- Moon altitude/azimuth/phase/separation and lunar-scattered-light inputs;
- natural night components (airglow, zodiacal/integrated starlight as model requires);
- artificial skyglow / site light pollution;
- clouds, especially because artificial light-cloud coupling can dominate;
- calibrated all-sky radiance.

Do not call a solar-only residual a twilight-model error if these components are omitted.

---

# Instrument/calibration minimums

A calibration-grade session must retain:

- immutable raw measurement files;
- calibration files/version;
- processing software/version/hash;
- instrument clock offset;
- pointing calibration;
- units and zero-point definitions;
- saturation/valid-range flags;
- dark/flat/temperature corrections where applicable;
- chain of provenance from raw data to analysis row.

SQM-specific:

- distinguish original wide-angle SQM from SQM-L;
- record instrument orientation and exact model/operator used to compare with it;
- do not apply an SQM-L angular response to an original SQM dataset.

---

# Pilot, calibration, and holdout split

## Pilot

Purpose:

- prove field procedure works;
- estimate missingness and observer repeatability;
- identify practical cadence, target-selection and instrumentation failures.

Pilot data may change the protocol. Therefore pilot data are **not** final validation holdout.

## Calibration/training set

May be used to:

- choose/freeze human confirmation criterion;
- estimate observer effects/F if desired;
- choose/freeze adaptation kernel/model among preregistered candidates;
- estimate nuisance terms and QC thresholds.

Every change made after reading calibration results must be versioned.

## Final holdout

Before opening holdout, freeze:

- software/model commit hashes;
- F or observer criterion policy;
- transient model/parameters or decision to omit it;
- mesopic policy;
- sky/stellar providers and support bounds;
- atmosphere source-resolution rules;
- event definition and stability interval;
- inclusion/exclusion/QC rules;
- uncertainty model;
- primary metrics and acceptance/reporting rules.

Do not reuse a holdout after model-changing inspection.

---

# Minimum analysis outputs

For every usable target/trial report:

- predicted equilibrium first-seeing time/depression;
- predicted transient first-seeing if that model was frozen;
- observed first `SUSPECTED` and first `CONFIRMED` times;
- explicit preceding non-detection interval;
- star apparent/catalog magnitude and modeled attenuated signal;
- local detection background measurement/model value;
- adaptation-field measurement/candidate value if applicable;
- AOD/atmosphere provenance;
- timing uncertainty;
- sky/instrument uncertainty;
- observer/session ID as random-effect grouping variable;
- support/OOD status;
- residual in seconds/degrees/magnitude-equivalent form without tuning parameters on the same row.

Across the dataset report:

- bias and uncertainty interval;
- RMS/MAE;
- calibration/coverage of predicted uncertainty;
- residual vs solar depression, target altitude/azimuth, magnitude, spectral type, AOD, observer and pre-exposure condition;
- false early predictions and false late predictions separately;
- non-detections/censoring explicitly, not dropped;
- observer random-effects / between-observer spread;
- calibration results and untouched holdout results separately.

---

# Stop rules

The project should **not** claim complete empirical validation until there are independent data for both:

1. calibrated sky/atmosphere behavior in the relevant twilight domain; and
2. human first-seeing under a frozen task/criterion.

Conversely, do not delay useful conclusions unnecessarily:

- mesopic sensitivity for the two frozen Jerusalem events is already computationally small;
- matched stellar transport is already too small to be the broad multi-minute explanation;
- Taylor's old late-primary large residual/AOD sensitivity has been numerically weakened/reclassified;
- further progress on transient physiology is legitimately blocked at external-curve fitting by current figure-image access, then by A1/H1 empirical identification.

Those items should remain explicitly separated rather than being combined into one adjustable correction.
