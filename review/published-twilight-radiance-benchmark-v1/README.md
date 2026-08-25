# Published Twilight Radiance Benchmark v1

This branch is deliberately separate from the untouched Izaña/Pandora source-admission lane.

It now contains two already-published historical diagnostics against the frozen Level-B v3 model. Neither lane is an untouched modern empirical validation, neither authorizes model retuning or production, and neither opens Izaña/Pandora target radiance.

## Koomen 1952 — Maryland photopic

The primary frozen subset is Koomen et al. (JOSA 42, 353–356, 1952), Table II: H = -3 and -6 degrees; P = 10, 30, 50, 70 degrees; Z = 0, 22.5, 45, 90, 135, 180 degrees; Maryland observer elevation 30 m; 48 cells total.

The source geometry maps directly as sunDepressionDeg = -H, targetAltitudeDeg = P, relativeAzimuthDeg = Z. Source brightness is published in candles per square foot and converted to cd/m2 by 10.763910416709722.

For every absolute cell, the benchmark first requires exact continuous-AOD Level-B support over AOD550 0.05–0.40. Supported cells use the already-reviewed certified full-AOD native + four-aerosol-scenario extrema algorithm.

The separate shape diagnostic pairs each published sky point at 3 and 6 degrees sun depression. The original frozen diagnostic uses the same AOD and same aerosol scenario at both depths over a 1001-point AOD grid. Its result is directional: every one of the 11 fully supported matched pairs has observed ln(L6/L3) below the entire modeled grid range, so the historical sky darkens more strongly from 3 to 6 degrees than the model.

`certify_koomen_shape_continuous_aod_v1.py` strengthens that exact same frozen question by interval branch-and-bound over continuous AOD. It partitions the shared AOD axis at every base-model and ASIV neighbor-order crossing relevant to either depth, then bounds f6(AOD)-f3(AOD) directly for the same aerosol scenario. This avoids the invalid shortcut of subtracting two independently optimized extrema and preserves the same-AOD requirement.

## Volz 1969 — 477 nm standard twilight curve

Volz, *Applied Optics* 8(12), 2505–2517 (1969), Table II publishes `log10(G_st/F_sun)+8` at 477 nm for unrefracted sun depression 0 through 10 degrees. The frozen model-domain selection takes every integer depth 2 through 10, before model evaluation, at target altitude 20 degrees and relative solar azimuth 0 degrees.

The v1 Volz comparison is deliberately shape-only. Ratios between depths cancel the unknown absolute `F_sun` normalization, so no absolute-radiance conversion is invented. The spectral comparison uses the frozen 13-output Level-B v3 model plus its exact frozen 380–780 nm spectral representation to reconstruct the exact 477 nm node. ASIV spectral aerosol scenarios are not applied because no full-spectrum aerosol interpolation PASS exists; this lane is native-aerosol only.

The observer-elevation value of 194 m is a frozen historical-geometry mapping convention associated with the reference standard-curve comparison; it is not a claim that every Volz observation was made at that elevation. Results must therefore be described as conditional on that frozen mapping.

Exact support over the full AOD550 0.05–0.40 interval admits depths 6–10 and rejects frozen depths 2–5. Unsupported rows remain reported and are not replaced by convenient alternatives. Among the four frozen adjacent pairs whose two endpoints are fully supported — 6→7, 7→8, 8→9 and 9→10 degrees — all four published 477 nm changes are more negative than the entire native model grid range. Their grid-miss equivalents are about 0.014, 0.102, 0.135 and 0.227 mag respectively.

This is the same directional tendency found independently in the supported Koomen shape comparison: these historical datasets do not support a simple hypothesis that the frozen physical sky model darkens too quickly through twilight. They instead indicate that, in the evaluated supported geometries, the model remains too bright / darkens too slowly over the compared intervals.

## Interpretation boundary

An observation outside a deliberately frozen model envelope is diagnostic evidence of inconsistency; an observation inside shows only consistency at that benchmark's resolution. These historical results do not establish modern atmospheric validity, do not establish human first-seeing, and do not authorize fitting the model to Koomen or Volz and then calling the same data untouched validation.

The Izaña/Pandora holdout remains unopened.
