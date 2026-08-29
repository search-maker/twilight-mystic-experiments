# AVPS v2 ordinal-41 science-workflow deployment review

Status: **REVIEW ONLY / SOLVER FREE / NO DISPATCH**

This child is based on exact reviewed AVPS-v2 aggregate head `b0721b0c17b64251cb388e5d0af4100e8ae23f3d` (PR #608). It implements the deployment mechanics required by the Issue #60 checkpoint after executor and aggregator parity passed. Nothing in this review authorizes a dispatch, consumes ordinal 41, opens a result, runs libRadtran/MYSTIC, opens Level-B, or changes production.

## Frozen identities

- stage: `aerosol-vertical-profile-sensitivity-v2`
- scientific ordinal: `41`
- execution key: `aerosol-vertical-profile-sensitivity-v2:numerical:41`
- authorization branch: `authorization/aerosol-vertical-profile-sensitivity-v2-ordinal-41`
- authorization head: `d5f5e4d9d19d7ede573fecae68565a92baabbec3`
- authorization parent: `b3d562222a38fc9d1ff5d218886afdda72c37fa2`
- authorization PR: `604`
- allocation marker: `ORDINAL41_AVPS_V2_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED commit=d5f5e4d9d19d7ede573fecae68565a92baabbec3 parent=b3d562222a38fc9d1ff5d218886afdda72c37fa2 pr=604`
- future consumed marker: `ORDINAL41_AVPS_V2_DISPATCH_CONSUMED`
- dispatch branch: `dispatch/aerosol-vertical-profile-sensitivity-v2-ordinal-41`
- executor path/blob: `review/aerosol-vertical-profile-sensitivity-v2-executor-parity-v1/executor.py` / `bb1e4276d6383127a6b7e820fc2568d87d5de4b0`
- aggregator path/blob: `review/aerosol-vertical-profile-sensitivity-v2-aggregator-parity-v1/aggregator.py` / `ef24a0d30af3dfb46a6b764f3e426465da870fbe`
- execution-control contract blob: `383db5619849cb499104826801ed82227e6a2ddf`
- candidate-seed canonical SHA-256: `02f624d582e9b2caba6b920d65a5e8a8bc8fc1a2693623bc2f73abf5d3f706d2`
- four-alias data-tree SHA-256: `5e1814dd36cf861fd85477a97607299248f8272268df7bf428d31bbb6aa4354a`
- OPAC archive SHA-256: `11daa1f1f4be0fd4ddf7e881ec2005498049674a1540d37b4b1e8f5e16052c7e`
- uvspec SHA-256: `2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3`

## Deployment architecture

The frozen authorization ref predates the reviewed executor/aggregator/workflow bytes. Therefore the science workflow MUST NOT assume that those later review files exist on the authorization or dispatch ref.

The callable workflow is published on the default branch after this exact-head solver-free review. A later zero-runtime publisher performs a fresh pre-dispatch fence, creates the dispatch branch **pointing exactly to the immutable authorization head**, posts the single consumed marker, persists publisher evidence, and then invokes the default-branch science workflow with the exact dispatch branch as an explicit bound input. The science run independently fetches and verifies the dispatch branch and authorization branch both resolve to the authorization head before any runtime setup or solver work. Reviewed implementation byte identities are verified from the callable/default-branch checkout; authorization bytes are read from the detached authorization commit, never inferred from later review state.

This separation preserves both facts simultaneously: (1) the dispatch identity is the exact frozen authorization head, and (2) the executable implementation is the separately reviewed later byte set.

## Required attempt-1 science behavior

Before runtime setup, the science workflow must fail closed unless all of the following hold:

1. event is `workflow_dispatch`, `run_attempt == 1`, and the explicit dispatch input names exactly `dispatch/aerosol-vertical-profile-sensitivity-v2-ordinal-41`;
2. the remote dispatch branch exists and points exactly to `d5f5e4d9d19d7ede573fecae68565a92baabbec3`;
3. the authorization branch independently points to the same SHA and remains the exact one-file reviewed authorization identity;
4. authorization PR #604 remains Draft/open/unmerged and its exact attempt-1 authorization review evidence remains PASS;
5. exactly one allocation marker and exactly one consumed marker exist for ordinal 41;
6. no earlier AVPS-v2 scientific workflow-dispatch run exists for ordinal 41 / the execution key;
7. a fresh repository-global candidate-seed recheck passes with the exact 72-seed canonical identity and no collision;
8. the executor, aggregator, execution-control contract, v2 adapter/runtime-stage, R8 process runner/derived-channel/grid, and callable workflow bytes match the exact reviewed bindings;
9. the exact 360-case / 72-CRN-group / five-state design is reconstructed in memory; seeds are not serialized into tracked science state;
10. retry, resume, GitHub Re-run, partial result interpretation, Taylor/Jerusalem scoring, result opening, Level-B and production remain false.

Case jobs may then stage only the exact locked libRadtran package/runtime and exact OPAC archive, reconstruct the four no-extension aliases, persist the exact rendered `<state>.four-species.dat`, and call the reviewed v2 executor once per case. Each case has exactly one syntax check and one solver execution, 20,000,000 photon histories, attempt 1, process-group isolation, and immutable raw artifact `avps-v2-case-<caseId>`.

After all 360 case jobs succeed, the reviewed v2 aggregator may emit only the closed acquisition ledger and closed verified-analysis-input envelope. **No primary analysis, Level-B endpoint, production materiality decision, or Taylor/Jerusalem comparison is part of this workflow.** Result opening remains a separate later gate after exact-universe verification.

## Zero-runtime publisher behavior

The publisher is not a science workflow. It must run no solver and perform no libRadtran runtime setup. Before the one git-ref creation it must freshly verify the exact authorization/review identities, one allocation marker, absent consumed marker, absent dispatch branch, zero prior candidate science runs/execution-key uses, fresh candidate-seed collision freedom, and the exact reviewed callable implementation on the default branch. Only then may it create the dispatch branch at the authorization head once, post the consumed marker once, re-read the post-dispatch surface, persist zero-runtime evidence, and invoke the callable science workflow once.

No GitHub Re-run/retry/resume is permitted for either the publisher identity or the scientific identity. A technical failure after consumption preserves all evidence and requires a separately reviewed fresh recovery identity; it never reuses ordinal 41's consumed run identity.

## Review boundary

The review workflow for this child is solver-free. It may parse YAML/Python/text, inspect repository/GitHub metadata, and run refusal/static tests. It must not download the OPAC archive, install libRadtran, create the dispatch ref, post the consumed marker, invoke the science workflow, or open any v2 result.
