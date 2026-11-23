# Source-admission: Upgren (1991), independent human naked-eye *dark-night* horizon visibility control — **NOT twilight first onset**

**Review date and safety:** 2026-11-23 08:04 America/New_York, Monday 13 Kislev 5787, Brooklyn (no Shabbat/diaspora Yom Tov blackout). Fresh scientific #152 and binding #60 reviewed; main SHA at reading: twilight `6cd7c075766fe0c86bc7561ec205a3f9120fd1fb`, stars `c945c07a6437bcdd689e3e4bd770aea56e2f37de`. No protected holdout or MYSTIC/ordinal activity.

## Primary original source, and what it actually measures

A. R. Upgren (1991), **“Night-Sky Brightness from the Visibility of Stars near the Horizon,”** *Publications of the Astronomical Society of the Pacific* **103**, 1292–1295. [Full original journal scan hosted via NASA ADS](https://adsabs.harvard.edu/pdf/1991PASP..103.1292U). This paper reports *actual unaided human observation*, not instrumental point-source detection. It covers clear, moonless dark nights predominantly within 30 minutes of midnight from 1977–1991; *not twilight* and *not a timed first-visibility search*. The field site was Laurel Hill, Middletown, Connecticut (published latitude 41°31′39″ N; longitude 72°40′57″ W; elevation 67 m). Thirty-eight southern stars (about decl. −30° to −45°, V below 3.7) were screened. Human ratings: **0** invisible, **1** flickering, **2** visible after searching, **3** obvious after adaptation. Six downgraded ratings in multi-year comparison are reported; this is a historical/condition-sensitive summary, not a synchronized observational panel fit.

The primary journal scan was opened for text extraction; screenshot/page-image requests and downloading original PDF bytes failed on the available surface. Therefore `raw_original_pdf_sha256=null`, `page_image_verified=false` and Table 2 figures below remain **provisional text transcription**, not fully authenticated page-image custody. No observer notebooks/individual timed events obtained.

## Reproducible bounded Table 2 arithmetic — explicitly **historical Schaefer comparator**, not project-model error

Published Table 2 gives zenith distances for four apparent limiting magnitude bins; altitude is exactly `90−z`. The comparator column is attributed to Schaefer in the *paper*, not a StarsVisibility result.

| V bin | Published Upgren observed z | Published Schaefer z | Observed altitude | Comparator altitude | Observed minus historical comparator |
|---:|---:|---:|---:|---:|---:|
| 2.0 | 86.5° | 85.0° | 3.5° | 5.0° | −1.5° |
| 2.5 | 85.0° | 84.0° | 5.0° | 6.0° | −1.0° |
| 3.0 | 82.0° | 82.5° | 8.0° | 7.5° | +0.5° |
| 3.5 | 77.5° | 79.0° | 12.5° | 11.0° | +1.5° |

Simple four-bin historical comparator altitude MAE = **1.125°**, **not** a model first-sighting time MAE. The 3.5°-altitude first row falls **below** a proposed 5° target-altitude admissibility floor; three remaining bins are at least 5°. These are summary bins, not four independent P1 observing nights. No Schaefer prediction or limit from this table should be treated as frozen preregistered StarsVisibility outputs.

The paper compares nocturnal zenith brightness ~20.5 mag arcsec⁻² at Laurel Hill with ~18.5 mag arcsec⁻² at Wesleyan/Van Vleck Observatory 3.56 km away; the 2.0 mag contrast implies a **6.30957×** relative zenith brightness ratio under direct magnitude conversion. These zenith measures **cannot** be substituted for the southern target-direction brightness and **cannot** be used to validate human twilight first appearance. There is no demonstrated matched-per-star simultaneous SQM/AOD/atmosphere metadata.

## Provenance and admission decision

- `HUMAN_NAKED_EYE_DETECTION=YES`; `INSTRUMENT_ONLY=NO`; `DARK_NIGHT_HORIZON_COMPARISON=PROVISIONAL_CONTEXT_ONLY`.
- `FIRST_TWILIGHT_NOT_SEEN_TO_SEEN_BRACKETS=0`; `ORIGINAL_PER_EVENT_UTC=UNAVAILABLE`; `SUN_DEPRESSION_AT_EVENT=NOT_APPLICABLE/UNRESOLVED`; `PER_STAR_LINE_OF_SIGHT_CLOUD_AOD_SKYGLOW_ADAPTATION_METADATA=INCOMPLETE`.
- `TIMED_FIRST_ONSET_VALIDATION=FAIL/NO_GO`; `STARS_VISIBILITY_PREDICTOR_SHA_SCIENTIFICALLY_LOCKED=null`; `MODEL_TIMING_ERROR_MINUTES=null`.
- Do not enlarge the validated domain. The existing [2,10.5]° remains conditional only; (10.5,16]° unsupported/null and >16° out of v1 domain. This *nighttime* source cannot fill that gap.
- No protected Taylor/Ann Arbor/Jerusalem data inspected; no old calibration or holdout reclassification, refit, MYSTIC dispatch, paid action, observer message, merge or deployment.

**Offline reproduction**: minimal standard-library Python fixture `upgren_1991_table2_control.py`, SHA256 `539f5bd69fe395f914363184f422dac6a511ad7a91bc453898365f7f0f7cd6f1`; emitted JSON SHA256 `575f0d791035be37de876a4a269b44e427b7c18651fbb69503b42623d73115f5`. Five bounded numeric/source-admission assertions passed. Fixture transcribes published aggregate numerical cells and computes altitude, historical comparison, zenith contrast, not a scientifically validated prediction. The fixture and resulting JSON are local conversation artifacts, not source PDF custody or model results.

**Actionable scientific handoff:** Coordinator or previously authorized outreach owner only may ask whether the original per-star notebooks still exist with direct observation timestamps, exact star identity, explicit failed attempts, exact field site, atmosphere/skyglow and adaptation protocol. Without those, keep as descriptive/low-horizon benchmark. Highest priority remains original **prospective** first-NO/confirmed-YES observer records after consent, site, stars, model *exact runnable SHA*, prediction blind custody, metadata fields, metrics/stopping/budget preregistration; no existing draft automatically registered or executed.