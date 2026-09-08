# ARM Stage-A timing-package chain v1

Status: **result-blind / control-plane only / non-science**.

## Purpose

This tool composes the already-merged Stage-A controls into one deterministic package receipt so a future timing-only handoff can be consumed without accidentally mixing evidence from different bytes. It stable-captures the priority CSV, continuity CSV and continuity JSON once, hashes and parses those exact captured bytes, runs the decoded-time continuity verifier and source-file/datastream binding against the same in-memory CSV rows, and binds the package to the frozen Stage-A input lock.

It does not acquire ARM data, open native ARM files, inspect credentials, expose SWS/SASZE held-out radiance, select a scientific case, authorize Stage B, run MYSTIC, allocate or consume an identity/seed/ordinal, or authorize production.

## Frozen component identities

The chain refuses silent drift of its control components. It pins the Git blob identities of:

- `tools/arm_stagea_time_continuity_contract_v1/verify.py` -> `49818b96c8c172d68a4b8d5cdc4e542bc7933c69`
- `tools/arm_stagea_source_file_binding_v1/verify.py` -> `d00895f21f61a3f8d9ad9921a3d50eb46f047b75`
- `tools/arm_stagea_input_lock_v1/input_lock.json` -> `9b3e32b319a1aa29f9de9b4e92ae94ecf3091929`

Any byte change requires an explicit successor/version update; the package never silently follows a changed implementation.

## Input-lock checks

The exact input lock must still say that:

- `ARM_SGP_C1_stageA_priority20.csv` has SHA-256 `345d7023bb4e29e0cc7bb47f1eaaef33636e0bd1719d05e796e3d30cba310ae0` and 20 data rows;
- `ARM_SGP_C1_MINIMAL_NEXT_EXTRACT_REQUEST.md` is provenance-only (`active_execution_contract=false`);
- protected SASZE radiance must remain sealed and the historical extraction request cannot authorize radiance opening;
- the safety boundary remains result-blind, missing native data does not count as PASS, and protected-result/Stage-B/science/production flags remain false.

## Same-consumed-byte composition

For one invocation, the chain:

1. opens each of the three timing-package inputs with fail-closed no-follow regular-file handling and stable-captures its bytes once;
2. computes each receipt SHA-256 from those captured bytes;
3. parses the priority ledger, continuity CSV and continuity JSON from those exact captured bytes rather than reopening live paths;
4. requires CSV/JSON semantic field equivalence;
5. runs the decoded-time continuity contract on the captured CSV rows;
6. runs the source-file/datastream binding on those same in-memory rows;
7. binds both component receipts to the SHA-256 of the exact captured continuity CSV bytes; and
8. records canonical SHA-256 digests of the two component receipts in the final package receipt.

A transient mutate/read/restore of a live pathname after capture cannot change either the parsed rows or the digest recorded in the receipt. A mutation during the stable capture itself is refused by file-identity/size/mtime checks. `same_input_bytes_hashed_and_parsed=true` means the receipt digests are hashes of the bytes actually parsed, not merely equal endpoint path hashes.

A package exit code 0 means only `stagea_timing_package_contract_valid=true`. Real continuity FAIL rows/cases remain FAIL and are preserved in `case_continuity`; they do not make the artifact structurally invalid and they are never promoted to scientific PASS.

## Fail-closed receipt boundary

The final receipt hard-keeps:

- `scientific_pass_inferred=false`
- `missing_native_data_counts_as_pass=false`
- `protected_results_opened=false`
- `heldout_sws_sasze_radiance_opened=false`
- `heldout_radiance_opening_authorized=false`
- `stage_b_authorized=false`
- `science_execution_authorized=false`
- `production_authorized=false`

The currently unresolved `stageA_actual_time_continuity_v2.csv` remains only `NOT_LOCATED_IN_CURRENT_LIBRARY_SEARCH` until independently supplied or located. This chain is prestaged so those timing-only bytes can be audited immediately when available without opening protected radiance.
