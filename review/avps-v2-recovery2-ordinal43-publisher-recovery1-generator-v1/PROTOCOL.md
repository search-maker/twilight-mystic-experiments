# AVPS v2 recovery2 ordinal 43 publisher recovery1 generator

Status: **review-only / zero-runtime / no dispatch / no scientific execution**.

## Frozen predecessor state

- Recovery2 ordinal 43 authorization remains exact head `5fd0c82cb14a02ace38a5a7be30b8b075ccae298`, reviewed and allocated, not consumed by the failed publisher attempt.
- Published recovery2 science workflow remains byte-frozen. The 360-case / 72-CRN / five-profile / 20,000,000-photon-per-case design, candidate seed identities, analysis rules, result-opening rules, Level-B gates, holdouts, and production state do not change here.
- Trigger bridge run `33290899555`, attempt 1, succeeded and requested the original reviewed publisher once.
- Original publisher run `33290906727`, attempt 1, job `99202243870`, failed in `Fresh zero-runtime pre-dispatch fence` because the step exported `GH_TOKEN` while `preauthorization_surface.collect(...)` required `GITHUB_TOKEN`.
- The dispatch-ref creation, consumed-marker write, evidence upload, and science-dispatch steps were all skipped. The failed run is immutable evidence and must never be GitHub Re-run/retried/resumed.

## Recovery design

This package does **not** publish an executable recovery. It deterministically generates a candidate fresh recovery publisher, fresh recovery trigger bridge, and their solver-free PR review workflow as CI artifacts only.

The generated recovery publisher:

1. binds failed run `33290906727` / job `99202243870` and proves the mutation/science steps were skipped;
2. supplies both verified token aliases (`GH_TOKEN` and `GITHUB_TOKEN`) only to the fresh pre-dispatch fence, correcting the exact mechanical failure without weakening authentication;
3. repeats the unchanged authorization, artifact, allocation-marker, no-consumed-marker, no-science-run, native seed-ledger, repository-global seed, and global-ordinal checks;
4. binds the already-reviewed implementation bytes and additionally requires a successful attempt-1 solver-free review receipt for the fresh recovery publisher/trigger bytes;
5. only after every gate passes may the later recovery publisher create the exact existing ordinal-43 dispatch ref and consumed marker and request the unchanged recovery2 science workflow once.

The generated trigger uses a new activation branch/marker and refuses duplicate workflow-dispatch runs of the fresh recovery publisher.

## Prohibitions

- No GitHub Re-run/retry/resume of `33290906727`.
- No reuse of a failed publisher-run identity.
- No new scientific ordinal, seed set, authorization head, case matrix, MYSTIC input, threshold, stopping rule, or analysis rule.
- No `uvspec`, libRadtran, or MYSTIC execution in this generator/review package.
- No dispatch branch, consumed marker, result opening, Level-B admission, protected holdout access, Taylor/Jerusalem residual use, or production transition.
- Generated candidate workflow bytes must receive their own separate exact-head review/publication gate before any trigger activation.

This is a mechanical recovery from a token-environment mismatch only.