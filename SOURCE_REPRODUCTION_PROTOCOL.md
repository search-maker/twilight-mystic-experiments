# Issue #117 source-reproduction gates before astronomical split-field shadow

Status: **REVIEW ONLY / PREREGISTERED BEFORE IMPLEMENTATION OUTPUT / NO SEMANTIC CHANGE**

This file freezes the next independent validation order for the human-vision transient/adaptation lane. It is deliberately upstream of any Taylor/Jerusalem event-time scoring and upstream of any production `starsvisibility` semantic change.

The purpose is to test proposed pieces of the split-field architecture against the laboratory evidence that motivates those pieces before applying them to astronomical event histories.

## Hard separation of factors

The future research implementation MUST preserve these as independent factors:

1. `B_d(t)`: local physical detection-background luminance at the star/task point;
2. spatial operator producing `B_a,instant(t)` from a retinal/fixation-centred physical luminance distribution;
3. spectral/receptor representation of the adaptation field;
4. temporal adaptation-state dynamics producing lagged adaptation state from `B_a,instant(t)`;
5. threshold mapping from adaptation state + `B_d(t)` to required point-source signal;
6. gaze / target retinal eccentricity.

No parameter in one factor may be tuned to compensate for another factor's failure.

Crumey/Blackwell equilibrium point-source threshold remains the steady-state detection model. These source-reproduction gates do not refit Crumey, F, stellar transport, sky radiance, or any atmospheric input.

## SR-SPATIAL-1 — Stokkermans spatial-distribution ordering

Primary source: Stokkermans, Vogels & Heynderickx (2016), *The effect of spatial luminance distribution on dark adaptation*, Journal of Vision 16(8):11, DOI `10.1167/16.8.11`.

### Source geometry frozen before implementation output

Experiment E2 used three non-uniform backgrounds with approximately equal calculated target veiling luminance (`0.07 cd/m^2`) but different spatial distributions:

- `Bar9`: two horizontal bars, each 2° wide, at 9° from target; bar luminance 42 cd/m²; image-average luminance 8.41 cd/m²;
- `Bar2.7`: two horizontal bars, each 2° wide, at 2.7° from target; bar luminance 5.1 cd/m²; image-average luminance 1.02 cd/m²;
- `Square`: a 2° x 2° bright square at 4.3° from target; square luminance 101 cd/m²; image-average luminance 1.02 cd/m².

The source reports significantly shorter net adaptation time for `Bar9` than for `Square` and `Bar2.7`; `Square` vs `Bar2.7` was not statistically significant in the main analysis. This is the preregistered qualitative ordering target. It is not a free value to discover after model output.

### Spatial operator arms

The source-reproduction implementation MUST calculate all arms before any astronomical use:

- `S0_POINT`: target-point luminance only (current same-field conceptual control);
- `S1_AREA`: a simple finite local area average control, with geometry fixed from an independent source rather than event fit;
- `S2_ALF`: source-defined Murdoch/Heynderickx adaptation-luminance-field sensitivity used by Stokkermans: target-centred sum of two Gaussian components, narrow SD ~0.67° with weight `0.9935`, broad SD ~3.9° with weight `0.0065`;
- `S3_UCHIDA_LOCAL`: 12.4°-radius target-centred local adaptation pattern from the Uchida-Ohno full-source geometry already frozen in this PR;
- optional surrounding-source arm only if its angle kernel and illuminance convention are implemented exactly as documented in `PROTOCOL.md`.

The numerical implementation MUST state its angular measure, pixel/solid-angle integration rule and normalization explicitly. No Gaussian width or weight may be optimized from source or astronomical outcomes.

### Veiling / double-counting boundary

Stokkermans evaluated an adaptation-luminance model in which image luminance was corrected for a veiling-luminance model before spatial weighting. In this astronomy project, atmospheric sky scattering is already part of the physical sky radiance. Intraocular veiling/glare is a different optical phenomenon.

Therefore the first spatial source check MUST report two separately named quantities:

- spatially weighted external physical luminance;
- any optional intraocular-veiling contribution.

They MUST NOT be silently summed as if atmospheric scattered sky and ocular glare were the same component. An ocular-veiling arm is research-only until separately justified.

### Acceptance / refusal

This gate is **directional, not fitted**.

A spatial operator is source-compatible only if it predicts greater local adaptation load for the source configurations with bright structure nearer the target than for the far `Bar9` configuration in a manner consistent with the reported adaptation-time ordering, without changing operator parameters after seeing its output.

Do not require exact adaptation-time magnitudes: the source's downstream DICOM/display model and task are not the astronomical star-threshold model. Exact-time fitting would overclaim transferability.

If an arm fails the qualitative spatial ordering, preserve that failure; do not tune it from the source result and do not advance that arm as the primary astronomical adaptation field.

## SR-DYNAMIC-1 — Spillmann waning-background history/rate ordering

Primary source: Spillmann, Nowlan & Bernholz (1972), *Dark Adaptation in the Presence of Waning Background Luminances*, JOSA 62:177-181, DOI `10.1364/JOSA.62.000177`.

