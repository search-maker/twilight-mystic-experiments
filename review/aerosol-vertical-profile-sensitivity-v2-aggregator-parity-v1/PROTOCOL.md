# AVPS v2 ordinal-41 aggregator parity review

This child is solver-free and result-closed. It follows exact-head PR #606 after the v2 per-case executor parity gate passed.

## Frozen identity

- stage: `aerosol-vertical-profile-sensitivity-v2`
- scientific ordinal: `41`
- execution key: `aerosol-vertical-profile-sensitivity-v2:numerical:41`
- authorization PR/head: `#604` / `d5f5e4d9d19d7ede573fecae68565a92baabbec3`
- execution-control parent: PR `#605`, head `53bfe783f5106252149e9da106ae87b5b6e3f710`
- executor parity parent: PR `#606`, head `c5354ff5aa95669cefbd96c41c54d78e7a6a2f6f`
- case universe: 360 cases, 72 CRN groups, five states per group, 24 analysis cells, three replicates, four primary contrasts per cell
- photon budget: 20,000,000 per case

## What this review adds

Only the v2 aggregate-verification primitive and tests/review needed to prove that completed per-case artifacts can be accepted without silently reverting to the scientifically invalid AVPS v1 aerosol transport representation.

The aggregator must independently rebind the exact authorization/case universe and refuse unless every one of the 360 case artifacts is present exactly once. Each result must be attempt 1, one syntax check plus one solver execution, no retry/resume/GitHub rerun, exact ordinal/execution-key/auth-head identity, exact four-alias runtime identity, and `resultOpeningAuthorized=false` / `productionAuthorized=false`.

For every case, the persisted profile member must be exactly `profiles/<state>.four-species.dat`, its SHA-256 must equal the authorized state hash, the input must contain `aerosol_species_file profiles/<state>.four-species.dat INSO WASO SOOT SUSO`, and no `aerosol_file` directive is accepted. Raw radiance and standard-deviation spectra are hash-verified and the derived channels are recomputed from the raw radiance bytes.

The aggregate output remains closed. It may produce only a complete verified acquisition ledger and a frozen verified-analysis-input envelope after all 360 artifacts pass. It must not interpret partial results, run the frozen analysis, run Level-B, score Taylor/Jerusalem, create a dispatch ref, create a consumed marker, or authorize production.

## Explicit non-goals

This PR does **not** create `dispatch/aerosol-vertical-profile-sensitivity-v2-ordinal-41`, does not post `ORDINAL41_AVPS_V2_DISPATCH_CONSUMED`, does not install or run libRadtran/MYSTIC, does not serialize candidate seed values into tracked scientific state, and does not open any scientific result.

After this exact-head parity review passes, the next safe implementation stage is the attempt-1 v2 science workflow and zero-runtime dispatch publisher, both bound to the reviewed executor and aggregator bytes. Dispatch remains a later fresh gate.