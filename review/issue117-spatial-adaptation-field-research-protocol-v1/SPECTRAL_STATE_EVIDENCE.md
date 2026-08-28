# Issue #117 spectral adaptation-state evidence addendum

Status: **REVIEW ONLY / NO IMPLEMENTATION / NO SEMANTIC CHANGE**

This addendum belongs to the spatial adaptation-field research protocol in PR #583. It freezes the current evidence boundary for the open question: should the transient adaptation state remain one scalar luminance, become a steady mesopic combined scalar, or eventually use separate rod/cone state variables?

## Why the current single photopic scalar is only a control

Current `starsvisibility` transient history uses one photopic adaptation-field luminance, and current Level-B also sets that adaptation-field sample equal to local physical detection `B`. This is an experimental Version-0 convenience, not independently calibrated receptor physiology.

Independent psychophysics/physiology does not support treating rods and cones as one universal dynamic state throughout mesopic/scotopic vision:

1. **Aparicio et al. 2016, Vision Research, DOI `10.1016/j.visres.2016.04.008`.** With steady backgrounds from `0.06` to `110 cd/m^2`, retinal eccentricities `0°–15°`, and background/test combinations `10°/2°`, `10°/0.45°`, `1°/0.45°`, their model/data show adaptation/spatial-summation mechanisms depend on eccentricity and field size. Under the small-background condition they report rod–cone interaction for eccentricities about `6°–9°` and background luminances about `0.6–5 cd/m^2`. This range is not a direct match to the lower luminances of late twilight, but it demonstrates that receptor interaction and spatial geometry can matter in the same eccentricity family relevant to averted vision.
2. **Frumkes, Sekuler & Reiss 1972, Science, DOI `10.1126/science.175.4024.913`.** Selective rod/cone conditioning under parafoveal scotopic conditions changed flash thresholds for both homochromatic and heterochromatic pairs; the time course indicated a longer rod-system latency than cone-system latency. A single receptor-independent temporal state is therefore not a generic physiological identity.
3. **Bauer, Frumkes & Holstein 1983, Journal of Physiology, DOI `10.1113/jphysiol.1983.sp014615`.** Cone-detected test thresholds were affected by a rod-detected mask while rods recovered from bleach and under selective rod light adaptation. This shows that rod adaptation state can alter a cone-detected threshold; receptor states/interactions cannot always be represented by independently isolated channels.
4. **Drum 1981, JOSA, DOI `10.1364/JOSA.71.000071`.** A parafoveal rod background changed foveal cone thresholds in the dark-adapted eye, again demonstrating lateral rod influence on cone sensitivity.
5. **Stabell & Stabell 1993 / 1998.** Long-term dark-adaptation experiments report changing rod/cone dominance and mutual rod–cone effects as adaptation progresses; rods may dominate form perception well above the absolute cone threshold. These bleach/long-adaptation paradigms are not the same as continuously waning natural twilight, but they warn against treating mesopic receptor weighting as a fixed scalar identity.
6. **Mesopic isolated-receptor timing evidence (Cao et al. / rod-cone reaction-time work, Vision Research 2007, DOI `10.1016/j.visres.2006.11.027`).** Under common mesopic adaptation conditions, isolated rod and cone signals exhibit different temporal response properties; rod reaction times were about 20 ms longer in the mixed functional range. This is a fast-response metric rather than the minutes/seconds adaptation state itself, but it independently establishes different receptor temporal channels.

## Important applicability boundary

None of the studies above directly measures the exact state variable needed here: known-position stellar point-source threshold during a smoothly waning natural-twilight sky over seconds to minutes. Bleach recovery, flashes, flicker, color/form and road-lighting contrast tasks must not be silently converted into transient coefficients for this project.

Therefore the correct conclusion is **not** “use two ODEs now.” The evidence supports keeping receptor-state structure as an explicit uncertainty/research dimension and forbids presenting the current one-state photopic EMA as validated physiology.

## Preregistered spectral-state research families

These families are frozen for future evidence collection. They are not authorized implementations and may not be selected from Taylor/Jerusalem residuals.

### Spectral State S0 — current photopic scalar control

`A(t)` is driven by the spatial adaptation field expressed in photopic luminance only.

Purpose: exact current-model control. No physiological validation claim.

### Spectral State S1 — CIE-style steady mesopic scalar control

Construct a single **steady** mesopic adaptation/effective-luminance control using the verified CIE TN 007 / CIE 257 practical structure: photopic adaptation luminance plus the field S/P information needed for the CIE mesopic coefficient/luminous-efficiency calculation.

Boundary:

- this is a practical steady mesopic-photometry control, not a transient physiological state equation;
- do not assign the current `tau` to this scalar merely because it is mesopic;
- preserve the CIE scope/provenance and report the photopic/scotopic inputs separately.

### Spectral State S2 — separate rod/cone state research arm

Maintain at least two precomputed state variables driven by the **same frozen spatial adaptation-field geometry**:

- cone-oriented state driven by a photopic/cone-weighted field quantity;
- rod-oriented state driven by a scotopic/rod-weighted field quantity.

This arm remains **blocked** until independent dynamic evidence defines:

1. state equations or kernels for the waning-background regime;
2. receptor-specific time constants/rate dependence, if any;
3. how rod/cone states combine to raise a point-source threshold at the relevant eccentricity;
4. whether interaction is additive, suppressive/facilitatory, threshold-ratio based, or requires a coupled model;
5. the wavelength/spectral convention for the twilight adaptation field;
6. domain limits across background luminance and retinal eccentricity.

Do not infer these coefficients from event-time fit.

### Spectral State S3 — externally measured dynamic threshold-state model

If future literature or a dedicated preregistered psychophysical experiment directly measures point-source thresholds under continuously waning backgrounds with controlled spectrum/eccentricity, use the measured threshold state itself rather than forcing it into one/two exponential luminance states. This is the scientifically preferred escape hatch if the simple-state families are inadequate.

## Evidence gate before any S2 implementation

Required before code:

- identify independent dynamic waning-background rod/cone data closer to late twilight than large-bleach dark adaptation;
- determine whether relevant target detection at roughly the astronomy averted-vision eccentricity is rod-dominated, mixed, or spectrum-dependent across the 2°–10.5° solar-depression range;
- use current Level-B photopic/scotopic sky channels only as physical inputs; do not relabel them as receptor state without a validated temporal transform;
- freeze all receptor-state equations and coefficients before observing Taylor/Jerusalem timing effects;
- retain S0/S1 controls so spatial-field and receptor-state changes are not confounded.

## Hard boundary

This addendum adds no workflow, no solver, no `starsvisibility` mutation, no tau/F tuning, no observational fitting and no production activation. The current fail-closed transient guard remains authoritative.