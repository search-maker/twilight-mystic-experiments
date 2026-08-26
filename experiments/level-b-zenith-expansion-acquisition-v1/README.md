# Level-B zenith expansion acquisition v1

One-shot **training acquisition only** for extending the solar-twilight MYSTIC surrogate geometry from 80 degrees target altitude toward the zenith. It does not change the current Level-B v3 model, support rule, runtime, UI, or production/default behavior.

The package contains 16 training geometries from 80 through 90 degrees plus two exact-zenith azimuth-invariance diagnostics. The four 80-degree anchors are altitude-only extensions from existing high-altitude v3 support coordinates, so they provide a controlled continuity seam. Exact-90 training cases use canonical relative azimuth 0 because azimuth is undefined at zenith; separate phi=90/180 runs test direct-MYSTIC invariance and are excluded from training.

Every elevated-site case reuses the reviewed Level-B ground-site semantics: AFGLUS is shifted with `atm_z_grid` so its bottom is the physical site elevation, while the observer remains at `zout 0` above the local surface. `altitude` and `mc_elevation_file` shortcuts are refused.

`holdout-design.review.json` is generated and frozen before acquisition results. It contains eight future untouched geometries, allocates no holdout seeds, and authorizes no holdout execution. No support expansion is allowed until a new zenith-safe representation is frozen, the holdouts pass, exact-zenith azimuth invariance passes, the 80-degree seam agrees with frozen v3, and the existing 5-80 degree domain shows no regression.

The acquisition is solar-twilight only. Lunar-scattered, natural-night, and artificial-skyglow backgrounds remain separate components and are not absorbed into this surrogate.
