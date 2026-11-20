# Original first-star study source audit — 2026-11-20

**Evidence category:** NEW primary-publication equation consistency verification; **NOT an independent observational validation**.

**Source:** R. O. Belokrylov, S. V. Belokrylov, M. G. Nickiforov, *Model of the stellar visibility during twilight*, Bulgarian Astronomical Journal 16 (2011), printed pp. 50–72, [publisher original PDF](https://astro.bas.bg/AIJ/issues/n16/08_MNikifor2.pdf). The actual PDF page **images** were inspected at printed pp. 53, 55, 56, 57, 58; no source-byte hash was established (direct download unsuccessful).

## New verified source contradiction, with quantitative effects

The **blue plotted faint-star regression in p. 56, Fig. 4** prints `m = 2.78 - 0.18*h`, `h = 15.62 - 5.61*m`, where h is signed Sun altitude. **Printed p. 57, Eq. (3a)/(3b)** instead prints `m = -2.78 - 0.18*h` and `h = 15.62 - 6.61*m`. Independently, **printed p. 58** explicitly repeats `h = 15.62 - 5.61*m` (the Fig. 4 coefficient), confirming internal text disagreement. The p. 57 branch inequalities also print bright Eq. (2b) `m > 4.2` and faint Eq. (3b) `m <= 4.2`, reversed relative to fitted data; p. 58 repeats the reversed faint `m' < 4.2` selector.

Exact decimal arithmetic (see the companion reproducible fixture):
- At `h=-14°`: literal p.57 (3a) yields `m=-0.26`; p.56 Fig.4 yields `m=5.30` — a **5.56-mag** discrepancy. This is an *arithmetic contradiction*, not a human observational error.
- At `m=5.28` (the paper's listed iota Lyr magnitude): literal p.57 (3b) yields `h=-19.2808°`; Fig.4 and p.58 yield `h=-14.0008°`, a **5.2800° solar-altitude** discrepancy. These are evaluation points, **NOT measured observation times**.
- At the stated transition `h=-7.7°`, bright fit `m=4.210`, plotted faint fit `m=4.166` (similar), but literal printed p.57 (3a) predicts `m=-1.394`, incompatible with an approximately continuous fit.

**Interpretation:** The original plot and independent p.58 text support `5.61` rather than `6.61`, and the plotted positive faint intercept rather than the printed negative one. No formal author erratum was independently found in this run: treat corrected reading as `FIGURE_SUPPORTED_INTERPRETATION__AUTHOR_ERRATUM_UNVERIFIED`, not a certified replacement formula or a validated model.

## Human ground-truth admission boundary

The paper reports **>600** human naked-eye twilight star appearances / morning disappearances over three years (p.53), with preliminary binocular locating, then unaided-eye detection; faint-star points were **selected best-visibility** examples used to fit the paper's own regression (p.57). The printed figure points lack event-level dated first-sight and preceding NON_SEEN times, observer visual-adaptation logs, matched cloud/aerosol, and exact event-direction sky brightness. This paper is **training/aggregate evidence**, not a result-blind independent blind trial. **New admissible independent late-band first-sighting events: zero.** The 10.5–16° prediction-precision gap stays open.

Suggested manifest classification: `HUMAN_FIGURE_AGGREGATE__NO_EVENT_TIMESTAMPS__PUBLISHED_EQUATION_CONFLICT`. Do NOT use literal Eq. (3a)/(3b) as data labels, calibrate on the curated best-case figure, or claim a late-band accuracy measurement based on this numerical discrepancy.

**Handoff:** Coordinator / authorized original outreach owner already has an unsent corresponding-author request. Ask for original dated logs with exact civil/UTC time and offsets, event identities/magnitudes, repeated pre-detection NON_SEEN checks, optical mode, site/pointing, skyglow/cloud/aerosols and adaptation conditions and permission to reuse. If unavailable, existing blinded prospective pilot remains the admissible route, after fixed SHA, input/cases, error thresholds, and stop budget are frozen before any predictions/outcomes.

**Guards:** no Taylor/Jerusalem protected access, no model fit, no solver or MYSTIC dispatch; ordinal67 spent, ordinal68 frozen; no funding/paid actions. Scientific release remains unsupported for late-band precise first visibility.
