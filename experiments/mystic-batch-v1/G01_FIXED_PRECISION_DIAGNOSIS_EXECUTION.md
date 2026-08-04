# Fixed g01 precision diagnosis execution

This stage is a final bounded Monte Carlo diagnosis for `g01-reference-bridge` after the successful ordinal-6 run established that g01 agrees with frozen VROOM but four 50M held-out ALIS blocks miss the 8% RSEM target marginally.

The stage preserves held-out blocks 1–4, executes only four fresh ALIS 600 nm blocks 5–8 with seeds 84601–84604 and 50M photons each, then combines exactly those eight held-out/diagnostic blocks. Selection data remains excluded from acceptance.

The stage is manual-only, first-attempt-only, duplicate-refusing, non-retrying, and requires a separate one-purpose authorization commit. There are no automatic blocks after this stage. The result is exactly one of: pass, persistent high variance, or method discrepancy.

Even a pass completes only a computational reference screen. It does not fit a surrogate, authorize production, or establish physical/observational validity.
