# P1 source verification | BAJ 16 (2011), first-star observations and formula conflicts

**Date:** 2026-11-23, New York after sunset (14 Kislev 5787). **Scope:** independent public-source triage only; **not** a validation run, atmospheric solve, or preregistration. No Taylor/Ann Arbor or Jerusalem protected records used.

## Direct original evidence
Publisher-hosted primary article, R. O. Belokrylov, S. V. Belokrylov, M. G. Nickiforov, “Model of the stellar visibility during twilight,” *Bulgarian Astronomical Journal* 16 (2011), pp. 50–72:
https://www.astro.bas.bg/AIJ/issues/n16/08_MNikifor2.pdf

The web reader resolved the original PDF and its **page images were individually inspected** for printed pp. 53 (methods), 56 (Fig. 4), 57 (formulas and author-stated errors), 58 (alternative printed 5.61), 60 (October 2009 visual records), 62–63 (June 2010 records). A complete raw PDF download and cryptographic file checksum were **not** obtained. This is a publisher-hosted typeset article **not** original notebooks/field cards.

- p. 53 describes >600 visual appearance/disappearance observations over three years. Observers marked target alt/az and briefly located it with binoculars before naked-eye onset, then in later sessions recorded first-star time and stopwatch intervals for later objects. **A binocular *pointing aid* is not a binocular-only detection**, but individual example entries lack per-check explicit modality and pre-event NOT_SEEN logs.
- p. 60 gives two explicit **same-evening author-reported onset times**: Vega at 18:55 and Arcturus at 19:02, 10 October 2009, “Moscow time”; respective reported solar *altitudes* −2.4° and −3.4°, with Arcturus altitude ≈28°. The 7-minute gap is a within-paper observation interval, **not a model error**.
- pp. 62–63 give two more specific reported timings, 28 June 2010: Capella at 23:14 “Moscow summer time,” solar altitude −5.67°, target H≈13°, Sun–target separation 27°; beta Aurigae at 23:48, solar altitude −7.90°, target H≈12°, separation 22°. **Do not assume Moscow was the 2010 observation site** merely because Moscow summer time is used.
- Neither original case pair includes target-specific preceding NOT_SEEN times, a second independent confirmation, original minute-to-minute atmosphere/aerosol/cloud state, measured directional skyglow at target, clock uncertainty, eye adaptation, precise observing coordinates, or independently locked model predictions. The examples were used within the same paper for fit, explanatory examples or author checks. **Strict eligible independent first-onset brackets = 0 / 4**. Do not call these source examples unseen model validation.
- The article says it selected *best* viewing conditions among repeated observations and limits its empirical fit to clean atmosphere (printed p. 57). It estimates bright-star timing error about 2 minutes but faint-star timing errors potentially >10 minutes (p. 57); these are **author estimates**, not measured error bars for our model. Its quoted k is estimated/assumed from Vega and extinction logic, **not contemporaneous independent AOD**.

## Material source-to-model hazard: inconsistent published equations

Comparing **actual page images** (not OCR) reveals contradictions. This matters if any worker treats the published empirical equations as an independent physical benchmark or silently transcribes them into code.

1. **Printed pp. 57 and 63, eq. (3a):** `m(h) = -2.78 - 0.18 h`; **figure 4 on p. 56 visibly instead:** `m(h) = +2.78 - 0.18 h`. At hypothetical `m=5.00`, literal printed (3a) implies `h=(-2.78-5)/0.18 = -43.22°`, not a twilight first appearance. The figure implies `h=(+2.78-5)/0.18 = -12.33°`.
2. **Printed pp. 57 and 63, eq. (3b):** `h(m)=15.62-6.61 m`; **figure 4 p. 56 and explanatory formula p. 58:** `h(m)=15.62-5.61 m`. At illustrative `m=5.00`, these give `-17.43°` versus `-12.43°`: exactly **5.00° difference in predicted solar depression**, **not a measured 5° bias of our model**. Figure's (3a)/(3b) are only approximate inverses due to fitting/rounding.
3. **Printed branches invert magnitude conditions:** p. 57 bright-star eqs. (2b),(4b) print `m>4.2`, while faint eq. (3b) prints `m<=4.2`, contrary to adjacent bright/faint prose and plotted division. Do not guess corrected definitions in production or mark them independently validated.
4. **Additional author example mismatch, p. 63:** beta Aurigae is given separation `x=22°`, while the background correction expression later plugs `58-28` yet reports `-1.22°`. The number `-0.0338*(58-22)=-1.2168°` agrees with the reported `-1.22°`; `-0.0338*(58-28)=-1.014°` does not. Treat the textual substitution as inconsistent, **not** a new physical measurement.

**No automatic repair:** There is sufficient evidence for **source transcription conflict**, not for asserting an intended canonical formula or producing validated late-twilight times. This study was already a target of an UNSENT contact draft for original unselected logs, so this source verification does not claim a newly discovered archive.

## Structured manifest and hard admission status
See `P1_BAJ2011_FOUR_AUTHOR_REPORTED_VISUAL_APPEARANCE_CASES_20261123.json` (same branch). Four named dated author-reported visual appearances are now anchored to printed page identifiers. No UTC timestamp has been invented; site for the 2010 pair is deliberately NULL. No original PDF SHA is claimed. These records **must not** be compared against model v1 as independent heldout cases, especially because their original authors used them in constructing/testing that very empirical methodology.

## Specific next authorized handoff
Coordinator / existing approved outreach owner must resolve disabled outreach agent (`requires_user_action=true`, no explanatory text in latest task result), verify human observer consent, get complete *unselected original per-check* records for these and other dates, and/or execute a new voluntary blinded pilot only after source, model git SHA, per-target attention windows, sampling intervals, atmospheric and SQM pointing, error thresholds, budget and stop rules are irrevocably frozen. Two drafts to Halifax RASC and Nickiforov are **not sent**, as confirmed by their Gmail DRAFT labels and one-message threads in this run. Do not send from another surface to evade the disabled owner. No outreach message was sent here.

Status: `NEW_SOURCE_PAGE_IMAGE_QC=PASS`; `REPORTED_APPEARANCE_RECORDS=4`; `STRICT_ONSET_BRACKETS=0`; `INDEPENDENT_MODEL_RESIDUALS=0`; `LATE_TWILIGHT_10_5_TO_16_VALIDATED=NO`; `REGISTERED_PROSPECTIVE_PILOT=NO`; `MYSTIC_DISPATCH=NONE`; `MODEL_SHA_LOCK=NOT_ESTABLISHED`.
