# AOPS v1 ordinal 37 run observer

Control-plane observer only.

- Reads GitHub Actions run metadata for the exact ordinal-37 dispatch branch/head.
- Does not download or open scientific case, aggregate, spectral, or Level-B artifacts.
- Does not request rerun, retry, resume, dispatch, runtime setup, or solver execution.
- Does not modify `main`, authorization, dispatch, seeds, science design, or analysis rules.
- The observer PR must remain unmerged and may be closed after its metadata artifact is verified.
