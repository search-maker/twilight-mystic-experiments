# OPAC continental_average multispecies transport capability v1

Status: **REVIEW ONLY / INACTIVE / NO SCIENTIFIC ORDINAL / NO OBSERVATIONAL SCORING**

## Why this gate exists

AVPS ordinal 40 is scientifically non-informative because its state-specific `aerosol_file tau` profile did not reach effective solver physics. Capability v5 / PR #590 fixed the explicit-species transport mechanism and proved a custom mass-density profile for single species `INSO` reaches both DISORT and MYSTIC through the trace-observed no-extension resolver alias.

That is not yet sufficient to replace the original AVPS science. The original preregistered question fixes the OPAC `continental_average` optical family while varying only vertical structure. Source audit PR #591 froze the locked runtime file `data/aerosol/OPAC/standard_aerosol_files/continental_average.dat` and showed that its species columns are exactly:

`INSO WASO SOOT SUSO`

The existing AFPF official-source/runtime-overlay audits already byte-bound the corresponding official assets:

- `inso.mie.cdf` SHA-256 `fe10348cbe585315d6e1db382563fdc054204ad35846f371dc9d8abeead36407`
- `waso.mie.cdf` SHA-256 `b6df493b77019bf5e22456e8fb8858c5a7d502bcc02fe6fc697ebd4844f2d4f5`
- `soot.mie.cdf` SHA-256 `44a0d2060101ca52c90ae64f005118dfba256b1f89a3049e1f758c55d634aa02`
- `suso.mie.cdf` SHA-256 `ce0e1bba4219c60af0af14d66a280b0d3d25188276eed0951d31594b947cd472`

What remains unproven is whether the locked binary can resolve and transport all four together through one explicit `aerosol_species_file` profile using the corrected no-extension representation.

## Exact capability question

Can the frozen libRadtran runtime execute two deliberately different four-species mass-density profiles through both deterministic DISORT and spherical MYSTIC when:

- `aerosol_species_library OPAC` is selected;
- the profile binds exactly `INSO WASO SOOT SUSO`;
- each official optical-property member is copied byte-for-byte to the analogous no-extension path under `data/aerosol/OPAC/optprop/`;
- no competing `aerosol_file tau/ssa/gg/moments` directive exists;
- total AOD550 is fixed by `aerosol_set_tau_at_wvl`?

## Frozen synthetic capability profiles

This gate deliberately does **not** attempt to reproduce the real `continental_average` mixture or any atmospheric climatology.

- LOW shape: `exp(-z/0.55 km)`.
- HIGH shape: Gaussian centered at 8.0 km with sigma 0.75 km.
- Both shapes are normalized to the same arbitrary total mass integral before AOD rescaling.
- Each of the four species receives equal positive mass weight `0.25` solely so that every resolver dependency is exercised.

The equal weights are not a scientific mixture choice, not an OPAC composition claim, and may not be reused as the replacement AVPS design.

## Frozen numerical surface

Retain the v5 capability-only settings so this gate changes only the multispecies dimension:

- AFGL-US, observer 0 m, albedo 0.15;
- AOD550 0.10;
- wavelength 540-560 nm on the frozen repository grid;
- deterministic DISORT at SZA 80 deg, 16 streams;
- target altitude 30 deg, relative azimuth 90 deg;
- spherical 1D MYSTIC at SZA 96 deg;
- VROOM and standard deviation output enabled;
- 500,000 photons/profile;
- same paired capability seed `730194613` for LOW/HIGH.

This seed is inherited only from the ordinal-free v5 capability. It is not a scientific seed and does not consume the scientific seed namespace.

## Required PASS

PASS requires all of the following on one fresh attempt-1 activation identity after review:

1. frozen runtime and official archive identities match;
2. exact #591 `continental_average.dat` bytes/species columns match;
3. all four official source member hashes match the previously frozen AFPF source evidence;
4. exactly four no-extension aliases are created byte-identically and no `.nc` alias is used;
5. syntax checks succeed for LOW/HIGH DISORT and MYSTIC inputs;
6. deterministic DISORT LOW/HIGH outputs are finite, share the same wavelength grid, and differ;
7. only then MYSTIC LOW/HIGH both execute successfully;
8. MYSTIC `mc.rad.spc` outputs are finite, share the same wavelength grid, and differ.

No minimum effect size is required. Output nonidentity is a transport witness only.

## Evidence bindings

- frozen main: `99ade7798627e67921139697ba1a004fa8a304bb`
- single-species v5 PR #590 review head: `f0675ec48c637509cd7a5bb9c2a2746507e5bea8`
- v5 one-shot run: `33186446347`, attempt 1 SUCCESS
- v5 artifact: `9691923455`, digest `sha256:fed6bb961088232e593159c4f50911758802e9209aed86e2a0eef4b403e4d9b7`
- source audit PR #591 review head: `2bfae9341075eb04fe4621f4f53d4ab56262c22b`
- #591 audit run: `33187119926`, attempt 1 SUCCESS
- #591 artifact: `9692162280`, digest `sha256:cdcb0041a5197e31ff24520b3e653119d11c5d4a1c1b4f727e392ba7e719101e`
- exact `continental_average.dat` SHA-256: `fc39fda0f8ada2d0a0a872b8b62d684cfccd74f7b0655b5af2dcdec51115e469`

## Hard boundaries

- no scientific ordinal; ordinal 41 remains unallocated;
- no new scientific seed/case identity;
- no Taylor or Jerusalem residual direction/magnitude may enter profile design, interpretation, or gating;
- no Level-B mapping;
- no production authorization;
- no inference about realistic aerosol vertical sensitivity or materiality;
- no claim that the synthetic equal-mass profile represents `continental_average`;
- no claim about scientifically correct humidity treatment from this capability alone;
- no GitHub rerun of a consumed activation.

A PASS permits only the next review-only step: design the replacement AVPS so that the independently preregistered five OPAC-derived vertical templates are expressed through an explicit four-species mass-density profile while preserving a separately frozen `continental_average` mixture rule. Scientific ordinal allocation remains later and separate.
