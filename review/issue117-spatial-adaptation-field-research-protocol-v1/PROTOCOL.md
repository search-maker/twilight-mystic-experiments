# Issue #117 spatial adaptation-field research protocol v1

Status: **REVIEW ONLY / NO IMPLEMENTATION / NO SEMANTIC CHANGE**

This protocol is frozen after the current same-field mathematical work but before any implementation of a separate broad adaptation field. It exists because the surviving transient mappings cannot be scientifically distinguished under current Level-B mechanics, which populate adaptation-field luminance and local detection-background luminance from the same photopic sky sample.

## Bound project state

- `starsvisibility` baseline: `e0da52eb0a2d5bac333da6572f51df52ea7e676e`
- Issue #117 real-trajectory evidence: twilight PR #577
- mapping-candidate preregistration: twilight PR #578, head `23f96613d553610f9e75ddd4c8c08d0240c354c6`
- Candidates 0–3 math gate: twilight PR #580
- Candidate 4 Crawford/generalized-inverse protocol: twilight PR #581
- Candidate 4 math gate: twilight PR #582, successful head `41dbb5202a5a10ccfffa64453b931c8da8037d4a`
- F remains `3.14`
- transient state dynamics/tau remain experimental sensitivity machinery; no calibration is authorized here

## Why this lane is necessary

Current Level-B history rows use the same instantaneous photopic Level-B sky luminance for both:

- broad/adaptation-field input `B_a`; and
- local detection background `B_d`.

