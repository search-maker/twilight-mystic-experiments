# 2026-11-18 — real independent *directional* aerosol-radiance source, bounded reproduction

**Source admission: PARTIAL PASS for published original relative directional radiometry, FAIL for matched local AOD550 / human first-star timing.** This is not a MYSTIC experiment, a registered volunteer trial, a protected holdout, or a timing-model validation. No new scientific prediction or threshold is generated.

## Original primary source (independently source-read)
M. Kocifaj, F. Kundracik, J. Barentine, “Aerosol parameters for night sky brightness modelling estimated from daytime sky images,” *MNRAS* 523(2) (2023), 2678–2683, DOI [10.1093/mnras/stad1570](https://doi.org/10.1093/mnras/stad1570). [Original publisher text/Table 1](https://academic.oup.com/mnras/article/523/2/2678/7179414).

**Original field data**: Bratislava, 2017-10-16/17, authors describe observations at 15:30–16:30 local (no per-ray UTC timestamps). Portable sky scanner at **450 nm**, *relative* and **not absolute-calibrated** spectral radiance. Sun azimuth 234°; article states solar zenith 73° in the field paragraph, but a nearby illustrative geometry / figure caption uses 70°.

| Type | Zenith z (deg) | Azimuth (deg) | Relative radiance |
|:---|---:|---:|---:|
| Red cross 1 | 70 | 234 | 292 |
| Red cross 2 | 60 | 234 | 184 |
| Red circle 1 | 70 | 276 | 125 |
| Red circle 2 | 30 | 234 | 83.7 |

**Optical observation is NOT the moment of first seeing a named star.** No observer IDs, star magnitudes, YES/NO detection bracket, adaptation protocol, or paired observed twilight first-sighting times. These daytime measurements cannot justify first-visibility timing in (10.5°,16°], and the 90°-zenith SG_088 shortcut is not relevant to the four actual pointing directions.

## Exact bounded reproduction, independent of the model
[Standard-library executable](bratislava_2017_daytime_aod_ratio_reproduce.py) uses the author's equation (3), the actual table ratio **83.7/125=0.669600**, bracketed bisection over tau in (0,2], and the author's Rayleigh optical depth **ROD450=0.23** (itself a stated paper input, not a separate local measurement).

- Assuming **zSun=70°**, algebraic tau **0.552266**, inferred **AOD450≈0.322266**; consistent with author's rounded tau≈0.55, AOD≈0.32.
- Substituting the field paragraph's **zSun=73°** without correcting the paper's equal-scattering-angle assumption gives algebraic tau **0.548453**, inferred AOD450≈**0.318453**. **This is NOT an alternative validated physical retrieval**.
- With the table azimuths and geometry, the two nominally equal scattering angles are **39.3587° and 40.0000°** at zSun=70°, versus **39.8423° and 43.0000°** at the field paragraph's zSun=73°. The cancellation of the aerosol scattering phase function in equation (3) presumes equal angles. The original observation-time Sun geometry / per-ray directions must be independently clarified before an exact AOD admission.

**Hard provenance limits:** the paper does not supply per-direction timestamps, raw scanner bytes/instrument calibration, measured uncertainty at the site, or a spectrally verified Ångström exponent. Consequently **AOD550 = null**, **AOD450 is a retrieval under paper assumptions**, and no uncertainty/bias of first-star prediction can be calculated. The reported Vienna/Brno AERONET values (about 0.25/0.22, 50–120 km away) are surrounding-site *comparisons*, not collocated ground truth. Do not silently treat AOD450 as AOD550, interpolate in time without actual data, or use a claim of observed star visibility.

## Status and next action
- **SOURCE-PASS**: verified primary published four distinct azimuth/zenith radiance readings; public original table; bounded executable arithmetic replication.
- **SCIENCE-FAIL-TO-ADMIT for target**: no independent human first-star sighting brackets; no matched measured AOD550 or checked geometry/time; no raw photo frames.
- **Next step for existing Outreach Replies owner / Coordinator only**: secure affirmative V0 consent and exact lawful observing site for existing PA/NJ/Southern-Cape leads, and freeze a runnable exact StarsVisibility model SHA, catalog, site, meteorology inputs, selected nonprotected cases and blinded predictions **before** new sightings. Separately seek the *original* scanner ray timestamps, spectral calibration and scan geometry from the 2023 source authors if useful for background/atmosphere validation. No direct unsolicited message or paid commitment from this source review.
- The prepared [FVS-PILOT-20261109-V0 protocol](https://github.com/search-maker/twilight-mystic-experiments/blob/science/first-visibility-blank-field-schema-20261109/review/first-visibility-pilot-20261109/PREREGISTRATION_PREPARATION.md) remains **DRAFT, NOT REGISTERED**. Do not assume the source-paper ratio registers or validates it.
- **MYSTIC controls**: #60 governs, ordinal67 spent, ordinal68 NEVER dispatch, Taylor/Jerusalem untouched, no new solver or CI workflow, no production merge. Conditional 2°–10.5° not certified minute-accurate; 10.5°–16° remains numeric **UNSUPPORTED/null**; >16° v1 OOD.
