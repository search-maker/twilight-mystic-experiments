# AVPS v2 post-consumption recovery2 seed freshness

Status: **REVIEW ONLY / CANDIDATE SEEDS ONLY / NO ORDINAL / NO AUTHORIZATION / NO RUNTIME**

This is the first gate after merged recovery2 science-transport protocol commit `b5784f0b9dd98a84b9798f6419229c1bf915b2b3`. It creates a fresh deterministic candidate CRN-group seed namespace for a later AVPS v2 recovery while preserving the previously frozen 360-case scientific design unchanged.

## Consumed identities

Two prior AVPS v2 scientific identities are permanently consumed and may not be reused:

- ordinal 41 / run `33236295233`, attempt 1 — pre-runtime structural failure;
- ordinal 42 / run `33259899524`, attempt 1 — pre-runtime seed-ledger path-context failure after exact one-use dispatch consumption.

Their dispatch identities, execution keys, authorization identities, workflow attempts and candidate seed sets are non-reusable. Neither failure provides a vertical-profile numerical conclusion.

## Fresh seed namespace

The only new scientific-identity material frozen here is the deterministic candidate namespace:

`aerosol-vertical-profile-sensitivity-v2|postconsumption-recovery2|group-seed|sha256-v1`

It is applied to the exact previously preregistered 72-group universe in canonical group order. Each group derives one signed-32-bit scanner-visible seed from SHA-256 of

`<namespace>|groupId=<groupId>|counter=<counter>`

using the same minimum/range/collision-counter algorithm as the two prior reviewed seed ledgers. No candidate seed value is tracked in Git or written in this protocol.

Expected identities, frozen before repository-global collision inspection:

- candidate seed count: `72`;
- candidate seed canonical SHA-256: `38c074fe01bd6d09fa7dc78af1ad323e2f42b606ca992c2950b8fc1f5b343a9f`;
- candidate row canonical SHA-256: `a88b28dcfaaeb354f294d1705a0f8ddbcd061083f277a038ab8c9dace44d9954`;
- all within-ledger collision counters: zero;
- overlap with consumed ordinal-41 seed set: zero;
- overlap with consumed ordinal-42 seed set: zero.

The ledger independently revalidates the known consumed seed identities before accepting the fresh candidate set:

- ordinal-41 canonical seed SHA-256 `02f624d582e9b2caba6b920d65a5e8a8bc8fc1a2693623bc2f73abf5d3f706d2`;
- ordinal-42 canonical seed SHA-256 `a514212990a94a39d577bd038b631a600e18e4c0f750f781bbd7c99b897228a7`.

## Frozen science preserved

This seed review changes no scientific design. A later recovery must preserve the already-reviewed AVPS v2 experiment unless a separate pre-result scientific preregistration explicitly changes it:

- 360 cases;
- 72 common-random-number groups;
- five independently selected OPAC vertical-profile states per group;
- 20,000,000 photon histories per case;
- fixed AOD550 levels 0.10 and 0.30;
- solar depressions 2, 4, 6 and 8 degrees;
- three frozen geometries and three CRN replicates;
- 380–780 nm at 1-nm calculation grid;
- fixed `continental_average` four-species optical family and the #596-validated `aerosol_species_file ... INSO WASO SOOT SUSO` transport;
- unchanged estimators, aggregation, Level-B propagation, classification and result-opening rules;
- no Taylor/Jerusalem residual use for seed generation, design, thresholds, profile selection or recovery choices.

## Required review

The exact-head review must remain solver-free and must:

1. bind exact base main `b5784f0b9dd98a84b9798f6419229c1bf915b2b3` and the merged recovery2 transport protocol;
2. re-prove run 41 and run 42 are immutable attempt-1 terminal failures with exactly one consumed marker each and no reusable scientific identity;
3. reconstruct the exact frozen 72-group universe and revalidate both consumed seed identities;
4. derive the new 72-seed candidate set in memory/artifact only;
5. prove zero overlap with both consumed seed sets;
6. scan the exact tracked tree for candidate-seed literals;
7. perform the unchanged snapshot-fenced two-pass repository-global collision scan;
8. require zero candidate collisions and stable repository-global enumeration.

Any metadata movement during the snapshot fence is a fail-closed review failure, not permission to weaken the scanner.

## Non-authorizations

PASS means only that the fresh candidate seed set may proceed to a separate dynamic global preauthorization/ordinal gate. PASS does **not**:

- allocate or reserve ordinal 43 or any other ordinal;
- create an authorization or dispatch identity;
- apply candidate seeds to tracked scientific cases;
- execute libRadtran, `uvspec` or MYSTIC;
- open AVPS numerical results or Level-B consequences;
- open a protected holdout;
- authorize a richer Operational Atmosphere State v2 mapper;
- authorize Taylor/Jerusalem fitting;
- change production behavior.

The next unused global scientific ordinal must be derived dynamically by a later fresh preauthorization scan. Ordinal 43 is not assumed here.
