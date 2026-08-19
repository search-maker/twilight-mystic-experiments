# Provenance — aerosol-family-challenge-v2 review R5

## Historical boundary

Historical aerosol-family challenge v1 is preserved conceptually as `PREREGISTERED_NOT_RUN`. Its exact generator/lock source bytes were not recovered from the accessible repository/history surfaces. R6 therefore does not claim byte-equivalence to v1 and does not rewrite v1. The documented 576-case family/season comparison structure is carried forward only as an additive clean-room v2 challenge.

## Public source snapshot

- repository: `search-maker/twilight-mystic-experiments`
- source base main: `34edfef1bb9a236f15e6ed456c3e8ef8871a4fc9`
- source base tree: `a41d45750607bd30d44fc2cc9d43bdf494c3fd7e`

This source-base identity binds reviewed scientific/runtime sources. It is not a claim about the future exact review, authorization or dispatch head.

## Geometry and photon budget

Geometry basis:

- path: `experiments/mystic-batch-v1/manifest.cross-geometry-pilot.proposal.json`
- Git blob: `b006c33eb37bece85d1330d44d56450d9496a447`
- selected view geometry only:
  - g02: target altitude 10°, relative azimuth 30°, observer elevation 0 m;
  - g04: target altitude 30°, relative azimuth 90°, observer elevation 0 m;
  - g06: target altitude 45°, relative azimuth 180°, observer elevation 0 m.

All three selected source geometries are sea-level in the bound manifest. The earlier review description that used 1000/2000 m for g04/g06 was incorrect and has been removed. Sun depression and AOD are refactored into the v2 factorial design. The uniform 20M histories/case budget is a new v2 choice grounded in the reviewed 20M/case pilot budget; it is not claimed as recovered historical-v1 budget.

## Runtime and transport sources

- base scientific adapter Git blob: `f69418843b3265f72c620ad3ff56a2582da461f1`
- base scientific case executor Git blob: `df679e54e2c95aa25f772927b2424d21b555638c`
- scientific execution contract Git blob: `bb4c5b04aef3b717cea27c686a43cd1dbca11803`
- runtime lock Git blob: `8573f62829371a0eb866976a5062ea61dc0767b1`
- exact package: `rubin-libradtran=2.0.6=py312pl5321he9373c2_1`
- runtime lock raw SHA-256: `3b5fbec964642b04c73a6423b3355dbcc4ba5e84f9614f6d74420491bacc20c5`
- uvspec SHA-256: `2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3`
- uvspec help SHA-256: `868aea5af762d968f6f62c4e1472916d25232ed9cab5be112d753b0823d20548`
- libRadtran data-tree SHA-256: `ad30b49177e9c84e46497d69faf0c75e466996b0d0003f1de210289ae9f847d7`
- AFGLUS atmosphere SHA-256: `dab26290ed81c762ed0c607e5dc2d53393c1462a0c3a528bc5e3f5935191cfb5`

A future case executor must receive a runtime identity report produced before the case solver and explicitly stating `scientificSolverExecuted=false`. The report bytes are preserved and hashed in the case evidence.

## Aerosol semantics

The challenge uses the frozen libRadtran 2.0.6 aerosol directive surface:

- haze 1: rural;
- haze 4: maritime;
- haze 5: urban;
- haze 6: tropospheric;
- season 1: spring-summer;
- season 2: fall-winter;
- vulcan 1: background aerosol above 2 km.

The rendered state block is exactly `aerosol_default`, explicit haze, `aerosol_vulcan 1`, explicit season, then `aerosol_set_tau_at_wvl 550 ...`. Thus AOD550 is paired while family/season changes. The view convention remains the pinned source convention: `phi0 0` and `phi` equal to the declared relative azimuth.

## Full-spectrum numerical provenance

The challenge uses the reviewed `reference-vroom-1nm` transport semantics to avoid selecting a geometry-specific ALIS importance center globally.

