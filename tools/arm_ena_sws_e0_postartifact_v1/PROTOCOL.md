# ARM ENA/SWS one-event E0 sanitized post-artifact ingest v1

This is a result-blind, non-science control-plane consumer for the single authenticated E0 artifact authorized by Issue #60 comment `5575796491`.

It does **not** invoke ARM Live, read credentials, open SWS/SASZE radiance, authorize Stage B, select a scientific case, run MYSTIC, or change any E0 threshold. It exists only so the already-authorized one-event sanitized artifact can be checked immediately when it appears.

## Frozen input identity

- execution ref: `review/arm-ena-sws-v1-stage0`
- execution head: `b8671665a2bf8fe9972b8cb48492abcfa6765140`
- probe case: `2017-06-16_dusk`
- frozen 906-event universe SHA-256: `87933189ff56322ce2b5d2821a1c2ab8094d0a472ef6c690cfbd90cd0451fa41`
- protocol: `ARM_ENA_SWS_V1_STAGE0_E0_RESULT_BLIND_V2`
- expected workflow artifact name: `arm-ena-sws-e0-oneevent-auth-v1`

## Fail-closed ingest contract

The verifier must refuse unless all of the following hold:

1. No `.nc`/`.cdf`, symlink, binary payload, credential-bearing ARM Live URL, access token, or Authorization bearer text is present.
2. `probe_receipt.json` is schema 4 with the frozen purpose/case/universe identity and explicit `protected_variable_values_read=false`, `raw_sws_files_retained=false`, `credentials_persisted=false`, `transport_errors_sanitized=true`, `stage_b_authorized=false`.
3. The receipt manifest covers every non-receipt file exactly once and every recorded size/SHA-256 matches the extracted file. Path traversal and absolute paths are forbidden.
4. The event-universe CSV has the exact frozen SHA-256, 906 rows, and exactly one `2017-06-16_dusk` row.
5. The summary has the exact E0-v2 protocol, 906 candidates, exactly one processed event, 905 remaining, and all holdout/Stage-B firewall flags false.
6. At least one native `kind=sws` schema record exists, with `protected_variable_values_read=false`, source SHA-256 provenance, and metadata-only variable records. Unexpected per-variable keys are refused so a future value-bearing field cannot silently enter this artifact.
7. The ledger contains exactly one pinned case. `SOURCE_FILE_MISSING`, transport/query errors, stream/audit errors, unreadable data, or unknown dispositions are refused and never count as good. A genuine non-photometric E0 timing/QC FAIL may be preserved as a valid result-blind disposition, but it is never promoted to PASS.
8. Provenance contains exactly one pinned case, raw/protected flags false, basename-only source filenames, positive sizes and SHA-256 values represented by SWS schema records.
9. Query-manifest rows are only for `enaswsC1.b1`, the pinned case, with `credentials_persisted=false` and basename-only returned filenames.
10. Output remains an ingest/verifier receipt only. It must always state `stage_b_authorized=false` and `heldout_radiance_opening_authorized=false`.

`missing` never counts as PASS. A verifier PASS is only `SAFE_E0_ONEEVENT_SANITIZED_ARTIFACT_VERIFIED`; it is not Stage-B authority and is not authority to open held-out radiance or to run later native gates.