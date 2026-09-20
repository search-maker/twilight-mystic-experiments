#!/usr/bin/env python3
"""Deterministic solver-free reconstruction of consumed LOWALT qa-001.

This is a narrow POST_V1 reference fixture, not a solver-equivalence claim.
It ports only the public libRadtran-2.0.6-family GEOFAST/opathfast/CHPMAN2
arithmetic needed to reproduce the already-consumed, nonprotected qa-001
surface-direct geometry.  It never invokes uvspec and contains no fitted
parameter.  The P/T and optical-depth inputs below are frozen from the
immutable qa-001 verbose artifact after its one permitted solve.

Historical source-byte provenance for the pinned runtime is still NOT PASS;
therefore agreement here is evidence about algorithm/runtime behavior, not
permission to promote a replacement solver.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

QA001_RUN_ID = 33902527328
QA001_ARTIFACT_ID = 9948189195
QA001_ARTIFACT_DIGEST = "sha256:e844a5ee8dbe72eda43df86c4df8990869db6149240b883b25ddbcd549f1d593"
QA001_PACKAGE = "rubin-libradtran-2.0.6-py312pl5321he9373c2_1"
QA001_UVSPEC_SHA256 = "2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3"
QA001_AFGLUS_SHA256 = "dab26290ed81c762ed0c607e5dc2d53393c1462a0c3a528bc5e3f5935191cfb5"

QA001_WAVELENGTH_NM = 400.0
QA001_SZA_DEG = 89.59
QA001_ALTITUDE_DEG = 0.41
QA001_SITE_ALTITUDE_KM = 0.640
QA001_EARTH_RADIUS_KM = 6370.0
QA001_EDIR = 5.735145e-7

# Frozen verbose P/T levels, descending from TOA to the forced site altitude.
# Values are intentionally the printed qa-001 values, not reconstructed hidden
# internal floats.  Each tuple is (z_km, pressure_hPa, temperature_K).
QA001_PT_DESC = (
    (120.0, 3e-05, 360.0),
    (115.0, 4e-05, 300.0),
    (110.0, 7e-05, 240.0),
    (105.0, 0.00014, 208.8),
    (100.0, 0.00032, 195.1),
    (95.0, 0.00076, 188.4),
    (90.0, 0.00184, 186.9),
    (85.0, 0.00446, 188.9),
    (80.0, 0.0105, 198.6),
    (75.0, 0.024, 208.4),
    (70.0, 0.0522, 219.6),
    (65.0, 0.109, 233.3),
    (60.0, 0.219, 247.0),
    (55.0, 0.425, 260.8),
    (50.0, 0.7978, 270.7),
    (47.5, 1.09, 270.6),
    (45.0, 1.491, 264.2),
    (42.5, 2.06, 257.3),
    (40.0, 2.871, 250.4),
    (37.5, 4.04116, 243.43),
    (35.0, 5.746, 236.5),
    (32.5, 8.25725, 229.59),
    (30.0, 11.97, 226.5),
    (27.5, 17.43, 224.0),
    (25.0, 25.49, 221.6),
    (24.0, 29.72, 220.6),
    (23.0, 34.67, 219.6),
    (22.0, 40.47, 218.6),
    (21.0, 47.29, 217.6),
    (20.0, 55.29, 216.7),
    (19.0, 64.67, 216.7),
    (18.0, 75.65, 216.7),
    (17.0, 88.5, 216.7),
    (16.0, 103.5, 216.7),
    (15.0, 121.1, 216.7),
    (14.0, 141.7, 216.7),
    (13.0, 165.8, 216.7),
    (12.0, 194.0, 216.7),
    (11.0, 227.0, 216.8),
    (10.0, 265.0, 223.3),
    (9.0, 308.0, 229.7),
    (8.0, 356.5, 236.2),
    (7.0, 411.10001, 242.7),
    (6.0, 472.20001, 249.2),
    (5.0, 540.5, 255.7),
    (4.0, 616.59998, 262.2),
    (3.0, 701.20001, 268.7),
    (2.0, 795.0, 275.2),
    (1.0, 898.79999, 281.7),
    (0.64, 938.3476, 284.04),
)

# Frozen final optical_properties() layer totals at 400 nm, descending from
# the 120->115 km layer to the 1.000->0.640 km bottom layer.  Each value is
# Rayleigh dtau + molecular-absorption dtau at the printed precision.
QA001_DTAU_DESC = (
    6.0237169100000005e-09,
    1.245062285e-08,
    2.8497904399999997e-08,
    6.71459619e-08,
    1.62346946e-07,
    3.97618994e-07,
    9.610379900000002e-07,
    2.21739434e-06,
    4.890629520000001e-06,
    1.034140674e-05,
    2.07864002e-05,
    4.01120569e-05,
    7.4919484e-05,
    0.00013691970700000002,
    0.00010719357400000001,
    0.00015052536500000002,
    0.00021856577,
    0.00032870014,
    0.0005096232,
    0.0007806487999999999,
    0.001157877,
    0.0016766691,
    0.0023802926,
    0.0033738463,
    0.0017151401,
    0.0019685850999999997,
    0.0022705067,
    0.0026241522000000003,
    0.0030367612,
    0.0035117383,
    0.0040594663999999996,
    0.0046994897,
    0.00544867943,
    0.00633037062,
    0.0073714833199999994,
    0.00860394867,
    0.01005874287,
    0.01176263423,
    0.01353586719,
    0.015316446780000001,
    0.01727212622,
    0.01941223312,
    0.02175012376,
    0.024296495549999998,
    0.02706633509,
    0.030072839139999998,
    0.033330311110000004,
    0.036853798869999996,
    0.01418319805,
)

QA001_TAU_VERTICAL = sum(QA001_DTAU_DESC)
QA001_TAUP_BOTTOM_MIDPOINT = sum(QA001_DTAU_DESC[:-1]) + 0.5 * QA001_DTAU_DESC[-1]


@dataclass(frozen=True)
class Qa001Reference:
    chp2: float
    tau_direct_predicted: float
    tau_direct_blackbox: float
    residual_tau: float
    nfac_bottom: int


def _edlen_penndorf_refind_minus_one(wavelength_nm: float, pressure_hpa: float, temperature_k: float) -> float:
    """Public source-family calculate_or_read_refind arithmetic."""
    nu = 1.0 / (wavelength_nm * 1.0e-3)
    if nu > 1.0 / 0.185:
        nu = 1.0 / 0.185
    n0 = (6432.8 + 2949810.0 / (146.0 - nu * nu) + 25540.0 / (41.0 - nu * nu)) * 1.0e-8
    return n0 * (1.0 + 0.00366 * 15.0) / (1.0 + 0.00366 * (temperature_k - 273.15)) * pressure_hpa / 1013.25


def _points_of_incidence_fast(z_cm: tuple[float, ...], z0_cm: float, sza_deg: float, earth_radius_cm: float) -> float:
    top_radius = earth_radius_cm + z_cm[-1]
    elevation_deg = 90.0 - sza_deg
    if elevation_deg == 90.0:
        return 0.0
    b = math.tan(math.radians(elevation_deg))
    p1 = 1.0 + b * b
    p2 = earth_radius_cm + z0_cm
    p3 = top_radius * top_radius * p1 - p2 * p2
    if p3 <= 0.0:
        return -1.0
    hp = (-b * p2 + math.sqrt(p3)) / p1
    return math.asin(hp / top_radius)


def _optical_path_fast(
    earth_radius_cm: float,
    ra: float,
    ca: float,
    gamma1: float,
    r1: float,
    r2: float,
    local_sza_deg: float,
) -> tuple[float, float, float, float]:
    if ca < 0.0:
        return ca, r2, local_sza_deg, -1.0
    ca -= gamma1
    if ca < 0.0 and abs(ca) > 1.0e-10:
        ca += gamma1
        sca = math.pi - ca - ra
        local_sza_deg = math.degrees(math.pi - sca)
        p1 = earth_radius_cm**2 + r1 * r1 - 2.0 * earth_radius_cm * r1 * math.cos(ca)
        r2 = r1 * math.sin(ra) / math.sin(math.pi - ra - ca)
        if r2 > earth_radius_cm - 1.0e2:
            if p1 > 0.0:
                rd = math.sqrt(p1)
                a = earth_radius_cm / rd * math.sin(ca)
                if abs(a) > 1.0:
                    ca -= gamma1
                    return ca, r2, local_sza_deg, 0.0
                ra1 = math.asin(a)
                rl = rd * math.sin(ra - ra1) / math.sin(sca)
                p2 = rl * rl + rd * rd - 2.0 * rl * rd * math.cos(ca + ra1)
                path = math.sqrt(p2) if p2 > 0.0 else 0.0
                p3 = rl * rl + earth_radius_cm**2 - 2.0 * rl * earth_radius_cm * math.cos(math.pi)
                if p3 > 0.0:
                    r2 = math.sqrt(p3)
                ca -= gamma1
                return ca, r2, local_sza_deg, path
            return -1.0, earth_radius_cm, local_sza_deg, 0.0
        return -1.0, r2, local_sza_deg, 0.0
    p1 = r1 * r1 + r2 * r2 - 2.0 * r1 * r2 * math.cos(gamma1)
    return ca, r2, local_sza_deg, math.sqrt(p1) if p1 > 0.0 else 0.0


def _natural_spline_second_derivatives(x: tuple[float, ...], y: tuple[float, ...]) -> list[float]:
    n = len(x)
    y2 = [0.0] * n
    u = [0.0] * (n - 1)
    for i in range(1, n - 1):
        sig = (x[i] - x[i - 1]) / (x[i + 1] - x[i - 1])
        p = sig * y2[i - 1] + 2.0
        y2[i] = (sig - 1.0) / p
        u[i] = (
            6.0
            * ((y[i + 1] - y[i]) / (x[i + 1] - x[i]) - (y[i] - y[i - 1]) / (x[i] - x[i - 1]))
            / (x[i + 1] - x[i - 1])
            - sig * u[i - 1]
        ) / p
    for k in range(n - 2, -1, -1):
        y2[k] = y2[k] * y2[k + 1] + u[k]
    return y2


def _spline_eval(xa: tuple[float, ...], ya: tuple[float, ...], y2a: list[float], x: float) -> float:
    klo = 0
    khi = len(xa) - 1
    while khi - klo > 1:
        k = (khi + klo) // 2
        if xa[k] > x:
            khi = k
        else:
            klo = k
    h = xa[khi] - xa[klo]
    a = (xa[khi] - x) / h
    b = (x - xa[klo]) / h
    return a * ya[klo] + b * ya[khi] + ((a**3 - a) * y2a[klo] + (b**3 - b) * y2a[khi]) * h * h / 6.0


def _opathfast_bottom_factors(
    sza_deg: float,
    z_cm: tuple[float, ...],
    refractive_index: tuple[float, ...],
    earth_radius_cm: float,
    z_lay: float = 0.5,
) -> tuple[list[float], int]:
    """Port GEOFAST's full aiming sequence; return bottom pre-tangent factors."""
    nlyr = len(z_cm) - 1
    dsdh1 = [[0.0] * nlyr for _ in range(nlyr)]
    nfac = [0] * nlyr
    deg_to_rad = math.pi / 180.0
    rad_to_deg = 180.0 / math.pi
    deltaz_top = 0.0
    tmp_top = 0.0
    nl = 0
    ind = 0
    a_fit = 0.0
    b_fit = 0.0
    xx = [0.0] * 6
    yy = [0.0] * 6
    nmax = 5

    for i in range(nlyr - 1, -1, -1):
        zi = z_cm[i] + z_lay * (z_cm[i + 1] - z_cm[i])
        if nl > 2:
            deltaz_top = -math.exp(a_fit + b_fit * zi)
        cptr = 0
        deltaz_bot = 0.0
        flag_secant = False
        while True:
            row_index = nlyr - i - 1
            nfac[row_index] = 0
            dsdh1[i] = [0.0] * nlyr
            cptr += 1
            if cptr > 15:
                break
            ca = _points_of_incidence_fast(z_cm, zi - deltaz_top, sza_deg, earth_radius_cm)
            ia = sza_deg * deg_to_rad - ca
            n2 = refractive_index[nlyr]
            r2 = 0.0
            gamma1 = 0.0
            for j in range(nlyr - 1, -2, -1):
                n1 = refractive_index[j + 1] if j < 0 else refractive_index[j]
                q = n2 / n1 * math.sin(ia)
                if abs(q) <= 1.0:
                    ra = math.asin(q)
                elif abs(q - 1.0) < 1.0e-15:
                    ra = math.pi / 2.0
                else:
                    break
                ztop = z_cm[j + 1]
                zbot = ztop - 2.0e5 if j < 0 else z_cm[j]
                r1 = earth_radius_cm + ztop
                r2 = earth_radius_cm + zbot
                g = r1 / r2 * math.sin(ra)
                if abs(g - 1.0) < 1.0e-15:
                    g = 1.0
                if g < 1.0:
                    ia = math.asin(g)
                    local_sza_deg = ia * rad_to_deg
                    gamma1 = ia - ra
                    ca, r2, local_sza_deg, path = _optical_path_fast(
                        earth_radius_cm, ra, ca, gamma1, r1, r2, local_sza_deg
                    )
                    if path == -1.0:
                        break
                    if j >= 0:
                        dsdh1[i][j] = path / (z_cm[j + 1] - z_cm[j])
                        nfac[row_index] += 1
                else:
                    scratch = 0
                    tanheight = r1 * math.sin(ra) - earth_radius_cm
                    if sza_deg > 90.0 and tanheight < 0.0:
                        raise RuntimeError("qa-001 reference unexpectedly falls below the refracted tangent")
                    if j >= 0:
                        while True:
                            tanheight = r1 * math.sin(ra) - earth_radius_cm
                            if tanheight == r2 - earth_radius_cm:
                                break
                            y2 = _natural_spline_second_derivatives(z_cm, refractive_index)
                            n1 = _spline_eval(z_cm, refractive_index, y2, tanheight)
                            q = n2 / n1 * math.sin(ia)
                            if abs(q) > 1.0 and abs(q) - 1.0 > 1.0e-14:
                                raise RuntimeError("qa-001 tangent spline leaves the Snell domain")
                            ra = math.asin(max(-1.0, min(1.0, q)))
                            scratch += 1
                            if scratch >= 6:
                                break
                    r2 = r1
                    local_sza_deg = (math.pi - ra) * rad_to_deg
                    gamma1 = math.pi - 2.0 * ra
                    ca, r2, local_sza_deg, path = _optical_path_fast(
                        earth_radius_cm, ra, ca, gamma1, r1, r2, local_sza_deg
                    )
                    if j >= 0:
                        dsdh1[i][j] = path / (z_cm[j + 1] - z_cm[j])
                        nfac[row_index] += 1
                    if ca > 1.0e-10:
                        ia = ra
                        for k in range(j + 1, nlyr + 1):
                            n2k = refractive_index[k - 1] if k == nlyr else refractive_index[k]
                            f = n1 / n2k * math.sin(ia)
                            if f <= 1.0:
                                ra2 = math.asin(f)
                                ztop2 = z_cm[k] + 3.0e5 if k == nlyr else z_cm[k + 1]
                                zbot2 = z_cm[k]
                                r1b = earth_radius_cm + zbot2
                                r2b = earth_radius_cm + ztop2
                                ia2 = math.asin(r1b / r2b * math.sin(ra2))
                                gamma2 = ra2 - ia2
                                ra_call = math.pi - ra2
                                local_top = (math.pi - ia2) * rad_to_deg
                                ca, r2b, local_top, _ = _optical_path_fast(
                                    earth_radius_cm, ra_call, ca, gamma2, r1b, r2b, local_top
                                )
                                r2 = r2b
                                ia = ia2
                                ra = ra2
                            n1 = n2k
                            if ca < 0.0:
                                break
                    break
                n2 = n1
                if ca < 1.0e-7:
                    break
            if ca > 0.5 * gamma1:
                break
            new_bot = r2 - earth_radius_cm - zi
            old_top = tmp_top
            old_bot = deltaz_bot
            deltaz_bot = new_bot
            if cptr > 1 and abs(deltaz_bot) > abs(old_bot) * 0.5:
                flag_secant = True
            if flag_secant:
                new_top = (old_top * deltaz_bot - old_bot * deltaz_top) / (deltaz_bot - old_bot)
            else:
                new_top = deltaz_top + deltaz_bot
            tmp_top = deltaz_top
            deltaz_top = new_top
            if abs(deltaz_bot) > 1.0e2:
                continue
            break
        if deltaz_top < -10.0:
            nl += 1
            n = nmax if nl > nmax else nl
            xx[ind] = zi
            yy[ind] = math.log(-deltaz_top)
            sx = sum(xx[:n])
            sx2 = sum(value * value for value in xx[:n])
            sy = sum(yy[:n])
            sxy = sum(xx[k] * yy[k] for k in range(n))
            delta = n * sx2 - sx * sx
            if delta != 0.0:
                a_fit = (sx2 * sy - sx * sxy) / delta
                b_fit = (n * sxy - sx * sy) / delta
            ind = 0 if ind == nmax - 1 else ind + 1

    bottom_factors = [dsdh1[0][nlyr - j] for j in range(1, nlyr + 1)]
    return bottom_factors, nfac[-1]