Under `B_a = B_d`, the mathematically surviving Candidate 2 path-envelope, Candidate 3 threshold-ratio, and Candidate 4 threshold-derived equivalent-background construction collapse to the same required threshold (Candidate 4 was verified against Candidate 2 on 6,561 same-field probes in PR #582).

Therefore another same-field twilight event run cannot discriminate the surviving semantic structures. The next scientifically meaningful question is how the visual system's adaptation state should sample the *spatial luminance distribution* around a point-source detection task.

## Independent external evidence frozen before implementation

The following evidence constrains the research direction but does **not** by itself establish an astronomy-specific adaptation-field formula:

1. **Uchida & Ohno 2013/2014, local-vs-global peripheral-adaptation experiment, DOI `10.1177/1477153513498084`.** The full NIST-hosted paper resolves the previously ambiguous `10°` wording. The fixation point was at screen centre; the target was a **1°-diameter dark spot at 10° retinal eccentricity from fixation**. The local adaptation pattern was **not a 10°-radius field**: for the circular conditions it was a circle **centred on the target with radius 12.4° of visual angle**, chosen so its area was 20% of the whole screen. Comparing this local circle with a uniform whole-screen pattern favoured the local-adaptation hypothesis. Thus `10°` is the target eccentricity in this experiment, while `12.4°` is the explicitly stated local-circle radius. These two angles must not be conflated.
2. **Stokkermans, Vogels & Heynderickx 2016, Journal of Vision, DOI `10.1167/16.8.11`.** With nonuniform backgrounds and controlled veiling luminance, bright regions nearer the viewing direction produced longer dark-adaptation times than equally veiling bright regions at larger visual angles. Thus spatial location/local luminance matters beyond a single global scalar.
3. **Uchida/Ohno surrounding-source studies, DOI `10.1177/1477153514558963` and `10.1177/1477153516638555`.** The peripheral task used a 1° target; point-source separation from the task point was experimentally varied. In the later wide-angle experiment the tested source/task separations were 5°, 7°, 10°, 15°, 20°, 25°, 30° and 40°. The 5° result was explicitly excluded when fitting the new angular model because its inferred adaptation state lay outside the empirically verified log-threshold/adaptation-luminance range. The paper also states that the lower angular applicability limit is unclear, that the angular characteristic was measured in one source direction, and that another task-point/source direction may differ. Therefore this kernel must not be extrapolated toward zero angle or assumed isotropic without a declared shadow approximation.
4. **Peripheral surrounding-luminance formula used by Uchida et al. 2016, DOI `10.1177/1477153515626210`.** Their simulation writes the Stiles–Crawford peripheral model as `L_veil = (16 / theta_d^2) E_n`, with `theta_d` in degrees and `E_n` the source normal illuminance at the eye. It also gives the Uchida–Ohno steeper empirical model as `L_veil = (260 / theta_d^3) E_v`, where `E_v` is vertical illuminance from the surrounding source. The same simulation generalizes these as `L_veil = (k / theta_d^n) E` and derives a retinal-coordinate surround kernel for integrating a luminance distribution. These are independently sourced candidate kernels; neither is automatically valid for a smooth natural-twilight sky or astronomical fixation.
5. **Uchida et al. 2016 spatial simulation.** Their mesopic adaptation-luminance simulation treats luminance distribution, eye movement, surrounding-luminance effect and area of measurement as separate factors. The surrounding effect is first applied as a spatial kernel/convolution to form an effective luminance distribution, after which eye-movement probability and task/measurement area are combined. In their outdoor-lighting simulations, simple area-average luminance often approximated the more complete model, with important exceptions where bright sources surround the task area.
6. **Driving eye-tracking evidence (Cengiz et al. 2014).** Circular fields of view of 1°, 5°, 10°, 15° and 20°, centred at the mode of gaze distributions, were evaluated as possible adaptation fields. These are a separate road-driving measurement family and must not be mistaken for the 12.4°-radius local circle in the Uchida–Ohno detection experiment.
7. **CIE 257:2026.** The current CIE report explicitly defines the adaptation field recommended for practical CIE mesopic photometry and states that its basic recommendations are unchanged from the earlier interim recommendation. Public preview/abstract text is insufficient to recover the normative field definition itself. The full report must be read before this project claims to implement “the CIE 257 adaptation field”.

Applicability boundary: these studies mainly concern mesopic peripheral outdoor-lighting tasks, not astronomical known-position stellar detection under continuously waning natural twilight. They are independent priors/constraints, not direct validation of a star-visibility adaptation field.

## Preregistered research questions

Before implementation, answer in this order:

1. **Retinal task geometry.** For a known star detected with direct or averted vision, where is the adaptation field centered: fixation direction, target retinal location, or a combination that changes with eye movements?
2. **Local field scale.** The strongest directly resolved local-field anchor is the Uchida–Ohno **12.4° radius circle centred on a target located 10° from fixation**. Is this geometry a defensible first astronomy shadow sensitivity condition, or does low-background rod spatial integration/averted stellar vision require a materially different scale? Do not relabel the experiment as a generic “10° adaptation field”.
3. **Spatial weighting.** Is a uniform local average adequate for a smooth natural-twilight sky, or must an angle-dependent surrounding-luminance kernel be included? If a kernel is tested, separately freeze the `16/theta^2` Stiles–Crawford and `260/theta^3` Uchida–Ohno forms, their illuminance conventions, angular domain/cutoff and any isotropy approximation. Do not fit those choices to star-visibility outcomes.
4. **Eye movements.** What gaze/averted-vision behaviour is appropriate for first detection of a known star, and over what temporal window should spatial samples contribute to the adaptation state?
5. **Spectrum.** Should the adaptation-field state use photopic luminance alone, scotopic/mesopic spectral weighting, or separate rod/cone state variables in the late-photopic/mesopic region relevant to 2–10.5° solar depression?
6. **Field-vs-detection separation.** Once `B_a` is spatially defined, local `B_d` must remain the physical sky background at the target detection location; adaptation processing must not overwrite MYSTIC/Level-B physical sky radiance.

## Candidate spatial-field families frozen for research, not selection

These are not yet executable mappings and may not be ranked by Taylor/Jerusalem residuals.

### Spatial Field A — current local-point baseline

`B_a = B_d`.

Purpose: current-system control only. It is not evidence that a point sample is physiologically correct.

### Spatial Field B — target-centred finite local field

First sensitivity anchor: the actual Uchida–Ohno local pattern, a **12.4°-radius circle centred on the task point**, with the task point 10° eccentric from fixation in the source experiment. Astronomy implementation must state separately what target eccentricity/fixation geometry is assumed. This is an externally motivated shadow condition, not a validated astronomy field.

For a smooth sky, compute the photometric field from Level-B/MYSTIC sky samples over the finite angular region. Do not substitute zenith SQM or global hemispheric average unless that is actually the task field.

### Spatial Field C — local field plus angle-dependent surrounding contribution

Start from Spatial Field B and add separately sourced peripheral surrounding-luminance kernels as sensitivity alternatives. At minimum preserve these source-defined forms rather than inventing weights:

- Stiles–Crawford candidate: `L_veil = (16 / theta^2) E_n`;
- Uchida–Ohno steeper empirical candidate: `L_veil = (260 / theta^3) E_v`.

`theta` is source/task visual separation in degrees; the normal-vs-vertical illuminance distinction must be preserved. The later Uchida–Ohno experiment covered 5°–40° separations but excluded 5° from the new-model fit and explicitly says the lower applicable angle is unclear. A future sky-integral implementation therefore needs a preregistered inner-domain treatment/cutoff and must not extrapolate the power law to zero separation. Directional/isotropy applicability is also not established.

### Spatial Field D — eye-movement/spatial-distribution model

A later, higher-fidelity option may follow the Uchida et al. structure: luminance distribution + eye-movement distribution + surrounding-luminance effect + task/measurement area. Astronomy-specific gaze behaviour would need independent observation/psychophysics before this can be treated as more than a shadow sensitivity model.

## Pre-implementation evidence gate

Before coding any of B/C/D:

1. **Completed:** exact Uchida–Ohno local experiment geometry is now known: 1° target, target at 10° eccentricity, local adaptation circle radius 12.4° centred on target.
2. **Completed for source equations, not applicability:** the two main peripheral surround formulae/units are identified (`16/theta^2 * E_n`; `260/theta^3 * E_v`), and the wide-angle experiment's 5°–40° sampling plus explicit lower-angle/directional limitations are documented.
3. inspect the full CIE 257:2026 normative adaptation-field recommendation if accessible; do not infer it from abstract/preview text;
4. identify point-source/low-background evidence on spatial adaptation around retinal eccentricities relevant to averted stellar vision;
5. document whether the available evidence supports a single scalar adaptation luminance or separate rod/cone states;
6. freeze the astronomy gaze/fixation assumptions before seeing any Taylor/Jerusalem event-time differences;
7. if a surround kernel is implemented, preregister the inner angular domain/cutoff and whether the source-derived anisotropy is approximated as isotropic. These choices must come from independent evidence/sensitivity design, never observational residuals.

If the literature leaves multiple plausible field models, retain them as a preregistered sensitivity family. Do not choose from observational fit.

## Shadow implementation requirements after the evidence gate

A future implementation must:

- be shadow-only;
- sample physical sky radiance/luminance spatially without changing the underlying sky model;
- keep `B_a(t)` and `B_d(t)` separately logged;
- keep current tau sweep sensitivity status and avoid calibration;
- preserve query-order-independent precomputed adaptation state;
- record the exact spatial grid/kernel, target/fixation geometry, eye-movement assumptions and source provenance;
- run Candidate 2/3/4 mappings against the **same** frozen `B_a(t), B_d(t)` histories so mapping and spatial-field effects are not confounded;
- report mathematical threshold differences before any event-time comparison;
- forbid Taylor/Jerusalem residual-based selection;
- retain the fail-closed production guard until independent validation exists.

## Hard boundary

This protocol adds no workflow and authorizes no implementation, MYSTIC execution, AVPS result opening, `starsvisibility` source change, F/tau tuning, observational fitting, production routing or merge of PR #116.