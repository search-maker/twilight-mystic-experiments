# ARM Stage-A input lock v1

Result-blind / non-science / no protected-radiance opening.

## Purpose

This directory pins the exact raw-byte provenance of the existing ARM SGP C1 Stage-A ranking and extraction inputs so later ingest/QC work cannot silently substitute a different candidate ledger or extraction contract.

The lock does **not** select a scientific validation case, authorize Stage B, authorize SWS/SASZE held-out radiance opening, authorize MYSTIC/solver execution, or convert missing data into PASS.

## Locked inputs

The exact byte hashes, sizes and row counts are recorded in `input_lock.json` for:

- `ARM_SGP_C1_stageA_priority20.csv`
- `ARM_SGP_C1_MINIMAL_NEXT_EXTRACT_REQUEST.md`
- `ARM_SGP_C1_stageA_twilight_extract_windows.csv`

The files were located in the user's ChatGPT Library, materialized as raw bytes, and hashed without rewriting them.

## Deterministic relationship check

The 20 priority rows were compared against the 190-row Stage-A window ledger using `(local_civil_date, event)` as the event key. All 20 keys occur exactly once in the 190-row ledger. For every priority row, the following fields matched the corresponding full-ledger row exactly:

- `window_start_utc`
- `window_end_utc`
- `t_minus6_utc`
- `t_minus7_utc`
- `t_minus8_utc`
- `t_minus12_utc`
- `nearest_sonde_file`
- `nearest_sonde_delta_min`

This is a provenance/consistency check only. It is not a cloud/aerosol/radiance quality decision.

## Unresolved continuity artifact

An exact-title Library search did not locate `stageA_actual_time_continuity_v2.csv` in the current search surface. Its status is therefore only `NOT_LOCATED_IN_CURRENT_LIBRARY_SEARCH`. It must never be treated as scientifically missing, failed, or passed merely because the current search did not locate it.

## Fail-closed boundary

Any downstream Stage-A package claiming this v1 lock must reproduce the exact hashes in `input_lock.json`. A changed byte requires a new explicit lock/version. Missing native data never counts as PASS. No file or result in this lock authorizes protected SWS/SASZE radiance opening, Stage B, MYSTIC/science, seed/identity/ordinal allocation, or production.
