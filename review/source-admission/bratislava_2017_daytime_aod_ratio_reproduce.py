#!/usr/bin/env python3
"""Non-model reproduction of Kocifaj et al. (2023) published Table 1 radiance ratio.

DOI: 10.1093/mnras/stad1570
Data: 2017-10-16/17 Bratislava, 450 nm, daytime; four directions.
No protected samples, MYSTIC, forecasts or first-star observations.
Requires only Python 3 standard library.
"""
import math

# Author's Table 1; relative radiances (NOT calibrated W/m2/sr/nm).
RAYS = [
    (70.0, 234.0, 292.0),
    (60.0, 234.0, 184.0),
    (70.0, 276.0, 125.0),
    (30.0, 234.0, 83.7),
]
ROD_450_PAPER = 0.23

def ratio_eq3(tau, z, z_sun):
    c, cs = math.cos(math.radians(z)), math.cos(math.radians(z_sun))
    return (cs * cs / ((c - cs) * tau)) * math.expm1(
        -tau * (1.0 / c - 1.0 / cs)
    )

def bisect(target, z, z_sun):
    lo, hi = 0.000001, 2.0
    assert ratio_eq3(lo, z, z_sun) < target < ratio_eq3(hi, z, z_sun)
    for _ in range(80):
        mid = (lo + hi) / 2.0
        if ratio_eq3(mid, z, z_sun) < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0

def angular_distance(z1, az1, z2, az2):
    a, b, da = map(math.radians, (z1, z2, az1 - az2))
    c = math.cos(a) * math.cos(b) + math.sin(a) * math.sin(b) * math.cos(da)
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))

if __name__ == "__main__":
    observed_ratio = RAYS[3][2] / RAYS[2][2]  # 83.7/125
    assert observed_ratio == 0.6696
    print("published nonabsolute radiance ratio:", format(observed_ratio, ".6f"))
    for z_sun in [70.0, 73.0]:
        tau = bisect(observed_ratio, 30.0, z_sun)
        sep1 = angular_distance(70.0, 276.0, z_sun, 234.0)
        sep2 = angular_distance(30.0, 234.0, z_sun, 234.0)
        print(
            f"assumed solar zenith {z_sun:.1f} deg: "
            f"tau algebraic={tau:.6f}; AOD450 algebraic={tau-ROD_450_PAPER:.6f}; "
            f"two angular separations={sep1:.4f}/{sep2:.4f} deg"
        )
    print("Author's rounded 84/125=0.672; published tau~0.55 and AOD450~0.32")
    print("AOD550=UNSUPPORTED; requires verified Angstrom spectral slope")
    print("FIRST_STAR_VISIBILITY_ERROR=UNSUPPORTED; no human first-star observations")
