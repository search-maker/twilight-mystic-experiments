# Native stellar zenith v3 — recovery 1

This is an infrastructure-only recovery from GitHub Actions run `33033344840`.

## Terminal state of the prior attempt

The original one-shot dispatch passed its single-use branch/commit boundary and installed the exact pinned libRadtran environment. The following immutable-input checks then passed before the failure:

- source native-v2 runtime SHA-256;
- frozen Pickles SED SHA-256;
- frozen Johnson-V SHA-256;
- `uvspec` executable SHA-256;
- `uvspec -h` identity check reached completion before the package-list parser.

The preflight then failed because the workflow assumed that `micromamba list --json` had a top-level list and iterated it as package dictionaries. On the installed micromamba runtime that assumption was false, producing `AttributeError: 'str' object has no attribute 'get'`.

The scientific execution step was skipped. Therefore the prior solver invocation count is exactly **0** and no training or holdout result was opened.

## Recovery scope

Recovery 1 changes only the package-identity preflight parser. It reads the stable human-readable `micromamba list rubin-libradtran` table and requires exactly one row equal to:

`rubin-libradtran=2.0.6=py312pl5321he9373c2_1`

The recovery does **not** change:

- the native MYSTIC-STATE-0081 source runtime;
- any wavelength, atmosphere, aerosol, altitude, elevation, or AOD coordinate;
- the 100 training spectra;
- the 64 disjoint fresh validation spectra;
- Pickles templates 1/26/45 or Johnson-V photometry;
- csc(altitude) trilinear direct-optical-depth interpolation;
- the 0.025 mag max-absolute and 0.010 mag RMS gates;
- any production, real-sky, or human-visibility claim boundary.

GitHub rerun of run `33033344840` remains forbidden. A separate one-shot recovery dispatch must bind that failed run, state `priorSolverInvocationCount: 0`, and be the only changed file in a single commit directly above the then-current `main`.
