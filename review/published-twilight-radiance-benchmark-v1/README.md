# Published Twilight Radiance Benchmark v1

This branch is deliberately separate from the untouched Izaña/Pandora source-admission lane.

It evaluates the already-published Maryland photopic sky-brightness values in Koomen et al. (JOSA 42, 353–356, 1952), Table II, against the exact frozen Level-B v3 model and frozen ASIV aerosol scenario set.

Primary frozen subset: H = -3 and -6 degrees; P = 10, 30, 50, 70 degrees; Z = 0, 22.5, 45, 90, 135, 180 degrees; Maryland observer elevation 30 m; 48 cells total.

The source geometry maps directly as sunDepressionDeg = -H, targetAltitudeDeg = P, relativeAzimuthDeg = Z. Source brightness is published in candles per square foot and converted to cd/m2 by 10.763910416709722.

For every cell, the workflow first requires exact continuous-AOD Level-B support over AOD550 0.05–0.40. Supported cells are then evaluated with the already-reviewed certified full-AOD native + four-aerosol-scenario extrema algorithm at 1e-4 natural-log enclosure tolerance.

This is a published/open historical benchmark, not an untouched modern empirical validation. An observation outside the deliberately broad full-AOD/five-scenario envelope is strong evidence of inconsistency. An observation inside that envelope shows only broad consistency. No model retuning or production authorization is permitted from this lane.

The Izaña/Pandora holdout remains unopened.
