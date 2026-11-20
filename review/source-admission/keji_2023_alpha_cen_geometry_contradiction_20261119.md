# Independent historical first-sighting source integrity check — Kejimkujik 2023, 2026-11-19

**Classification: ORIGINAL-LOG GEOMETRY CONTRADICTION / EXCLUDE THE CLAIMED α CENTAURI IDENTIFICATION, NOT THE ENTIRE OBSERVER OR ALL OTHER NIGHTS.** This is a new observational **provenance and sky-geometry QC result**, not human-visibility model validation, not a preregistered prediction test, not a MYSTIC run.

## Immutable references and quoted claim

1. Published original observation log, Judy Black, "General Session - June 22-23, 2023 (6th Annual Big Muise Island Star Party)", site 15, Big Muise Island, Kejimkujik National Park, Nova Scotia; source created 2023-06-22, page updated 2024-09-20: https://sciencedowneast.com/joomla/index.php/observations/general-session-june-22-2023 . In the **10:51 PM** "Centaurus" passage the observer lists **α Centauri** among the purportedly seen Centaurus stars; the passage lists equipment "Visual, Binoculars". Earlier first-appearance language occurs at **9:48 PM Arcturus** and **10:05 PM Big Dipper handle**; method for these particular reports is not resolved by the page's shared Visual+Binoculars header. No prior time-stamped non-sightings are given. SQM **21.63** was recorded only at **12:30 AM**, not at the earlier apparent onsets.
2. Parks Canada official inland park entrance GPS **44.43829° N, 65.20860° W** (a proxy, **NOT** claimed to be site 15's GPS): https://parks.canada.ca/pn-np/ns/kejimkujik/visit/directions . The observations are in the INLAND Kejimkujik park, not the separate Seaside park.
3. SIMBAD α Cen astrometric position (ICRS J2000): declination **−60°50′02.3″**: https://simbad.harvard.edu/simbad/sim-id?Ident=%2A+alf+Cen&Name=%2A+alf+Cen&Radius=submit%3Dsubmit .
4. Independent context: Menkent (θ Centauri) declination about **−36°22′12″**; a northern observer can genuinely glimpse northern Centaurus while α Centauri remains permanently below the horizon. This **does not** make the entire Centaurus report physically impossible.

## Bounded independently calculated visibility screen (geocentric; no weather/model parameters)

For positive latitude φ and stellar declination δ, geometric maximum altitude at upper culmination is

`h_max = 90° − abs(φ − δ)`.

Using only the published entrance proxy and SIMBAD position:

- α Cen: φ = 44.43829°, δ = −60.83397222° -> `h_max = −15.27226222°` (more than **15° BELOW** a mathematically level horizon, even at its highest).
- Visibility at any northern latitude requires `φ <= 90° + δ = 29.16602778°N`. Kejimkujik is more than 15 degrees farther north.
- Even substituting a deliberately *southern* latitude **43.0°N** — far south of the actual inland site — gives `h_max = −13.83397222°`. Small site-location, clock, refraction, horizon, epoch or instrument uncertainties cannot bridge that gap.
- θ Cen comparator: δ ≈ −36.36995556° gives `h_max ≈ +9.19175444°` at the entrance proxy; possible geometry only, NOT verification of the specific 10:51 PM report.

The calculation is reproducible with `python3 -c 'phi=44.43829; delta=-(60+50/60+2.3/3600); print(round(90-abs(phi-delta),8))'` -> `-15.27226222`. This is a position/celestial-sphere identity check, not a solar-depth or first-visibility timing calculation.

## Scientific evidence disposition

- **α Cen at Kejimkujik 2023: GEOMETRY_IMPOSSIBLE / IDENTITY_CONFLICT**, not an admitted sighting; plausible causes include mistaken star ID, chart transcription/label, or prose error. Actual cause unknown. Ask author to clarify privately, without assuming misconduct.
- **Other stars/2023**: not automatically rejected. The log has several specific apparently visual first-appearance descriptions (Arcturus 9:48, three Big Dipper handle stars 10:05); these are historical context only until original identity, instrumental modality, checking-before-seen, exact site, atmosphere and clock are established. This source does not create a valid bracket [NOT_SEEN, SEEN] or blind validation item.
- **Previously logged 2017/2019/2022/2025 nights**: not invalidated by a different 2023 claim; instead independently run a plausibility and star-identity/alt-az screen on every candidate before any validation admission, without tuning the model.
- **Raw original bytes and hash**: NOT_ACQUIRED. This audit is based on a directly read original public **published HTML** page, not custodial access to handwritten/audio field records. Do not fabricate original SHA-256.
- **Real physical validation still blocked**: accepted prediction SHA not locked, zero consented prospective observers or confirmed site permissions, prediction manifest not frozen; no AOD/meteorology matching this 2023 log; [10.5°,16°] remains unsupported. The official published claim is not human first-sighting ground truth.

## Coordinator / outreach handoff

1. Add a **hard automatic geometric horizon and star-ID eligibility check** to future original-source admission before first-sighting model scoring (predeclare it in enrollment/registration; do not change criteria after outcomes). Preserve rejected raw evidence.
2. If existing outreach owner contacts Judy Black about originals, **add one narrow neutral question**: in the 2023 June 22/23 Kejimkujik 10:51 PM Centaurus entry, could α Cen have been a chart label or mistaken identification? Confirm exact site and modality for the earlier appearance times. Use the **existing unsent draft or owner**, no duplicate message, paid commitment, or unapproved send.
3. Continue FIRST priority: consent + weekday site access + original NOT_SEEN/SEEN timestamps; scientifically accepted model SHA and blinded prediction commitments must be frozen **before** any true prediction-validation outcomes.

**No protected Taylor/Jerusalem records opened. No ordinal67/68 reuse, new dispatch, model fitting, release claim, or observer contact.**
