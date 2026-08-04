# Adaptive final convergence and parallel model work

The completed pilot and Stage-2 runs contain 40 verified case results and 800 million configured photon histories. Reanalysis uses the relative standard error of the independent-block mean rather than raw block CV as the convergence gate. Raw CV remains a noise diagnostic.

This changes the immediate allocation:

- `g04-mid-perpendicular` is carried as screening agreement; no more photons are spent there.
- `g05-mid-opposite-low` receives blocks 5 and 6 for both methods.
- `g01-reference-bridge` and `g06-late-opposite-high-aerosol` receive VROOM blocks 5 and 6, while ALIS tests importance wavelengths 500, 550, and 600 nm with three independent blocks each.

The 26-case matrix totals 520 million configured photon histories and runs at most sixteen cases in parallel. The analysis selects the lowest-variance ALIS reference that remains compatible with VROOM. Every ALIS reference selected from diagnostic data is sent to an independent held-out four-block confirmation. If g05 remains noisy, the same analysis emits a fixed precision-confirmation proposal for only the noisy method. Photon counts are calculated in advance and capped; blocks never continue without a fixed stop.

In parallel, `modeling/twilight-surrogate-v1/reference-readiness.cross-geometry.json` exposes the verified reference-screening state to the surrogate/LUT track without authorizing training, a LUT, or a production default. Observation validation remains a separate required gate.
