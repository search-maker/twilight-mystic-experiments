# Star-visibility model closure matrix — computational work vs empirical evidence

Status: **review-only master checklist.** This file does not change any runtime, threshold, F, tau, atmosphere, Level-B support, production routing, or validation flag.

Purpose: distinguish rigorously between (a) questions already closed computationally, (b) questions that can still be advanced from independent external data without new project observations, and (c) questions that are not identifiable without new human/open-sky evidence.

## Global governance

- Never choose `F`, `tau`, AOD, sky correction, stellar correction, adaptation field, spectral weighting, support bound, interpolation rule, or stop rule to move Jerusalem/Tishrei/Tammuz toward a desired time.
- External psychophysical data may be used to select/freeze a human/adaptation candidate **before** project-event scoring.
- Atmosphere/sky data may be used only with independently measured/retrieved provenance; do not infer atmosphere parameters from Taylor residuals and then call the same residual a validation.
- Human calibration/training data and human final holdout must remain separate.
- Production/default activation is a separate authorization after validation; a successful diagnostic does not imply deployment.

---

## 1. Solar-twilight radiative transfer / Level-B shape

### Status: COMPUTATIONALLY STRONG; REAL-SKY VALIDATION PARTIAL

Already closed/known:

- Direct-MYSTIC exact-event comparisons do **not** support one uniform claim that Level-B darkens too fast. Tishrei direct MYSTIC is darker than Level-B at all three determining directions; Tammuz has mixed spatial sign.
- Exact same-geometry matched stellar-family differences are millimagnitude scale (max absolute about 0.00625 mag in the dedicated isolation), too small to explain a broad multi-minute error by themselves.
- Taylor Ann Arbor gives one independent real-SQM consistency case for **direct MYSTIC**, not a measured-real-sky validation of Level-B.
- Taylor late-primary broadband ALIS uncertainty has been reconverged sufficiently to show that the former row25 `+0.393 mag` residual was not a stable physical discrepancy. Six-seed 200k central reanalysis gives rows23/24/25 about `+0.085/+0.174/+0.177 mag`.
- A primary-interval numerical screen shows empirical 50k single-run numerical SD is only about `0.0026–0.0110 mag` at preselected rows1–17, `0.0263 mag` at row21, then grows sharply: immutable row24/25 50k values are about `0.070/0.091 mag`. A blanket high-photon rerun of all primary rows is not justified by this screen.
- The old `mc.rad.std.spc` integrated broadband sigma is not a calibrated between-seed uncertainty estimator. Use empirical between-seed numerical uncertainty for ALIS broadband quantities.
- The legacy late-primary AOD finite-difference slopes are numerically unresolved under six 200k CRN pairs and must not be reused as resolved physical derivatives.
- The Taylor timing derivative is numerically resolved; the unchanged +/-30 s timestamp contract contributes about `0.095–0.099 mag` at rows23–25.

Atmospheric vertical-profile finding:

- Independent HRRR-Smoke mass profiles show strong low-tropospheric/near-surface loading plus elevated structure.
- Replacing only the normalized aerosol vertical **shape proxy** with HRRR, while retaining Taylor-v1 total AOD and `aerosol_default` optical properties, makes the modeled sky darker at 550 nm and in all 18/18 paired broadband CRN contrasts tested. This is a robust **directional diagnostic**, not calibrated optical physics.
- Same-cycle CAMS direct `aerosol_extinction_coefficient_532nm` is internally valid at forecast03 but unavailable at forecast00: all 137 forecast00 coefficients are zero despite nonzero column AOD. Therefore the exact same-cycle direct-extinction profile cannot close the 00–01Z Taylor atmosphere from that product without an unauthorized substitution.

What still requires evidence:

- More independent calibrated real-sky datasets spanning geometry/AOD/season are required before `measuredRealSkyValidated=true` can be claimed for the operational sky model.
- Exact aerosol vertical optical profiles at validation times would materially improve attribution but are **not required** for basic model-vs-sky validation if the actual sky radiance and column atmosphere are measured independently.

Do not do next:

- no universal sky magnitude offset;
- no residual-fitted AOD/profile;
- no blanket 800k rerun of all Taylor rows;
- no promotion of HRRR smoke mass to calibrated aerosol extinction.

---

