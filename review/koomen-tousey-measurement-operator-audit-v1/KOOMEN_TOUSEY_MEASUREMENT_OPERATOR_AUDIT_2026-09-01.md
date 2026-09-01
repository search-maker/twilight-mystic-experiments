# Koomen/Tousey historical measurement-operator audit

**Date:** 2026-09-01  
**Scope:** research/review only; follow-up to completed Issue #828; no fitting, no solver retuning, no production/Level-B or human-vision change.

## Bottom line

The historical Koomen observable used at the zenith is **not a hemispheric or SQM-like wide-field quantity**. The 1952 primary paper describes a recording photometer with a **nominal circular 1.5-degree-diameter field of view**, swept along a meridian through the zenith. Its output `B` is the calibrated brightness of a local place in the sky, published in candles per square foot. The paper separately measures planar illumination `E` on opal glass and states that `E` can be obtained by integrating `B` over the sky; this independently rules out interpreting `B` itself as a hemispheric integral.

However, the historical operator is **not completely reconstructable from the recovered sources**. The source gives the nominal 1.5-degree field but not the within-field angular weighting/vignetting function; it targets the light-adapted-eye spectral response but does not provide the exact combined response curve in this paper; it explicitly says a later-twilight color/Purkinje correction was needed but was not applied; the 12-second full-meridian sweep is known but the detector/recorder time constant or exact effective integration time is not; no numerical absolute-calibration uncertainty is stated; and `H` is defined only as solar altitude above/below the horizon without stating geometric versus apparent/refracted convention.

Therefore Issue #828's **-0.2826 mag original-wide-SQM minus true-point-zenith diagnostic must remain a same-atmosphere SQM operator diagnostic, not an attribution of about 72% of the Taylor-Koomen offset to instrument field of view**. The historical Koomen field is narrow enough that a point-zenith quantity may be a useful approximation, but the source does not support silently equating the two, and the Taylor-versus-Koomen offset is also a cross-site/cross-season/reduced-data comparison rather than a controlled two-instrument experiment.

## 1. Primary sources and exact locations

### 1.1 Source measurement paper

M. J. Koomen, C. Lock, D. M. Packer, R. Scolnik, R. Tousey, and E. O. Hulburt, **"Measurements of the Brightness of the Twilight Sky,"** *Journal of the Optical Society of America* **42**(5), 353-356 (1952), DOI `10.1364/JOSA.42.000353`.

- **p.353, instrument paragraph:** nine-stage RCA Type P22 photomultiplier; ground glass and green filter; 0.6-cm circular aperture at the lens focus; the paper explicitly says the **"field of view was therefore 1.5 degrees in diameter"**; the green filter was intended to make the response that of the light-adapted eye; the instrument automatically swept any meridian from horizon to horizon through the zenith in 12 s; a DC amplifier/Brush recorder followed the sweep.
- **p.353, calibration paragraph:** daylight-sky response was compared with a calibrated blue-filtered Macbeth illuminometer. Relative response after changes in PMT voltage, amplifier gain, and lens aperture was transferred with a standard tungsten lamp attenuated in a known nonselective manner. A luminous radium-phosphor button was used as an in-series calibration check.
- **p.353, spectral limitation paragraph:** the authors state that values were photometrically correct in the first half of twilight, but that the second half required a color/Purkinje correction that they did not apply because the needed sky spectral distributions were not known exactly.
- **p.353, observing sample:** Sacramento Peak: seven clear/cloudless/moonless evenings in May-June 1951; Maryland: January-March 1951. Reported clear-day vertical transmission for sunlight viewed with the light-adapted eye was 85-90% at Sacramento Peak and 75-85% in Maryland.
- **p.354, Tables I and II and geometry paragraph:** `B` is the brightness of the place in the sky in candles per square foot; historical `H` is solar altitude (positive above, negative below horizon); sky position is altitude `P` and bearing `Z` from the Sun's direction.
- **pp.354-355, reduction paragraph/Fig. 1:** more than 1000 `B` values at each station were read from the records and plotted against `H`; smooth curves were drawn through observed points; **Tables I and II were read from those curves**. Thus the published table entries are reduced/smoothed historical values, not raw individual photometer samples.
- **p.356, Table III discussion:** `E` is illumination on a flat opal-glass surface. The paper says `E` may be obtained by suitable integration of `B` over the sky and reports checks by integrating Table-I `B`. This separates local sky brightness `B` from broad angular illumination `E`.

For a zenith Koomen series, the directly relevant published source cells are the `P=90 degrees` entries of **Table I (Sacramento Peak)** and **Table II (Maryland)** at the tabulated solar altitudes. `Z` is directionally degenerate at the zenith; the tables repeat the same zenith value across their `Z` blocks.

### 1.2 Spectral-correction reference cited by the instrument paper

