# Cross-geometry stage-two proposal

The completed pilot and artifact-only post-processing selected four geometries for additional Monte Carlo blocks:

- `g01-reference-bridge`
- `g04-mid-perpendicular`
- `g05-mid-opposite-low`
- `g06-late-opposite-high-aerosol`

The selection is frozen from scientific run `30856116586` and post-processing run `30858046820`. The committed screening analysis has SHA-256 `c4e9808102a4b9d78163daff9c066a27379355e299582b39a4c9e509aff65abb`.

The proposal contains blocks 3 and 4 for both `reference-vroom` and `alis` at each selected geometry: 16 cases, 20 million photon histories per case, and 320 million configured photon histories in total. Every seed is new and distinct from the pilot seeds.

This is a proposal only. It creates no authorization, exposes no execution workflow, performs no syntax check or solver process, and makes no claim of physical, observational, surrogate, LUT, or production validity. A separate reviewed execution bridge and a separate one-purpose authorization would be required before any stage-two scientific run.
