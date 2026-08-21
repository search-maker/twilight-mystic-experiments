# Aerosol optical-property sensitivity v1 — scientific review

Status: **review only; execution disabled; no result opening authorized**.

This package is a fresh experiment motivated by completed AFC2 R8 evidence. It does not amend, rerun, reinterpret, or reuse the scientific identity of R8.

## Question

At fixed AOD550 and fixed R8 geometry/numerics, how strongly can twilight sky radiance and the already-frozen Level-B naked-eye threshold respond to two independent aerosol optical-property levers:

1. single-scattering albedo (SSA), representing the absorption-versus-scattering partition; and
2. asymmetry parameter `g`, representing the gross degree of forward scattering within the phase-function approximation used by this screen.

The purpose is sensitivity screening, not aerosol climatology.

## Why these controls are technically legitimate

The libRadtran 2.0.6 User's Guide explicitly documents `aerosol_modify ssa set` and `aerosol_modify gg set`. It states that aerosol optical properties can be overwritten after the default/Shettle setup and that `aerosol_file moments` is the separate route for prescribing a full phase function.

Primary software reference:
- libRadtran User's Guide, version 2.0.6, aerosol section: https://www.libradtran.org/doc/libRadtran.pdf

The experiment therefore uses:

```text
aerosol_default
aerosol_haze 1
aerosol_vulcan 1
aerosol_season 1
aerosol_set_tau_at_wvl 550 <AOD550>
# controlled factorial states only:
aerosol_modify ssa set <SSA>
aerosol_modify gg set <G>
```

The native reference omits the two `aerosol_modify` lines and keeps the R8 rural/spring-summer Shettle optical properties at the same fixed AOD550.

## Why `set`, not `scale`

`set` is intentional for this screen: it makes the manipulated SSA or g value explicit and identical across the controlled factorial state instead of inheriting an unknown wavelength/profile-dependent baseline and multiplying it. This produces a cleaner sensitivity question.

The cost is realism. A constant `set` value across the visible spectrum/profile is not a real aerosol climatology. Therefore:
- absolute factorial states must not be described as actual named aerosol types;
- no frequency/probability is assigned to any endpoint;
- the screen can identify sensitivity, but cannot by itself establish the distribution of real-world effects.

## Why the endpoints are 0.85/0.98 SSA and 0.60/0.80 g

They are deliberately broad sensitivity endpoints, not a fitted prior.

Published AERONET-based literature reports wide visible SSA variation across aerosol regimes. For example, Che et al. summarize globally reported AERONET SSA440 values around 0.82–0.98:
- Che et al., *Atmospheric Chemistry and Physics* 18, 405–425 (2018): https://acp.copernicus.org/articles/18/405/2018/

Observed asymmetry parameters also vary substantially by aerosol type/site/wavelength; examples summarized for visible/near-visible conditions span values below 0.60 through about 0.80:
- Hilario et al., *Atmospheric Chemistry and Physics* 23, 10579–10604 (2023): https://acp.copernicus.org/articles/23/10579/2023/

The selected endpoints therefore make a useful broad envelope for screening without asserting that the four combinations are equally likely or even internally representative of a particular natural aerosol mixture.

## Critical phase-function limitation

`g` is not the full scattering phase function. Two aerosols can share the same asymmetry parameter and have materially different angular scattering, especially in geometries where forward/backward lobes matter.

Accordingly, this experiment is explicitly an **SSA + HG/asymmetry sensitivity screen**, not a complete phase-function experiment.

If the preregistered `g` contrast produces a material response, the next fresh experiment should use one of libRadtran's richer optical-property routes, such as `aerosol_file moments`, `aerosol_species_file`/OPAC, or a size-distribution + refractive-index Mie construction. That next design must be separately preregistered before its results are opened.

## Frozen design

The screen keeps the completed R8 axes unchanged:
- sun depression: 2, 4, 6, 8 degrees;
- AOD550: 0.10, 0.30;
- three R8 geometries: near-solar, cross-solar, opposite-solar;
- three replicates;
- 20,000,000 photon histories per case;
- 380–780 nm full-spectrum calculation on the existing reference-vroom 1-nm method;
- sea-level observer, AFGL US atmosphere, surface albedo 0.15.

Five states per CRN group:
- native rural/spring-summer reference;
- SSA 0.85, g 0.60;
- SSA 0.85, g 0.80;
- SSA 0.98, g 0.60;
- SSA 0.98, g 0.80.

Thus: 24 cells × 3 replicates × 5 states = **360 cases**, organized as 72 fresh common-random-number groups.

## Preregistered analyses

For photopic luminance, scotopic luminance, and Johnson V effective radiance:
- each controlled state versus native reference: paired replicate log ratio;
- SSA main sensitivity within each fixed g endpoint;
- g main sensitivity within each fixed SSA endpoint;
- replicate-wise 2×2 interaction contrast on log response;
- retain all 3 paired replicate contrasts and report mean, sample SD, and SE=SD/sqrt(3);
- no independent-error quadrature, p-values, or confidence intervals.

Secondary endpoint is preregistered now, before any new result exists: use exact `starsvisibility` Level-B `human-threshold.mjs` at main `a422afe5fc4197ab15323bafb15512001e061454`, blob `bb4cd0ff02159ecffe276022cec9d292c7a434a3`, to compute paired limiting-V-magnitude deltas from photopic luminance.

Nonpositive/nonfinite required responses are `NUMERICALLY_UNRESOLVED`; no epsilon substitution is permitted.

## Execution boundary

This review does **not** authorize execution. Before any solver run:
- exact adapter/rendering implementation and refusal tests must be reviewed;
- 72 fresh group seeds must be derived under the new namespace and proven globally fresh;
- a fresh monotonic scientific ordinal and one-file Draft authorization must be created;
- authorization review and dispatch must remain separate;
- the scientific identity is attempt-1 only; GitHub Re-run/retry/resume is forbidden;
- result opening is forbidden unless exactly 360 case artifacts and the frozen aggregate succeed.

No adaptive case addition or post-result redesign is permitted inside this experiment.
