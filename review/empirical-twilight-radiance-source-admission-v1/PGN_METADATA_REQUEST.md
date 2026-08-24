# PGN metadata resolution request — Pandora209 at Izaña

**Status:** draft only; not sent by this repository action.  
**Purpose:** resolve calibration/product metadata before any selected target sky-radiance values are opened.

Suggested primary contact: `productinfo@pandonia-global-network.org` (Calibration & Production / PGN data questions).  
API-specific fallback: `techsupport@pandonia-global-network.org`.  
Operation-file questions if needed: `operation@pandonia-global-network.org`.

## Suggested subject

Pandora 209 Izaña — calibration and absolute-radiance L1 metadata question

## Suggested message

Hello,

I am working on an independent validation of a twilight-sky radiative-transfer model and would like to evaluate whether the public Izaña Pandora 209 data can be used as an **absolute directional spectral-radiance** validation source. Before looking at any selected validation spectra, I am trying to bind the instrument metadata and calibration provenance first.

Could you please clarify the following for `Pandora209s1` and `Pandora209s2` at Izaña?

1. Which exact instrument calibration file(s) (ICF/CF), including version and validity start date, currently apply to each spectrometer and to which historical periods?
2. Which instrument operation file(s) (IOF/OF) apply over the same periods?
3. Are there public L1 measurements for Pandora 209 whose `Level 1 data type` is **2 = radiance [W/m²/nm/sr]**, rather than type 1 corrected count rate or type 3 irradiance? If yes, which measurement/sequence codes identify those radiance observations?
4. For those L1 radiance measurements, where are the absolute-radiometric calibration and per-wavelength measurement uncertainties documented?
5. Does the radiometric calibration apply independently to both spectrometers, including spectrometer 2 over the visible/NIR range, and are there wavelength or filter ranges that should be excluded from absolute-radiance use?
6. Is there a recommended public API query for retrieving only the calibration/operation metadata and file headers for Pandora 209, without downloading the spectral measurement values?
7. For sky/profile L1 radiance measurements, is the actual pointing for each exposure recoverable directly from metadata (zenith angle, azimuth angle, and whether each angle is absolute or relative to the Sun/Moon)?
8. For Pandora209 as a two-spectrometer system, are `s1` and `s2` exposures simultaneous or otherwise traceably paired to the same optical input, routine, UTC interval and pointing? If pairing is not one-to-one, what metadata should be used to associate the two spectrometers without matching on spectral values?

For context, the current public calibration report shows historical spectrometer-1 CF entries (`20220720 v5` and `20221111 v4`) and ongoing Izaña calibration-analysis sessions including spectrometer 2 session 4, but I do not want to infer the current s2 calibration/validity from that report alone.

I am deliberately keeping the validation spectra unopened until the source/calibration and comparison protocol are frozen, so metadata-only guidance would be especially helpful.

Thank you.

## Why these questions are fail-closed

The project will not treat an L1 file as absolute radiance merely because it is instrument-corrected. Blick metadata distinguishes:

- type 1: corrected count rate `[s^-1]`;
- type 2: radiance `[W/m2/nm/sr]`;
- type 3: irradiance `[W/m2/nm]`.

Only a traceably calibrated type-2 directional-radiance path can satisfy the current strict real-sky validation target without a separately reviewed conversion.

For the current frozen Level-B validation domain, zenith (`90°` target altitude) is outside support. The project will therefore admit only sky exposures whose metadata places the target altitude within the frozen `5–80°` interval and whose Sun depression is within `2–10.5°`, before any target radiance array is inspected.

No selected target spectral values should be attached to, summarized in, or used to revise this request.
