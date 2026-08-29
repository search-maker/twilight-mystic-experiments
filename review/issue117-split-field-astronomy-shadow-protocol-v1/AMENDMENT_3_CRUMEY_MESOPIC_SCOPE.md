# Issue #117 split-field SF-A — Amendment 3 / Crumey mesopic-scope boundary

Status: **FROZEN BEFORE ANY SF-A SKY-LUMINANCE OR CANDIDATE-THRESHOLD OUTPUT / PRIMARY-SOURCE SCOPE CLARIFICATION**

This amendment narrows the scientific claim permitted from the photopic-only Candidate 2/3/4 mapping frozen in Amendment 1. It changes no candidate formula, threshold coefficient, `F`, tau, atmosphere, spatial field, gaze arm, or output ledger.

Primary source: Andrew Crumey, *Human contrast threshold and astronomical visibility*, MNRAS 442 (2014) 2600–2619, DOI `10.1093/mnras/stu992`, especially section 1.3 “Photometric considerations”.

## 1. What Crumey's full threshold relation does justify

Crumey's model is an **achromatic** visibility model spanning background luminance from very low levels through daylight. The conventional luminance coordinate `B` is expressed in photopic `cd m^-2`. For target and background having the same relative spectral radiance, contrast is independent of which sensitivity function is used to define photometry; the Blackwell threshold relation can therefore be represented on that photopic-defined luminance coordinate.

That is the limited role of the bound Eq.34 implementation in SF-A: it supplies the already-reviewed equilibrium achromatic threshold curve on a common scalar coordinate so the transient mappings can be tested structurally.

## 2. What it does not justify in twilight

Crumey explicitly distinguishes spectral sensitivity from this achromatic baseline:

- Blackwell's calibration source was incandescent light at about 2850 K (approximately CIE illuminant A), with an S/P ratio specific to that source;
- when target/background spectral radiances differ, a spectral correction is generally required;
- a correction is required at mesopic levels too, but mesopic photometry is not uniquely specified by the achromatic threshold relation;
- Crumey states that mesopic photometry is important for visibility under severe light pollution, **including twilight**;
- his astronomical applications with explicit spectral treatment are deliberately restricted to fully adapted scotopic conditions, approximately background `<= 3e-3 cd m^-2`, rather than presented as a complete twilight mesopic model.

Therefore `photopic B -> Eq.34 -> Candidate 2/3/4` in SF-A v1 must **not** be described as a validated receptor-specific or mesopic transient-adaptation model. A photopic scalar alone cannot encode the changing rod/cone weighting of a twilight spectrum.

## 3. Consequence for SF-A interpretation

SF-A v1 may use the photopic coordinate to answer these preregistered questions:

1. Does a candidate preserve the required transient-debt monotonicity and same-field identity?
2. Does it remain structurally well-defined when `B_a != B_d`?
3. Are C2/C3/C4 numerically separable under a controlled astronomical split field?
4. How sensitive are those structural conclusions to frozen spatial/gaze/tau arms?

SF-A v1 may **not** use that coordinate to claim:

- a final twilight rod/cone adaptation state;
- a physiologically complete mesopic threshold;
- a final spectral correction for a star whose spectrum differs from the sky;
- that agreement with any later observation validates the photopic-only transient state;
- that a candidate surviving SF-A is automatically production-eligible.

A structural failure remains informative and may reject a candidate. Structural survival is only a necessary condition.

## 4. Role of the bound scotopic channel

Amendment 1 remains controlling:

- instantaneous photopic and scotopic field values may both be retained as scene descriptors;
- their ratio may diagnose how strongly the sky spectrum changes across time, space, and gaze;
- scotopic `cd/m2` must not be numerically substituted into the photopic Eq.34 coordinate;
- no ad-hoc P/S interpolation is allowed;
- no scotopic first-order state may be called a validated rod state;
- no rod/cone ODE split is authorized.

The existence of both provider channels makes the missing spectral physiology more visible; it does not supply it.

## 5. Later gate required for physiological closure

If one or more candidates survive the preregistered SF-A structural shadow, physiological closure of twilight adaptation still requires a separately frozen, independently sourced receptor/mesopic mapping or equivalent dynamic psychophysical evidence that specifies how the spectral scene drives the adaptation state and threshold. That later gate must be fixed before observational scoring and must not be chosen from Taylor/Jerusalem residuals.

Until then, the photopic SF-A branch is labelled:

`ACHROMATIC_CRUMEY_BLACKWELL_STRUCTURAL_BASELINE_NOT_MESOPIC_PHYSIOLOGY`.

PR #116 remains non-final and `TRANSIENT_VISIBILITY_NEGATIVE_PENALTY` remains fail-closed.
