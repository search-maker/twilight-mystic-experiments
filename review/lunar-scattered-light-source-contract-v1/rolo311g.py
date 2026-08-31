#!/usr/bin/env python3
from __future__ import annotations
import csv, math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

COEFFICIENTS = Path(__file__).with_name('rolo311g-visible-coefficients.csv')
MOON_STANDARD_SOLID_ANGLE_SR = 6.4177e-5
STANDARD_VIEWER_MOON_DISTANCE_KM = 384_400.0
PHASE_SUPPORT_DEG = (1.55, 97.0)
# Kieffer & Stone (2005), Eq. 11. p4 is 16.7498 deg in the original paper.
C1 = 0.00034115
C2 = -0.0013425
C3 = 0.00095906
C4 = 0.00066229
P1_DEG = 4.06054
P2_DEG = 12.8802
P3_DEG = -30.5858
P4_DEG = 16.7498

RECONSTRUCTION_ID = 'ROLO311G_BAND_NODE_LOG_REFLECTANCE_LINEAR_INTERPOLATION_RESEARCH_ONLY'

@dataclass(frozen=True)
class RoloGeometry:
    phase_deg: float
    subobserver_latitude_deg: float
    subobserver_longitude_deg: float
    subsolar_longitude_deg: float
    sun_moon_distance_au: float = 1.0
    observer_moon_distance_km: float = STANDARD_VIEWER_MOON_DISTANCE_KM

class RoloSupportError(ValueError):
    pass

def _finite(name: str, value: float) -> float:
    x = float(value)
    if not math.isfinite(x):
        raise RoloSupportError(f'{name} must be finite')
    return x

def validate_geometry(g: RoloGeometry) -> RoloGeometry:
    phase = _finite('phase_deg', g.phase_deg)
    if not (PHASE_SUPPORT_DEG[0] <= phase <= PHASE_SUPPORT_DEG[1]):
        raise RoloSupportError(f'phase_deg outside original ROLO 311g fitted support {PHASE_SUPPORT_DEG}')
    lat = _finite('subobserver_latitude_deg', g.subobserver_latitude_deg)
    lon = _finite('subobserver_longitude_deg', g.subobserver_longitude_deg)
    slon = _finite('subsolar_longitude_deg', g.subsolar_longitude_deg)
    if abs(lat) > 15 or abs(lon) > 15:
        raise RoloSupportError('subobserver libration outside conservative +/-15 deg admission envelope')
    if abs(slon) > 120:
        raise RoloSupportError('subsolar longitude outside conservative +/-120 deg admission envelope')
    sm = _finite('sun_moon_distance_au', g.sun_moon_distance_au)
    vm = _finite('observer_moon_distance_km', g.observer_moon_distance_km)
    if sm <= 0 or vm <= 0:
        raise RoloSupportError('distances must be positive')
    return RoloGeometry(phase, lat, lon, slon, sm, vm)

