# AVPS v2 recovery3 — live dynamic preauthorization v3

## Recovery lineage

This is a fresh control identity from exact public main after two immutable failures that remain preserved and non-rerunnable:

- v1 PR #692 / head `0a1a747d1ade460c3eba92c52cb77cebd6114b8d` / run `33308955617` attempt 1 failed before any global scan because it bound a nonexistent ordinal-43 consumed-comment ID. The actual consumed marker is Issue #60 comment `5467301509`, body exactly `ORDINAL43_AVPS_V2_POSTCONSUMPTION_RECOVERY2_DISPATCH_CONSUMED`.
- v2 PR #693 / head `b690443fdbf55ea46de44486a3a8ad09cbd59b51` / run `33309180266` attempt 1 passed provenance/native-ledger/candidate/fence checks, then the unchanged protected repository-global scanner failed closed because fenced metadata changed between its two complete enumerations. No dynamic ordinal or proof artifact was produced.

V3 changes only review/control mechanics: it preserves the v2 provenance corrections and adds repository-wide workflow quiescence plus a cooldown before the unchanged protected two-pass global scan. Frozen AVPS science, 72 reviewed candidate seeds, thresholds, analysis and result-opening rules are unchanged.

## Bound recovery3 evidence

Public main is `384f94c02b892768a9dde6fe17e69a384112ef73`. The protected recovery3 seed proof is PR #689, head `ad2632c3d32b9a72805ade2c61c2ad3fe882fb09`, run `33305675119` attempt 1 SUCCESS, artifact `9730444904`, digest `sha256:13f833045d446b813e653ea10f018db98df956e80c51f76eccd9802f0bd47a48`, published by PR #691.

The candidate ledger remains exactly 72 unique common-random-number seeds with canonical seed SHA-256 `d2817b1ea4f2bdc8cb1842e565b099b015e4e28c5874482629fadc450069d9bf` and row SHA-256 `b6a519eadacdb99ea53c52d483c8acfeba05829643cb988de21682a53fc47896`, with zero overlap against consumed ordinals 41, 42 and 43. Ordinal 42's historical ledger must still be validated only at its native authorization-head path.

## Required protected review

The exact-head review must:

1. bind exact base/main, exact fresh v3 branch/head, and an exact three-file additive review-only diff;
2. bind the protected recovery3 proof/publication plus consumed ordinal-41/42/43 run identities and exact ordinal-43 consumed marker;
3. rebuild exactly the reviewed 72-candidate ledger and preserve zero-overlap evidence;
4. require the exact Issue #60 WRITE_QUIET fence, then wait until every repository workflow except the current audit run is terminal, apply a cooldown, and recheck repository-wide quiescence before the protected scan;
5. repeat the tracked-tree and unchanged complete two-pass repository-global seed scan in `authorization-recheck` mode;
6. dynamically derive the next unused repository-global scientific ordinal from the authoritative observation surface, never hard-coding a successor number, and refuse existing authorization/dispatch/marker evidence for the proposed successor;
7. recheck unchanged branch/global ordinal state before PASS and upload only a zero-runtime proof artifact.

Any provenance drift, seed collision, global metadata instability, branch movement, ordinal-surface change, or boundary violation fails closed. A failed attempt must never be rerun/retried/resumed; any continuation requires another fresh control identity.

## Boundary

PASS would authorize only a separately reviewed authorization-control/allocation proposal that itself performs another freshness recheck. This package does not allocate/apply seeds or ordinals, create authorization or dispatch refs, execute libRadtran/MYSTIC/uvspec, open AVPS results, admit vertical profile/spectral AOD/SSA/phase/family into Level-B, access protected holdouts, use Taylor/Jerusalem residuals, or change production behavior.

`AOD550` remains the only directly consumed validated-v3 aerosol coordinate. Every richer Operational Atmosphere State v2 `newMappingAuthorized` flag remains `false`.