Koomen et al. p.353 footnote 6 cites W. S. Plymale, *Review of Scientific Instruments* **18**, 535-539 (1947), **"Filters for Spectral Corrections of Multiplier Photo-Tubes Used from Scotopic to Photopic Brightness Levels."** The work concerns correction filters for RCA 1P21/1P22 tubes over the Purkinje range. The exact filter-glass identity/combined response curve used in the 1952 twilight photometer has not yet been recovered with enough source binding to claim an exact spectral operator.

A related later paper, W. S. Plymale and G. T. Hicks, **"Physical Photometry in the Purkinje Range,"** JOSA **42**, 344-348 (1952), DOI `10.1364/JOSA.42.000344`, documents the difficulty of heterochromatic low-luminance photometry and shows 1P22/filter correction behavior. It supports the importance of the spectral issue but is not treated here as proof of the exact 1952 twilight filter curve.

### 1.3 Related earlier NRL sky photometer is not the same operator

D. M. Packer and C. Lock, **"The Brightness and Polarization of the Daylight Sky at Altitudes of 18,000 to 38,000 Feet above Sea Level,"** JOSA **41**, 473-478 (1951), DOI `10.1364/JOSA.41.000473`, describes an aircraft sky-photometer system with its own circular-aperture field (reported there as about 2.5 degrees). That is useful historical context but **must not be substituted for the explicitly stated 1.5-degree 1952 twilight field**.

### 1.4 Downstream visibility paper

R. Tousey and M. J. Koomen, **"The Visibility of Stars and Planets During Twilight,"** JOSA **43**, 177-183 (1953), DOI `10.1364/JOSA.43.000177`. Its abstract and Table I make clear that it calculates stellar visibility from known twilight sky brightness, atmospheric transmission, and eye sensitivity. It is downstream use of the brightness data, not a replacement description of the 1952 source instrument.

### 1.5 Taylor use of Koomen

Aster G. Taylor, **"The Astronomy of Halakhic Nightfall: Calculating Ts'eit HaKokhavim and Motsa'ei Shabbat,"** arXiv:2608.04064v1 (2026):

- Sec. III states that the twilight calculation interpolates the empirical Koomen data.
- The two Koomen sites (Maryland 30 m, Sacramento Peak 2800 m) are elevation-corrected using Taylor Eq. (2), then **averaged to obtain `B0`**, after which the requested observer-elevation correction is applied.
- Appendix A / Fig. 4 is explicitly a **"Zenith Brightness Comparison"**.
- Taylor's Ann Arbor measurements use a Unihedron SQM described as measuring within 60 degrees of the zenith, sampled every minute, with stated uncertainty +/-10% or +/-0.10 mag/arcsec^2; solar altitude was calculated with PyEphem.
- Appendix A then compares the Ann Arbor SQM measurements to the elevation-adjusted Koomen-derived model and says the Koomen interpolation is used throughout the work.

This means the plotted/modelled "Koomen" curve in Taylor is already a transformed cross-site historical product, not a simultaneous narrow-photometer reading at Ann Arbor.

## 2. Reconstructed historical measurement operator

| Component | Best-supported reconstruction | Status |
|---|---|---|
| Observable class | Local sky brightness/luminance `B`; finite aperture, not hemispheric | **known** |
| Nominal angular field | Circular, **1.5 degrees diameter / 0.75 degrees radius** | **known** |
| Within-field acceptance | Exact radial weighting, vignetting/baffling response | **unknown** |
| Pointing at zenith | Center crosses `P=90 degrees` during meridian sweep; `Z` degenerate at zenith | **known** |
| Scan | Horizon-to-horizon through zenith in **12 s** | **known** |
| Effective integration/time constant | Detector/recorder time constant and exact effective sample exposure | **unknown** |
| Detector | Nine-stage RCA Type P22 photomultiplier | **known** |
| Spectral shaping | Ground glass + green filter; intended light-adapted-eye response | **partly known** |
| Exact spectral response | Exact combined PMT/filter/optics relative response curve | **unknown here** |
| Late-twilight spectral correction | Needed by authors in second half of twilight; **not applied** | **known limitation** |
| Absolute calibration | Clear daylight sky versus calibrated blue-filtered Macbeth illuminometer; tungsten transfer calibration; radium check source | **known method** |
| Numerical calibration uncertainty | No explicit number recovered | **unknown** |
| Published units | `B` in candles per square foot | **known** |
| Table reduction | Smooth curves through >1000 record values per station; Tables I/II read from curves | **known** |
| Solar altitude `H` | Defined as altitude above/below horizon | **known definition** |
| Geometric vs apparent/refracted `H` | Not stated in recovered source | **unknown; no residual-driven inference allowed** |

The machine-readable partial declaration is `koomen_1952_zenith_operator.partial.json`. Its incomplete fields are deliberate evidence, not placeholders to be filled by convenience.

## 3. Correct like-for-like mathematical observable

Let `L_lambda(Omega,t)` be MYSTIC spectral radiance and let the historical instrument have angular acceptance `A_K(Omega)`, spectral response `R_K(lambda)`, and effective temporal/scan response `T_K(t)`. The quantity comparable to one historical instrument sample at zenith is of the form

