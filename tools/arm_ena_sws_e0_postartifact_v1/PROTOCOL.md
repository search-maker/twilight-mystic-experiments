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

## Mandatory outer-archive gate before extraction

Before any ZIP extraction or artifact-content parsing, first verify the authorized GitHub run envelope with `verify_authorized_run_envelope_v1.py`, then bind the exact downloaded archive bytes with `verify_downloaded_artifact_zip_v1.py`.

The byte-binding gate is deliberately content-blind. It requires the exact closed run-envelope receipt, hashes the downloaded file as opaque bytes, and requires byte-for-byte SHA-256 equality with GitHub's canonical `artifact.digest`. It refuses missing, empty, non-regular or symlink inputs, does not inspect the ZIP central directory, and emits `zip_contents_inspected=false` and `zip_extracted=false`.

## Mandatory safe extraction gate

Only after the outer-byte gate passes may `extract_sanitized_artifact_zip_v1.py` inspect ZIP structure. The extractor re-hashes the same archive against the closed digest receipt before opening it, then requires the exact seven root-level sanitized filenames, no directories/nested/traversal paths, duplicates, encrypted members, explicit symlink/non-regular Unix file types or unsupported compression methods. Permission-only Unix mode bits with no file-type bits are accepted rather than misclassified as a non-regular member; explicit regular-file mode bits are also accepted. It bounds every uncompressed member to 32 MiB and the total to 64 MiB, extracts only into a fresh directory, removes its own partial output on any failure, and parses no artifact file values. Its receipt keeps protected-result, Stage-B, held-out and science authority false.

Only after safe extraction succeeds may the extracted directory be supplied to the strict content verifier below.

## Integrated offline ingest pipeline

`run_sanitized_ingest_pipeline_v1.py` composes the reviewed gates in exactly that order without contacting GitHub or ARM itself. It accepts already-fetched GitHub run JSON, artifact JSON, a complete workflow-dispatch inventory JSON, and the already-downloaded artifact ZIP. It then performs:

1. exact authorized-run-envelope verification;
2. opaque downloaded-ZIP digest binding to GitHub's canonical artifact digest;
3. bounded safe extraction of the exact seven sanitized files; and
4. strict sanitized-content verification.

The pipeline requires a fresh work directory, writes a separate canonical JSON receipt for every completed gate, SHA-256 binds those receipts in a final success receipt, and emits no final success receipt if a later gate refuses. It cross-checks run/artifact/ref/head/digest identity between stages and requires all protected-result, Stage-B, held-out, science, credential-read, network-access and production authority flags to remain false. An E0 timing/QC disposition is preserved exactly as a result-blind disposition; even `E0_PASS_BLIND_CANDIDATE` is not Stage-B or held-out-opening authority.

This orchestration layer is optional convenience around the mandatory gates, not a broader trust boundary. The individual gates remain authoritative for their own checks.

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
