# OPAC 550 nm / RH optical-property source audit v1

Status: **REVIEW/SOURCE EVIDENCE ONLY — NO UVSPEC, NO MYSTIC, NO SCIENTIFIC ORDINAL**

## Purpose

Four-species transport capability #592 proved that explicit profiles containing the locked `continental_average` component set `INSO WASO SOOT SUSO` reach both DISORT and MYSTIC when the official OPAC assets are exposed under the trace-grounded no-extension resolver names.

The next scientific problem is representation, not transport. The replacement AVPS intends to preserve the fixed OPAC `continental_average` optical family while changing only the independently preregistered vertical optical-depth template at fixed AOD550. Because `aerosol_species_file` accepts **mass-density** profiles, and because OPAC soluble-species optical properties are humidity dependent, a new renderer may not equate mass shape with optical-depth shape without evidence.

This audit freezes the exact source structure required before any mapping formula is reviewed.

## Frozen inputs

- frozen repository main `99ade7798627e67921139697ba1a004fa8a304bb`;
- locked `rubin-libradtran 2.0.6` runtime identity used by the project;
- official optical-property archive URL already used by #590/#592;
- archive SHA-256 `11daa1f1f4be0fd4ddf7e881ec2005498049674a1540d37b4b1e8f5e16052c7e`;
- archive byte count `743391266` and member count `28`;
- exact official assets and previously frozen SHA-256 values:
  - INSO `data/aerosol/OPAC/optprop/inso.mie.cdf` — `fe10348cbe585315d6e1db382563fdc054204ad35846f371dc9d8abeead36407`;
  - WASO `.../waso.mie.cdf` — `b6df493b77019bf5e22456e8fb8858c5a7d502bcc02fe6fc697ebd4844f2d4f5`;
  - SOOT `.../soot.mie.cdf` — `44a0d2060101ca52c90ae64f005118dfba256b1f89a3049e1f758c55d634aa02`;
  - SUSO `.../suso.mie.cdf` — `ce0e1bba4219c60af0af14d66a280b0d3d25188276eed0951d31594b947cd472`;
- exact AFGL-US atmosphere source SHA-256 `dab26290ed81c762ed0c607e5dc2d53393c1462a0c3a528bc5e3f5935191cfb5`.

## Audit actions

Without invoking `uvspec`, syntax checking, DISORT, or MYSTIC:

1. verify the frozen runtime identity;
2. download and verify the exact OPAC archive;
3. selectively extract only the four required official NetCDF assets;
4. verify each file byte-for-byte by its frozen SHA-256;
5. record NetCDF data model, dimensions, variables, units/attributes and compact coordinate arrays;
6. identify candidate wavelength, relative-humidity and extinction variables descriptively from names/metadata;
7. record extinction-variable dimension structure and any coordinate value nearest 550 nm;
8. freeze the exact AFGL-US source rows/comments used by the locked runtime;
9. upload only the compact JSON audit plus runtime report, not the large NetCDF files.

## Interpretation boundary

This audit does **not** authorize a humidity-selection algorithm, mass-extinction formula, interpolation convention, or scientific renderer. Candidate-variable detection is descriptive only.

After the exact file structure is known, a separate review must define and validate the mapping from the locked local `continental_average.dat` composition plus background humidity to target normalized tau550 vertical fractions.

## Hard boundaries

- no scientific ordinal; ordinal 41 remains unallocated;
- no candidate scientific seeds;
- no `uvspec`, DISORT, MYSTIC or solver syntax check;
- no Taylor/Jerusalem residuals or target scoring;
- no Level-B inference;
- no production mutation;
- no change to the five independently preregistered vertical templates;
- no assumption that a detected candidate variable has the desired physical meaning until its metadata/units are reviewed.
