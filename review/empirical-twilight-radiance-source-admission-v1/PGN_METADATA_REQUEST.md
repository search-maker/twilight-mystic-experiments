# PGN metadata resolution request — Pandora209 at Izaña

**Status:** draft only; not sent by this repository action.  
**Purpose:** metadata-only resolution of calibration/product metadata before any selected target sky-radiance values are opened.

Suggested primary contact: `productinfo@pandonia-global-network.org` (Calibration & Production / PGN data questions).  
API-specific fallback: `techsupport@pandonia-global-network.org`.  
Operation-file questions if needed: `operation@pandonia-global-network.org`.

## Suggested subject

Pandora 209 Izaña — absolute sky-radiance calibration traceability and L1 metadata

## Suggested message

Hello,

I am working on an independent validation of a twilight-sky radiative-transfer model and would like to evaluate whether the public Izaña Pandora 209 data can be used as an **absolute directional spectral-radiance** validation source. Before looking at any selected validation spectra, I am trying to bind the instrument metadata and calibration provenance first.

Could you please clarify the following for `Pandora209s1` and `Pandora209s2` at Izaña?

1. Which exact instrument calibration file(s) (ICF/CF), including version and validity start date, currently apply to each spectrometer and to which historical periods?
2. Which exact instrument operation file(s) (IOF/OF) apply over the same periods?
3. Are there public L1 measurements for Pandora 209 whose `Level 1 data type` is **2 = radiance [W/m²/nm/sr]**, rather than type 1 corrected count rate or type 3 irradiance? If yes, which measurement/sequence codes identify those radiance observations?
4. Most importantly, for those type-2 sky-radiance measurements, **what establishes the absolute radiance scale**? Is the sky-radiance response calibrated against an integrating sphere, STAIRS or another traceable radiance standard/reference, or is it derived by applying the instrument's irradiance calibration to diffuse-sky measurements?
5. If a laboratory/transfer radiance standard is used, what calibration certificate/file/method and metrological traceability chain apply specifically to Pandora209 s1 and s2, and over what validity periods?
6. If a field absolute-radiance calibration is used instead, does it determine the scale by comparison with a radiative-transfer simulation of sky/twilight radiance? If so, which RT model and atmospheric inputs are used? I need to distinguish an independent radiometric calibration from a model-derived scale because the intended validation is itself a test of a twilight radiative-transfer model.
7. What uncertainty components apply to the absolute sky-radiance product: common-mode absolute-scale uncertainty, wavelength-dependent relative-response uncertainty, repeatability/noise, stray light, field-of-view effects and pointing uncertainty? Are wavelength-to-wavelength correlations or common calibration components documented?
8. Does the absolute radiance traceability apply independently to both spectrometers and across the full useful visible range needed here (approximately 380–780 nm)? Are there wavelength/filter ranges that should be excluded from absolute-radiance use?
9. Is there a recommended public API query for retrieving only calibration/operation metadata and file headers for Pandora 209, without downloading the spectral measurement values?
10. For sky/profile L1 radiance measurements, is the actual pointing for each exposure recoverable directly from metadata (zenith angle, azimuth angle, and whether each angle is absolute or relative to the Sun/Moon)?
11. For Pandora209 as a two-spectrometer system, are `s1` and `s2` exposures simultaneous or otherwise traceably paired to the same optical input, routine, UTC interval and pointing? If pairing is not one-to-one, what metadata should be used to associate the two spectrometers without matching on spectral values?

For context, the current public calibration report shows historical spectrometer-1 CF entries (`20220720 v5` and `20221111 v4`) and ongoing Izaña calibration-analysis sessions including spectrometer 2 session 4, but I do not want to infer the current s2 calibration/validity from that report alone.

I also found historical PGN/DIVA documentation from 2020 stating that Pandora instruments were routinely calibrated in absolute **irradiance**, while the LuftBlick laboratory was not yet equipped for absolute **sky-radiance** calibration requiring a radiance standard/integrating sphere. I found later NPL work proposing SI-traceable Pandora characterization with STAIRS, but I have not found public documentation showing whether and how that capability became part of the operational Pandora/PGN calibration chain. Clarification of the current situation for Pandora209 would therefore be particularly helpful.

I am deliberately keeping the validation spectra unopened until the source/calibration and comparison protocol are frozen, so metadata/calibration-document guidance without selected sky-radiance values would be ideal.

Thank you.

## Why these questions are fail-closed

The project will not treat an L1 file as independently calibrated absolute radiance merely because it is instrument-corrected, labelled `radiance`, or expressed in `W/m²/nm/sr`. Blick metadata distinguishes:

- type 1: corrected count rate `[s^-1]`;
- type 2: radiance `[W/m²/nm/sr]`;
- type 3: irradiance `[W/m²/nm]`.

Type 2 is necessary for the intended source, but the strict validation additionally requires an absolute sky-radiance scale traceable through a calibration chain independent of the twilight radiative-transfer model being tested.

A field calibration that obtains the absolute scale by matching twilight measurements to an RT simulation can be useful scientifically, but it cannot serve as the independent absolute calibration for this particular validation without creating circular/model-dependent evidence.

For the current frozen Level-B validation domain, zenith (`90°` target altitude) is outside support. The project will therefore admit only sky exposures whose metadata places the target altitude within the frozen `5–80°` interval and whose Sun depression is within `2–10.5°`, before any target radiance array is inspected. Exact frozen base-model support (`nearest V1_IDW_COS training distance <= 0.60`) must also hold before target-value opening.

No selected target spectral values should be attached to, summarized in, or used to revise this request.
