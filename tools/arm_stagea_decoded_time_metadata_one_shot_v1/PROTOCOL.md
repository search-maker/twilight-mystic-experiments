# ARM Stage-A decoded-time metadata one-shot v1

Status: **installed control plane only / result-blind / no current dispatch authority**.

This tool implements the frozen non-authorizing request contract with raw SHA-256 `5ec3fb6b052d886091a77704bf425abcb0d04ea4279727c3a37b4f5ab6e63318` and the exact 20-row priority ledger SHA-256 `345d7023bb4e29e0cc7bb47f1eaaef33636e0bd1719d05e796e3d30cba310ae0`.

A future `workflow_dispatch` is fail-closed before credentials unless a newer direct Issue #60 Coordinator claim has the exact first line `COORDINATOR::ARM_STAGEA_DECODED_TIME_METADATA_ONE_SHOT_V1_AUTHORIZED` and literal bindings for the installed workflow blob SHA, current main SHA, workflow path, event, ref, run attempt 1, request-contract SHA, one-shot semantics, and `protected_scope=DECODED_TIME_METADATA_ONLY`. A direct revocation with the matching exact revocation title supersedes authorization. Other-lane comments do not count as Stage-A direct claims.

The protected runtime, if separately authorized later, may download native files only to a temporary directory and read only decoded time-coordinate inputs (`time`, or `base_time` + `time_offset`, including time units/calendar) plus the explicitly allowed HSRL global processing/provenance/calibration metadata and presence-only QC variable names. HSRL continuity PASS requires the exact observed code-version set `{2.6.7}`. Science arrays, SASZE radiance, Stage B, model execution, Taylor/Jerusalem selection or tuning, and production are not implemented or authorized. Native files and raw time arrays are not artifacts.

The final continuity CSV/JSON is exactly 20 cases x 5 mandatory streams = 100 rows with the frozen 19-column schema. The merged Stage-A package-chain verifier is run on those outputs before a successful dispatch can be classified as clean. A sanitized closed-schema receipt and credential-free pre/post governance receipts are the only additional artifacts.
