# R3 accuracy changes

1. Bound generic adapter/executor, execution contract, runtime lock, full-spectrum executor basis and 1-nm grid to exact current-main Git blobs.
2. Replaced the misleading sparse-grid `rawSpectrum` claim with a frozen 401-node 380–780 nm reference-VROOM spectrum.
3. Added exact libRadtran 2.0.6 aerosol directive semantics; family mapping remains rural=1, maritime=4, urban=5, tropospheric=6.
4. Added fail-closed aerosol directive surface checking.
5. Froze CRN-aware uncertainty: use three paired-seed replicate contrasts; marginal MC std spectra are diagnostics, not independent-quadrature ratio errors.
6. Added review-only tracked-tree and Actions artifact seed scanners; any expired/unavailable artifact keeps complete history proof false.
7. Freeze now requires analysis-contract.v3.json and byte-equivalent reviewed 1-nm grid.
