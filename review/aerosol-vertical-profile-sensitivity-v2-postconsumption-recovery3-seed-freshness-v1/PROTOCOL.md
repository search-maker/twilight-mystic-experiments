# AVPS v2 post-consumption recovery3 — fresh candidate-seed review

Status: **REVIEW-ONLY / ZERO-RUNTIME / NO ORDINAL / NO AUTHORIZATION / NO DISPATCH**

This package implements the first fresh-identity prerequisite required by the merged recovery3 snapshot-fence protocol after consumed ordinal 43 failed before solver runtime. It changes identity/control evidence only; the frozen AVPS v2 science remains 360 cases / 72 common-random-number groups / five independently defined vertical-profile states / 20,000,000 photon histories per case.

## Immutable consumed predecessors

- Ordinal 41: run `33236295233`, attempt 1, pre-solver structural failure; seed canonical `02f624d582e9b2caba6b920d65a5e8a8bc8fc1a2693623bc2f73abf5d3f706d2`.
- Ordinal 42: run `33259899524`, attempt 1, pre-solver relocated seed-ledger path-context failure; native historical seed-ledger blob `491d1b6653bea0fcc5275269723a76aa1af52300`; seed canonical `a514212990a94a39d577bd038b631a600e18e4c0f750f781bbd7c99b897228a7`.
- Ordinal 43: run `33298433506`, attempt 1, exact runtime head `970a566f33fefe80590c84cccf3bbe0b1176ec23`, failure class `PRE_SOLVER_REPOSITORY_GLOBAL_SNAPSHOT_STABILITY_FAILURE`, zero artifacts and zero solver execution; consumed marker Issue #60 comment `5467062055`; recovery2 seed canonical `38c074fe01bd6d09fa7dc78af1ad323e2f42b606ca992c2950b8fc1f5b343a9f`.

All three ordinals, their seeds, authorization/dispatch identities and run identities are permanently non-reusable. Nothing in this review reinterprets any predecessor as numerical vertical-profile evidence.

## Fresh recovery3 candidate identity

The fresh result-blind namespace is:

`aerosol-vertical-profile-sensitivity-v2|postconsumption-recovery3|group-seed|sha256-v1`

For each of the frozen 72 AVPS group IDs, candidate seeds are derived deterministically from SHA-256(namespace, groupId, collisionCounter) into the existing signed-32-bit scanner domain. The collision counter advances only for a within-ledger collision or collision with a consumed ordinal-41/42/43 seed. The preregistered outcome for the deterministic candidate ledger is:

- candidate count: `72`
- seed canonical SHA-256: `d2817b1ea4f2bdc8cb1842e565b099b015e4e28c5874482629fadc450069d9bf`
- row canonical SHA-256: `b6a519eadacdb99ea53c52d483c8acfeba05829643cb988de21682a53fc47896`
- expected collision counters: all zero
- expected overlap with consumed ordinals 41/42/43: zero

These are candidate identities only. Review-time freshness does not allocate/apply a seed and does not authorize science.

## Protected review contract

The exact-head review must:

1. bind the merged recovery3 snapshot-fence protocol blob `4526e5a2703ff3024c465a7b2f109034bd029786` and unchanged AVPS preregistration skeleton;
2. independently validate the consumed ordinal-41 ledger, the ordinal-42 ledger at its native historical authorization-head worktree path, and the consumed ordinal-43 recovery2 ledger;
3. verify the exact terminal attempt-1 failure identities for runs 41/42/43 and the unique ordinal-43 consumed marker;
4. rebuild exactly 72 recovery3 candidates and prove zero overlap with all three consumed seed sets;
5. scan the exact tracked tree and then the complete repository-global collision surface using the unchanged bound two-pass scanner;
6. fail closed on any collision or snapshot instability; no epsilon/exception/metadata-ignore rule may be added to force success;
7. freeze a proof artifact with all authorization/runtime/result/Level-B/holdout/production flags false.

The repository-global review must run only inside an explicit Issue #60 WRITE_QUIET fence. If this first review attempt fails because repository metadata changes between the two complete enumerations, preserve it and use a fresh attempt-1 review head/fence; never GitHub Re-run.

## Dynamic ordinal remains a separate protected observation

This package intentionally does **not** hard-code or allocate ordinal 44. After this seed-freshness package itself passes and is reviewed, the next protected preauthorization gate must freshly enumerate the global scientific-ordinal surface and dynamically derive the next unused ordinal while rechecking these exact candidate seeds. The expected number 44 has no authority until that later global observation passes.

## Scientific and Level-B boundary

No Taylor/Jerusalem residual, protected holdout, desired event time, prior AVPS numerical effect, or mapper residual may influence this namespace, seed set, thresholds, profile states, or later ordinal choice. No solver/runtime/result opening occurs here.

Until a successful future AVPS result is opened through its separately frozen result gate and a separately preregistered component-selective shadow mapper passes held-out direct-MYSTIC validation, `AOD550` remains the only directly consumed validated-v3 aerosol coordinate. Vertical profile, arbitrary spectral AOD, SSA spectrum, phase function and aerosol family/classification remain represented but not newly consumed; every richer `newMappingAuthorized` flag remains `false`.
