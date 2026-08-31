# LOWALT-STELLAR-STATE-0003 — pinned-source recovery audit v1

Status: `POST_V1_NONBLOCKING / RESULT_BLIND / SOLVER_FREE_RECOVERY_AUDIT`

Parent evidence: PR #747 source-equivalence audit attempt 1 and Issue #60 comments `5471893658`, `5472132388`.

## Purpose

Resolve the exact-source provenance prerequisite without running any scientific transport solver and without consuming opened LOWALT protected residuals. The prior attempt fetched the HTTPS spelling of the libRadtran 2.0.6 URL, while the exact conda-forge build-1 recipe pins the literal HTTP URL. This recovery identity therefore binds the recipe literally, records redirect behavior rather than silently substituting schemes, and independently binds the exact conda package/runtime that produced the inherited stellar evidence.

This stage cannot promote support below 5 degrees and cannot freeze a NONPROTECTED solver matrix.

## Frozen identities

- feedstock commit: `d6f1997b2f486541136f514188c650fdd370f8e2`
- literal recipe source URL: `http://www.libradtran.org/download/libRadtran-2.0.6.tar.gz`
- required source SHA-256: `999e47f4af4b5df6f85a6887fc105fc8f6e1a7cee89a3124f69ac8d8912c8e85`
- exact Linux package: `rubin-libradtran-2.0.6-py312pl5321he9373c2_1.conda`
- package channel URL: `https://conda.anaconda.org/conda-forge/linux-64/`
- inherited exact `uvspec` SHA-256: `2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3`
- authoritative >=5deg runtime/support: unchanged MYSTIC-STATE-0081/v3.2

## Frozen recovery procedure

1. Fetch the exact feedstock recipe at the frozen commit and mechanically verify its literal HTTP URL, source SHA and build number.
2. Fetch the source by that literal HTTP URL with redirects enabled, preserving the complete response-header chain, effective final URL, HTTP status and downloaded-byte SHA-256. No HTTPS substitution is allowed in the request string.
3. Fetch `repodata.json.zst` for conda-forge/linux-64, decompress it, locate the exact package filename, and bind its current repodata SHA-256/size/build record.
4. Download exactly that `.conda` package and require its bytes to match the repodata SHA-256/size.
5. Treat `.conda` as a ZIP container; extract only its `info-*.tar.zst` and `pkg-*.tar.zst` members into a temporary directory. List the package payload, extract `info/` metadata and only `bin/uvspec` from the payload. Do not execute `uvspec`.
6. Require the extracted `bin/uvspec` SHA-256 to equal the inherited exact runtime hash. Capture bounded text evidence from package metadata and inventory whether any of the six governing source files or an embedded libRadtran source archive are present.
7. If and only if the literal-HTTP source bytes equal `999e47...`, invoke the already reviewed solver-free `source_audit.py` against those recovered bytes into a nested isolated output directory. This is source parsing/fingerprinting only; it must not invoke uvspec/sDISORT/MYSTIC.
8. Upload only the dedicated `recovery-evidence/` directory. Never upload repository-root `evidence/` or unrelated historical artifacts.

## Frozen terminal classes

- `PASS_LITERAL_RECIPE_SOURCE_RECOVERED`: exact package and inherited `uvspec` identity are bound, and the literal recipe HTTP fetch yields exact source SHA `999e47...`. The source may then be passed to the existing six-file source capture. This does not itself resolve the ten scientific checklist items or authorize solver comparison.
- `FAIL_PINNED_SOURCE_NOT_RECOVERED`: exact package and inherited `uvspec` identity are bound, but the literal recipe URL still does not yield `999e47...` and package metadata contains no independently sufficient recovery of those exact governing source bytes. This is a durable provenance blocker for source-clone equivalence, not a low-altitude physics failure.
- `FAIL_RECOVERY_IDENTITY_OR_MECHANICS`: recipe/package/repodata/uvspec identity or safe extraction mechanics fail. No scientific inference is allowed.

No result from PR #747's HTTPS fetch is used to select formulas, knots, support floor, matrix coordinates or error gates. No Taylor/Jerusalem/halachic target is consulted.

## After terminal result

If exact source is recovered, finish and review all ten STATE-0003 source-equivalence checklist classifications before freezing a wholly fresh NONPROTECTED solver-equivalence matrix. If exact source remains unavailable, do not substitute the current `64930...` archive as governing source; instead review a scientifically distinct exact-runtime black-box equivalence path, with its own result-blind protocol, before any numerical matrix is frozen.
