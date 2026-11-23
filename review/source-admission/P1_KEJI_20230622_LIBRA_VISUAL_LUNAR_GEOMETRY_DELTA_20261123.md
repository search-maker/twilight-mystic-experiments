# P1 original 2023-06-22 Big Muise, Libra visual observations — independent contextual geometry admission, NOT first onset
**Review date:** 2026-11-23 (09:05 America/New_York); **classification:** RETROSPECTIVE HUMAN VISUAL CONTEXT / **FIRST-SIGHTING VALIDATION NO-GO**. This is a new, bounded delta from earlier 2023 log review; it does not re-admit the previously rejected alpha Cen claim.

## Original evidence and provenance
- Original first-person report by Judy Black (dated 2023-06-22, source updated 2024-09-20): https://sciencedowneast.com/joomla/index.php/observations/general-session-june-22-2023 . Under **22:30 ADT** the observing log labels **Equipment: Visual** and notes **Brachium (sigma Librae)** and **Zubeneschamali (beta Librae)** in a near-vertical arrangement, both faint. A shared equipment header also lists 10x42 binoculars, so do not extend any visual modality to other sections without checking their own labels. Under 22:17 it notes Denebola as newly noticed; under 22:38 it states all seven Big Dipper stars now visible, without seven separately timed first-onsets.
- Catalog values used solely as approximate input: sigma Lib **V≈3.29**, J2000 15h04m04s, −25°16′54″ (https://theskylive.com/sky/stars/brachium-sigma-librae-star); beta Lib **V≈2.61**, 15h17m00.41s, −09°22′58″ (https://theskylive.com/sky/stars/zubeneschamali-beta-librae-star). Independent catalogue/version and exact apparent coordinates are not verified.
- Site 15 Big Muise waypoint **44.38217° N, 65.24302° W, nominal 5m** from an older GPX-derived **proxy**, not surveyed observer eye location. Historical ADT = UTC−03.
- Weather: source says **no clouds**, but **no numerical transparency, aerosol/AOD, contemporaneous directional sky brightness, or adaptation protocol**. One SQM **21.63 mag/arcsec² at 00:30 ADT June23**, two hours *after* the 22:30 visual section and not a target-direction or coincident measurement.

## Independent bounded replay — one night, not multiple validation samples
Executed twice to identical JSON using Python / Swiss Ephemeris **2.10.03**. Calculations: true geometric solar-center altitude (pressure=0), topocentric geometric Moon, approximate precessed catalogue stellar positions (no refraction/extinction), all azimuths true north clockwise. **Not a predictive model comparison.**

| Local June22 ADT | UTC June23 | Sun below geometric horizon | Additional checked observation |
|---|---|---:|---|
| 22:17 | 01:17Z | 9.9668° | Denebola section, onset not bracketed |
| **22:30** | **01:30Z** | **11.4976°** | **sigma Lib** alt **20.2249°**, az **181.7936°**; **beta Lib** alt **36.1363°**, az **178.3582°** (consistent nearly vertical pairing) |
| 22:38 | 01:38Z | 12.3992° | Big Dipper collective visual note, not 7 individual onsets |
| 00:30 June23 | 03:30Z | 21.1069° | SQM 21.63, non-contemporaneous, direction unknown |

At **22:30 ADT**, topocentric Moon true altitude **19.1192°**, geocentric illuminated fraction **0.209**. Thus this event is **not moon-free**, an important confound even with zero clouds. ±0.5° site latitude, ±0.5° longitude and ±2 min clock sensitivity yields solar depression **[10.6560°,12.3401°]**, still inside (10.5°,16°]; it does *not* address sighting-time uncertainty or prove any precise onset.

## Validation decision and immutable limitations
**Admit only** two retrospective **visual field mentions** with separate target IDs and approximate geometry/epoch; **DO NOT count either as an observed first-NOT_SEEN→SEEN event**, as no pre-detection target-specific checks, time-specific adaptation log, matched atmosphere/cloud radiance, directional SQM or prediction-blind consent exists. The **22:30 value is a section timestamp**, not an independent per-star detection timestamp. One site-night, **0 eligible P1 onset brackets, 0 scoreable model errors**, no scientifically approved frozen prediction-model SHA. The scope of [10.5°,16°] **remains unsupported for first-visibility timing**; [2°,10.5°] only conditional support and >16° out of v1 distribution. No post-hoc fitting, no Taylor/Ann Arbor/Jerusalem protected samples opened.

Prior **same log alpha Cen identification** was independently rejected by horizon geometry in #152 issue comment [7030104498](https://github.com/search-maker/starsvisibility/issues/152#issuecomment-7030104498); this report does not alter that exclusion or infer that every other claim is invalid. Report original text carefully with its known identity conflict.

## Reproduction receipt and next action
Local stand-alone fixture: `p1_2023_libra_source_geometry.py` (SHA256 `aef005a8b5db3108b973d6f013021bf700a7a85c0d7bb19d2e0098764788be91`); generated JSON SHA256 `4831621b33a43a4c3708d51a799714c4debdd2d22ed31c959ee85c23b1003362`. Two replays byte-equal, seven explicit numerical assertions passed. These hashes refer to working-run local artifacts, not repository files, and reproducibility depends on Swiss Ephemeris 2.10.03 and declared approximate input coordinates.

**Coordinator/authorized outreach owner handoff:** only using existing authorized channels, request original raw observer timestamps and previous NOT_SEEN attempts (if actually recorded), target IDs, visual/binocular field-specific distinctions, exact site and horizon, SQM field of view, any atmosphere records and consent for a *future* blind observation; do not invent missing data or solicit outside the approved owner. Before new prospective enrollment freeze approved model SHA, source/input versions, selected cases/criteria, error metrics, acceptance/stopping and budget, blind prediction receipts; protect all holdouts. No MYSTIC dispatch or spent ordinal reuse.