# OPAC staged-runtime syntax resolver audit — review v1

Status: **REVIEW ONLY — SYNTAX CHECKS ONLY — NO SCIENTIFIC SOLVER**

This stage follows the verified exact-runtime overlay PASS and does not preregister any aerosol state for scientific execution.

## Bound prior evidence

- exact overlay main: `ea60021574b60363b7e9c0089a95b71749adc0a8`;
- overlay run: `32656136706`, attempt 1;
- overlay artifact: `9497493535`;
- overlay report SHA-256: `54eafae989d3b7ad369fa8cf194c69efde203b54ebed5b248cf9e80da9deec7a`;
- official optprop archive SHA-256: `11daa1f1f4be0fd4ddf7e881ec2005498049674a1540d37b4b1e8f5e16052c7e`;
- official archive size: `743391266` bytes;
- locked base data-tree SHA-256: `ad30b49177e9c84e46497d69faf0c75e466996b0d0003f1de210289ae9f847d7`;
- exact staged augmented data-tree SHA-256: `5d8bbf8e6b91ec3d405dee36f21a94afbb6e5ec6cd67da2dd5dd541738199d80`;
- locked uvspec SHA-256: `2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3`.

## Audit question

Does the exact locked libRadtran 2.0.6 executable, when pointed at the exact staged augmented data tree, successfully resolve every documented predefined OPAC mixture and accept the intended AOD550 normalization surface during `uvspec -c` syntax checking?

## Frozen syntax set

Exactly ten documented predefined mixtures are checked once each:

- `continental_clean`
- `continental_average`
- `continental_polluted`
- `urban`
- `maritime_clean`
- `maritime_polluted`
- `maritime_tropical`
- `desert`
- `antarctic`
- `desert_spheroids`

Each check uses the same non-scientific parser surface:

- exact staged `data_files_path`;
- AFGL US atmosphere from that same staged tree;
- `source solar`;
- wavelength range `380 780`, which contains 550 nm;
- `aerosol_default`;
- `aerosol_species_library OPAC`;
- exactly one `aerosol_species_file <mixture>`;
- `aerosol_set_tau_at_wvl 550 0.10`;
- a simple DISORT parser configuration solely to make the input complete.

The command is exactly the locked `uvspec -c`. It is process-group isolated with the already reviewed process runner. Every input, stdout, stderr, exit status, timeout flag, and input SHA-256 is preserved.

## Pass rule

PASS requires:

1. exact prior overlay Issue #60 checkpoint exists once;
2. base runtime and staged-tree hashes reproduce exactly;
3. exactly ten syntax checks are attempted, one per documented mixture;
4. every `uvspec -c` returns exit code 0 without timeout;
5. no unexpected files are produced by a syntax check;
6. exact input surface contains OPAC library, the intended mixture, and AOD550 normalization;
7. no non-`-c` `uvspec` call occurs;
8. `scientificSolverExecuted=false`, `resultOpeningPerformed=false`, and no scientific identity/seed/ordinal is created.

A failure is terminal for this review identity; no GitHub rerun is permitted. A corrected fresh review identity is required for any control-plane defect.

## Interpretation boundary

PASS proves parser/data-resolution readiness for the documented OPAC mixtures and the AOD550 normalization option. It does not prove MYSTIC numerical behavior, does not select a scientific mixture subset, does not establish a climatological prior, and does not authorize scientific execution.

Only after PASS may a separate scientific preregistration choose the smallest physically informative OPAC subset and bind its exact MYSTIC adapter, geometry, AOD, photon budget, CRN seeds, analysis and one-use execution identity.
