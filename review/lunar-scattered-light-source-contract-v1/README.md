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

Before this component may enter the default total-sky compositor it still requires independent source-spectrum cross-checks, atmospheric scattered-moonlight validation against measured moonlit skies, uncertainty calibration, and a separately reviewed production decision.
