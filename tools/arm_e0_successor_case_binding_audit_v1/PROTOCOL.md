# ARM E0 successor case-binding audit v1

## Purpose

This is a result-blind, non-science preregistration of the source surfaces that must be rebound before any future query-selected ARM ENA/SWS E0 successor can be executed or consumed. It performs no ARM Live query/download, reads no credential values, opens no SWS/SASZE radiance, and grants no Stage B, MYSTIC/science, or production authority.

The audit exists because the already-spent one-event E0 lane is intentionally pinned to `2017-06-16_dusk` and to its historical authorization/run envelope. A future metadata-selected successor must not silently reuse those bindings for another case.

## Frozen science identity preserved

The audit does not alter the frozen E0 scientific semantics:

- source ref: `review/arm-ena-sws-v1-stage0`
- source head: `b8671665a2bf8fe9972b8cb48492abcfa6765140`
- 906-event universe SHA-256: `87933189ff56322ce2b5d2821a1c2ab8094d0a472ef6c690cfbd90cd0451fa41`
- protocol: `ARM_ENA_SWS_V1_STAGE0_E0_RESULT_BLIND_V2`

The lower frozen runner remains capable of receiving a selected `--start-case` through its forwarded argument surface. The legacy portable wrapper, however, hard-pins `PROBE_CASE_ID = "2017-06-16_dusk"` and supplies that value to `--start-case`.

The portable wrapper and lower runner live only on the frozen execution ref; they are intentionally absent from an ordinary current-main checkout. The audit therefore records their immutable Git blob identities (`d8c29b09b39918415dabc6c9c6cb4110ec4c82c2` and `de0c3978ba3c01c723ff1ff7cd33fee8f840c89d`) without pretending current-main CI re-read absent bytes. A separately materialized frozen-ref checkout can be passed through `--frozen-source-root` to reverify the exact wrapper/runner tokens fail-closed.

## Complete rebind surface identified before any new query result

The audit freezes seven result-blind/provenance surfaces that cannot be reused unchanged for a different selected case or a fresh authorization identity:

1. frozen-ref `review/arm-ena-sws-v1-stage0/run_one_ena_sws_schema_probe_v3.py` — legacy portable wrapper/case pin;
2. `tools/arm_ena_sws_e0_postartifact_v1/verify_oneevent_e0_artifact_v1.py` — legacy content verifier/case pin;
3. `tools/arm_ena_sws_e0_postartifact_v1/verify_oneevent_e0_artifact_strict_v1.py` — strict verifier inherits the same case identity through `base.PROBE_CASE_ID`;
4. `tools/arm_ena_sws_e0_postartifact_v1/verify_authorized_run_envelope_v1.py` — historical authority `5575796491`, frozen branch/head, and one-dispatch envelope;
5. `tools/arm_ena_sws_e0_postartifact_v1/verify_downloaded_artifact_zip_v1.py` — downloaded-ZIP digest receipt is also bound to the historical authority/branch/head;
6. `tools/arm_ena_sws_e0_postartifact_v1/extract_sanitized_artifact_zip_v1.py` — safe-extraction receipt is likewise bound to the historical authority/branch/head;
7. `tools/arm_ena_sws_e0_postartifact_v1/run_sanitized_ingest_pipeline_v1.py` — offline ingest cross-checks the legacy case through the strict content verifier and its own case binding.

This is broader than the wrapper alone: the content verifiers, exact run envelope, ZIP-digest gate, extraction gate, and complete sanitized ingest chain are all case/authorization-bound.

## Future successor requirements

Before any future E0 successor dispatch can be treated as consumable, a separately reviewed successor package must mechanically cross-bind all of the following to the same accepted freeze receipt and future authorization identity:

- the first-positive query-selected case/date;
- the execution wrapper `--start-case`;
- the producer receipt `probe_case_id`;
- strict content/postartifact verification;
- the authorized GitHub run/artifact envelope;
- downloaded-artifact digest and safe-extraction receipts;
- sanitized ingest final receipt/probe case;
- the unchanged frozen E0 source head, universe, and protocol.

There must be no fallback to `2017-06-16_dusk`, no reuse of historical authority `5575796491`, no reuse/rerun/retry/resume of consumed runs, and no case choice after protected values are seen. The future exact authorization/main/run identities are intentionally **not** guessed or hard-coded by this preregistration; they must come from a later explicit Coordinator transition.

