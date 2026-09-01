# Koomen/Tousey historical measurement-operator audit

**Date:** 2026-09-01  
**Scope:** research/review only; follow-up to completed Issue #828; no fitting, solver retuning, production/Level-B, atmosphere, or human-vision change.

## Bottom line

The historical Koomen zenith observable is **not SQM-like wide-field** and is not an exact mathematical point ray. Koomen et al. (1952) used a recording photometer with a **nominal circular 1.5-degree diameter field** (0.75-degree half-angle; geometric cone support `5.382957282296464e-4 sr`) swept through zenith. The reported `B` is calibrated local sky brightness/luminance in candles per square foot. Their separate planar illumination `E` was obtained by integrating `B` over the sky, confirming that `B` itself is not a hemispheric integral.

The exact historical operator is nevertheless incomplete: no within-field acceptance/vignetting function was recovered; the exact combined P22+filter response was not recovered; a later-twilight Purkinje/color correction was explicitly needed but not applied; the full meridian sweep took 12 s but the detector/recorder time constant is unstated; no numerical absolute-calibration uncertainty is stated; and historical solar altitude `H` is defined only relative to the horizon, without saying geometric versus apparent/refracted.

Therefore Issue #828's `original-wide-SQM minus true-point-zenith = -0.2826 mag` remains a valid **same-atmosphere SQM operator diagnostic**, but it is **not** evidence that about 72% of the approximately 0.39-mag Taylor-Koomen offset is explained by field of view. That percentage was only a ratio of numerical scales.

## 1. Primary sources and exact locations

### 1.1 Koomen et al. source measurement paper

M. J. Koomen, C. Lock, D. M. Packer, R. Scolnik, R. Tousey, and E. O. Hulburt, **"Measurements of the Brightness of the Twilight Sky,"** *JOSA* **42**(5), 353-356 (1952), DOI `10.1364/JOSA.42.000353`.

- **p.353 instrument paragraph:** nine-stage RCA Type P22 photomultiplier; ground glass + green filter; 0.6-cm circular aperture at the lens focus; the paper explicitly states the **1.5-degree diameter field of view**. The filter was intended to give the response of the light-adapted eye. The instrument swept any meridian horizon-to-horizon through zenith in 12 s and fed a DC amplifier/Brush recorder.
- **Derived scan scale:** 180 degrees / 12 s = 15 deg/s average sweep rate; a 1.5-degree field corresponds to 0.10 s of scan travel at that average rate. This is not an integration-time claim: uniformity of scan speed and recorder/detector time response are not specified.
- **p.353 calibration paragraph:** clear daylight sky compared with a calibrated blue-filtered Macbeth illuminometer; gain/PMT-voltage/lens-aperture transfer by a standard tungsten lamp attenuated nonselectively; radium-phosphor source used as a continuing calibration check.
- **p.353 spectral limitation:** values were stated to be photometrically correct in the first half of twilight; later values needed a color/Purkinje correction that was not applied because the needed sky spectra were not known exactly.
- **p.353 observing sample:** seven clear/cloudless/moonless Sacramento Peak evenings in May-June 1951; Maryland observations in January-March 1951. Clear-day vertical sunlight transmission was reported as 85-90% at Sacramento Peak and 75-85% in Maryland.
- **p.354 Tables I/II and definitions:** `B` is brightness of a place in the sky in candles per square foot; `H` is solar altitude, positive above and negative below the horizon; sky position is altitude `P` and bearing `Z` from the Sun's direction.
- **pp.354-355 reduction/Fig. 1:** more than 1000 `B` values per station were read from records and plotted versus `H`; smooth curves were drawn; **Tables I and II were read from the curves**. Fig. 1 explicitly shows scatter attributed jointly to sky variation and instrumental inaccuracy. The tables are therefore reduced/smoothed historical values, not raw individual photometer samples.
- **p.356 Table III discussion:** `E` is illumination on a flat opal-glass surface; the authors say `E` can be obtained by integrating `B` over the sky and check it that way. This separates local finite-field luminance `B` from broad angular illumination `E`.

For the historical zenith series, the source cells are the `P=90 degrees` column in **Table I (Sacramento Peak, 2800 m)** and **Table II (Maryland, 30 m)**. At zenith, `Z` is directionally degenerate and the same zenith value is repeated across the table's `Z` blocks.

### 1.2 Spectral-correction reference

