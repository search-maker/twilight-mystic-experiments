# Held-out computational confirmation

The final-convergence run selects a low-variance ALIS importance wavelength and may request additional precision. Selection blocks are not allowed to confirm their own choice.

This package promotes the generated `next-confirmation-proposal.json` from one exact successful first-attempt final-convergence run into a guarded, dynamic scientific matrix. Each requested method receives exactly four fresh held-out blocks. The package accepts between 1 and 24 cases, caps each case at 400 million photon histories, permits at most 16 parallel jobs, performs one syntax check and at most one solver execution per case, and has no retry or open-ended extension path.

The analysis compares held-out results with the frozen precise counterpart, requires held-out relative standard error of the mean no greater than 8 percent, retains the existing broad spectral screening checks, and emits an audited computational reference dataset only for passing geometries.

A passing result completes computational screening for the tested geometries. It does not prove atmospheric realism, observational validity, human-visibility calibration, surrogate validity, LUT readiness, or production readiness. Observation validation remains mandatory, and no model training or default-model change is automatically authorized.
