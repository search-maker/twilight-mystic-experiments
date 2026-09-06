# LOWALT-STELLAR-STATE-0003 — source provenance timeline v1

Status: `POST_V1_NONBLOCKING / SOLVER_FREE / PROVENANCE_ONLY`

This checkpoint is additive provenance evidence only. It does not authorize solver-equivalence, protected-result access, `<5 deg` promotion, AVPS invocation/science, or any change to the inherited `>=5 deg` seam.

## Corrected producer timeline

### 2025-09-03 — initial 2.0.6 recipe did not produce the successful Linux py312 build

Feedstock commit `34661f6d1776374c409908256c38055b6641f4e1` (`Update to 2.0.6`, 2025-09-03T15:11:27Z) introduced libRadtran 2.0.6 with source archive SHA-256:

`64930cc40b6e4a37aa220520974d330fc1563796f466a649b2238131f2d69840`

Its Azure build was `1327727`. The overall build failed, and the Linux x86_64 Python 3.12 check `49513147462` also failed.

### 2025-09-03 — hash-only correction established the successful build-0 source identity

Verified feedstock commit `a5d9c9c629395bbf850d73ef774d41879dab15fd` (`Update meta.yaml`, 2025-09-03T16:05:41Z) changed only the source SHA-256 in `recipe/meta.yaml`:

`64930cc40b6e4a37aa220520974d330fc1563796f466a649b2238131f2d69840`

→

`999e47f4af4b5df6f85a6887fc105fc8f6e1a7cee89a3124f69ac8d8912c8e85`

The build number remained `0`.

The corrected Azure build was `1327806`. It succeeded overall with zero reported errors, and its Linux x86_64 Python 3.12 check `49518565433` succeeded.

### 2026-03-01 — build 1 retained the same source identity

Feedstock commit `d6f1997b2f486541136f514188c650fdd370f8e2` (`Rebuild for libnetcdf 4.10.0`, 2026-03-01T15:59:19Z) changed `build.number` from `0` to `1` and added the libnetcdf migration. The patch context retains the source SHA-256 exactly as:

`999e47f4af4b5df6f85a6887fc105fc8f6e1a7cee89a3124f69ac8d8912c8e85`

The pinned LOWALT runtime package is `rubin-libradtran=2.0.6=py312pl5321he9373c2_1`.

## Provenance conclusion

The successful conda-forge build-0 lineage and the later pinned build-1 lineage both bind to source archive SHA-256 `999e47f4...`. The earlier `64930cc4...` value was the source hash in an initial 2.0.6 recipe whose Linux py312 build failed; it is not evidence of a distinct successful build-0 source lineage.

Therefore STATE-0003 must not treat `64930cc4...` versus `999e47f4...` as a build-0/build-1 source split. The exact pinned source-byte target remains `999e47f4af4b5df6f85a6887fc105fc8f6e1a7cee89a3124f69ac8d8912c8e85`.

## Residual provenance gaps

This timeline does **not** establish source-byte equivalence by itself. The `999e47...` archive still needs an independently retrieved byte copy (or a rigorously content-equivalent source tree) before source-level constants and algorithms can be promoted to exact-pinned evidence. The exact solved dependency set, ambient compiler/linker flags, and immutable container image digest also remain provenance work items where they matter to runtime equivalence.

No solver was executed and no scientific result was opened by this checkpoint.

## Next bounded step

Acquire the `999e47...` source bytes from a durable independent cache/archive or build-source cache, verify the SHA-256 locally, and then audit the STATE-0003 source-equivalence checklist beginning with Earth-radius/constants, geometric-angle mapping, Chapman/layer integration, TOA termination, site-altitude truncation, spectral-extinction assembly, and null-versus-sdisort preprocessing. Keep solver execution closed until that source checklist is reviewed.
