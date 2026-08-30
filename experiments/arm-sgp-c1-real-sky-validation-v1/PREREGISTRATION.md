# ARM SGP C1 SASZE real-sky MYSTIC validation v1 — frozen preregistration

**Status: FROZEN BEFORE MYSTIC; SASZE 464.020874-nm comparison radiances remain sealed.**

## Scientific question
Can a direct spherical scalar MYSTIC calculation, driven only by independently measured/retrieved atmospheric information and a preregistered uncertainty ensemble, reproduce SASZE zenith spectral radiance at geometric solar-center depressions -6, -7 and -8 degrees on 2024-02-08 dusk?

This is a validation, not a fit. No atmospheric input, wavelength, timestamp rule, QC rule, model option, or acceptance rule may be changed after SASZE comparison radiances are opened.

## Frozen observation
- Site: ARM SGP C1, 36.607322 N, -97.487643 W, 314.8 m ASL.
- Native SASZE VIS pixel: **464.020874 nm**.
- Anchors: -6 = 2024-02-09T00:29:01.099671Z; -7 = 2024-02-09T00:34:09.432376Z; -8 = 2024-02-09T00:39:16.805063Z.
- Sample rule: within +/-15 s, choose the finite/non-fill native pixel with minimum absolute time offset; ties choose earlier. If none, that anchor is unavailable. Do not widen the window or substitute a wavelength.
- Conservative SASZE absolute calibration interval: +/-10% systematic.

464.020874 nm was selected before MYSTIC because ARM AOP blue is 464 nm, blue nephelometer data are not the DQR-flagged green/red channels, CAPS green is invalid in this period, AERONET Level-2 provides 440-nm AOD plus Angstrom exponent, and SASZE has valid native samples there.

## Cloud/Moon gates
Cloud screen is PASS_CLEAR from independent ARSCL/ceilometer/Raman evidence over the frozen interval plus guard band. Moon is below the horizon and ~1.5% illuminated; no lunar source is included.

## Molecular atmosphere
Primary v1 uses the inherited AFGL-US vertical molecular shape, truncated at **0.3148 km**, with measured sonde surface pressure **970.570 hPa**, sonde-derived precipitable water **8.428 mm**, GE-COMI ozone **300 DU**, and `day_of_year 40`. The full radiosonde is retained as evidence but is not used directly in v1 because combining a dynamically rebuilt radiosonde z-grid with the custom `aerosol_file tau` surface has not yet been runtime-reviewed. At 464 nm the measured pressure column is the dominant molecular-scattering constraint.

## Aerosol column
AERONET Level-2 at 23:12:01 UTC gives AOD440=0.043537, AE440-870=0.752409, yielding AOD464=0.04183013. AERONET +/-0.01 visible-AOD instrument stress maps to [0.03222218, 0.05143808].

FEX `extinction_be` is **not independent extinction truth** here: the twilight best-estimate lidar ratio near 50.24 sr is source flag 512 = assumed values. FEX extinction is used only as a diagnostic for the core/stress AOD envelope. Primary absolute normalization remains AERONET-centered.

Frozen AOD464 core: **[0.02847449, 0.06761784]**, central **0.04183013**.  
Frozen AOD464 LR-only stress: **[0.01441294, 0.10100953]**. Stress limits are not confidence intervals.

## Aerosol vertical shape
Use FEX `particulate_backscatter_be` as a **shape only**, never as absolute extinction. A bin contributes only when: `qc_profile=0`, aerosol feature bit 2 is set, source flag is 1 or 2 (low/high Raman backscatter), value is finite/nonnegative, and 0.2-5.0 km AGL. Above 5 km set aerosol to zero. 0-0.2 km is a separate shallow slab constrained by E13 dry AOP extinction.

For each anchor, central is the nearest profile within 3 min whose aerosol bins are >=95% Raman-source; temporal variants are the nearest qualifying profiles around it:
- -6: prev 00:24, central 00:28, next 00:32 UTC.
- -7: prev 00:32, central 00:34, next 00:36 UTC.
- -8: prev 00:36, central 00:40, next 00:42 UTC.

The exact shape nodes are frozen in `fex-profile-shapes.csv`.

