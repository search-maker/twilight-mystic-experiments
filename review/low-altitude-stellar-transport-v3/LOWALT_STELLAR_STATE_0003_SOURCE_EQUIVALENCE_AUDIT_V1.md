# LOWALT-STELLAR-STATE-0003 — pinned-source equivalence audit v1

Status: `POST_V1_NONBLOCKING / RESULT_BLIND / SOLVER_FREE_SOURCE_AUDIT`

Parent protocol: `LOWALT_STELLAR_STATE_0003_DIRECT_PATH_PROTOCOL_V1.md`.

## Purpose

This review resolves the provenance prerequisite that must precede any fresh NONPROTECTED numerical equivalence matrix. It does not execute libRadtran, `uvspec`, DISORT, sDISORT, MYSTIC, or any scientific transport solve. It acquires and fingerprints the exact source archive named by the conda-forge recipe that built the pinned runtime family, then captures bounded source evidence for the ten frozen source-equivalence checklist items.

No LOWALT-STELLAR-STATE-0001 protected residual, Taylor/Jerusalem residual, halachic target time, support-floor decision, interpolation formula, knot set, or protected acceptance set is used here.

## Pinned identities

Application/runtime lineage remains the previously reviewed `rubin-libradtran=2.0.6=py312pl5321he9373c2_1` runtime used by LOWALT-STELLAR-STATE-0002. The exact executable/runtime hashes remain inherited evidence; this source review does not re-run it.

The conda-forge rebuild commit that raised build number `0 -> 1` without changing the source hash is:

- feedstock commit: `d6f1997b2f486541136f514188c650fdd370f8e2`
- source URL: `https://www.libradtran.org/download/libRadtran-2.0.6.tar.gz`
- source SHA-256 required by that build-1 recipe: `999e47f4af4b5df6f85a6887fc105fc8f6e1a7cee89a3124f69ac8d8912c8e85`
- recipe build number: `1`

Historical feedstock commit `34661f6d1776374c409908256c38055b6641f4e1` initially pointed the same version string at archive SHA-256 `64930cc40b6e4a37aa220520974d330fc1563796f466a649b2238131f2d69840`; commit `a5d9c9c629395bbf850d73ef774d41879dab15fd` changed only that source hash to `999e47...`. Therefore version label `2.0.6` alone is insufficient source identity. This audit must fail closed unless the bytes acquired for the pinned build-1 source equal `999e47...` exactly.

## Governing source capture

Only after exact archive hash verification, extract and fingerprint these files:

1. `doc/radiative_transfer_theory.tex`
2. `doc/radiative_transfer.tex`
3. `libsrc_c/cdisort.c`
4. `libsrc_c/cdisort.h`
5. `src/solve_rte.c`
6. `src/uvspec_lex.l`

The artifact records byte counts, SHA-256 values, and line-numbered bounded context for source tokens relevant to:

- Earth-radius/default spherical constants;
- geometric SZA/mu0 mapping and pseudo-spherical/Chapman activation;
- layer/radius and Chapman-factor construction;
- top-of-atmosphere and model-bottom handling;
- `altitude`, `atm_z_grid`, aerosol optical-depth scaling and truncation/rebasing pathways;
- `rte_solver null` versus `sdisort` setup paths;
- direct-output/`edir` semantics;
- exponential/underflow handling.

Token capture is discovery evidence only. A token hit does not itself resolve scientific equivalence.

## Frozen outcomes

The source-acquisition stage has only these admissible terminal classes:

- `PASS_PINNED_SOURCE_CAPTURED`: exact build-1 recipe is bound, exact `999e47...` archive bytes are obtained, all six governing files are safely extracted, and source evidence is fingerprinted.
- `FAIL_PINNED_SOURCE_ARCHIVE_DRIFT`: the official URL no longer serves the exact build-1 source bytes. This is a provenance blocker for source interpretation under this identity, not evidence that low-altitude transport is impossible.
- `FAIL_PINNED_RECIPE_DRIFT`: the independently fetched feedstock recipe does not match the frozen commit/version/source-hash/build contract.
- `FAIL_SOURCE_CAPTURE`: exact archive identity passed but a governing file is missing/unsafe/unreadable or evidence generation fails.

No source-acquisition outcome promotes support below 5 degrees.

## After a PASS

Review the captured exact source before any solver comparison and explicitly classify each existing STATE-0003 checklist item. If any item remains unresolved, continue source/runtime audit only. If the source trace is sufficient, freeze a wholly fresh NONPROTECTED equivalence matrix before running `sdisort`; that matrix must be disjoint from all opened protected evidence. A later production/support claim still requires wholly fresh unopened protected validation and exact continuity with the authoritative 5-degree v3.2 seam.