Koomen p.353 footnote 6 cites W. S. Plymale, **"Filters for Spectral Corrections of Multiplier Photo-Tubes Used from Scotopic to Photopic Brightness Levels,"** *Rev. Sci. Instrum.* **18**, 535-539 (1947). Indexed material says it gives glass numbers/thicknesses for RCA 1P21/1P22 correction over the Purkinje range. The exact glass/combined response actually installed in the 1952 twilight photometer has not been source-bound strongly enough to claim an exact spectral operator.

W. S. Plymale and G. T. Hicks, **"Physical Photometry in the Purkinje Range,"** *JOSA* **42**, 344-348 (1952), DOI `10.1364/JOSA.42.000344`, confirms the importance/difficulty of corrected 1P22 photometry at low luminance, but is not treated as proof of the exact 1952 twilight response.

### 1.3 Related instruments and downstream use

D. M. Packer and C. Lock, **"The Brightness and Polarization of the Daylight Sky at Altitudes of 18,000 to 38,000 Feet above Sea Level,"** *JOSA* **41**, 473-478 (1951), describes a related aircraft system with a different field (about 2.5 degrees). It must not be substituted for the explicitly stated 1.5-degree twilight instrument.

R. Tousey and M. J. Koomen, **"The Visibility of Stars and Planets During Twilight,"** *JOSA* **43**, 177-183 (1953), DOI `10.1364/JOSA.43.000177`, uses known twilight sky brightness, atmospheric transmission, and eye sensitivity to calculate star/planet visibility. It is downstream use, not a replacement instrument specification.

## 2. Exact Taylor use and data lineage

Taylor's public repository `astertaylor/halakhic_calc` was audited at main commit `9d9b6a9cf5837044717ef65dc5e1f14ccecc895f`.

- `calc_time.py` blob `7df303872c329e3ff68154d5481698a88b007fc4` reads `data/KoonanDataCombined.csv`, constructs a `RegularGridInterpolator` over `(sky altitude, azimuth offset, solar altitude)` in **`log10(B)`**, and exponentiates the interpolated value.
- CSV blob `57243cb54599e7965ca92a2cfe1aa0bd8373d5c2` contains the transformed grid. It was introduced by Taylor commit `2713e043077c1015078ea89f1c4396f45c73ccf5` (`Upload twilight light data`). No separate grid-generation script was found in that public repository.
- The numerical zenith lineage is nevertheless independently reproducible. Using the source `P=90 degrees` values from Koomen Tables I/II, Taylor's `10.76` conversion, and his extinction law

```text
kV(elev) = 0.1066 + 0.12 exp(-elev/1500)
B0_site(H) = 10.76 B_table(H) / [1 - 10^(-0.4 kV(elev))]   (zenith airmass = 1)
B0(H) = mean(B0_Sacramento(H), B0_Maryland(H))
```

reproduces **all eight committed Taylor zenith grid values exactly to floating-point precision** for `H = -15,-12,-9,-6,-3,0,+3,+5 degrees`. This also disambiguates the historical table's compact subscript decimal notation at late twilight. Exact hashes, source numbers, formulas, and reproduced values are recorded in `taylor_koomen_runtime_lineage.json`.

Thus the Taylor "Koomen" curve is not a raw 1952 instrument record: it is a cross-site historical product after unit conversion, site-elevation/extinction normalization to `B0`, averaging of Sacramento Peak and Maryland, and log-space interpolation.

### Taylor solar-altitude convention is separately identifiable

Taylor's public runtime creates `ephem.Observer()`, does **not** override `Observer.pressure`, computes `ephem.Sun()` for that observer, and feeds `float(sun.alt)` into the Koomen interpolation. PyEphem documents a default pressure of 1010 mbar and states that body `alt` includes atmospheric refraction unless pressure is set to zero. Therefore the audited public Taylor runtime uses an **apparent/refracted PyEphem solar altitude** under the documented default.

This does **not** establish the 1952 Koomen `H` convention. Historical `H` remains unknown as geometric-versus-apparent. The mismatch must remain explicit rather than choosing whichever convention improves Taylor agreement.

## 3. Reconstructed historical operator: known versus unknown