For each scenario: shallow-slab tau = `near_surface_ext_Mm-1 * 0.001 km^-1 * 0.2 km`. Refuse if slab tau >= scenario AOD. Distribute the remaining AOD over the normalized 0.2-5 km FEX shape. Total AOD remains independently set by `aerosol_set_tau_at_wvl`.

## Optical properties and surface
AOP blue SSA core = [0.88908857, 0.92232573], central 0.90414536; stress [0.87288231, 0.92928463]. Absorption/SSA source QC is indeterminate because the absorption signal is weak, so this is an uncertainty prior, not truth.

AOP blue g core = [0.27050053, 0.53481855], central 0.34695503; stress [0.25000528, 0.57595062].

The scalar v1 phase function is Henyey-Greenstein with measured g. This is an explicit model approximation because no independently measured full phase function/scattering matrix exists. No phase-family substitution after unblinding is permitted.

Near-surface dry extinction core = [2.970670, 4.236296] Mm^-1, central 3.603000; stress [0, 7.206000]. The slab contributes only a few percent of total AOD.

Lambertian albedo464 central = **0.07046037**, core **[0.05132009, 0.10596962]**, from the QC-good 10-m/25-m MFR footprint envelope interpolated per timestamp from 415.3 and 502.8 nm.

SMPS is measured during twilight and supports a fine-particle-dominated case; APS/coarse-mode size distribution is missing. SMPS is supporting evidence only and is not fitted into MYSTIC optics.

## Solver surface
Primary scalar run:
`rte_solver mystic`; `mc_spherical 1D`; `mc_vroom on`; `mc_std`; wavelength 464.020874 nm; sza 96/97/98; zenith `umu -1`; `phi0=0`, `phi=0`; site altitude 0.3148 km; pressure 970.570 hPa; H2O 8.428 mm; O3 300 DU; `aerosol_default`; custom `aerosol_file tau`; `aerosol_modify ssa set`; `aerosol_modify gg set`; `aerosol_set_tau_at_wvl 464.020874`; Lambertian albedo.

The exact runtime must pass `uvspec -c` before solver dispatch. Syntax failure halts the experiment; no observational values may be opened and any repair requires a versioned preregistration amendment.

## Frozen uncertainty experiment
Phase 1 screening uses **45 core scenarios** (central + 32 scrambled Sobol points + 10 continuous one-factor endpoints + 2 profile-only endpoints) and **10 one-factor stress scenarios**, at each of 3 anchors. 5,000,000 photons/case. Scenario values are frozen in `uncertainty-scenarios.csv`; case identities in `screening-case-ledger.csv`.

SASZE stays sealed. After all Phase-1 model results are terminal, select per anchor, using model radiance only, central + model-min/model-max core + model-min/model-max stress (deduplicate). Phase 2 reruns each selected state with 3 fresh common-random-number replicates at 20,000,000 photons/case.

If any required Phase-2 result has >2% relative numerical uncertainty or is nonpositive/nonfinite, classify `NUMERICALLY_UNRESOLVED` and do not open SASZE. No retries/reseeding after result inspection unless the preregistered executor itself fails before producing a scientific result.

## Unblinding and interpretation
Only after Phase 2 is complete may the 464.020874-nm SASZE radiances be read.

For each anchor report:
1. observed radiance and +/-10% calibration interval;
2. central model radiance and percent residual;
3. core model envelope with actual numerical uncertainty;
4. stress model envelope;
5. twilight slope across -6/-7/-8.

Interpretation:
- overlap SASZE interval vs core envelope: compatible at the uncertainty level this atmosphere permits;
- no core overlap but stress overlap: tension, explainable only by stress assumptions;
- no stress overlap: strong discrepancy for this frozen scalar/HG MYSTIC configuration.

This does not prove MYSTIC universally correct. It tests the frozen real-atmosphere configuration. Corrected HSRL 2.6.7, if later obtained, is a Stage-2 cross-check on the **same frozen event**, not permission to reselect the case.

## Forbidden after unblinding
No change to date, anchors, wavelength, pixel-selection window, atmospheric inputs/ranges, profile source/times, albedo, AOD, SSA, g, phase model, photon budget, acceptance logic, or DQR policy because of the observed residual. HSRL 2.6.5 is forbidden.
