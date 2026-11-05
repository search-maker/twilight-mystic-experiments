# Prospective ESO Paranal FORS1/FORS2 raw-metadata identification (2026-11-05)

**Scope:** metadata discovery only, without a physics fit or claim of star-visibility validation. Script is executable, fail-closed and has synthetic offline fixture checks. No raw FITS frames or model outputs are downloaded or opened.

## Original source and pre-fixed targets

Patat, Ugolnikov & Postylyakov, *UBVRI twilight sky brightness at ESO-Paranal*, A&A 455 (2006), 385–393, DOI [10.1051/0004-6361:20064992](https://doi.org/10.1051/0004-6361:20064992). [Original Table 2, printed p.389](https://www.aanda.org/articles/aa/pdf/2006/31/aa4992-06.pdf#page=5). Spectra derive from actual FORS1/FORS2 *spectrophotometric standard star* observations; published Fig.9 spectra are vertically offset and cannot be used directly as absolute radiance.

| UTC Table 2 start | Solar depression | Telescope altitude | Azimuth | Lunar context |
| --- | ---: | ---: | ---: | --- |
| 1999-04-16T09:54:36Z | 14.8° | 41.1° | 233.4° | Moon ~18.77° below horizon from previous ephemeris check |
| 2003-02-28T09:45:52Z | 11.9° | 27.5° | 299.3° | Moon ~19.05° above horizon; thin 7.58%-lit crescent, not necessarily serious contamination |

These two targets were already used in the 2006 publication. Reducing the original FITS can give timestamped, directional **raw-data auditability**, **not fresh independent held-out validation** by itself. No source model is fitted or retuned against them.

## Source, programmatic interface and preregistered source-selection rule

ESO officially offers [anonymous public TAP](https://www.eso.org/cms/eso-data/programmatic-access.html) at https://archive.eso.org/tap_obs; [ESO's example notebook](https://archive.eso.org/programmatic/HOWTO/jupyter/authentication_and_authorisation/programmatic_authentication_and_authorisation.html) documents the real dbo.raw columns (mjd_obs, date_obs, instrument, tel_alt, tel_az, dp_id, access_url and available calibration/observing metadata).

The supplied Python 3 standard-library script **must** first inspect the published TAP_SCHEMA.columns, rejecting absent required fields. For each fixed UTC time, query dbo.raw for FORS1 or FORS2 within **±15 minutes**, with SELECT TOP 201; refuse >**200** rows, TAP error, overflow, ambiguous/incomplete VOTable or malformed metadata. Keep original source IDs and archive links. Select as an **unverified metadata candidate** only when all three conditions hold: |start time − published start| ≤**180 s**, |telescope altitude − Table 2 altitude| ≤**2°**, and circular |telescope azimuth − Table 2 azimuth| ≤**2°**. Classify zero, exactly one, or multiple candidates separately. No post-result enlargement of tolerances or selection by agreement with the model. An apparent unique candidate still requires verification of original FITS headers and spectrophotometric standard-star identity.

This is a *bounded source-identification operation*, not a new costly MYSTIC run; no one-shot ordinal, seeds, GitHub Actions dispatch, output fitting, unapproved spend or protected data. The normal ESO TAP interface is wholly independent of previously denied GitHub workflow mutations and must not be used as an alternative route for such mutations.

## Actual test state and limitations

At 2026-11-05 06:05 EST, Brooklyn was outside Shabbat/Yom-Tov blackout. Before executing live mode on any future date, independently verify local time and the 60-min-before/after blackout. Local Python source py_compile and **exact committed file** parser/selection fixtures **PASS** with synthetic records; test cases include exact matches, missing/duplicate records, time/alt/az mismatches, nonnumeric metadata, angle wrap, and TAP query overflow refusal. This is **not** a network test.

**Live ESO query is NOT RUN**: this container has no DNS/outbound access to archive.eso.org; web reading is adequate to verify official documentation but not to issue a live TAP POST. The true source IDs, original FITS, calibration master and coincident aerosol/meteorological records have **not** been retrieved. No independent visual-star threshold data exist from this test. (10.5,16] remains explicitly unsupported for precise star-first-visibility until independent absolute-sky and eye-threshold benchmarks pass.

Run only on a normal permitted, network-enabled research surface:

    python3 eso_paranal_raw_metadata_probe.py --fixtures
    python3 eso_paranal_raw_metadata_probe.py --live --output paranal_archive_metadata_results.json

**Follow-on independent acceptance gate (not run):** Freeze exact model SHA and atmosphere/observer conditions *before* seeing absolute raw-sky model residuals. Download original eligible published frames and related calibration files by ESO's native access_url/DataLink, hash and provenance-log sources, derive directional calibrated sky flux with uncertainty and exact filter/units, and obtain independently timestamp-matched atmosphere, Moon/cloud checks and separate visual star observations with an explicit observer F. Without these, report only source metadata or UNSUPPORTED, never exact first-visibility times. Coordinator owns integration and promotion.
