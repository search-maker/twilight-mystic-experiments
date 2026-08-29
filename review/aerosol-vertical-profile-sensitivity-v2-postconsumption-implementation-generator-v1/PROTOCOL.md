# AVPS v2 post-consumption recovery1 implementation generator v1

Status: **review-only / zero runtime / no dispatch / results closed**.

This package advances the reviewed ordinal-42 recovery after merged execution-delta control `83ee3dba1ddf371cd0dd30a3e6436ca5049b22b0`. It does not place an executable recovery workflow on `main`. Instead it deterministically generates three candidate workflow files as a CI artifact from already-reviewed ordinal-41 transport templates:

1. `avps-v2-postconsumption-recovery1-science.yml`;
2. `avps-v2-postconsumption-recovery1-dispatch-publisher.yml`;
3. `avps-v2-postconsumption-recovery1-publisher-trigger-bridge.yml`.

The generator may change only recovery identity/provenance transport required by the merged execution-delta contract. Frozen scientific design remains unchanged: 360 cases, 72 common-random-number groups, five profile states, 20,000,000 photon histories/case, the exact four-species profile bytes, geometry/AOD/wavelength grid, executor, aggregator, stopping and analysis rules.

Fresh identity bindings are:

- scientific ordinal `42`;
- authorization head `e627a689ada0493a8a5b9cdafc4aba0198fbabec`, parent `a68f603d6da21cd28ab8324da080cc8ad27f9094`, Draft PR #629;
- authorization review run `33250602685`, artifact `9714316591`, digest `sha256:083d7127a1591810870875d1b6c15f795c1fee0996c1dadaec5838b785bce8c2`;
- execution key `aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery1:numerical:42`;
- dispatch branch `dispatch/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery1-ordinal-42`;
- candidate-seed canonical SHA-256 `a514212990a94a39d577bd038b631a600e18e4c0f750f781bbd7c99b897228a7`;
- fresh seed ledger Git blob `491d1b6653bea0fcc5275269723a76aa1af52300`, loaded byte-exactly from the authorization lineage and used only in-memory/temporary workspace state.

The generator deliberately does **not** merge the authorization PR or serialize the fresh seed values into tracked science state. It replaces the old main-local authorization/seed assumptions with exact fetched authorization-lineage byte checks. It also scopes workflow uniqueness checks to the fresh recovery workflow identity.

## Review gate

The dedicated review must run on attempt 1, exact branch/head, and exact three-file review-only scope. It must verify the merged execution-delta control exists byte-identically, verify source workflow blobs, run the generator, prove all three candidate workflows were emitted, prove the new identity tokens and closed-result boundaries, prove no old ordinal-41 authorization/dispatch/seed identity remains in the generated candidates, and upload only the generated candidate files plus manifest as review evidence.

No generated candidate is executable merely because this review passes. After PASS, the next safe stage is a separate publication PR that copies the exact artifact-reviewed candidate bytes into `.github/workflows/`, with another exact-byte/zero-runtime review. Only after publication may a one-use marker activate the reviewed trigger bridge; the publisher must recheck authorization, allocation-marker cardinality, absence of consumed marker/dispatch branch/prior recovery science run, fresh repository-global candidate-seed collision state, and exact implementation-review receipt before creating the dispatch ref and consumed marker once and requesting the fresh science workflow.

No MYSTIC/libRadtran/uvspec execution, result opening, Level-B opening, Taylor/Jerusalem scoring, protected holdout opening, retry/resume/GitHub Re-run, production/default change, or consumed-identity reuse is authorized here.
