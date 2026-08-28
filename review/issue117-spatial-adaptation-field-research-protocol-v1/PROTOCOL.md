# Issue #117 spatial adaptation-field research protocol v1

Status: **REVIEW ONLY / NO IMPLEMENTATION / NO SEMANTIC CHANGE**

This protocol is frozen after the current same-field mathematical work but before any implementation of a separate broad adaptation field. It exists because the surviving transient mappings cannot be scientifically distinguished under current Level-B mechanics, which populate adaptation-field luminance and local detection-background luminance from the same photopic sky sample.

## Bound project state

- `starsvisibility` baseline: `e0da52eb0a2d5bac333da6572f51df52ea7e676e`
- Issue #117 real-trajectory evidence: twilight PR #577
- mapping-candidate preregistration: twilight PR #578, head `23f96613d553610f9e75ddd4c8c08d0240c354c6`
- Candidates 0–3 math gate: twilight PR #580
- Candidate 4 Crawford/generalized-inverse protocol: twilight PR #581
- Candidate 4 math gate: twilight PR #582, current successful head `41dbb5202a5a10ccfffa64453b931c8da8037d4a`
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

1. **Uchida & Ohno, mesopic adaptation-field experiments (CIE/NIST work).** Peripheral object-detection performance was reported to depend predominantly on **local rather than global adaptation**; an approximately `10°` field-of-view condition was the local experimental anchor. This argues against using a whole-sky/global-average luminance as the default adaptation signal.
2. **Stokkermans, Vogels & Heynderickx 2016, Journal of Vision, DOI `10.1167/16.8.11`.** With nonuniform backgrounds and controlled veiling luminance, bright regions nearer the viewing direction produced longer dark-adaptation times than equally veiling bright regions at larger visual angles. Thus spatial location/local luminance matters beyond a single global scalar.
3. **Uchida/Ohno surrounding-source studies, Lighting Research & Technology, DOI `10.1177/1477153514558963` and `10.1177/1477153516638555`.** Surrounding high-luminance sources affect peripheral adaptation in an angle-dependent way; veiling/surround effects are relevant, but published peripheral angular behavior does not reduce safely to an arbitrary global average.
4. **Uchida et al. 2016, DOI `10.1177/1477153515626210`.** A mesopic adaptation-luminance simulation treats luminance distribution, eye movement, surrounding-luminance effect and area of measurement as separate spatial factors. The authors found simple area-average luminance often approximated their outdoor-lighting simulations, with important exceptions where bright sources surround the task area.
5. **CIE 257:2026** now explicitly defines/recommends an adaptation field for practical CIE mesopic photometry. Its full normative definition must be obtained/read before any claim that this project implements “the CIE adaptation field”; the public abstract alone is insufficient for exact implementation.

Applicability boundary: these studies mostly concern mesopic peripheral outdoor-lighting tasks, not astronomical known-position stellar detection under continuously waning natural twilight. They are independent priors/constraints, not direct validation of a star-visibility adaptation field.

## Preregistered research questions

Before implementation, answer in this order:

1. **Retinal task geometry.** For a known star detected with direct or averted vision, where is the adaptation field centered: fixation direction, target retinal location, or a combination that changes with eye movements?
2. **Local field scale.** Does a roughly `10°` local field-of-view provide a defensible first astronomy shadow prior, or does low-background rod spatial integration require a materially different scale? Do not reinterpret the published `10°` anchor as radius/diameter without the source's exact geometry.
3. **Spatial weighting.** Is a uniform local average adequate for a smooth natural-twilight sky, or must an angle-dependent surrounding-luminance/veiling kernel be included even without artificial glare sources?
4. **Eye movements.** What gaze/averted-vision behavior is appropriate for first detection of a known star, and over what temporal window should spatial samples contribute to the adaptation state?
5. **Spectrum.** Should the adaptation-field state use photopic luminance alone, scotopic/mesopic spectral weighting, or separate rod/cone state variables in the late-photopic/mesopic region relevant to 2–10.5° solar depression?
6. **Field-vs-detection separation.** Once `B_a` is spatially defined, local `B_d` must remain the physical sky background at the target detection location; adaptation processing must not overwrite MYSTIC/Level-B physical sky radiance.

## Candidate spatial-field families frozen for research, not selection

These are not yet executable mappings and may not be ranked by Taylor/Jerusalem residuals.

### Spatial Field A — current local-point baseline

`B_a = B_d`.

Purpose: current-system control only. It is not evidence that a point sample is physiologically correct.

### Spatial Field B — local finite-field average

Use a preregistered finite field around the retinal task location/fixation geometry. A `10°` field-of-view sensitivity point may be included because of the Uchida/Ohno mesopic local-vs-global experiment, but its exact angular definition must be copied from the source rather than guessed.

For a smooth sky, compute the photometric field from Level-B/MYSTIC sky samples over the finite angular region. Do not substitute zenith SQM or global hemispheric average unless that is actually the task field.

### Spatial Field C — local field plus angle-dependent surrounding contribution

Start from Spatial Field B and add a separately sourced angular surrounding-luminance/veiling contribution. The kernel/function must be copied/derived from independent literature applicable to peripheral adaptation and must retain provenance. Do not fit angular weights to star-visibility outcomes.

### Spatial Field D — eye-movement/spatial-distribution model

A later, higher-fidelity option may follow the Uchida et al. structure: luminance distribution + eye-movement distribution + surrounding-luminance effect + task/measurement area. Astronomy-specific gaze behavior would need independent observation/psychophysics before this can be treated as more than a shadow sensitivity model.

## Pre-implementation evidence gate

Before coding any of B/C/D:

1. obtain the exact experimental geometry/definition behind the local `10°` adaptation-field result;
2. obtain/read the exact angle-dependent peripheral surrounding-luminance formula(s), including units/domain;
3. inspect the full CIE 257:2026 adaptation-field recommendation if accessible; do not infer its definition from abstract text;
4. identify point-source/low-background evidence on spatial adaptation around retinal eccentricities relevant to averted stellar vision;
5. document whether the available evidence supports a single scalar adaptation luminance or separate rod/cone states;
6. freeze the astronomy gaze/fixation assumptions before seeing any Taylor/Jerusalem event-time differences.

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
