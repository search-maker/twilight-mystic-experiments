# Independent near-new-Moon SG_088 late-twilight **zenith** measurements (2026-11-05)

**STATUS: New direct measured-source time series, exploratory only; NOT an accepted Model-v1 benchmark.** No protected dataset, fit, solver run, workflow dispatch, model promotion, merge or deployment. This is an additive science-only study; the coordinator owns integration.

## Authentic source and non-cherry-picked retrospective slice

- Native original CSV, Zenodo EELabs, *SG - June 2023*, DOI [10.5281/zenodo.8104891](https://doi.org/10.5281/zenodo.8104891): [SG_June_2023.csv](https://zenodo.org/records/8104891/files/SG_June_2023.csv?download=1); published MD5 `e39d6c8a63177b5f3412a09f8bd7a847`.
- **24 consecutive time-slot measurements** from SG_088: June 17, 18, 19 and 20 UTC, `03:30`–`03:55` at 5-minute cadence, six per night. Explicit 0-based source line IDs are preserved in `sg088_jun17_20_24rows.csv`. All four nights kept, even the moon-present and nonmonotone cases. Date selection is *retrospective*, subsequent to inspection of June 2; **not an unbiased/blind preregistered validation sample**.
- Full-file native byte MD5 was **not independently recomputed** on this surface; the published MD5 is a metadata reference only. Data were visually transcribed from the live Zenodo text view. No one should claim raw-file hash custody.

## Executable physical-context QC

Run `python sg088_jun17_20_geometry_qc.py` after installing `pyswisseph` (Moshier ephemeris). It computes geometric topocentric Sun/Moon altitudes across broad assumed position bounds 32.0–32.4 N / 111.1–110.5 W and elevation 0–2500 m. It asserts all 24 points have solar depression in **(10.5,16] degrees** at *all* box corners, and classifies as conservatively moon-free only when Moon geometric altitude is **below -5° for the entire box**.

Observed source plus locally executed QC:
- **June 17:** 6/6 moon-free; lunar upper altitude over box < -18.5°; sky magnitude 18.708→19.444.
- **June 18:** 6/6 moon-free; lunar upper altitude over box < -9.4°; magnitude 18.039→18.227, with intra-night *brightening* as Sun descended (including 03:50→03:55, **0.411 mag, 1.460× flux**).
- **June 19:** lunar geometry borderline just below local horizon early in window, **excluded by strict -5° rule**; retained in fixture.
- **June 20:** moon above horizon, 0/6 accepted by moon-free screen; retained in fixture.

At the same six UTC slots June 18 is **1.70–3.07 times brighter** than June 17 in the *same SG-WAS instrumental band*, despite both days satisfying the strict lunar geometry screen. This is source-observed between-night variability, **not** measurement of solar-only physical sky uncertainty and not necessarily due to aerosols: clouds, local artificial light, sensor/environment changes, geographic mismatch and spectral response remain uncontrolled. No instrumental formal `mag_err` accounts for these systematic variables.

## Hard domain and admission boundary

This is a **zenith-pointing 90°** SG-WAS broad-band night-sky brightness sensor series, whereas late-v1 local ray-domain ends at **80°**; therefore **no direct numeric MYSTIC v1 benchmark** and no precise first-star times. Site coordinates and cloud/aerosol profiles are **not authenticated**. A moon below -5° does not prove absolute zero lunar-scattered contribution. There are no human star-detection records, calibrated model passband conversion or matched four-component sky decomposition. Comparisons to predictions must remain blocked until actual site, angular passband, atmosphere, component terms, model head SHA and a *prospectively frozen* test are established.

**Next permitted science:** secure verified SG_088 instrument position/field-of-view and coincident cloud/AOD/meteorology, or recover directional (altitude <=80°) time-stamped calibrated spectra with measured aerosol profile for an independent no-retuning benchmark. Do not retune on Taylor/Ann Arbor or Jerusalem holdouts.
