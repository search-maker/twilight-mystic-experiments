# AVPS v2 ordinal 41 execution-control gate

Status: **review-only / solver-free / no dispatch / results closed**.

This gate follows the successful attempt-1 authorization review for PR #604 and the single exact Issue #60 allocation marker for scientific ordinal 41. It does not create the dispatch ref and it does not install or run libRadtran/MYSTIC.

## Bound authorization identity

- stage: `aerosol-vertical-profile-sensitivity-v2`
- scientific ordinal: `41`
- execution key: `aerosol-vertical-profile-sensitivity-v2:numerical:41`
- authorization PR: `#604`, Draft/open/unmerged
- authorization head: `d5f5e4d9d19d7ede573fecae68565a92baabbec3`
- authorization parent/control head: `b3d562222a38fc9d1ff5d218886afdda72c37fa2`
- authorization JSON blob: `dcfbd39081abe8e98604eedd48a1d934cea5483a`
- authorization review run: `33218101573`, attempt 1, SUCCESS
- authorization review artifact: `9704345296`
- artifact digest: `sha256:fdabe0425c3de893866c25f14b0da1e0038a8e6498b83a281fcae0e773e605d4`
- allocation marker: `ORDINAL41_AVPS_V2_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED commit=d5f5e4d9d19d7ede573fecae68565a92baabbec3 parent=b3d562222a38fc9d1ff5d218886afdda72c37fa2 pr=604`

The marker allocates ordinal 41. It does **not** consume or dispatch it. The only permitted consumed marker is `ORDINAL41_AVPS_V2_DISPATCH_CONSUMED`, and that marker must remain absent until an independently reviewed publisher has actually created the exact dispatch ref.

## Scientific design remains unchanged

This gate is not a second scientific preregistration. It binds the already reviewed v2 protocol. The physical/numerical screen remains exactly:

- five independently selected OPAC vertical-profile states;
- fixed `continental_average` four-species optical family (`INSO/WASO/SOOT/SUSO`);
- total AOD550 = 0.10 or 0.30;
- sun-center geometric depression = 2, 4, 6, or 8 degrees;
- the same three target geometries;
- three CRN replicates per cell;
- 72 CRN groups, five states per group, 360 cases total;
- 20,000,000 photon histories per case;
- 380–780 nm at 1 nm calculation grid;
- spherical 1D MYSTIC, VROOM and standard-deviation output;
- primary channels photopic, scotopic and Johnson-V effective radiance;
- four paired alternative/reference contrasts per analysis cell.

No AOD, profile, aerosol family, wavelength, geometry, photon budget, threshold, fitting rule or analysis rule may be changed after results.

## Corrected vertical transport is mandatory

Ordinal 40 is permanently consumed and scientifically non-informative because its intended vertical state did not reach effective solver physics. V2 exists specifically to avoid repeating that failure.

Every scientific v2 case must use the reviewed explicit four-species surface:

```text
aerosol_default
aerosol_species_library OPAC
aerosol_species_file profiles/<state>.four-species.dat INSO WASO SOOT SUSO
aerosol_set_tau_at_wvl 550 <AOD550>
```

A competing `aerosol_file tau`, INSO-only transport, or the earlier synthetic equal-weight capability mixture is forbidden scientifically. The exact rendered four-species profile bytes and SHA-256 for the selected state must be preserved inside each case evidence package and checked again before opening results.

## Execution invariants to implement next

A later child implementation may add an executor, aggregator, dispatch publisher and scientific workflow only if exact-head review proves all of the following:

1. exactly 360 cases and 72 CRN groups are generated from the authorized candidate seed set in memory;
2. all five states inside each CRN group share exactly one fresh authorized seed and no seed collides with prior repository scientific state;
3. one syntax check and one solver execution are possible per case, and retry/resume/GitHub Re-run remain unavailable;
4. each process is isolated as a process group and bounded by a reviewed timeout;
5. the locked libRadtran package, uvspec SHA, AFGL-US bytes, official OPAC archive and four-alias data tree are reverified before solving;
6. every rendered case contains the explicit four-species profile and contains no competing vertical-tau directive;
7. raw 380–780 nm radiance and standard-radiance spectra, inputs, seed, runtime report and SHA maps are preserved;
8. result opening refuses partial case universes or mixed attempts;
9. derived channels are independently recomputable from raw spectra;
10. Level-B propagation uses the unchanged preregistered `human-threshold.mjs` byte identity at `starsvisibility@e0da52eb0a2d5bac333da6572f51df52ea7e676e`, full branch, field factor 3.14;
11. no Taylor/Jerusalem residual or event time is used for selection, fitting or rule changes;
12. no production activation is implied by successful sensitivity execution.

## Reuse boundary

The previous AVPS v1 analysis, Level-B, aggregation and process-group utilities are useful candidate mechanics, but this review does **not** declare them automatically reusable. A later exact-head implementation review must prove parity for:

- the new `avps-v2-` case namespace;
- explicit four-species profile persistence and verification;
- v2 authorization/dispatch markers;
- v2 seed materialization in memory only;
- v2 runtime staging and four-alias tree;
- result-opening refusal when any v2 transport identity is absent.

Only generic mechanics that pass that parity review may be reused byte-for-byte.

## Pre-dispatch transition

A future publisher may create `dispatch/aerosol-vertical-profile-sensitivity-v2-ordinal-41` exactly once only after the implementation gate passes and a fresh pre-dispatch audit proves:

- PR #604 is still Draft/open/unmerged at the exact authorization head;
- the attempt-1 authorization review and exact evidence artifact remain intact;
- exactly one allocation marker exists;
- no consumed marker exists;
- the dispatch branch is absent;
- no ordinal-41 scientific run exists;
- the execution key has never been used;
- the authorized candidate seed canonical identity still passes a repository-global collision recheck;
- the exact reviewed execution implementation is bound.

The publisher must then create the exact dispatch ref, record the consumed marker once, and invoke only the attempt-1 scientific workflow. Any failure after identity consumption is evidence; it does not authorize rerun/retry/reuse.

## Opening boundary

Scientific interpretation is forbidden until a separate result-opening gate verifies the complete immutable 360-case universe, all attempt-1 identities, raw-member hashes, exact four-species profile identities, runtime identities, derived-channel recomputation, frozen analysis and frozen Level-B propagation. No partial-result interpretation, epsilon substitution, p-values, confidence intervals, universal degrees-to-minutes conversion, target-residual scoring or new production materiality threshold is permitted.
