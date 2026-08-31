# AVPS v2 Recovery4 seed/global-control trigger bridge v3

Status: **zero-runtime mechanical recovery only / not activated / no scientific transition**.

## Why v3 exists

Fresh activation v2 head `63b1ce0eb59c62b9401e5af40a64cc5ff3511c25` triggered bridge run `33347498399` attempt 1 / job `99354322564`, which failed before the target global control was dispatched. Its parser correctly recognized `begin=`, `beginComment=` and `begin_comment=`, but searched the entire WRITE_QUIET_END body. A legitimate historical END can bind one fence in its first-line header while later prose names other historical BEGIN ids, producing the false conflict `conflicting WRITE_QUIET_END begin ids: [5463819190, 5467489757, 5472322006]`.

Issue #60 matching END `5472575510` closed that failed fence. The failed v2 activation/run are immutable and may never be rerun or reused. No target control run, seed application, ordinal allocation, authorization, science, result opening or Level-B admission occurred.

## Exact v3 correction

For a body beginning `WRITE_QUIET_END`, only the first line is the authoritative END header. Bridge v3 searches that header, and only that header, for the three already-reviewed durable key forms:

- `begin=<id>`
- `beginComment=<id>`
- `begin_comment=<id>`

Later body/prose references are ignored for fence closure. Multiple distinct supported ids in the first-line header remain a fail-closed conflict. Ordinary non-END comments never close a fence. The complete paginated ledger must still replay to exactly one unmatched BEGIN: the newly supplied Recovery4 global-control fence.

The review fixture must include all three header key forms, a realistic header binding followed by unrelated later-body historical id mentions, a true same-header conflict, and a genuinely unmatched BEGIN.

## Frozen target and fresh identity

- source main/base for review: `f5bd81b7706c9cc56592667709a6aa725a5f48ba`
- frozen target control: `.github/workflows/avps-v2-recovery4-seed-global-control-v1.yml`
- frozen target Git blob: `875bd21758a0ac0a2e2aed57bfc428df4e1e9578`
- future activation branch: `control-trigger/aerosol-vertical-profile-sensitivity-v2-recovery4-seed-global-control-v3`
- future marker: `control-triggers/avps-v2-recovery4-seed-global-control-v3.txt`
- future schema: `AVPS_V2_RECOVERY4_SEED_GLOBAL_CONTROL_TRIGGER_V3`

Bridge v3 may be activated only after exact-head zero-runtime review succeeds, the correction is merged, post-merge workflows/metadata are quiescent, and a fresh Issue #60 read permits a wholly new WRITE_QUIET fence. The activation must be a one-file direct child of then-current main. Never reuse v1 or v2 activation heads/runs.

## Scientific boundary

Recovery4 candidate seed canonical SHA-256 remains `ddded6b2d170ca2fac8d498bdba2887446c16995df0880d948fb2be00870b3de`; rows canonical SHA-256 remains `c439de417520b330c037e2628df02b6955f652563300aa5ef30477abf7661a98`. Candidates are still unapplied/unconsumed and no successor ordinal is allocated. The target control is zero-runtime and may only prove global seed freshness and derive the next unused ordinal. It may not allocate/authorize/dispatch science. Frozen AVPS design remains 360 cases / 72 CRN groups / five profiles / 20,000,000 photons per case. Ordinals 41-44 remain permanently consumed. Taylor/Jerusalem and invalidated low-altitude exec001 downstream evidence remain excluded. Every richer OAS-v2 `newMappingAuthorized` remains `false`.
