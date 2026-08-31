# AVPS v2 Recovery4 seed/global-control trigger bridge v4

Status: **zero-runtime mechanical recovery only / not activated / no scientific transition**.

## Why v4 exists

Reviewed bridge v3 was merged on main `aac0b9a4b999287ad1ce38aea3fa641c9e4361d7` and activated once with fresh head `adbd91cea950c229a67c2309dbd0bc0cae3509c7`. Bridge run `33350883070` attempt 1 / job `99363881112` failed in its first pre-dispatch verification step solely because a read-only GitHub API call returned transient HTTP 502. The final dispatch step was skipped. Issue #60 BEGIN `5472957418` was closed by matching END `5472987087` after independent terminal readback, zero active/queued workflows and confirmation that no Recovery4 target-control workflow_dispatch run existed.

The v3 activation head/run are immutable failed mechanical identities and may never be rerun, retried, resumed or reused. No target control, seed application, ordinal allocation, authorization, science, result opening or Level-B admission occurred.

## Exact v4 correction

Bridge v4 preserves the reviewed v3 fence parser and every frozen target-control binding. It changes only the activation identity from v3 to v4 and adds bounded retries (maximum three attempts with short increasing delay) around **read-only** network operations used to verify main, Issue #60, workflow quiescence and prior target-control absence. This protects the one-shot activation from transient GET/read failures such as the observed HTTP 502 without weakening any semantic guard.

The control-dispatch POST remains exactly one single-shot command and is never placed inside a retry helper. A failed or ambiguous dispatch POST therefore cannot be automatically repeated. Header-only WRITE_QUIET_END parsing remains unchanged: only `begin=`, `beginComment=` or `begin_comment=` on the first END header line may bind a closure; later body references are ignored; distinct same-header ids fail closed; the complete paginated ledger must replay to exactly the newly supplied Recovery4 BEGIN.

## Frozen target and fresh identity

- source main/base for review: `aac0b9a4b999287ad1ce38aea3fa641c9e4361d7`
- source bridge-v3 Git blob: `5c28836d2a95c1b4460568665c72f49e02a2b03b`
- frozen target control: `.github/workflows/avps-v2-recovery4-seed-global-control-v1.yml`
- frozen target Git blob: `875bd21758a0ac0a2e2aed57bfc428df4e1e9578`
- future activation branch: `control-trigger/aerosol-vertical-profile-sensitivity-v2-recovery4-seed-global-control-v4`
- future marker: `control-triggers/avps-v2-recovery4-seed-global-control-v4.txt`
- future schema: `AVPS_V2_RECOVERY4_SEED_GLOBAL_CONTROL_TRIGGER_V4`

Bridge v4 may be activated only after exact-head zero-runtime review succeeds, this three-file mechanical package is merged, post-merge workflows/metadata are quiescent, and a fresh Issue #60 read permits a wholly new WRITE_QUIET fence. The activation must be a one-file direct child of then-current main. Never reuse v1, v2 or v3 activation heads/runs.

## Scientific boundary

Recovery4 candidate seed canonical SHA-256 remains `ddded6b2d170ca2fac8d498bdba2887446c16995df0880d948fb2be00870b3de`; rows canonical SHA-256 remains `c439de417520b330c037e2628df02b6955f652563300aa5ef30477abf7661a98`. Candidates remain unapplied/unconsumed and no successor ordinal is allocated. The target control is zero-runtime and may only prove live global seed freshness and dynamically derive the next unused ordinal. It may not allocate/authorize/dispatch science. Frozen AVPS design remains 360 cases / 72 CRN groups / five profiles / 20,000,000 photons per case. Ordinals 41-44 remain permanently consumed. Taylor/Jerusalem and invalidated low-altitude exec001 downstream evidence remain excluded. Every richer OAS-v2 `newMappingAuthorized` remains `false`.
