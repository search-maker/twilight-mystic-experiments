# LOWALT-STELLAR-STATE-0001 Phase-B protocol

Status: **FROZEN BEFORE ANY PHASE-B TRAINING OR PROTECTED-HOLDOUT SOLVER VALUE**

Authoritative Issue #60 freeze: comment `5467228174`.
Phase-A capability evidence: comment `5467224023`, run `33297587050`, job `99219802369`, artifact `9727914763`.
Review base main: `9ef3b3e000d79e1bcca8ada6c5ab76ea4e492cb8`.

## Scientific representation

The only representation tested in this state is linear interpolation of direct optical depth `tau=-ln(T)` against topocentric vacuum/geometric target altitude. Elevation and AOD interpolation remain linear. This state does not extrapolate `csc(h)` below 5 degrees and does not claim a universal scalar Chapman coordinate.

Radiative-transfer source geometry remains `sza=90-h_geometric`, with `sdisort`, `sdisort nscat 1`, AFGL US, `mol_abs_param crs`, `aerosol_default`, AOD550, albedo 0.15, site truncation with `atm_z_grid`, local `zout 0`, exact 380..780 nm / 1 nm, and no RT refraction.

## Training universe

Fresh lower-altitude training knots, degrees:

`0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5`

Inherited axes:

- observer elevation m: `0,500,1250,2000,2500`
- AOD550: `0.05,0.10,0.20,0.30,0.40`

Exactly `11*5*5 = 275` fresh deterministic training spectra are authorized only by a future separately reviewed one-shot execution identity.

Exact 5 degrees is not regenerated. Its 25 elevation/AOD spectra are inherited from the authoritative v3.2 runtime:

- source repository: `search-maker/twilight-mystic-experiments`
- source commit: `279ba344ab0e868df1319c01291418ec8786d261`
- source path: `generated/level-b-stellar-v32/stellar-transport-v32-zenith-lut.json`
- source runtime SHA-256: `0b96bd5868dc0c72d5cd77b504098d35086feaf573d92556c4f8311a163e3ce2`

The lower interpolator is eligible only for `0.25 <= h < 5`. Exact `h=5` and all higher values route to the unchanged v3.2 provider. The lower `[4.5,5]` interpolation cell consumes the inherited 5-degree optical-depth seam as its upper knot.

## Fresh protected validation universe

Protected altitude coordinates, degrees, 3/8 inside each lower training interval:

`0.34375, 0.59375, 0.84375, 1.1875, 1.6875, 2.1875, 2.6875, 3.1875, 3.6875, 4.1875, 4.6875`

Protected observer elevations, m:

`187.5, 781.25, 1531.25, 2187.5`

Protected AOD550:

`0.06875, 0.1375, 0.2375, 0.3375`

Exactly `11*4*4 = 176` protected solver spectra and, with Pickles library numbers `1,26,45`, exactly `528` protected Johnson-V comparisons.

Every protected target altitude is strictly below 5 degrees, whereas all inherited 0077/0081/v3/v3.2 protected target-altitude coordinates are >=5 degrees. Therefore full coordinate tuples are mechanically collision-free by their target-altitude component. The generator must additionally prove no collision with the fresh lower training coordinates.

## Acceptance gates

A PASS requires, without post-result relaxation:

1. exactly 275 fresh training spectra and 176 fresh protected spectra, one intended solver invocation each and no retry/resume/GitHub rerun;
2. every spectrum complete on 380..780 nm and every direct transmission finite and strictly positive; zero/underflow/nonfinite is a terminal refusal, never epsilon;
3. protected Johnson-V max absolute `delta A_V <= 0.025 mag` globally and separately in every one of the 11 altitude intervals;
4. protected Johnson-V RMS `<=0.010 mag` globally and separately in every altitude interval;
5. exact 5-degree seam spectra content-identical to the authoritative v3.2 source, and exact-5 application routing to the unchanged v3.2 provider;
6. `exp(-tau)` from the lower runtime must be finite and strictly positive at every wavelength; otherwise fail closed;
7. outside a passed lower support interval return `STELLAR_SPECTRAL_RUNTIME_OOD`.

If this protected state passes, the minimum scientifically supported geometric altitude may be declared 0.25 degrees. If any protected interval fails, this state is terminal FAIL. Its protected residuals cannot be used to back-select a higher minimum altitude or tune a successor.

Exact geometric horizon 0 degrees is outside this state and remains unsupported.

## Anti-fitting / lane separation

Taylor, Jerusalem, desired halachic first-seeing times, 0077 holdout residual directions, or any empirical real-sky desired outcome are forbidden model-selection inputs. AVPS richer aerosol-profile science is not consumed. Horizon obstruction, terrain and clouds remain separate providers/blockers.

## Execution ordering

This review package is solver-free. First review/merge the generator, seam-consumption rules, routing contract, fail-closed interpolation and exact ledger counts. Only then, after a fresh Issue #60 fence and exact-main check, may a separately controlled fresh one-shot 275-spectrum training execution be considered. Protected holdout remains unopened until the training asset is assembled and reviewed without protected values.