## 2. Stellar direct transport / aerosol-family matching

### Status: COMPUTATIONALLY CLOSED FOR CURRENT QUESTION

- Matched-stellar v2 transport is validated computationally under its frozen support/method.
- Same-geometry shadow-vs-matched stellar isolation is too small to explain the multi-minute timing concern under ordinary supported geometries.
- Low-altitude/red-star cases can be larger and must remain individually reported rather than hidden in a global median.

Observation need:

- No dedicated human observation is required merely to choose between native vs matched stellar direct extinction.
- Human observations remain necessary for the total star-detection model, not for this transport subcomponent itself.

---

## 3. Achromatic human point-source threshold (Blackwell/Crumey family)

### Status: FORMULA APPLICABILITY REASONABLY SUPPORTED; HUMAN FIRST-SEEING NOT VALIDATED

Already closed/known:

- Crumey's smooth all-range point-source relation is not simply an unsupported extrapolation from deep scotopic astronomy; it is tied to all-range Blackwell point-source data.
- Tousey & Koomen provide real twilight-star observations consistent enough with the current stack to reject a claim of gross contradiction, but their rows are not an exact modern first-seeing calibration dataset.
- The small intrinsic non-monotonic interval of the smooth full threshold occurs around `B≈0.0216–0.0471 cd/m²` and has only about `0.0286 mag` amplitude; frozen Jerusalem equilibrium events are around `1–4 cd/m²`, so this cannot explain the early-Jerusalem scale.
- Current event logic should preserve genuine multiple visibility windows rather than smoothing the formula post hoc.

What remains empirical:

- Exact naked-eye **first-seeing criterion** for modern observers under real twilight.
- Observer-to-observer distribution and the meaning of the current field factor `F` for the project population/task.
- Direct versus averted vision, known-location vs search, and detection/confirmation criterion.

Governance:

- Keep `F=3.14` until independent evidence justifies another value. Lowering F to classic ~2.4 makes events earlier and therefore does not explain an already-too-early prediction.

---

## 4. Mesopic/color spectral weighting

### Status: COMPUTATIONAL SENSITIVITY CLOSED FOR FROZEN JERUSALEM EVENTS; EMPIRICAL STAR TASK VALIDATION OPEN

Already closed/known:

- Review-only CIE MES2 star-vs-sky spectral sensitivity has been run end-to-end on all 7,653 transformed rows for the frozen Jerusalem cases.
- Tishrei Three-Star event moves only about `+17.8 s`; Tammuz moves `0 s`.
- Therefore a standardized mesopic spectral reweighting is not a plausible multi-minute explanation for the two frozen events.

What remains empirical:

- CIE MES2 is not validated specifically as the weighting rule for foveal/averted naked-eye point-source first detection.
- A color-specific human experiment can test whether residual spectral-type effects remain after local sky spectrum and stellar attenuation are accounted for.

Priority:

- This is lower priority than human first-seeing/adaptation and calibrated real-sky evidence because the exact-event computational effect is already small.

---

## 5. Transient adaptation / waning twilight

### Status: CURRENT RUNTIME EXISTS BUT IS EXPERIMENTAL; STRUCTURE NOT YET PHYSIOLOGICALLY CALIBRATED

Current runtime facts:

- The application already contains a first-order log-luminance adaptation state with default `tau=30 s` and sensitivity values 20/30/45/60 s.
- It is explicitly experimental/unvalidated/non-production.
- A positive adaptation debt is intended only to worsen/equal equilibrium visibility; PR #116 separately fixes a topology artifact where the Crumey mesopic dip could otherwise produce a negative raw penalty/support discontinuity.
- Current prehistory assumes equilibrium at application sunset under continuous outdoor exposure.

Independent literature constraints now admitted:

- Spillmann, Nowlan & Bernholz (1972): threshold lag under continuously waning backgrounds depends strongly on rate and pre-exposure/history. Their 1.25-log-unit maximum occurs in a much faster/pre-exposed laboratory condition and must **not** be imported as ordinary twilight correction. They explicitly state sufficiently slow change approaches equilibrium and discuss natural twilight as much slower than their laboratory descents.
- Uchida/Ohno mesopic field experiments: adaptation at a task point is mainly **local**, with a smaller surrounding-luminance contribution; whole-field influence exists but local luminance remains dominant.
- Howard, Tregear & Werner (2000): early recovery after mesopic luminance decrements is exponential-like in log contrast threshold, but the rate depends on decrement size and spatial task. This supports an exponential state shape without supporting one universal physiological tau.

