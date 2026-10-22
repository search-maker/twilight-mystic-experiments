# Lunar CRS custom-source binding checkpoint v1

Status: **PREREGISTERED — exact-runtime capability result pending**.

The frozen lunar renderer currently combines `source solar <lunar_source_file>` with `mol_abs_param crs`. libRadtran 2.0.6 documentation is internally inconsistent about whether the explicit source file is consumed in this combination, so atmospheric lunar MYSTIC execution must not rely on the renderer until a version-bound source-binding probe passes.

The preregistered gate is `libradtran-custom-source-crs-admission-gate-v1.json`. It binds conda-forge `rubin-libradtran=2.0.6=py312pl5321he9373c2_1`, uvspec SHA-256 `2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3`, and the base libRadtran data-tree SHA-256 `ad30b49177e9c84e46497d69faf0c75e466996b0d0003f1de210289ae9f847d7`.

The probe is deliberately non-MYSTIC and non-empirical. Two otherwise identical DISORT direct-irradiance runs use source amplitudes 1 and 7 at 380/550/780 nm under `mol_abs_param crs`. Admission requires every finite Arm-B/Arm-A direct-irradiance ratio to be 7 within the pre-frozen absolute tolerance 0.01. A ratio near 1, nonzero solver exit, parse failure, runtime hash mismatch, or any tolerance failure blocks the current CRS custom-source route.

Passing this gate proves only that the exact runtime consumes the custom extraterrestrial source amplitude with CRS. It does **not** validate ROLO, atmospheric scattered moonlight, finite-disk treatment, X-Shooter agreement, Air-LUSI agreement, total-sky performance, or production use. Failing this gate does not authorize an alternate source mode; lowtran, reptran, or transfer-kernel alternatives require a separate result-blind review before use.

Next action: obtain the first-attempt exact-head Actions artifact from `.github/workflows/lunar-custom-source-crs-admission-v1.yml`, independently read back `probe-report.json`, and record PASS/FAIL without changing the frozen ratio criterion after observing the result. No Taylor/Jerusalem residuals are involved.
