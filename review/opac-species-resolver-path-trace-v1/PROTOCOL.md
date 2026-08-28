# OPAC explicit-species resolver path trace v1

Status: **REVIEW ONLY / INACTIVE / NO SCIENTIFIC ORDINAL / NO TARGET SCORING**

## Why this diagnostic exists

AVPS ordinal 40 is scientifically non-informative because its intended vertical-profile state did not reach effective solver physics. Corrective ordinal-free capabilities v2, v3, and v4 all reached the same locked libRadtran runtime failure before deterministic transport:

`found neither netcdf nor ASCII optical property files`

V3 proved that a byte-identical alias at `aerosol/OPAC/optprop/INSO.nc` was insufficient. V4 proved that a byte-identical alias at `aerosol/OPAC/INSO.nc` was also insufficient. Both aliases used the exact official `inso.mie.cdf` optical-property bytes.

The next step must therefore **observe**, not guess, the concrete pathname(s) attempted by the locked `uvspec` binary.

## Frozen input identity

This diagnostic reuses the exact reviewed v2 input builder from review head:

`d90d3bca966d566d328fc1d91fb44f65c58d12b4`

and exact builder blob:

`fd859415cd3f05367b1f121a3286588bb4eb1882`

Only the deterministic LOW input is executed. Its aerosol surface remains exactly:

```text
aerosol_default
aerosol_species_library OPAC
aerosol_species_file <synthetic-low-profile> INSO
aerosol_set_tau_at_wvl 550 0.100000
```

The LOW profile remains `exp(-z/0.55 km)` on the exact AFGL-US altitude grid, with AOD550 `0.10`, DISORT SZA 80 deg, wavelength 540-560 nm on the frozen 1-nm repository grid, target altitude 30 deg, relative azimuth 90 deg, and albedo 0.15.

No alias is created in this diagnostic. No transport correction is attempted.

## Frozen runtime/archive identity

The diagnostic uses the same locked runtime and exact official OPAC archive as v2-v4:

- locked `uvspec` SHA-256 `2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3`
- official OPAC archive SHA-256 `11daa1f1f4be0fd4ddf7e881ec2005498049674a1540d37b4b1e8f5e16052c7e`
- official archive size `743391266` bytes
- staged OPAC data-tree SHA-256 `5d8bbf8e6b91ec3d405dee36f21a94afbb6e5ec6cd67da2dd5dd541738199d80`

The exact v4 reviewed archive extractor is reused from review head `7b2a2f7ae14a7777408ab36de65fcc4a91b4a8de`, blob `c3a6bdf832dbb78da74e0157c0124b12c53c1c0e`.

## Trace surface

Run exactly one deterministic LOW `uvspec` execution under `strace` with file-resolution syscalls enabled. Preserve:

- the exact input file;
- generated LOW profile;
- `uvspec` stdout;
- `uvspec` stderr;
- `uvspec` exit code;
- full file-syscall trace;
- machine-parsed candidate missing paths;
- exact runtime/archive identities.

MYSTIC must not run. No HIGH solver execution is allowed. No retry/rerun/resume is allowed.

## Diagnostic terminal status

This is not a transport PASS/FAIL experiment. A terminal diagnostic success is:

`TRACE_IDENTIFIED_CANDIDATE_OPTICAL_PROPERTY_LOOKUPS`

and requires all of the following:

1. exact runtime/archive/input dependencies are proven;
2. the LOW input is generated from the exact frozen v2 builder;
3. `strace` captures the one deterministic execution;
4. solver stderr retains the expected unresolved optical-property failure;
5. the trace contains one or more failed file lookups plausibly associated with the INSO/OPAC optical-property resolution;
6. the candidate pathname list is frozen as evidence.

The diagnostic is allowed and expected to observe nonzero `uvspec` exit status. Solver success is not required and would itself be diagnostically important.

## Interpretation boundary

This diagnostic answers only: **which filesystem pathnames does this exact locked binary attempt while resolving the explicit INSO species?**

It does not establish a corrected path, optical-property validity, profile sensitivity, material effect size, Taylor/Jerusalem agreement, Level-B mapping, or production readiness.

No scientific ordinal is allocated. Ordinal 41 remains unallocated.

After a terminal trace result, a separate fresh reviewed transport capability may test the minimal correction indicated by the observed lookup. V2, v3, v4, and ordinal 40 must never be rerun or reused.
