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

## Complete rebind surface identified before any new query result

The audit freezes five result-blind/provenance surfaces that cannot be reused unchanged for a different selected case or a fresh authorization identity:

1. `review/arm-ena-sws-v1-stage0/run_one_ena_sws_schema_probe_v3.py` — legacy portable wrapper/case pin.
2. `tools/arm_ena_sws_e0_postartifact_v1/verify_oneevent_e0_artifact_v1.py` — legacy content verifier/case pin.
3. `tools/arm_ena_sws_e0_postartifact_v1/verify_oneevent_e0_artifact_strict_v1.py` — strict verifier inherits the same case identity through `base.PROBE_CASE_ID`.
4. `tools/arm_ena_sws_e0_postartifact_v1/verify_authorized_run_envelope_v1.py` — historical authority `5575796491`, frozen branch/head, and one-dispatch envelope.
5. `tools/arm_ena_sws_e0_postartifact_v1/run_sanitized_ingest_pipeline_v1.py` — offline ingest cross-checks the legacy case through the strict content verifier and its own case binding.

This is broader than the wrapper alone: the post-artifact verifier, exact run envelope, and complete sanitized ingest chain are also case/authorization-bound.

## Future successor requirements

Before any future E0 successor dispatch can be treated as consumable, a separately reviewed successor package must mechanically cross-bind all of the following to the same accepted freeze receipt and future authorization identity:

- the first-positive query-selected case/date;
- the execution wrapper `--start-case`;
- the producer receipt `probe_case_id`;
- strict content/postartifact verification;
- the authorized GitHub run/artifact envelope;
- sanitized ingest final receipt/probe case;
- the unchanged frozen E0 source head, universe, and protocol.

There must be no fallback to `2017-06-16_dusk`, no reuse of historical authority `5575796491`, no reuse/rerun/retry/resume of consumed runs, and no case choice after protected values are seen. The future exact authorization/main/run identities are intentionally **not** guessed or hard-coded by this preregistration; they must come from a later explicit Coordinator transition.

## Audit behavior

`audit.py` is source-only. It hashes every known legacy rebind surface, confirms the expected hard-pins remain present (so an unexpected source drift fails closed), and confirms the lower frozen runner still forwards remaining arguments without acquiring the legacy one-case hard-pin itself.

A successful audit emits `ARM_E0_SUCCESSOR_REBIND_SURFACE_FROZEN` with the source hashes and explicit false flags for network access, credential reading, native download/opening, protected-value reading, held-out opening, Stage B, MYSTIC/science, and production.

A success receipt is preparation evidence only. It does not authorize authenticated ARM activity or any scientific execution.
