# ARM SGP C1 Stage-A decoded-time continuity intake v1

This is **result-blind, non-science preregistration** for a future Stage-A screening package. It does not query ARM, inspect credentials, read any SASZE/SWS/other scientific values, select cases, open held-out radiance, authorize Stage B, run MYSTIC, fit Taylor/Jerusalem, allocate identities/seeds/ordinals, or authorize production.

## Frozen external metadata inputs

The verifier binds the raw bytes of the already-existing ChatGPT Library planning assets without copying those assets into the repository:

- `ARM_SGP_C1_stageA_priority20.csv` raw SHA-256 `345d7023bb4e29e0cc7bb47f1eaaef33636e0bd1719d05e796e3d30cba310ae0`; exactly 20 extraction-priority dawn/dusk windows.
- `ARM_SGP_C1_MINIMAL_NEXT_EXTRACT_REQUEST.md` raw SHA-256 `96ba04ad1e5f8c7f6c8f3ffd2bbf2116fb5137de9e88d716de3d73c8e75c5996`; its Stage-A purpose is objective residual-blind screening before any MYSTIC comparison.

The priority list is an **extraction queue, not final case selection**.

## Why this layer exists

The older order-268668 processor records global `time_coverage_start` / `time_coverage_end` metadata. That is useful provenance but it is not proof that decoded native time samples actually populate every requested twilight window. A previously expected generated artifact named `stageA_actual_time_continuity_v2.csv` has not been located in the current Library search; that state is only `NOT_LOCATED_IN_CURRENT_LIBRARY_SEARCH`, never a scientific `MISSING` verdict and never PASS.

This verifier therefore preregisters a narrow future continuity-evidence schema. It refuses metadata-only substitution and requires one evidence row for every exact priority case x each of five screening streams: SASZE VIS timing metadata, corrected HSRL, RLPROFBE, ARSCL and CEIL.

## Continuity-evidence schema

Exact columns:

`case_id,stream,source_filename,source_sha256,native_time_decode_status,decoded_time_vector_sha256,decoded_sample_count,window_overlap_sample_count,first_overlap_sample_utc,last_overlap_sample_utc,max_gap_seconds_within_window,metadata_time_coverage_used_as_substitute,protected_values_read,science_values_read,hsrl_code_version`

The producer must compute these fields from decoded native time coordinates only. The verifier requires:

- exact 20 x 5 = 100 case/stream rows, with no unknown, missing or duplicate identity;
- exact source basename from the frozen priority ledger and SHA-256 provenance;
- `native_time_decode_status=DECODED_NATIVE_TIME`;
- a SHA-256 for the ordered decoded-time vector and positive decoded/overlap counts;
- first/last overlap timestamps inside the frozen case window, plus a recorded finite nonnegative maximum internal gap;
- `metadata_time_coverage_used_as_substitute=false`;
- `protected_values_read=false` and `science_values_read=false`;
- HSRL `code_version=2.6.7` exactly for this frozen v1 gate; any later superseding release needs an explicit reviewed transition rather than silent acceptance.

This v1 verifier intentionally **does not classify the recorded maximum gap against a scientific threshold**. It proves only structural/provenance readiness from decoded sample times. Therefore even a verifier success is not a statement that any case is scientifically acceptable.

## Fail-closed authority boundary

A successful receipt is only:

`ARM_SGP_STAGEA_DECODED_TIME_CONTINUITY_EVIDENCE_VERIFIED_RESULT_BLIND`

The receipt always leaves case selection, Stage B, held-out-radiance opening, science execution and production unauthorized. Missing/unreadable/no decoded-time evidence cannot count as good. Any future scientific continuity threshold, case ranking/selection, or Stage-B transition requires separate explicit governance.
