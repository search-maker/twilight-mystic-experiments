# Twilight MYSTIC Experiments

Public, execution-only repository for preregistered libRadtran/MYSTIC twilight diagnostics.

This repository intentionally contains no application code, user data, credentials, or private repository history. Its only purpose is to make bounded scientific experiments and their audits independently inspectable.

## Current experiment

`corrected-spectral-convergence-v1` repeats the previously intended 12-case ALIS-versus-conventional-reference convergence diagnostic after a structural input failure prevented the reference cases from running.

The correction is narrow:

- the requested wavelength domain remains 380–780 nm;
- the conventional-reference custom wavelength grid now also spans exactly 380–780 nm;
- the same 15 diagnostic nodes from 470–660 nm are preserved;
- all 12 seeds are fresh;
- numerical gates, photon ceilings, geometry, no-retry policy, and success boundaries remain frozen.

## Safety boundary

The committed `experiment/authorization.json` is disabled. Contract CI never runs MYSTIC. Scientific execution can occur only from a one-purpose authorization commit on the exact branch `authorization/corrected-spectral-convergence-v1`, after exact-head contract CI is green.

A successful result does not establish physical validity, observational validity, LUT readiness, production readiness, or permission to change any default model.

## Workflows

- `contract.yml`: static validation and unit tests only.
- `execution.yml`: exact one-shot MYSTIC execution; no manual dispatch.
- `audit.yml`: read-only audit of the exact uploaded artifact after the execution workflow completes, including failed execution artifacts.

No license is granted by publication of this repository.
