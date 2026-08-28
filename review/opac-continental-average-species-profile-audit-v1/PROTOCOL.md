# OPAC continental_average species-profile source audit v1

Status: **REVIEW / SOURCE-EVIDENCE ONLY / NO UVSPEC / NO SCIENTIFIC ORDINAL**

## Purpose

The replacement vertical-profile sensitivity experiment must preserve the original preregistered scientific question: vary only vertical structure while keeping the OPAC `continental_average` aerosol optical family fixed.

Capability v5 proved that a custom `aerosol_species_file` reaches DISORT and MYSTIC when the optical-property resolver exposes the official species asset at the trace-observed no-extension path. However, v5 deliberately used one synthetic `INSO` species and therefore is only a transport capability proof, not the replacement science design.

Before scientific preregistration, freeze the exact locked-runtime definition of:

`data/aerosol/OPAC/standard_aerosol_files/continental_average.dat`

This audit exists to prevent guessing the species-column order, mass-density values, humidity handling, or mixture composition.

## Frozen runtime

- `main`: `99ade7798627e67921139697ba1a004fa8a304bb`
- exact package: `rubin-libradtran=2.0.6=py312pl5321he9373c2_1`
- expected `uvspec` SHA-256: `2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3`
- expected base libRadtran data-tree SHA-256: `ad30b49177e9c84e46497d69faf0c75e466996b0d0003f1de210289ae9f847d7`

## Allowed operations

- install/reconstruct the exact locked conda runtime;
- verify runtime identity without invoking `uvspec`;
- locate the exact `continental_average.dat` standard aerosol file;
- preserve its exact bytes, SHA-256, size, line count and non-comment rows;
- record comment/header lines verbatim in the artifact because they may define species columns/units;
- make a machine-readable row parse without changing values.

## Forbidden

- no `uvspec`, including no syntax check;
- no DISORT or MYSTIC;
- no alias creation;
- no scientific ordinal or seeds;
- no Taylor/Jerusalem scoring;
- no fitting or profile selection;
- no modification of the source file.

## Interpretation

This audit is source evidence only. Its result may be used to design a later review-only replacement AVPS preregistration that preserves the fixed `continental_average` species mixture while applying independently frozen vertical templates. It cannot by itself authorize science or production.
