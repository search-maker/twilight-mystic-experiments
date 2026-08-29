# Lunar scattered-light source contract v1

This review lane creates a physically explicit **lunar extraterrestrial source** for later MYSTIC atmospheric scattering. It is not yet a validated moonlit-sky provider and changes no production/default behavior.

## Primary source

Kieffer & Stone (2005), *The Spectral Irradiance of the Moon*, AJ 129, 2887-2901. The implementation uses the original paper's ROLO model 311g Eq. 10, distance scaling Eq. 7, irradiance relation Eq. 8, wavelength-dependent Table 4 coefficients, and constant Eq. 11 values. In particular, the original paper gives `p4 = 16.7498 deg`; that value is frozen by regression because some secondary transcriptions disagree.

The original fitted phase support is 1.55-97 deg. Phase outside that range fails closed. The polynomial phase and subsolar-longitude variables use radians, observer libration terms use degrees, and p1-p4 nonlinear phase scales use degrees.

## Continuous visible spectrum boundary

The published band-node reflectance calculation is implemented directly. A 380-780 nm MYSTIC source still requires values between the ROLO effective wavelengths. This package uses linear interpolation in **log disk-equivalent reflectance** between the published nodes and labels the result `RESEARCH_ONLY`. It is explicitly not represented as the full operational ROLO/GIRO spectral interpolation because the paper describes an Apollo-derived between-band spectral shape adjustment not fully supplied as an executable public coefficient table.

The interpolated reflectance is multiplied by a caller-bound 1-AU solar spectrum; lunar distance scaling is then applied explicitly. The resulting lunar top-of-atmosphere spectrum is written in libRadtran's default solar-source file units, mW/(m2 nm).

## MYSTIC geometry

The lunar source is treated as a collimated external source:
- `sza` is the Moon zenith angle;
- `phi0 = 0` defines the source azimuth reference;
- target `phi` is the target relative azimuth from the Moon;
- `day_of_year` is forbidden because lunar source irradiance already contains explicit distance scaling;
- elevated sites use the same reviewed Level-B `atm_z_grid` plus local `zout 0` semantics;
- finite lunar-disk angular extent is not yet modeled.

## Independent Air-LUSI source cross-check

The public NIST Air-LUSI 2022 dataset is preregistered as the independent TOA cross-check before atmospheric-scattering validation. The exact NIST repository commit, Git-LFS object identity and official example-notebook blob are frozen. The official notebook semantics and the open NIST metadata corrections are also bound before any model/reference residual calculation.

The validation is now separated into two non-overlapping arms:

1. **Direct disk-reflectance arm.** The official notebook identifies `Lunar_Disk_Reflectance` as the quantity compatible with ROLO/GIRO. The frozen ROLO Eq. 10 disk-equivalent reflectance is compared only at original ROLO effective wavelengths, with a deterministic bracketing interpolation of the high-resolution Air-LUSI channel-centroid reflectance. This arm needs no separately downloaded solar spectrum and no distance correction. It therefore isolates the coefficient/geometry reflectance calculation from Eq. 7/8 source conversion.
2. **Full TOA irradiance arm.** This separately checks Eq. 7/8 and the full source conversion. It remains blocked until the exact TSIS-1 Hybrid Solar Reference Spectrum Version 2 artifact named by the NIST notebook is byte-hash-bound. Standard-distance and true-distance comparisons are separate modes; true-distance Air-LUSI irradiance follows the NIST correction and is obtained by dividing by `distance_correction_factor`.

Neither arm permits scale, tilt, phase or libration fitting, and neither has a post-hoc pass/fail threshold. Air-LUSI used ROLO for relative within-flight normalization, so even a good comparison is not represented as fully independent validation of ROLO phase evolution.

Before this component may enter the default total-sky compositor it still requires exact Air-LUSI binary admission, the preregistered TOA comparisons, atmospheric scattered-moonlight validation against measured moonlit skies, uncertainty calibration, and a separately reviewed production decision.
