# Deep-twilight bare-Shettle NULL optical-property parity capability v1

Status: **zero-radiance capability gate only**. This protocol does not authorize MYSTIC, Eradiate radiance, a scientific ordinal, a deep-twilight support extension, or any production/application change.

## Purpose

Resolve the remaining optical-property extraction blocker for the historical bare libRadtran `aerosol_default` atmosphere before any independent-renderer deep-twilight comparison. The existing OPAC NULL calibration in PR #595 already established, for this locked libRadtran runtime, that the verbose `optical_properties()` aerosol `scatter.` + `abs.` columns behave as layer aerosol optical depth and that `aerosol_set_tau_at_wvl` can be used as a diagnostic column rescale. That OPAC result does not establish parity for historical bare Shettle `aerosol_default`.

## Frozen matrix

Use the exact installed runtime `rubin-libradtran=2.0.6=py312pl5321he9373c2_1`, with `uvspec` SHA-256 `2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3` and the standard packaged data tree. No external OPAC/species file is introduced.

Atmosphere is AFGL-US. Aerosol directives are exactly `aerosol_default` followed by `aerosol_set_tau_at_wvl 550 <target>`. Base AOD550 is 0.15. The fixed wavelength set is 380, 550 and 780 nm. The fixed diagnostic AOD scale factors are 1, 100 and 10000, corresponding to requested AOD550 values 0.15, 15 and 1500. No scale may be added or changed after seeing output.

All nine cases use `rte_solver null`. The Sun angle and albedo are setup-only constants (`sza 80`, `albedo 0.15`) and have no deep-twilight interpretation. No radiance value is generated or consumed.

## Quantization / zero semantics

The verbose aerosol scattering and absorption columns are printed to six decimals, so each printed nonnegative value is carried as a rounding interval with half-quantum 0.5e-6. A printed zero is therefore a censored upper-bound interval; it is never interpreted as physical zero. Aerosol asymmetry `g` is printed to three decimals and is carried with half-quantum 0.0005.

For each layer and wavelength, scattering+absorption intervals are divided by the predeclared scale factor and must possess a common intersection across the three scale arms. For arms whose scaled layer optical-depth interval has a strictly positive lower bound, SSA is bounded from the independently quantized scattering/absorption intervals and `g` is bounded from its print interval. When at least two arms resolve that layer, their SSA intervals and their `g` intervals must intersect. Failure is capability-unresolved; no adaptive retry is allowed.

At 550 nm, the printed aggregate aerosol scattering+absorption must reproduce each requested AOD550 within the already reviewed #595 absolute print-precision tolerance 2.1e-6. Layer-row sum versus printed sum-line retains the reviewed #595 tolerance 7e-5.

## Outcomes

`PASS_BARE_SHETTLE_FIXED_AMPLIFICATION_PARITY` means only that the predeclared fixed amplification scheme yields mutually consistent bounded layerwise tau/SSA/g evidence for bare `aerosol_default` at the three wavelengths. It does not validate Eradiate, deep twilight, or a rare-event estimator.

`AMPLIFICATION_PARITY_CAPABILITY_UNRESOLVED` means the fixed print-resolution route is insufficient or inconsistent. Do not add a fourth scale or tune thresholds. The only admissible next extraction route is the separately preregistered tiny serializer of the final post-redistribution aerosol optical state, still without RTE/photons.

If this capability passes, the next gate is an explicit source-to-Eradiate optical-property translation parity object, followed by the separately frozen shallow true-spherical Korkin benchmark. Only after both pass may the already frozen synthetic deep matrix at 11.5/12.5/14.5/17.0 deg be considered under a fresh scientific identity.

## Boundaries

Historical deep values are diagnostic evidence only and are not inputs or targets. Taylor/Jerusalem/desired halachic times are not used. Level-B v1 remains exactly 2.0-10.5 deg. The invalidated low-altitude chain identified by correction `5468736357` is not used. No total-sky negligibility claim is made here.