```text
Q_K = C_K [ integral T_K(t) integral A_K(Omega)
              integral R_K(lambda) L_lambda(Omega,t) d lambda d Omega dt ]
```

with the normalization implied by the calibrated luminance/brightness measurement and with `C_K` reproducing the historical photometric calibration/units. For the zenith table datum, `A_K` is centered on zenith with support nominally inside the 1.5-degree circular field. The exact angular weighting is not known, and the exact late-twilight spectral operator is not known.

The *published table value* adds another reduction layer: it is a value read from a smooth `B`-versus-solar-altitude curve built from many historical record values, not a single instantaneous raw datum. A strict comparison to a table value therefore also inherits historical night-to-night atmospheric/sample variability that cannot be reconstructed from the table alone.

### Consequence for MYSTIC

- **Do not use Taylor's original-wide-SQM synthetic operator as the Koomen operator.** It is much broader and has a different spectral/calibration chain.
- **Do not silently use a mathematical point ray as an exact Koomen operator.** A point ray is an approximation to a narrow 1.5-degree field, not the documented instrument itself.
- **Do not invent a 1.5-degree top-hat.** The nominal support is known but the weighting is not.
- An exact research-only Koomen forward operator should be evaluated only after the missing angular/spectral/time-response information is recovered, or after a separately preregistered uncertainty-bound experiment that explicitly ranges over all scientifically justified response families rather than choosing one from the Taylor residual.

No new Koomen MYSTIC magnitude correction is reported in this audit because the historical acceptance function is not sufficiently reconstructed to justify one. This is a deliberate fail-closed result.

## 4. Taylor-specific consequence for the approximately 0.39-mag offset

Three quantities must remain distinct:

1. **Issue #828 same-atmosphere operator diagnostic:** original-wide-SQM synthetic magnitude minus true-zenith-direction synthetic magnitude = about **-0.2826 mag** over the tested interval (with the #828 paired-MC uncertainty already recorded there).
2. **Historical Koomen operator:** nominal 1.5-degree finite-aperture photopic recording photometer, with incomplete angular/spectral/temporal provenance as documented above.
3. **Observed Taylor-vs-Koomen absolute difference:** comparison of Ann Arbor wide-SQM measurements to a Koomen-derived historical curve made from two other sites/seasons and transformed by Taylor's elevation correction and averaging.

Therefore the approximately 0.39-mag absolute difference **cannot presently be decomposed causally into an instrument term plus an atmospheric/model term with defensible percentages**. In particular, `abs(-0.2826)/0.39` is only a numerical scale ratio. It is **not** an explained fraction of the Koomen offset.

The audit does establish a narrower qualitative point: Taylor's SQM and Koomen's source photometer have materially different angular operators, so a like-for-like comparison must not compare the SQM integral directly to a nominal point/Koomen zenith quantity without carrying the operator difference. But the exact Koomen correction remains unresolved.

Uncertainties must stay separated:

- historical Koomen operator/reduction uncertainty;
- Taylor SQM angular/spectral/calibration uncertainty;
- MYSTIC Monte Carlo/numerical uncertainty;
- atmosphere/site/season mismatch and Taylor's historical elevation transform;
- unresolved solar-altitude convention in the 1952 source.

## 5. Repository safeguard added

Added `integration/measurement-operator-provenance-v1/measurement_operator_contract.py` plus tests and README.

For a claim classified `quantitative-validation`, the guard refuses unless:

- measured and synthetic operator records explicitly contain observable class, angular response/FOV, pointing, spectral response, calibration, temporal response, units, and geometry convention;
- every material component is marked `complete` with provenance;
- `syntheticOperatorApplied=true`;
- measured and synthetic physical operator specifications match canonically.

Incomplete/unknown historical records may be carried only as `diagnostic`; the result is `DIAGNOSTIC_ONLY` and reports missing/mismatched components. There is no hidden fallback to point zenith.

The existing `twilight-observation-v1` schema is not retroactively changed; the new comparison contract is a separate validation boundary so old observations do not acquire invented metadata.

## 6. Exact next action

**Primary historical action:** obtain and source-bind the full Plymale 1947 filter paper and any NRL instrument/calibration documentation that can establish the actual 1952 P22+green-filter response and the photometer's within-field angular acceptance/time response. Separately search observing/reduction notes for the solar-altitude ephemeris/refraction convention and a numerical calibration error budget.

If those records still do not establish the acceptance function, the next numerical action should **not** choose a convenient FOV. Instead preregister a small research-only **bounded operator-sensitivity experiment**: hold atmosphere/model fixed, use the documented 1.5-degree support, and propagate a predeclared family/bounds of physically plausible acceptance functions. Report a range, not a fitted correction. Until then, preserve #828's -0.2826-mag result only as the SQM-versus-point diagnostic it actually measured.
