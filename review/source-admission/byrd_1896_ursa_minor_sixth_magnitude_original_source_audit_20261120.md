# Mary E. Byrd (1899) original historical visual sixth-magnitude twilight observation: admission audit (2026-11-20)

**Disposition: NEW PRIMARY PRINTED HUMAN VISUAL REPORT / NOT AN INDEPENDENT FIRST-STAR MODEL-TIMING VALIDATION.** This is NOT a prospective study, a new model prediction, or a preregistered holdout. No fitting/tuning, protected Taylor/Jerusalem material, or MYSTIC solver execution was performed.

## Provenance and what the *original book* actually records

* Mary E. Byrd, *A Laboratory Manual in Astronomy*, Ginn & Company (Boston), **1899**, printed **p.135, section 120, Observation 2**. Open-access original scan hosted by Wikimedia: https://upload.wikimedia.org/wikipedia/commons/0/06/A_laboratory_manual_in_astronomy_%28IA_laboratorymanual00byrdrich%29.pdf . The original-page *extracted text* and source title page were read directly, with printed-page landmarks. PDF page-image screenshot and raw original scan-byte SHA-256 **NOT VERIFIED** (standard source screenshot returned cache miss, direct raw download failed). This cannot be described as a completed page-image/byte-custody pass.
* **Friday October 9, 1896**, "Back Campus" in Northampton, Massachusetts, associated with Smith College: the watch reads **5:07 p.m.** for solar upper-limb disappearance **behind trees / distant hills**, **6:32 p.m.** for the reported appearance of **sixth-magnitude stars in Ursa Minor**, and **6:34 p.m.** for the Milky Way becoming distinct, followed by a 6:37 p.m. mean twilight endpoint. The publication uses initials A.E.T. for the observer.
* Distinct **July 1, 1896** mention on the same printed page has another observation of sixth-magnitude Ursa Minor stars used to mark twilight end but **NO independent first-star clock time**; it is not a second timestamped star datum.
* Book's preceding section notes artificial light, atmospheric conditions, and condition of observer's eyes as important to actual twilight length; **this is an acknowledgment, NOT logged event-specific weather, aerosol, light, or visual adaptation measurements.**

## Independent, reproducible SOLAR geometry only (no model score)

Using Python Swiss Ephemeris **2.10.03**, Moshier geocentric apparent solar equatorial position, horizontal transform without atmospheric refraction, **representative modern Smith College campus center 42.31750 N, -72.63750 W**, and ASSUMING the published watch represents **EST = UTC-05:00**, obtain:

| Watch time (interpreted EST) | Derived true Sun-center altitude | Status |
|---|---:|---|
| 17:07 apparent upper-limb disappearance behind hills | **+1.0773 deg** | Directional hill/trees horizon, NOT geometric sunset; site/time assumption unverified |
| 18:32 sixth-mag Ursa Minor group became visible | **-14.5916 deg** | Nominal solar depression 14.5916 deg; NOT exact star threshold |
| 18:34 Milky Way described as distinct | **-14.9607 deg** | Milky Way visibility, NOT first-star threshold |
| 18:37 observer's mean twilight endpoint | **-15.5139 deg** | Author's composite endpoint, NOT individual star first sighting |

Sensitivity assuming (NOT measured) clock/watch interpretation **plus or minus 10 minutes** and site representative coordinate plus/minus **0.05 deg** in both axes: calculated 18:32 nominal Sun depression spans **12.7051-16.4770 deg**. This is a *stress-test range, not observational confidence interval*. It partly crosses the v1 >16-deg OOD boundary; do not claim exact late-band identification. Historical time standard and exact 1896 observing spot are **not verified**; the 1896 optical refraction of Sun near the hills is not constrained.

## What this novel original report does and does not establish

**PASS:** original published dated human-era direct sky visibility account mentioning an approximately sixth-magnitude *group* at a clock time and meaningful twilight geometry. Its distinct historical provenance supplements other previously-audited named-star reports and directional photometer studies.

**FAIL for model-first-visibility validation:** no individually named star/HIP, no star-specific true visual magnitude or pointing direction, no preceding target-specific NOT_SEEN, no confirmation sequence, no measured atmospheric AOD/profile, clouds/skyglow or adaptation log, no verified watch timezone/uncertainty, no exact historical observing coordinates, no sealed independent prediction SHA, no raw book-image SHA. Naked-eye modality is plausible given the pedagogical context but is not explicitly certified for these individual stars. Do **not** treat an *earliest written first notice* as a timestamped observed visibility threshold or a valid model minute-error. **Admissible 10.5-16 deg individual first-star onset brackets from this source = 0; genuine forecast residual = null.** It is retrospective/public and therefore cannot become a new blind holdout.

### Provenance manifest / reproducibility

This note and accompanying script implement a **source-only** post-publication audit of one already-published record. Script records both the assumed EST geometry and a finite uncertainty grid, and never imports prediction outcomes. No source clock precision, local aerosol, or star identity is fabricated. A genuine future test requires the already-drafted observer consent, site permission, frozen exact scientifically runnable model SHA + inputs, and forecast blinding **before** real prospective first-YES / last-NO pairs. Keep 2.0-10.5 deg conditional, >10.5 through 16 deg UNSUPPORTED/null for timing, >16 deg OOD.

**Primary source:** Wikimedia-hosted 1899 scanned book, printed p.135. **Site contextual reference:** Smith College official current location [Smith College contact](https://www.smith.edu/discover-Smith/contact-Smith); numeric coordinates here are APPROXIMATE modern campus center, not an original GPS fix. **Validation status:** SOURCE_TEXT_PASS / PAGE_IMAGE_NOT_VERIFIED / FIRST_STAR_TIMING_FAIL.
