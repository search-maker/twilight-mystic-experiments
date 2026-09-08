# ARM Stage-A input lock v1

Result-blind / non-science / no protected-radiance opening.

## Purpose

This directory pins exact raw-byte provenance for the existing ARM SGP C1 Stage-A ranking/window inputs and preserves the historical extraction-request document as provenance. It prevents later ingest/QC work from silently substituting a different candidate ledger or silently treating an older extraction instruction as current authority.

The lock does **not** select a scientific validation case, authorize Stage B, authorize SWS/SASZE held-out radiance opening, authorize MYSTIC/solver execution, or convert missing data into PASS.

## Locked inputs

The exact byte hashes, sizes and row counts are recorded in `input_lock.json` for:

- `ARM_SGP_C1_stageA_priority20.csv`
- `ARM_SGP_C1_MINIMAL_NEXT_EXTRACT_REQUEST.md`
- `ARM_SGP_C1_stageA_twilight_extract_windows.csv`

The files were located in the user's ChatGPT Library, materialized as raw bytes, and hashed without rewriting them.

### Governance supersession of the historical extract request

`ARM_SGP_C1_MINIMAL_NEXT_EXTRACT_REQUEST.md` is retained here **only as a historical provenance source**, not as an active execution contract. Inspection of its current Library bytes shows that its Stage-A SASZE section requests fixed-band `zenith_radiance_*nm` extraction. Current Issue #60 governance is stricter: protected SWS/SASZE radiance remains sealed unless an exact later gate explicitly permits opening it.

Therefore any radiance-bearing instruction in that historical document is superseded for this lane. The document can support non-protected provenance, candidate-window identity, and metadata/QC preparation only where those actions are independently permitted by current Issue #60 governance. It can never be cited as authority to inspect, extract, transport, open, or classify protected SASZE radiance.

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

Any downstream Stage-A package claiming this v1 lock must reproduce the exact hashes in `input_lock.json`. A changed byte requires a new explicit lock/version. Missing native data never counts as PASS. No file or result in this lock authorizes protected SWS/SASZE radiance opening, Stage B, MYSTIC/science, seed/identity/ordinal allocation, or production. When historical text conflicts with newer Issue #60 governance, the newer authoritative governance controls and this lock fails closed.
