# Cross-geometry Stage 3 diagnostics

Stage 3 corrects the stopping statistic before spending more Monte Carlo work. The primary noise metric is the relative standard error of the mean across independent blocks (`CV / sqrt(n)`), not the coefficient of variation itself. A zero ALIS `mc.rad.std.spc` value is recorded as unavailable and is never interpreted as zero uncertainty.

The corrected Stage-2 assessment treats g02, g03, and g04 as converged screening agreement. It does not rerun them. g05 receives only two fresh 405 nm ALIS blocks because VROOM is already stable and ALIS is just above the 10 percent RSEM threshold.

For g01 and g06, Stage 3 runs two fresh reference-VROOM blocks and three fresh ALIS replicates at each of 500, 550, and 600 nm. This diagnoses whether the original 405 nm ALIS reference wavelength caused poor efficiency or spectral-approximation sensitivity. The batch contains 24 cases and 480 million configured photon histories.

After execution, candidate selection must use independent replicate scatter, integrated ALIS/VROOM agreement, and spectral-shape screening. If no candidate passes, the result is technical diagnosis required. Stage 3 forbids automatic additional blocks, production use, LUT or surrogate authorization, or a default-engine change.