def load_coefficients(path: Path = COEFFICIENTS) -> list[dict[str, float]]:
    rows = []
    with path.open(newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            rows.append({k: float(v) for k, v in row.items()})
    if len(rows) != 19:
        raise RoloSupportError(f'expected 19 frozen visible/NIR ROLO rows, got {len(rows)}')
    wavelengths = [r['wavelength_nm'] for r in rows]
    if wavelengths != sorted(wavelengths) or len(set(wavelengths)) != len(wavelengths):
        raise RoloSupportError('coefficient wavelengths must be strictly increasing')
    if wavelengths[0] != 350.0 or wavelengths[-1] != 865.3:
        raise RoloSupportError('coefficient endpoint drift')
    return rows

def disk_equivalent_reflectance(row: dict[str, float], geometry: RoloGeometry) -> float:
    g = validate_geometry(geometry)
    phase_rad = math.radians(g.phase_deg)
    sunlon_rad = math.radians(g.subsolar_longitude_deg)
    # Eq. 10 units from the original table: phase and SunLon polynomials use rad;
    # observer libration uses deg; nonlinear p1..p4 terms use deg.
    ln_a = (
        row['a0']
        + row['a1'] * phase_rad
        + row['a2'] * phase_rad**2
        + row['a3'] * phase_rad**3
        + row['b1'] * sunlon_rad
        + row['b2'] * sunlon_rad**3
        + row['b3'] * sunlon_rad**5
        + C1 * g.subobserver_latitude_deg
        + C2 * g.subobserver_longitude_deg
        + C3 * sunlon_rad * g.subobserver_latitude_deg
        + C4 * sunlon_rad * g.subobserver_longitude_deg
        + row['d1'] * math.exp(-g.phase_deg / P1_DEG)
        + row['d2'] * math.exp(-g.phase_deg / P2_DEG)
        + row['d3'] * math.cos((g.phase_deg - P3_DEG) / P4_DEG)
    )
    value = math.exp(ln_a)
    if not math.isfinite(value) or value <= 0:
        raise RoloSupportError('nonpositive/nonfinite disk-equivalent reflectance')
    return value

def band_reflectances(geometry: RoloGeometry, rows: Sequence[dict[str, float]] | None = None) -> list[tuple[float, float]]:
    data = list(rows) if rows is not None else load_coefficients()
    return [(r['wavelength_nm'], disk_equivalent_reflectance(r, geometry)) for r in data]

def log_reflectance_interpolated(wavelength_nm: float, geometry: RoloGeometry, rows: Sequence[dict[str, float]] | None = None) -> float:
    wavelength = _finite('wavelength_nm', wavelength_nm)
    values = band_reflectances(geometry, rows)
    if not (values[0][0] <= wavelength <= values[-1][0]):
        raise RoloSupportError('wavelength extrapolation forbidden')
    for (w0, a0), (w1, a1) in zip(values, values[1:]):
        if wavelength == w0:
            return a0
        if w0 <= wavelength <= w1:
            if wavelength == w1:
                return a1
            t = (wavelength - w0) / (w1 - w0)
            return math.exp(math.log(a0) * (1 - t) + math.log(a1) * t)
    raise RoloSupportError('interpolation interval not found')

def distance_factor_to_standard(geometry: RoloGeometry) -> float:
    g = validate_geometry(geometry)
    return g.sun_moon_distance_au**2 * (g.observer_moon_distance_km / STANDARD_VIEWER_MOON_DISTANCE_KM)**2

def actual_lunar_irradiance_w_m2_nm(
    wavelength_nm: float,
    solar_irradiance_at_1au_w_m2_nm: float,
    geometry: RoloGeometry,
) -> float:
    solar = _finite('solar_irradiance_at_1au_w_m2_nm', solar_irradiance_at_1au_w_m2_nm)
    if solar < 0:
        raise RoloSupportError('solar irradiance must be nonnegative')
    a = log_reflectance_interpolated(wavelength_nm, geometry)
    standard = a * MOON_STANDARD_SOLID_ANGLE_SR * solar / math.pi
    actual = standard / distance_factor_to_standard(geometry)
    if not math.isfinite(actual) or actual < 0:
        raise RoloSupportError('invalid lunar irradiance')
    return actual

def reconstruct_spectrum(
    wavelengths_nm: Iterable[float],
    solar_irradiance_at_1au_w_m2_nm: Iterable[float],
    geometry: RoloGeometry,
) -> dict:
    wl = [float(x) for x in wavelengths_nm]
    solar = [float(x) for x in solar_irradiance_at_1au_w_m2_nm]
    if len(wl) != len(solar) or not wl:
        raise RoloSupportError('wavelength and solar arrays must be same nonzero length')
    if wl != sorted(wl) or len(set(wl)) != len(wl):
        raise RoloSupportError('wavelength grid must be strictly increasing')
    if wl[0] < 355.1 or wl[-1] > 865.3:
        raise RoloSupportError('research spectral reconstruction may not extrapolate beyond 355.1..865.3 nm')
    values = [actual_lunar_irradiance_w_m2_nm(w, s, geometry) for w, s in zip(wl, solar)]
    return {
        'schemaVersion': 1,
        'reconstructionId': RECONSTRUCTION_ID,
        'operationalRoloOrGiroClaim': False,
        'interpolation': 'linear-in-log-disk-reflectance-between-original-ROLO-band-effective-wavelengths',
        'solarSpectrumMustBeExplicitlyBoundByCaller': True,
        'wavelengthNm': wl,
        'lunarToaIrradianceWm2Nm': values,
        'geometry': geometry.__dict__,
        'validatedForAtmosphericScatteredMoonlight': False,
        'productionAuthorized': False,
    }