### Source geometry / history frozen

Use the source-relevant facts already documented in `DYNAMIC_WANING_BACKGROUND_EVIDENCE.md`:

- approximately 1° test stimulus;
- ~10° retinal eccentricity;
- circular adapting background stated as 30° angular subtense;
- approximately seven-log-unit continuous background decline;
- descent durations 3.5, 7, 14 and 21 min;
- pre-exposure and no-pre-exposure conditions remain separate;
- tungsten spectrum is a deliberate spectral control and must not be relabelled as natural twilight spectrum.

### Mapping arms

Use exactly the same frozen physical `B_a(t)` and local `B_d(t)` histories for all surviving threshold mappings:

- Candidate 2: path-envelope mapping;
- Candidate 3: adaptation-threshold-ratio mapping;
- Candidate 4: threshold-derived equivalent-background / generalized-inverse mapping.

PR #116 / endpoint floor remains historical diagnostic only and is not eligible for promotion after its preregistered debt-monotonicity failure.

### Preregistered scientific interpretation

The source establishes that waning-background thresholds are elevated above stationary-background thresholds at the same instantaneous luminance, with a strong dependence on decline rate and prior exposure. It also establishes the historical logical order for an `equivalent background`: infer threshold desensitisation through a stationary threshold-vs-background relation, then combine the inferred equivalent and real backgrounds.

Consequently Candidate 4 is designated **primary historical-equivalent-background candidate by provenance**, Candidate 3 is a threshold-space structural control, and Candidate 2 is a monotone/path control. This is not final psychophysical or astronomy selection.

The source-reproduction gate must test only qualitative invariants that transfer safely:

1. no waning condition may become easier than stationary equilibrium solely because adaptation debt is positive;
2. greater independently defined maladaptation/history debt may not reduce required signal;
3. faster/stronger source histories must not produce a reversal contrary to the documented rate/history dependence;
4. pre-exposure and no-pre-exposure conditions remain distinguishable inputs;
5. no astronomy tau is fitted to reproduce the source's threshold magnitudes.

Exact 1.25-log or ~0.4-log source deviations are evidence targets for scale context, not fitting targets for the astronomy model.

## SR-TIME-1 — time-scale provenance, not coefficient calibration

The present project tau values `20/30/45/60 s` remain **sensitivity arms only**.

Independent references delimit what may be claimed:

- Pianta & Kalloniatis (2000), DOI `10.1111/j.1469-7793.2000.00591.x`, develops human cone dark adaptation using equivalent-background logic; the paired human cone ERG literature reports the psychophysical equivalent-background components after ~90% bleach at approximately 19 s and 51 s.
- Lamb (1981), DOI `10.1016/0042-6989(81)90211-X`, reports rod equivalent-background components around 5 s, 100 s and 7 min after bleach.
- Spillmann's continuously waning protocol shows explicit rate and prehistory dependence.

Thus 20-60 s overlaps one cone post-bleach order of magnitude, but no current project tau is independently calibrated for natural twilight, and a one-state 20-60 s model is not a sourced rod/scotopic physiology model.

No separate rod/cone ODE implementation is authorized by these constants. Receptor-specific dynamic equations require independent continuously waning-background evidence or a separately frozen mechanistic translation.

## SR-SPECTRAL-1 — spectrum enters adaptation field before receptor dynamics are claimed

Spillmann deliberately used tungsten to avoid the changing evening spectrum as a rod-kinetics confound. CIE TN 007:2017 likewise states that measured spectral information for the adaptation field should be used when available rather than relying on a simplified source S/P ratio.

Therefore a future split-field research implementation must preserve enough spectral information to calculate, as separate reported controls:

- photopic adaptation-field luminance;
- scotopic adaptation-field luminance / S:P information where the physical sky spectrum supports it;
- a CIE steady-mesopic scalar control where applicable.

This does **not** authorize distinct rod/cone temporal ODEs. It prevents a single photopic scalar from being mislabelled as a validated full mesopic/scotopic state.

## Astronomy shadow gate comes later

Only after the source-reproduction checks above are implemented and their outcomes frozen may a separate preregistered astronomical split-field shadow be opened.

That later protocol must freeze before outputs:

- gaze/eccentricity arms, including Alexander et al. 2021 source-defined ~8°-14° sensitivity band as fixed arms rather than a fitted gaze distribution;
- spatial operator arms;
- spectral state arm;
- temporal dynamics/tau sensitivity arms;
- Candidate 2/3/4 mappings;
- output metrics and refusal rules.

No arm may be selected from Taylor/Jerusalem residual agreement.

## Current production boundary

This file adds no workflow and authorizes no `starsvisibility` semantic change, MYSTIC run, F change, tau fit, protected holdout opening, empirical human-validation claim or production routing change.

`TRANSIENT_VISIBILITY_NEGATIVE_PENALTY` remains the authoritative fail-closed guard until a replacement survives the independent evidence and preregistered shadow chain.