def reconstruct_qa001(*, unity_refractive_index: bool = False) -> Qa001Reference:
    nlyr = len(QA001_PT_DESC) - 1
    z_desc = tuple(row[0] for row in QA001_PT_DESC)
    if unity_refractive_index:
        vn_desc = tuple(1.0 for _ in QA001_PT_DESC)
    else:
        vn_desc = tuple(
            1.0 + _edlen_penndorf_refind_minus_one(QA001_WAVELENGTH_NM, pressure, temperature)
            for _, pressure, temperature in QA001_PT_DESC
        )
    z_cm = tuple(z_desc[nlyr - i] * 1.0e5 for i in range(nlyr + 1))
    vn = tuple(vn_desc[nlyr - i] for i in range(nlyr + 1))
    factors, nfac_bottom = _opathfast_bottom_factors(
        QA001_SZA_DEG, z_cm, vn, QA001_EARTH_RADIUS_KM * 1.0e5, 0.5
    )
    if nfac_bottom != nlyr:
        raise RuntimeError(f"qa-001 bottom target expected {nlyr} pre-tangent layers, got {nfac_bottom}")
    chp2 = sum(factor * dtau for factor, dtau in zip(factors, QA001_DTAU_DESC, strict=True))
    ch = QA001_TAUP_BOTTOM_MIDPOINT / chp2
    tau_direct_predicted = QA001_TAU_VERTICAL / ch
    tau_direct_blackbox = -math.log(QA001_EDIR / math.sin(math.radians(QA001_ALTITUDE_DEG)))
    return Qa001Reference(
        chp2=chp2,
        tau_direct_predicted=tau_direct_predicted,
        tau_direct_blackbox=tau_direct_blackbox,
        residual_tau=tau_direct_predicted - tau_direct_blackbox,
        nfac_bottom=nfac_bottom,
    )


if __name__ == "__main__":
    calc = reconstruct_qa001()
    unity = reconstruct_qa001(unity_refractive_index=True)
    print(f"calc-vn CHP2={calc.chp2:.15g} tau={calc.tau_direct_predicted:.15g} residual={calc.residual_tau:+.15g}")
    print(f"unity-vn CHP2={unity.chp2:.15g} tau={unity.tau_direct_predicted:.15g} residual={unity.residual_tau:+.15g}")
