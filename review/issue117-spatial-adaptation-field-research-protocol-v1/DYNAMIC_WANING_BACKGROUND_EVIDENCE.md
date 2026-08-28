# Issue #117 dynamic waning-background evidence addendum

Status: **REVIEW ONLY / NO IMPLEMENTATION / NO SEMANTIC CHANGE**

This addendum freezes the most directly relevant historical dynamic-background evidence found so far for the twilight transient-adaptation problem.

## Spillmann, Nowlan & Bernholz 1972 is unusually close to the natural-twilight question

Source: *Dark Adaptation in the Presence of Waning Background Luminances*, JOSA 62, 177-181 (1972), DOI `10.1364/JOSA.62.000177`.

The paper explicitly motivates the experiment by natural sunset/dusk rather than only by large laboratory light-to-dark steps. It notes that abrupt transitions to darkness are unlike natural conditions and that the global sky luminance falls over a very large range while the Sun moves through twilight.

### Exact task / spatial geometry from the full text

The OCR in accessible copies drops some degree symbols, but the apparatus description identifies:

- test stimulus: approximately **1° white square**;
- presentation duration: **0.04 s**;
- test retinal location: approximately **10° from centre/fixation on the horizontal meridian in the nasal field**;
- adapting/pre-exposure background: **circular field of 30° angular subtense**;
- fixation: small red fixation mark superimposed on the field;
- Maxwellian view; effective pupil 1.5 mm.

This is important for the present spatial-adaptation question: the closest dynamic-waning-background experiment is not a point-adaptation experiment. It used a broad 30° circular adapting field around a small off-axis detection stimulus.

Do **not** convert this fact into a claim that the astronomy adaptation field must be 30°. The source geometry is an independent shadow anchor only, and the exact interpretation of the 30° subtense as diameter/field extent must preserve the source wording rather than silently relabelling it as radius.

### Dynamic background protocol

- observer first underwent 45 min dark adaptation;
- except where noted, 5 min pre-exposure at 325 mL;
- the waning background was then reduced continuously by about **7 log units** to `3.25e-5 mL`;
- total descent durations: **3.5, 7, 14, 21 min**;
- another condition performed the 3.5-min waning descent without the preceding pre-exposure;
- steady-state increment-threshold comparison adapted 90 s at each fixed luminance level;
- temporary-background-extinction intervals lasted 15-90 s in separate measurements.

### Spectral control is directly relevant

The paper states that **tungsten light was used throughout to eliminate possible favourable effects on rod-threshold kinetics that might result from reddening of the sky during evening hours**.

This is direct evidence that the authors regarded twilight spectral change as a possible confound in adaptation kinetics. Therefore our future dynamic adaptation state cannot be described as fully sourced if it uses only one photopic scalar while silently ignoring the evolving photopic/scotopic spectrum. It still does not provide a ready-made rod/cone dynamic equation for this project.

### Main dynamic result relevant here

- increment thresholds on waning backgrounds were higher than on stationary backgrounds of the same instantaneous luminance;
- the deficit depended strongly on rate of background change and became large in the low-luminance/scotopic portion;
- the paper reports up to about **1.25 log unit** threshold elevation under the steepest pre-exposed waning condition;
- a much smaller maximum deviation (~0.4 log unit) occurred for the fastest-changing condition without the preceding pre-exposure;
- dark thresholds measured during temporary extinction of slowly waning backgrounds remained persistently elevated;
- the authors conclude that prolonged waning illumination can retard adaptation below its potential maximum rate.

The paper also reports discontinuities that may be associated with the cone/rod transition under some slower waning conditions. That is qualitative evidence that a single receptor-independent state may be incomplete, but the experiment does not uniquely identify separate rod/cone state equations or coefficients.

## Consequences for the project research design

1. **Spatial state:** retain the 30° circular adapting-background geometry as a dynamic-waning-background sensitivity anchor alongside the 12.4°-radius Uchida-Ohno local-field anchor and the CIE-style evaluation-area control. Do not select among them from Taylor/Jerusalem fit.
2. **Spectrum:** a future shadow family should explicitly compare physical photopic/scotopic/mesopic adaptation-field inputs; Spillmann deliberately controlled spectrum because evening reddening could alter rod kinetics.
3. **Dynamics:** the delay is rate/history dependent. Do not interpret the current one-parameter EMA/tau as if Spillmann calibrated it.
4. **Pre-exposure/history:** threshold lag in Spillmann depends materially on pre-exposure history; our application-sunset prehistory is therefore a scientifically meaningful part of the model and must remain separately auditable.
5. **No direct coefficient transfer:** their pre-exposure, tungsten spectrum, Maxwellian-view geometry and threshold task differ from free-viewing astronomical star detection. Do not transfer a 3.5/7/14/21-min background descent into a fitted project tau.
6. **No claim that 30° is the physiological field:** the experiment shows a successful relevant dynamic paradigm using a broad background, not the unique retinal adaptation-field size.

## New preregistered dynamic/spatial control family

### Spatial Field F - Spillmann 30°-subtense waning-background anchor

For a future shadow sensitivity run only:

- reproduce a target-centred/fixation-aware physical sky field corresponding to the source's stated **30° circular angular subtense**;
- preserve whether the numerical implementation treats source 'subtense' as a full angular diameter/extent rather than silently turning it into a radius;
- use the same frozen physical sky history for all candidate transient mappings;
- report separately from the 12.4°-radius Uchida-Ohno local-field arm and CIE evaluation-area control;
- no observational-residual selection.

Before code, independently verify the source's angular-subtense convention from the original typeset PDF if possible; accessible OCR can remove degree symbols but should not change the stated field geometry.

## Hard boundary

No workflow is added. No dynamic coefficient, field size, spectral weight, tau, F, gaze geometry or production routing is authorized by this addendum. It is evidence/preregistration only.