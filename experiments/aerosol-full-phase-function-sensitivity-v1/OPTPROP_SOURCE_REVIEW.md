# Official OPAC optical-properties source audit — review v1

Status: **REVIEW ONLY — NO SCIENTIFIC EXECUTION OR STATE FREEZE**

## Trigger for this review

The exact locked runtime capability audit on main `47b2c5ae1cba7118f5501320096ba78bfb3906ce` completed as:

`AEROSOL_FULL_PHASE_FUNCTION_RUNTIME_CAPABILITY_V1 status=PARTIAL_OPAC_ASSETS_PRESENT main=47b2c5ae1cba7118f5501320096ba78bfb3906ce run=32654308301 attempt=1 artifact_id=9497032915 report_sha256=9fe594db5b99f28f4ced3f2563a6d69370f34860b77af81e989d5c3a34aa05a2 uvspec_invoked=false syntax_check=false scientific_solver=false results_opened=false`

Independent inspection of artifact `9497032915` established both facts below:

1. the locked `rubin-libradtran=2.0.6=py312pl5321he9373c2_1` data tree contains the ten documented OPAC standard mixture profile files, OPAC refractive-index tables, `size_distr.cfg`, and packaged OPAC examples;
2. that same locked data tree contains **zero** `.nc`/`.cdf` optical-property files under `data/aerosol/OPAC`.

The second fact is material. The libRadtran 2.0.6 User's Guide states that `aerosol_species_library OPAC` expects a NetCDF optical-property file for each aerosol species (for example `INSO.nc`). The official libRadtran download page separately provides `optprop_v2.1.tar.gz` as the additional module containing optical properties of water clouds, ice clouds, and OPAC aerosols in NetCDF format.

Therefore the conda runtime alone is not yet a complete, byte-bound OPAC full-phase-function scientific runtime.

## Authoritative source to audit

Official libRadtran download page:

`https://www.libradtran.org/doku.php?id=download`

Official linked archive:

`https://www.libradtran.org/lib/exe/fetch.php?media=download%3Aoptprop_v2.1.tar.gz`

No archive hash is assumed before acquisition. The first successful source audit must preserve the exact downloaded-byte SHA-256, byte size, HTTP response metadata, full archive-member listing, and SHA-256 of every required OPAC species optical-property member.

## Required OPAC species surface

The libRadtran 2.0.6 User's Guide documents these spherical OPAC species:

- `INSO`
- `WASO`
- `SOOT`
- `SSAM`
- `SSCM`
- `MINM`
- `MIAM`
- `MICM`
- `MITR`
- `SUSO`

For the documented `desert_spheroids` mixture, the guide additionally documents nonspherical mineral components:

- `MINM_SPHEROIDS`
- `MIAM_SPHEROIDS`
- `MICM_SPHEROIDS`

The source audit accepts NetCDF members with `.nc` or `.cdf` extensions and matches case-insensitively by basename. It does not assume an archive directory layout before acquisition.

## Zero-science audit contract

The companion workflow may:

1. install ordinary host tooling needed to download/hash/list an archive;
2. download the exact official archive URL above;
3. record HTTP response headers/final URL, byte length and SHA-256;
4. inspect the tar archive without executing any archive content;
5. locate the required species optical-property members;
6. stream and SHA-256 those members without extracting arbitrary paths;
7. upload only the compact audit report/member list/headers, not the large source archive;
8. publish one Issue #60 checkpoint.

It must not:

- invoke `uvspec` or MYSTIC;
- run a libRadtran syntax check;
- open scientific output;
- allocate a scientific ordinal or seed;
- generate a case manifest;
- freeze the candidate OPAC state set;
- modify the AOPS or AFC2 R8 evidence.

## Gate after audit

A PASS only proves that the authoritative external optical-property archive contains the required OPAC species assets and gives us reproducible source hashes. It does **not** authorize a scientific experiment.

After PASS, a separate review package must define how the pinned archive is overlaid onto the exact locked libRadtran runtime and must verify that the intended OPAC mixtures resolve under that byte-bound combined runtime. Only after that runtime-overlay review passes may a fresh scientific preregistration freeze aerosol states, photon budgets, seeds, case identities, analysis rules, and an authorization/dispatch path.