Structural runtime gap already identified:

- The project currently changes the definition of adaptation field across the twilight path: broad/hemispheric prehistory proxy in one regime versus target-direction luminance later. This is not a defensible single physiological variable.
- Detection background and adaptation field must remain separate: detection background is local around the target; adaptation state should be local-dominant with an angularly weighted surround/history term.

What can still be completed **without project observations**:

1. obtain reproducible source images/data for the admitted dynamic-adaptation figures;
2. digitize with explicit axis/pixel calibration and digitization uncertainty;
3. preregister a small family of external-data-only history/adaptation models;
4. fit/select parameters on the external psychophysical data only;
5. freeze the selected candidate before running any project-event sensitivity.

Current blocker:

- The article text/captions/methods are accessible, but exact figure pixels are presently inaccessible through the available public paths: Optica figure assets require subscription; UNL direct PDF fetch returns 403; ResearchGate exposes figure pages/asset URLs but the image bytes are not retrievable through the current research environment. **No digitized coordinates may be invented from OCR/text preview.**

What still requires project/open-sky observations even after an external fit:

- effective angular adaptation kernel during real star search;
- actual gaze trajectory and pre-exposure behavior;
- direct vs averted vision interaction;
- spectral × transient interaction for point-source detection;
- observer variability;
- mapping from laboratory contrast-threshold history to star first-seeing.

---

## 6. F / observer criterion

### Status: SENSITIVITY CLOSED; EMPIRICAL CALIBRATION OPEN

- F changes limiting magnitude uniformly for a common background definition; lowering F from 3.14 to 2.4 shifts the threshold by about +0.292 mag and makes frozen events earlier by roughly 1.7–2.1 min, not later.
- Therefore F is not a legitimate knob to repair the current early-timing concern.

Observation requirement:

- If the project wants an observer-population F rather than a chosen conservative criterion, it must be estimated from blinded repeated human trials after sky/atmosphere prediction is frozen.
- Estimate observer random effects/distribution; do not fit one F on the same final holdout used to claim accuracy.

---

## 7. Late twilight / total sky (> roughly solar-only validated regime)

### Status: ARCHITECTURAL FOUNDATION EXISTS; EMPIRICAL/PROVIDER VALIDATION OPEN

- Solar twilight alone is not a complete physical sky once lunar scattered light, airglow, zodiacal light, integrated starlight and artificial skyglow become material.
- The application has fail-closed total-sky composition foundations, but individual background components require their own source admission/validation.

Observation requirement:

- Treat this as a separate S2 campaign from early twilight star first-seeing.
- Do not use late rows to validate a solar-only model while silently absorbing moon/natural/artificial light into an offset.

---

## 8. What is now *not* worth further untargeted computation

Absent new independent evidence, do not spend effort on:

- lowering F;
- arbitrary tau sweeps beyond declared sensitivity;
- smoothing Crumey to eliminate its tiny topology feature;
- universal Level-B sky offsets;
- repeated matched-stellar rewrites;
- blanket Taylor all-row high-photon reruns;
- choosing aerosol vertical profiles from which one best matches Taylor;
- converting HRRR smoke mass into exact extinction/SSA/phase without a frozen external optical mapping;
- production activation of mesopic/transient layers.

---

## 9. Remaining empirical work, in priority order

1. **H1 + S1 combined human first-seeing / calibrated early-sky campaign** — highest value because it directly validates the complete quantity the application predicts.
2. **A1 adaptation subexperiment** — randomized pre-exposure/search-field conditions, ideally embedded in H1 but analyzed separately.
3. **Independent real-sky replication across multiple nights/sites/atmospheres** — supports model generalization and separates one-night Taylor coincidence from robust sky validation.
4. **C1 color/mesopic matched-star experiment** — useful if residual spectral-type effects remain; lower priority because MES2 exact-event sensitivity is already small.
5. **S2 late/total-sky campaign** — separate from solar-only early-twilight validation.

The exact field protocol and mandatory data are defined in `FIELD_CHECKLIST.md` in this review package.
