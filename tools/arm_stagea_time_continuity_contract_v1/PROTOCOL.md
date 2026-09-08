# ARM Stage-A decoded-time continuity contract v1

Status: **result-blind / control-plane only / non-science**.

This tool prepares consumption of the already-frozen `stageA_actual_time_continuity_v2.csv` + JSON handoff. It does not acquire ARM data, inspect credentials, open SWS/SASZE held-out radiance, select a scientific case, authorize Stage B, run MYSTIC, allocate an identity/seed/ordinal, or authorize production.

## Frozen source rules

The active Issue #60 Stage-A continuity rule requires:

1. Decode real sample times from native source coordinates (`time` plus units/calendar when available, otherwise valid ARM `base_time` + `time_offset`). Filename dates and global `time_coverage_*` attributes are diagnostic only and cannot satisfy the gate.
2. Remove masked/non-finite times for calculations while preserving their count and duplicate count; sort unique UTC sample times and retain contributing source filenames and SHA-256 values.
3. For each priority case define `core_start=min(t_minus8,t_minus6)` and `core_end=max(t_minus8,t_minus6)` without assuming dawn/dusk ordering.
4. Permit contributing files across adjacent UTC dates; do not restrict by filename date.
5. For each mandatory stream require a decoded sample at/before the core start, a decoded sample at/after the core end, and `max_gap_s <= 2 * median_positive_cadence_s` over the bracketed interval.
6. HSRL PASS is allowed only for corrected `code_version=2.6.7` in this v1 verifier. Any later release needs a separately reviewed supersession binding rather than an inferred version comparison.
7. A case continuity result is PASS only when all five mandatory streams PASS. The screening SASZE stream is filterbands only; full SASZE VIS/NIR spectra remain sealed.

Mandatory streams in this verifier are canonicalized to:

- `sasze_filterbands` (`sgpsaszefilterbandsC1.a1` alias accepted)
- `hsrl` (`sgphsrlC1.a1`)
- `rlprofbe` (`sgprlprofbeC1.c1`)
- `arscl` (`sgparsclkazr1kolliasC1.c0`)
- `ceil` (`sgpceilC1.b1`)

The machine-readable handoff must contain exactly 20 x 5 = 100 rows and the frozen minimum fields:

`case_id`, `stream`, `core_start_utc`, `core_end_utc`, `source_files`, `source_sha256s`, `decoded_time_basis`, `code_version`, `sample_count_core`, `left_bracket_utc`, `right_bracket_utc`, `left_bracket_delta_s`, `right_bracket_delta_s`, `median_positive_cadence_s`, `max_gap_s`, `duplicate_count`, `nonfinite_or_masked_count`, `continuity_pass`, `failure_reason`.

The priority ledger is bound to exact raw SHA-256 `345d7023bb4e29e0cc7bb47f1eaaef33636e0bd1719d05e796e3d30cba310ae0` and 20 rows, matching the merged Stage-A input lock.

## Verifier semantics

`verify.py` checks only deterministic provenance/shape/timing consistency:

- exact priority-ledger hash and 20 unique `(date,event)` cases;
- exact 100-row / five-stream coverage;
- core bounds recomputed from frozen `t_minus6_utc` / `t_minus8_utc`;
- CSV/JSON semantic field equivalence;
- source file/hash pairing and lowercase SHA-256 syntax;
- decoded-time basis cannot claim filename or `time_coverage_*` as the gate basis;
- bracket timestamps/deltas, positive median cadence, and the frozen `2 x cadence` condition;
- HSRL PASS requires `code_version=2.6.7`;
- a declared PASS that violates any frozen necessary condition is rejected;
- a FAIL must retain a nonempty failure reason.

A verifier exit code 0 means **artifact contract valid**, not scientific PASS. Real FAIL rows/cases are preserved and do not make the artifact invalid. Missing native data never counts as PASS.

The receipt hard-keeps:

- `scientific_pass_inferred=false`
- `protected_results_opened=false`
- `heldout_sws_sasze_radiance_opened=false`
- `heldout_radiance_opening_authorized=false`
- `stage_b_authorized=false`
- `science_execution_authorized=false`
- `production_authorized=false`

## Current unresolved input

At preparation time, an exact Library search still had not located `stageA_actual_time_continuity_v2.csv`. Its status remains only `NOT_LOCATED_IN_CURRENT_LIBRARY_SEARCH`, never MISSING/PASS/FAIL. This verifier is prestaged so that a future supplied timing-only artifact can be audited immediately without opening protected radiance.
