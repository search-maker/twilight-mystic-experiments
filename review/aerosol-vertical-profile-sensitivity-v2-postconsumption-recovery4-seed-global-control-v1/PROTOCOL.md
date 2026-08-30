# AVPS v2 post-consumption recovery4 seed/global control v1

Status: `REVIEW_ONLY_REAL_CANDIDATE_SEEDS_FROZEN_GLOBAL_SCAN_NOT_YET_RUN_ORDINAL_NOT_SELECTED`.

This is the separately required result-blind stage after the reviewed recovery4 routing infrastructure. It is the first stage permitted to select a real recovery4 candidate seed namespace. The namespace is frozen here before any repository-global collision result or successor ordinal is observed:

`aerosol-vertical-profile-sensitivity-v2|postconsumption-recovery4-fresh-seed-control-v1|group-seed|sha256-v1`

The seed ledger binds the immutable 72-group AVPS-v2 skeleton and the consumed recovery3 seed ledger. Recovery3 in turn byte-validates consumed ordinals 41, 42 and 43 at their historical/native paths. Thus the new 72-row ledger refuses any overlap with all consumed AVPS seed sets 41-44. Expected deterministic candidate identities are:

- candidate seed canonical SHA-256: `ddded6b2d170ca2fac8d498bdba2887446c16995df0880d948fb2be00870b3de`
- candidate row canonical SHA-256: `c439de417520b330c037e2628df02b6955f652563300aa5ef30477abf7661a98`

The frozen scientific design is unchanged: 360 cases, 72 CRN groups, five OPAC profile states, 20,000,000 photons per case, unchanged wavelengths/geometries/AOD/profile/source/runtime/estimator/threshold/result-opening rules. Candidate seeds are not applied to cases here. No scientific ordinal is hard-coded, proposed in source, allocated, reserved, or consumed by this review package.

After this package is independently reviewed and merged, the manual `AVPS v2 recovery4 seed/global control` workflow may be run once under a matching Issue #60 WRITE_QUIET fence on an exact current main SHA. That zero-runtime control must: rebuild the exact 72 candidates; scan the tracked tree; perform the complete two-pass repository-global collision scan; dynamically derive the next unused global scientific ordinal from the already-reviewed global-ordinal control surface; freeze a proof artifact; and leave authorization/dispatch/case application/solver/result opening/Level-B/holdout/production false. A PASS is freshness evidence only. It does not allocate the derived ordinal.

The workflow must not be dispatched while another repository-global fence is active or while relevant repository metadata is not quiescent enough for the frozen scanner. The fence must be closed immediately after the exact run becomes terminal. GitHub Re-run/retry/resume is forbidden; a failed attempt is preserved and any recovery uses a fresh control identity.

Taylor/Jerusalem residuals and invalidated low-altitude downstream evidence are excluded from every seed, ordinal, profile, threshold and mapper decision. Every richer OAS-v2 `newMappingAuthorized` flag remains false.
