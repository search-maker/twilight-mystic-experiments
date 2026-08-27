# Taylor CAMS AOD provider cross-check v1

Status: retrieval-only provenance diagnostic. No Taylor SQM values or residuals are read and no MYSTIC/libRadtran solver is executed.

## Frozen question

Taylor v1 froze AOD550 through Open-Meteo `domains=cams_global`. A later direct ADS CAMS prior-cycle vertical-extinction retrieval returned materially lower column AOD. Before any broadband vertical-profile rerun, determine whether this is a forecast-cycle/product/provider difference rather than choosing the value that gives the preferred Taylor fit.

## Frozen retrievals

1. ADS CAMS Global Atmospheric Composition Forecasts, base `2025-08-08 00Z`, lead `0` and `3 h`, total aerosol optical depth at `532 nm` and `550 nm`, exact Ann Arbor site `42.256 N, 83.709 W` by bilinear interpolation of the enclosing returned grid nodes.
2. Fresh capture of the same Open-Meteo Air Quality API path used by the Taylor-v1 fallback: `hourly=aerosol_optical_depth`, `domains=cams_global`, `cell_selection=nearest`, GMT.
3. ADS 01Z value is the linearly interpolated value one-third of the way from valid 00Z to valid 03Z. This interpolation rule is frozen before output is opened.

## Decision boundary

The result may identify a provider/product/cycle mismatch. It does **not** replace the frozen Taylor-v1 atmosphere, pick a winning AOD, validate a vertical profile, or authorize a new MYSTIC run. Any subsequent atmospheric choice must be justified independently of the Taylor brightness residual.
