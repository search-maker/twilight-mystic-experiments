# Jerusalem Tishrei direct-MYSTIC proposal v1

This directory preregisters a direct-MYSTIC diagnostic at the exact Level-B equilibrium Three-Star event already frozen for Jerusalem, 2025-09-23.

It is proposal-only. It does not authorize syntax execution or `uvspec`, does not tune any parameter, does not change `F=3.14`, and does not authorize production, full-spectrum sky validation, measured-real-sky validation, human-first-seeing validation, or Pandora.

## Exact event binding

- application evidence head: `0ac8c551738354bdde320b50d6facac40d7acb9a`
- merged application main containing the catalog-handoff fix: `e2d5b761206b6223526f6f79fcb0af5f6de3ba06`
- event workflow run: `32982830256`
- Tishrei evidence artifact: `9612259358`
- artifact digest: `sha256:d43120ad60d2e4a502023cd187bbeffecd6364d4edc975c14c84432c3c8097c5`
- event time: `1758642904994.5` ms Unix
- solar depression: `5.2416836635666755 deg`
- observer elevation: `800 m`
- admitted atmosphere: CAMS Global AOD550 `0.22`, sample 2025-09-23T16:00:00Z, 80.802 s from the requested event time

The three geometries are the exact lines of sight to Antares (HR 6134), Rasalhague (HR 6556), and completing star 37 Gamma Cygni (HR 7796) at the frozen event.

## Numerical plan

For each geometry the existing `mystic-cross-geometry-v1` contract is used with two independent 20M-photon blocks for `reference-vroom` and two independent 20M-photon blocks for `alis`: 12 cases, 240M configured photon histories total. The existing frozen AFGLUS atmosphere, scalar `mc_spherical 1D`, aerosol default with exact AOD550, albedo 0.15, 380-780 nm domain, and diagnostic spectral nodes are retained.

The purpose is to measure direct solver-vs-surrogate sky-radiance error at the actual event geometry. It is not an aerosol-family validation and must remain separated from matched-stellar v2 family diagnostics.

Execution must remain blocked until the repository's existing one-purpose authorization/guard machinery is explicitly instantiated for this exact manifest hash.
