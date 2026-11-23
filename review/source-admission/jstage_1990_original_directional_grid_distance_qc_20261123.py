#!/usr/bin/env python3
"""Reproducible geometry-only audit of published J-STAGE 1990 Table 5 against published photometer scan sectors.
NOT source extraction, instrument calibration, observer proof, or a predicted first-sighting comparison.
Source DOI: 10.9749/jin.83.65; p.66 directional sampling 0/45/90/135/180 az and 10/30/50/70/90 alt;
Table 5, p.69: five published object positions in degrees + arcminutes.
The reflected bearing is a CONDITIONAL symmetry assumption; not a verified author reconstruction.
"""
import math
ROWS = (
    ("Jupiter", 28 + 50.7 / 60, 240.8),
    ("Sirius", 61 + 7.9 / 60, 202.6),
    ("Canopus", 69 + 30.6 / 60, 107.8),
    ("Achernar", 47 + 55.5 / 60, 35.3),
    ("Aldebaran", 36 + 17.9 / 60, 271.7),
)
AZ_GRID = (0, 45, 90, 135, 180)
ALT_GRID = (10, 30, 50, 70, 90)

def angular_sep_deg(a_deg, az_deg, b_deg, bz_deg):
    a, az, b, bz = map(math.radians, (a_deg, az_deg, b_deg, bz_deg))
    dot = math.sin(a) * math.sin(b) + math.cos(a) * math.cos(b) * math.cos(az - bz)
    return math.degrees(math.acos(max(-1, min(1, dot))))

def audit():
    output = []
    for name, alt, rel_az in ROWS:
        folded_az = min(rel_az, 360 - rel_az)
        dist, grid_alt, grid_az = min(
            (angular_sep_deg(alt, folded_az, grid_alt, grid_az), grid_alt, grid_az)
            for grid_alt in ALT_GRID for grid_az in AZ_GRID
        )
        output.append((name, rel_az > 180, folded_az, grid_az, grid_alt, dist))
    assert len(output) == 5
    assert sum(item[1] for item in output) == 3
    assert all(item[-1] > 6 for item in output)
    print("object,outside_0_180,conditional_reflected_az,nearest_sample_az,nearest_sample_alt,angular_distance_deg")
    for name, outside, reflected, az, alt, dist in output:
        print(f"{name},{outside},{reflected:.3f},{az},{alt},{dist:.3f}")

if __name__ == "__main__":
    audit()
