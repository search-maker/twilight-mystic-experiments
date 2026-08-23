# OPAC optical-properties exact-runtime overlay audit — review v1

Status: **REVIEW ONLY — ZERO SCIENTIFIC EXECUTION**

This stage follows the verified official-source audit v2 and still does not preregister an aerosol experiment.

## Frozen inputs

Locked base runtime:

- package: `rubin-libradtran=2.0.6=py312pl5321he9373c2_1`;
- runtime lock: `experiments/mystic-batch-v1/runtime-lock.micromamba.json`;
- pre-overlay libRadtran data-tree SHA-256: `ad30b49177e9c84e46497d69faf0c75e466996b0d0003f1de210289ae9f847d7`;
- uvspec SHA-256: `2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3`.

Verified official optical-properties source:

- source-v2 run: `32655624673`, attempt 1;
- source-v2 artifact: `9497367203`;
- archive: `optprop_v2.1.tar.gz`;
- archive size: `743391266` bytes;
- archive SHA-256: `11daa1f1f4be0fd4ddf7e881ec2005498049674a1540d37b4b1e8f5e16052c7e`;
- source-v2 report SHA-256: `d0fd37adad50ab96096f75e26223ce1716b3c5fffc815c765d3af07202c8cef3`;
- 13 documented required OPAC optical-property members passed exact path/byte hashing; `MITR_SPHEROIDS` was also present as an additional asset.

## Audit question

Can the exact official optical-property archive be combined with the exact locked conda runtime without overwriting or mutating that runtime, while producing a deterministic staged augmented data tree in which every OPAC component referenced by the packaged standard mixture files resolves to an exact optical-property member?

## Frozen no-science method

The companion workflow must:

1. install the exact locked conda package;
2. run the existing runtime probe with `--skip-help`, so no `uvspec` invocation occurs;
3. require the exact pre-overlay uvspec/data-tree/runtime-lock hashes;
4. copy the locked libRadtran `data/` tree into a workspace staging directory and thereafter treat `$CONDA_PREFIX` as read-only, preventing cache contamination or hidden mutation of the installed runtime;
5. reacquire the same official archive and require the exact frozen archive size/SHA-256;
6. inspect all archive members before staging and reject absolute paths, `..`, non-regular members, member-count drift, or any collision with the copied base data tree;
7. stream each archive member manually into the staging tree with exclusive-create semantics; do not call a generic tar extraction routine;
8. byte-verify every staged archive member against the archive stream;
9. require the exact 13 documented OPAC member hashes from source-v2 and record the extra `MITR_SPHEROIDS` hash;
10. parse all ten packaged `standard_aerosol_files/*.dat` files from the staged copy as text only, identify documented OPAC species tokens, and require that every referenced species maps to a verified optical-property member; `desert_spheroids` must reference at least one documented spheroid species;
11. compute and preserve the staged augmented data-tree SHA-256/file-count/byte-count and the exact 28 added paths, while separately proving the original `$CONDA_PREFIX/share/libRadtran/data` tree still has its frozen pre-overlay SHA-256;
12. upload compact evidence only and delete the downloaded archive before artifact upload.

The workflow is attempt-1 only. No GitHub rerun is to be used if a control-plane defect is found; a corrected fresh review identity must be used instead.

No `uvspec`, syntax check, MYSTIC solver, case execution, result opening, seed derivation, scientific ordinal, model fitting, or aerosol-state freeze is permitted.

## Interpretation boundary

A PASS proves installation/data dependency readiness only. It does **not** prove a physically appropriate aerosol state set, does not authorize a scientific run, and does not validate the model against observations.

Only after this overlay audit passes may a separate scientific review choose a small physically coherent OPAC state set and preregister its geometry, AOD normalization, analysis and one-use scientific identity.
