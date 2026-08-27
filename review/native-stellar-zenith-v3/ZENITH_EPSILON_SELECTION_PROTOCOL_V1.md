# Native stellar zenith — preregistered epsilon selection protocol v1

This protocol is frozen **before** opening the training-only epsilon-convergence results. It does not itself select a canonical epsilon and it does not authorize protected-holdout access or production use.

## Evidence being awaited

The frozen diagnostic evaluates 19 strictly positive source zenith angles at four atmosphere/AOD corners using the exact pinned SDISORT/libRadtran runtime. Each solver call is classified usable/rejected. Usable calls must produce the exact 401-node 380–780 nm spectrum. Johnson-V differences for frozen Pickles templates 1, 26, and 45 are measured relative to the smallest solver-usable SZA at each atmosphere corner.

A rejected case may be interpreted as part of the numerical zenith boundary only if it matches the already-proven endpoint signature: solver return code 0, zero stdout spectral rows, and `Error,  Does not work for umu0=1.0` in stderr. Any other rejection invalidates canonical-epsilon selection from this diagnostic.

## Selection rule

A future canonical numerical representation for physical target altitude 90 deg may be selected from the already-tested SZA values only if **all** of the following hold:

1. The diagnostic completed all 76 authorized solver calls once, with no retry/resume.
2. Every rejected case matches the proven SDISORT `umu0=1.0` endpoint signature described above. Any non-endpoint solver failure or malformed nonempty spectrum is disqualifying.
3. Solver usability is monotonic toward zenith at every atmosphere/AOD corner: as SZA decreases, the sequence may transition from usable to rejected at most once and may never become usable again after rejection.
4. Let `R` be `largestSourceZenithAngleRejectedByAnyCornerDeg`. Let the candidate set contain only tested SZA values that are solver-usable at **all four** atmosphere/AOD corners.
5. A candidate must satisfy `SZA >= 1.25 * R`. This is a preregistered numerical safety margin from the observed SDISORT endpoint boundary; choosing merely the closest passing value is forbidden.
6. A candidate must satisfy the analytic plane-parallel vertical-airmass bound `sec(SZA) - 1 <= 1.0e-7`.
7. Across all four atmosphere/AOD corners and Pickles templates 1/26/45, the candidate's reported Johnson-V extinction difference relative to that corner's smallest solver-usable SZA must satisfy `abs(delta A_V) <= 1.0e-4 mag`.
8. Among candidates satisfying items 4–7, choose the **smallest tested SZA**. No other post-result preference or retuning is allowed.
9. If no tested candidate satisfies every condition, **no canonical epsilon is selected**. A separately preregistered diagnostic or a different solver treatment is required.

## Post-selection boundary

Freezing a canonical epsilon under this rule would authorize only a new computational stellar-transport candidate. The 100 training spectra and the already-protected 64 atmospheric holdout spectra must then be executed/evaluated under a separately authorized recovery. Existing <=80 deg runtime values, atmosphere identity, photometric assets, csc-altitude interpolation, and the 0.025 mag maximum / 0.010 mag RMS stellar validation gates remain unchanged.

Passing this numerical selection protocol does not by itself authorize production, empirical real-sky validation claims, or human first-seeing validation claims.
