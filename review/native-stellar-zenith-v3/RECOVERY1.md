# Native stellar zenith v3 recovery history

This file preserves the recovery history for the native stellar zenith extension.

- v3 exact physical zenith attempted SDISORT with `sza=0`, which implies `umu0=1.0`.
- The exact-90 diagnostic run `33034345605` established the reviewed libRadtran 2.0.6 SDISORT behavior: it emits `Error,  Does not work for umu0=1.0`, returns code 0, and produces no stdout spectrum.
- v3.1 therefore keeps the physical target altitude at exactly 90 degrees but evaluates that one endpoint using the documented solver-limit ray `sza=0.001 deg` and normalizes `edir` using the matching `mu0=cos(0.001 deg)`.
- The relative plane-parallel airmass excess of this solver-only regularization is below `2e-10`.
- Training coordinates, protected holdout coordinates, acceptance thresholds, atmosphere, photometric assets, csc-altitude interpolation, and all source-v2 values through 80 degrees remain unchanged.
- No production authorization, empirical real-sky validation, or human first-seeing validation follows from this numerical recovery.
