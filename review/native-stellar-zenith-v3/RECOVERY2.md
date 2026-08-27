# Native stellar zenith v3.1 — recovery2

## Why a method revision is required

The one-shot v3 recovery run `33033742217` passed all frozen runtime/input identity checks and then stopped during the sequential training campaign when the strict parser received no wavelength rows.  The independently frozen one-case structural diagnostic run `33034345605` reproduced the first exact-zenith coordinate only and preserved raw process output.  Its `case.stderr.txt` states:

`Error,  Does not work for umu0=1.0`

The exact-zenith diagnostic returned process code 0 but an empty stdout spectrum.  This establishes that the frozen SDISORT 2.0.6 executable does not evaluate the exact numerical endpoint `umu0=1.0` even though the physical vertical direct-transmission limit is well defined.

## v3.1 convention

The physical model domain remains exactly `targetAltitudeDeg <= 90.0`.  For a physical target altitude of exactly 90 degrees only, the deterministic SDISORT input uses `sza=0.001 deg` (solver target altitude `89.999 deg`).  All non-zenith coordinates are rendered unchanged.

The parser divides `edir` by the matching solver `mu0=cos(0.001 deg)` rather than by 1.  Physical and solver geometry are both retained in provenance.

The plane-parallel airmass difference introduced by this numerical limiting ray is

`1/cos(0.001 deg) - 1 = 1.5230883221306613e-10`,

which is required to remain below the frozen bound `2e-10`.

## What is unchanged

- Training altitude coordinates: 82.5, 85.0, 87.5, 90.0 deg.
- 100 training spectra: 4 altitudes x 5 site elevations x 5 AOD550 knots.
- Fresh protected validation altitudes: 80.9375, 83.4375, 85.9375, 88.4375 deg.
- 64 fresh validation spectra: 4 altitudes x 4 elevations x 4 AOD550 values.
- 192 Johnson-V comparisons using frozen Pickles library templates 1, 26, and 45.
- Native MYSTIC-STATE-0081 atmosphere and AFGLUS identity.
- Deterministic `sdisort nscat 1` direct-beam method.
- Existing native v2 values at all coordinates through 80 degrees.
- csc-altitude / linear-elevation / linear-AOD interpolation contract.
- Acceptance gates: maximum absolute delta A_V <= 0.025 mag and RMS delta A_V <= 0.010 mag, globally and for every new altitude interval.

## Evidence and failure preservation

v3.1 writes every solver input, stdout, stderr, and case metadata before parsing.  The recovery workflow uploads the execution directory even on failure.  No GitHub rerun, solver retry, solver resume, post-result retuning, production activation, empirical real-sky validation claim, or human first-seeing validation claim is authorized by this recovery.