## Audit behavior

`audit.py` is source-only. In an ordinary current-main checkout it hashes and verifies all six current-tree legacy rebind surfaces and records the immutable frozen-ref wrapper/runner Git blob identities as external frozen evidence. With `--frozen-source-root`, it additionally hashes and token-verifies the separately materialized frozen wrapper and lower runner, including the runner's selected-case passthrough and absence of the legacy one-case hard-pin.

A successful audit emits `ARM_E0_SUCCESSOR_REBIND_SURFACE_FROZEN` with explicit false flags for network access, credential reading, native download/opening, protected-value reading, held-out opening, Stage B, MYSTIC/science, and production.

A success receipt is preparation evidence only. It does not authorize authenticated ARM activity or any scientific execution.

## Result-blind successor rebind plan

`build_rebind_plan_v1.py` preregisters the next boundary without applying any source change. It consumes only the sanitized query-only receipt, the zero-runtime exact-executable stress receipt, the exact frozen 25-case manifest, and externally verified GitHub provenance supplied as explicit arguments. It contains no default current-main SHA and no default future authorization comment.

The planner is fail-closed. It requires the exact manifest digest `8a0756be59dac59cd8ad4fab77e499ec19069e24d2d2a636fa4352713b550def`, exact closed receipt schemas, `workflow_dispatch` on an explicitly supplied `refs/heads/main` SHA, fresh attempt 1, artifact IDs/digests, and a single-line exact Coordinator authorization title. It accepts only `FIRST_NATIVE_FILENAME_RESOLVED`, verifies that every earlier ordered case has zero matches, verifies that the final checked case is the first positive case, and verifies filename/date consistency. Exhaustion, query failure, schema widening, earlier positives, wrong-date filenames, forbidden activity flags, non-main query dispatch, or a non-fresh attempt are refusals.

A successful plan preserves the frozen science source `review/arm-ena-sws-v1-stage0@b8671665a2bf8fe9972b8cb48492abcfa6765140`, the frozen 906-event universe and protocol, and enumerates the same seven rebind surfaces above. It deliberately does **not** populate a future E0 execution authorization/ref/head: those remain required future bindings from a later explicit Coordinator transition. It does not edit the wrapper or any verifier, does not download/open ARM data, and does not grant held-out opening, Stage B, MYSTIC/science, or production authority.

The planner output is therefore a deterministic result-blind plan only, not a dispatch instruction and not an authorization. A later successor package must be separately reviewed and must prove that all seven bindings were applied consistently before any future authenticated E0 can be treated as consumable.

## Guarded authorization provenance v2

`build_rebind_plan_guarded_v2.py` wraps the v1 plan with an additional governance/provenance gate. This gate exists because a separately supplied authorization comment ID or title is not sufficient evidence that the exact zero-runtime stress run actually saw that authorization in the authoritative Issue #60 ledger.

The guarded planner therefore requires the claimed future query authorization comment ID to appear in the stress receipt's exact `arm_relevant_comment_ids_after_baseline`, to be the latest ARM-relevant governance ID in that receipt, to lie strictly after the recorded baseline and not beyond the stress receipt's latest Issue #60 comment ID, and never to reuse consumed historical authority `5575796491`.

It additionally consumes an exact Issue #60 comments snapshot as GitHub provenance. The snapshot is canonicalized with the same ordered `{id,body}` projection used by the query-only `stress.py`; its count, latest ID, and SHA-256 must reproduce `issue60_comment_count`, `issue60_latest_comment_id`, and `issue60_ledger_sha256` from the stress receipt. Only then is the claimed authorization comment located in that bound snapshot. Its actual first nonempty line must exactly equal the supplied title, must be a direct `COORDINATOR::ARM...` query transition, must contain explicit positive `AUTHORIZED`/`AUTHORIZATION_GRANTED`/`AUTHORITY_GRANTED` semantics, and must not contain false, revoked, request, pending, proposed, expired, or second-attempt semantics.

This prevents an owner request, stale allowed control, or unrelated Coordinator line from being relabeled after the fact as query authority. Ledger bodies are used only for exact provenance verification and are never copied into the emitted rebind plan. The guarded plan remains result-blind and non-authorizing: it performs no ARM query/download, reads no credential values, opens no protected SWS/SASZE values, applies no source rebind, and grants no E0 execution, held-out opening, Stage B, MYSTIC/science, or production authority.
