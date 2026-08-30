# AVPS v2 recovery3 — live dynamic preauthorization v4

## Why this identity exists

Recovery3 v3 (PR #694, head `ec8af2af3e4eff1c9afd51d2d42a2b93698ab51a`, run `33309725499` attempt 1, artifact `9731800150`) technically completed its protected zero-runtime scan, but Issue #60 later classified that proof as diagnostic-only and not transition-eligible because its matching WRITE_QUIET fence remained explicitly open after the run became terminal while unrelated repository metadata writes occurred. The matching END is Issue #60 comment `5468608255`. No v3 seed/ordinal allocation, authorization, dispatch, solver runtime, result opening or Level-B admission occurred.

V4 is therefore a fresh attempt-1 control identity. It does not repair or reinterpret v3 results. It repeats the same frozen recovery3 candidate/global-preauthorization question under a new WRITE_QUIET fence after repository workflow/metadata quiescence is re-established.

## Frozen science and candidate evidence

The scientific design is unchanged: 360 cases, 72 common-random-number groups, five independently defined vertical-profile states, 20,000,000 photon histories per case, and unchanged geometry, wavelengths, optical properties, estimator, aggregation, classification and result-opening rules. Taylor/Jerusalem residuals are not inputs.

The only candidate seed universe remains the protected recovery3 package from PR #689, head `ad2632c3d32b9a72805ade2c61c2ad3fe882fb09`, run `33305675119` attempt 1 SUCCESS, artifact `9730444904`, digest `sha256:13f833045d446b813e653ea10f018db98df956e80c51f76eccd9802f0bd47a48`. It contains exactly 72 unique candidate CRN seeds with seed canonical SHA-256 `d2817b1ea4f2bdc8cb1842e565b099b015e4e28c5874482629fadc450069d9bf` and row canonical SHA-256 `b6a519eadacdb99ea53c52d483c8acfeba05829643cb988de21682a53fc47896`, with zero overlap against consumed ordinals 41, 42 and 43.

Ordinals 41, 42 and 43, their seeds, authorization/dispatch identities and run attempts are permanently consumed and non-reusable. Ordinal 43's exact consumed marker remains Issue #60 comment `5467301509`, body exactly `ORDINAL43_AVPS_V2_POSTCONSUMPTION_RECOVERY2_DISPATCH_CONSUMED`.

## V4 mechanical rule

To prevent accidental scientific/control-logic drift, the tracked V4 `preauthorize.py` is only a thin identity wrapper around the exact technically successful v3 preauthorization implementation blob `286b489911ce83f4eb6d6f0817f3c6271731a036` at head `ec8af2af3e4eff1c9afd51d2d42a2b93698ab51a`. The wrapper changes only the live V4 branch/base identity and report stage suffix. The v3 global-ordinal derivation, collision checks, final verification and all refusal semantics remain byte-bound.

The V4 base is not hard-coded in scientific/control logic. The review binds the exact pull-request-open base SHA, requires that it is then-live `main`, requires the V4 head to be exactly one additive commit above it, and fails closed if `main` moves before the protected scan completes.

## Required protected review

The exact-head V4 review must:

1. bind exact fresh V4 branch/head, the pull-request-open live `main`, and an exact three-file additive review-only diff;
2. bind the exact v3 preauthorization implementation blob used by the V4 identity wrapper;
3. bind the recovery3 seed proof/publication, consumed ordinal-41/42/43 run identities and exact ordinal-43 consumed marker;
4. rebuild exactly the same reviewed 72-candidate ledger and preserve zero-overlap evidence;
5. require the exact V4 Issue #60 WRITE_QUIET_BEGIN marker, wait until every repository workflow except the current audit run is terminal, apply a cooldown, and recheck repository-wide quiescence before the protected scan;
6. repeat tracked-tree and complete two-pass repository-global seed scans in `authorization-recheck` mode;
7. dynamically derive the next unused repository-global scientific ordinal from the authoritative observation surface, never hard-coding 44 or any other successor, and refuse existing authorization/dispatch/marker evidence for the proposed successor;
8. recheck branch/main/global-ordinal state before PASS and upload only a zero-runtime proof artifact.

Any provenance drift, candidate collision, global metadata instability, branch/main movement, ordinal-surface change, or boundary violation fails closed. A failed V4 attempt must never be rerun/retried/resumed; continuation would require another fresh control identity.

## Boundary

A V4 PASS would authorize only a separately reviewed authorization-control/allocation proposal that performs another live freshness recheck. This package does not allocate/apply seeds or ordinals, create authorization or dispatch refs, execute libRadtran/MYSTIC/uvspec, open AVPS results, admit vertical profile/spectral AOD/SSA/phase/family into Level-B, access protected holdouts, use Taylor/Jerusalem residuals, or change production behavior.

`AOD550` remains the only directly consumed validated-v3 aerosol coordinate. Every richer Operational Atmosphere State v2 `newMappingAuthorized` flag remains `false`.