| Component | Best-supported reconstruction | Status |
|---|---|---|
| Observable | Local sky brightness/luminance `B`, finite field; not hemispheric | **known** |
| Nominal angular support | circular **1.5 deg diameter / 0.75 deg radius**, geometric support `5.38296e-4 sr` | **known** |
| Within-field weighting/effective solid angle | radial acceptance, vignetting, baffling | **unknown** |
| Zenith pointing | field center crosses `P=90 deg` during a meridian sweep; `Z` degenerate | **known** |
| Scan | horizon-to-horizon through zenith in **12 s**; 15 deg/s average | **known/derived** |
| Effective temporal response | detector/recorder time constant and exact zenith exposure/smear | **unknown** |
| Detector | nine-stage RCA Type P22 photomultiplier | **known** |
| Spectral shaping | ground glass + green correction filter, intended photopic | **partly known** |
| Exact spectral response | combined optics/filter/P22 relative response | **unknown** |
| Late-twilight correction | Purkinje/color correction needed, **not applied** | **known limitation** |
| Absolute calibration | Macbeth daylight comparison + tungsten transfer + radium check | **known method** |
| Numerical calibration uncertainty | no separate number recovered | **unknown** |
| Units | candles per square foot, local sky brightness/luminance | **known** |
| Published table reduction | values read from smooth curves through >1000 records/station | **known** |
| Historical `H` definition | solar altitude above/below horizon | **known** |
| Historical geometric vs apparent/refracted `H` | not stated | **unknown** |

The machine-readable declaration `koomen_1952_zenith_operator.partial.json` deliberately preserves these unknowns.

## 4. Correct like-for-like MYSTIC observable

Because the instrument was calibrated to report sky brightness/luminance, the appropriate synthetic quantity is an **acceptance-weighted average radiance/luminance over the finite field**, with the historical spectral and temporal response applied, not total flux and not an SQM integral. Schematically,

```text
Q_K = C_K *
      [ integral T_K(t) integral A_K(Omega,t) integral R_K(lambda) L_lambda(Omega,t) d lambda d Omega dt ]
      / [ integral T_K(t) integral A_K(Omega,t) d Omega dt ]
```

where the field center crosses zenith, the nominal angular support is the 1.5-degree circle, and `C_K` reproduces the historical photometric calibration/units.

Consequences:

- do **not** use Taylor's original-wide-SQM operator as the Koomen operator;
- do **not** silently call a point ray the exact Koomen measurement;
- do **not** invent a 1.5-degree top-hat response;
- do **not** infer the historical `H` convention from residual agreement.

A point zenith calculation can be labeled only as a narrow-field approximation. An exact research-only Koomen forward operator is **not implemented**, because the missing acceptance/spectral/time response is material. This is the intended fail-closed outcome.

## 5. Can the approximately 0.39-mag Taylor-Koomen offset be decomposed?

**No, not defensibly at present.** Keep these quantities separate:

1. #828 same-atmosphere diagnostic: wide-SQM minus true-point-zenith about **-0.2826 mag**;
2. historical Koomen source operator: narrow **1.5-degree finite field**, incompletely reconstructed;
3. Taylor comparison: Ann Arbor wide-SQM versus a transformed, elevation-normalized, averaged, log-interpolated historical product from two other sites/seasons;
4. geometry: Taylor public runtime uses refracted PyEphem `H`, while historical 1952 geometric-versus-apparent `H` is unresolved.

Therefore `abs(-0.2826)/0.39 ~= 0.725` is only a scale ratio. It is **not** an explained fraction, and no causal instrument/atmosphere percentage is warranted.

Historical-operator uncertainty, Taylor-SQM uncertainty, MYSTIC numerical uncertainty, atmosphere/site/season mismatch, Taylor's elevation transform, and solar-altitude convention uncertainty must remain separate.

## 6. Repository safeguard added

Added `integration/measurement-operator-provenance-v1/measurement_operator_contract.py`, README, and tests.

For `quantitative-validation`, the guard refuses unless both measured and synthetic records explicitly and completely provide:

- observable class;
- angular response/FOV;
- pointing;
- spectral response;
- calibration/zero point;
- temporal response;
- units;
- geometry convention;
- and `syntheticOperatorApplied=true` with matching canonical operator specifications.

Partial/unknown records are allowed only as `diagnostic` and return `DIAGNOSTIC_ONLY`; there is no fallback to point zenith. The legacy `twilight-observation-v1` schema is left unchanged so older observations do not acquire invented metadata.

## 7. Exact next action

1. Obtain/source-bind the full Plymale 1947 filter paper and any NRL photometer/recorder documentation that can establish the actual P22+filter response and within-field/time response; search observing/reduction notes for historical `H` ephemeris/refraction convention and a calibration error budget.
2. Preserve Taylor's public-runtime apparent/refracted `H` as an explicit provenance fact; **do not change it** merely because another convention changes the residual.
3. If the historical acceptance function remains unavailable, preregister a small research-only **bounded operator-sensitivity** experiment: fixed atmosphere/model, documented 1.5-degree support, predeclared scientifically plausible response families/bounds, reporting a range rather than a fitted correction.

Until those steps, preserve #828's `-0.2826 mag` only as the SQM-versus-point diagnostic it actually measured.