- full-spectrum executor basis Git blob: `4d4ee9af433157182185784ded162fb139c9fa2d`
- reviewed 1-nm calculation-grid Git blob: `3bb3db96580d555ef758f57cabd6cac55b61cebb`
- calculation grid: 401 nodes, 380–780 nm, 1-nm step
- postprocess grid contract Git blob: `47e90aa128942276e1510305449bb3c58930032e`
- postprocess contract SHA-256: `d7d9c98e5676689959dcc3ffca4778925728df819d3fdbc7e39bfa9be92069a3`
- expected serialized raw radiance/std grid: 8001 nodes, 380–780 nm, 0.05-nm step, 5e-05-nm point tolerance

The 401-node calculation grid and 8001-node serialized output grid are separate contracts. The raw parser follows the reviewed full-spectrum convention of wavelength in the first column and the radiance/std value in the last numeric column, with exact grid validation before channel derivation.

## Derived-channel and analysis provenance

Derived-channel source basis:

- `review/full-spectrum-estimator-pilot-v2/build_full_spectrum_training_handoff.py`
- Git blob: `9bc53956fc4a49935ba2957087d8bf4203b7e8be`

R5 copies only the reviewed CIE photopic/scotopic constants, Bessell-V response, interpolation and trapezoidal channel definitions. It consumes no historical result values as challenge results. Local derived-channel and analysis implementations are raw-hash-bound in `analysis-contract.v3.json`.

The primary uncertainty unit is the three independent paired-seed replicate contrasts after within-group state-vs-baseline pairing. Marginal `mc.rad.std.spc` values are retained only as numerical diagnostics and are never combined by independent quadrature for the CRN contrast. Fractional-change bands and the directional ratio flag are reported separately; the latter marks `>=1.5` or `<=2/3` strong and `>=2` or `<=0.5` very large.

## Seed provenance boundary

The 72 SHA-256-derived group seeds are deterministic candidate identities only. A future preregistration proof must run on the exact published review head and combine:

1. exact `git ls-files` byte scanning, permitting candidate integers only in the explicit self-ledger paths; and
2. repository-global collision scanning over branches, Actions runs/artifact metadata, all-state PRs/issues, repository-wide issue/pull-review/commit comments, and Issue #60.

Raw historical artifact-byte scanning remains an optional forensic enhancement rather than a mandatory gate. Even after preregistration freeze, authorization must repeat the exact-head freshness/identity checks.

## Authorization and dispatch boundary

The authorization document does not and cannot embed the SHA of the Git commit containing itself. It binds the then-live parent commit and all frozen payload bytes while `exactAuthorizationCommit` remains null. The real authorization HEAD is established externally by one-parent Git metadata, exactly one changed authorization path, an attempt-1 zero-runtime same-repository Draft PR review, one exact Issue #60 allocation marker, and a dispatch ref pointing to that reviewed head.

The execution workflow candidate is disabled. No authorization ordinal, execution key, control marker, dispatch ref or solver run is created by this review package.

## Evidence boundary

Future completed cases must preserve exact `case.inp`, input hash, runtime report/hash, seed, syntax/solver logs, raw radiance spectrum/hash, raw MC standard-deviation spectrum/hash, flux/std files, the 1-nm grid, prepared metadata and per-member hashes. No scientific result has been generated or opened by R5.

## Superseded pre-result references

Earlier pre-result analysis contract v2 is retained under `reference/superseded-pre-result/` for audit history. Only `analysis-contract.v3.json` at the package root is active for freeze; `freeze.py` refuses any other analysis-contract filename/version.

## R6 proof persistence and enumeration stability

R6 corrects two review-transport gaps discovered after the R5 clean-room build. First, the review seed-proof workflow now freezes `manifest.frozen.json` and `freeze-record.json` in the same pre-solver run and persists them with the exact seed proof as artifact `aerosol-family-v2-r6-freeze-proof`; the artifact is not considered permanent evidence and must be followed by a byte-preserving evidence-only commit before authorization. Second, repository-global metadata is enumerated completely twice and the canonical external snapshots must match after excluding only the current audit run and artifact metadata generated by that same run. Any concurrent external metadata change makes the audit fail closed.

Because GitHub documents that `workflow_dispatch` only receives events when its workflow file exists on the default branch, R6 does not claim that this proof can run on an unpublished review branch. The intended order is review/merge the non-scientific proof workflow, run it on exact default-branch HEAD, preserve the resulting evidence, then perform a fresh authorization-time audit.
