# Aerosol full-phase-function sensitivity v1 — runtime capability review

Status: **REVIEW ONLY — NO SCIENTIFIC EXECUTION AUTHORIZED**

## Why this review exists

AFC2 R8 already challenged the model with libRadtran/Shettle aerosol family and season states at paired AOD550. AOPS v1 then held AOD550 fixed while varying constant SSA and asymmetry parameter g. The verified AOPS result shows universal SSA direction but geometry/context-dependent g effects; the AOPS scientific review explicitly warns that g is not a full phase function and that constant SSA/g overrides are sensitivity controls rather than an aerosol climatology.

The verified R8 combined analysis and Level-B propagation show that the built-in family/season envelope is material but smaller than the most extreme AOPS control response: R8 family/season states reach about +/-21% in scalar channels and about +0.132/-0.089 mag in Level-B relative to rural spring-summer, whereas AOPS constant SSA/g controls reach roughly 50% scalar effects and larger Level-B shifts. This comparison is descriptive only and creates no post-hoc acceptance threshold.

The next scientifically coherent aerosol challenge should therefore use wavelength-dependent optical properties and a real phase function/phase matrix rather than another constant-g endpoint. This is required before a strong same-atmosphere physical aerosol claim unless an independently measured aerosol state can be mapped to an equivalently rich frozen representation. It is not, by itself, a reason to forbid exploratory/end-to-end observational testing whose aerosol claim is explicitly limited and whose aerosol uncertainty is retained.

## libRadtran 2.0.6 capability basis

The official libRadtran 2.0.6 User's Guide documents these richer aerosol routes:

- `aerosol_file moments`: replace the Henyey-Greenstein phase function with supplied phase-function moments;
- `aerosol_file explicit`: specify wavelength-dependent extinction, SSA, and phase-function moments per layer;
- `aerosol_refrac_index` + `aerosol_sizedist_file`: derive optical properties from microphysics using Mie theory;
- `aerosol_species_file` + `aerosol_species_library OPAC`: use physically coherent OPAC-derived species/mixtures with full optical properties/phase matrices.

Documented predefined OPAC mixtures include `continental_clean`, `continental_average`, `continental_polluted`, `urban`, `maritime_clean`, `maritime_polluted`, `maritime_tropical`, `desert`, `antarctic`, and the nonspherical mineral variant `desert_spheroids`.

References used for this review only:

- libRadtran 2.0.6 User's Guide, sections 3.3.4 and 6.1: https://www.libradtran.org/doc/libRadtran.pdf
- Emde et al. (2016), *The libRadtran software package for radiative transfer calculations (version 2.0.1)*, describing OPAC mixtures and aerosol optical properties.

## Exact-runtime gate before preregistration

The project is locked to:

`rubin-libradtran=2.0.6=py312pl5321he9373c2_1`

No OPAC experiment state is frozen merely because the public documentation supports it. The exact project runtime must first prove, without invoking `uvspec`, that the locked package/data tree actually contains the required OPAC species/mixture assets.

The companion workflow `aerosol-full-phase-function-capability-audit.yml` is therefore limited to:

1. installing that exact locked package build;
2. running the existing runtime identity probe with `--skip-help` so `uvspec` is not invoked;
3. verifying the locked libRadtran data-tree hash;
4. inventorying OPAC/species/mixture assets and their hashes;
5. emitting a machine-readable audit artifact and Issue #60 checkpoint.

It must report `uvspecInvoked=false`, `syntaxCheckExecuted=false`, and `scientificSolverExecuted=false`.

## Candidate scientific design — deliberately not frozen yet

If the exact-runtime audit proves the required assets exist, the next separate preregistration should preserve the already validated R8/AOPS comparison structure where possible:

- Sun depression: 2, 4, 6, 8 degrees;
- AOD550: 0.10 and 0.30, normalized explicitly at 550 nm;
- geometries: the same three sea-level R8/AOPS templates (near-solar low, cross-solar mid, opposite-solar high);
- three independent CRN replicates per analysis cell;
- full visible-spectrum raw radiance and MC-standard-deviation evidence;
- scalar photopic/scotopic/Johnson-V channels and frozen Level-B propagation;
- no p-values/CIs and no epsilon substitution.

Candidate coherent aerosol states for later review are a Shettle rural spring-summer reference plus a deliberately small, broad OPAC set such as `continental_average`, `urban`, `maritime_clean`, and `desert_spheroids`. **These state names are candidate-only until the runtime audit and a fresh scientific review freeze them.** No seed, ordinal, case manifest, photon budget, or authorization is created here.

## Claim boundary

This review does not declare a post-hoc numeric definition of “material g response”, does not turn AOPS into a universal correction, and does not claim that the candidate OPAC set is climatologically representative of every observing site. Its only scientific decision is that any next aerosol-model experiment should move from constant-g controls to physically coherent wavelength-dependent phase-function treatment.
