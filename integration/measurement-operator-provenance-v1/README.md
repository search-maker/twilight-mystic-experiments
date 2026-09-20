# Measurement-operator provenance contract v1

This is a small, review/integration-only fail-closed guard for measured-sky validation. It prevents a measured quantity from being treated as a point-zenith model value merely because the word `zenith` appears in its description.

A v1 operator record must explicitly state every material component:

- observable class: point-direction, finite aperture, wide field, hemispheric, other explicit, or explicitly unknown;
- angular response / field of view;
- pointing;
- spectral response;
- calibration or zero-point transform;
- temporal integration / scan / averaging;
- units and reported physical quantity;
- relevant geometry convention (for example, geometric versus apparent/refracted solar altitude when it matters).

Every component is independently marked `complete`, `partial`, or `unknown`, with provenance. Missing fields are refused rather than defaulted.

`measurement_operator_contract.py` supports two claim classes:

- `quantitative-validation`: requires every material component on both measured and synthetic sides to be `complete`, requires `syntheticOperatorApplied=true`, and requires the canonical physical operator specifications to match exactly. Otherwise it refuses.
- `diagnostic`: permits explicit partial/unknown provenance and explicit mismatches, but always returns `DIAGNOSTIC_ONLY`. A diagnostic result must not be promoted to quantitative validation.

This contract says only that the compared measurement operators are compatible. It does not validate the atmosphere, MYSTIC/libRadtran physics, a calibration's accuracy, a historical transcription, or any production model.

The existing `twilight-observation-v1` schema is intentionally left unchanged. Its legacy `angularRadiusDeg`, calibration ID, and raw-file hashes remain valid metadata, but any future quantitative measured-vs-synthetic comparison should additionally pass through this operator contract. This avoids retroactively inventing operator metadata for older observations.
