#!/usr/bin/env python3
from __future__ import annotations
import math
import rolo311g as r

rows = r.load_coefficients()
assert len(rows) == 19
assert rows[0]['wavelength_nm'] == 350.0
assert rows[-1]['wavelength_nm'] == 865.3
assert r.P4_DEG == 16.7498, 'guard against secondary-source p4 transcription error'
assert r.P3_DEG == -30.5858
assert r.C2 == -0.0013425

row553 = next(x for x in rows if x['wavelength_nm'] == 553.8)
g = r.RoloGeometry(
    phase_deg=7.0,
    subobserver_latitude_deg=0.0,
    subobserver_longitude_deg=0.0,
    subsolar_longitude_deg=7.0,
)
a553 = r.disk_equivalent_reflectance(row553, g)
assert math.isclose(a553, 0.09869856650046396, rel_tol=0, abs_tol=2e-15), a553

# Polynomial phase and subsolar-longitude terms are radians; nonlinear phase
# scales are degrees. This known fixture catches accidental all-degree/all-radian rewrites.
g2 = r.RoloGeometry(16.0, 1.0, -2.0, 10.0)
a2 = r.disk_equivalent_reflectance(row553, g2)
assert math.isclose(a2, 0.07577298460473274, rel_tol=0, abs_tol=2e-15), a2

# Exact band nodes must survive the reconstruction unchanged.
for wavelength, reflectance in r.band_reflectances(g):
    assert math.isclose(r.log_reflectance_interpolated(wavelength, g), reflectance, rel_tol=0, abs_tol=1e-15)

# Distance law follows original Eq. 7: actual irradiance is standard / f_d.
standard_geom = r.RoloGeometry(7, 0, 0, 7, 1.0, 384400.0)
farther_geom = r.RoloGeometry(7, 0, 0, 7, 1.0, 2 * 384400.0)
i0 = r.actual_lunar_irradiance_w_m2_nm(553.8, 1.85, standard_geom)
i2 = r.actual_lunar_irradiance_w_m2_nm(553.8, 1.85, farther_geom)
assert math.isclose(i2 / i0, 0.25, rel_tol=0, abs_tol=2e-15)

# Phase range is the fitted ROLO 311g range, not an extrapolation to exact full Moon.
for bad_phase in [0.0, 1.54, 97.01, 120.0]:
    try:
        r.band_reflectances(r.RoloGeometry(bad_phase, 0, 0, 0))
        raise AssertionError('unsupported phase accepted')
    except r.RoloSupportError:
        pass

for bad_wavelength in [350.0, 355.0, 865.31, 900.0]:
    try:
        r.reconstruct_spectrum([bad_wavelength], [1.0], standard_geom)
        raise AssertionError('spectral extrapolation accepted')
    except r.RoloSupportError:
        pass

spectrum = r.reconstruct_spectrum([380.0, 553.8, 780.0], [1.7, 1.85, 1.4], standard_geom)
assert spectrum['reconstructionId'] == r.RECONSTRUCTION_ID
assert spectrum['operationalRoloOrGiroClaim'] is False
assert spectrum['validatedForAtmosphericScatteredMoonlight'] is False
assert spectrum['productionAuthorized'] is False
assert all(x > 0 for x in spectrum['lunarToaIrradianceWm2Nm'])

print('ROLO 311g unit/source/distance/reconstruction contract: PASS')
