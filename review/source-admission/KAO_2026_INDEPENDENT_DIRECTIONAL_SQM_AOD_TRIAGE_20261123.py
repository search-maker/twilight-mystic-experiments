#!/usr/bin/env python3
"""Published aggregate range arithmetic; never classify as human first visibility."""
import json
import math
Z_MIN, Z_MAX, W_MIN, W_MAX = 19.7, 20.0, 17.5, 17.8
delta = (Z_MIN - W_MAX, Z_MAX - W_MIN)
contrast = tuple(10 ** (0.4 * d) for d in delta)
assert math.isclose(delta[0], 1.9, abs_tol=1e-12)
assert math.isclose(delta[1], 2.5, abs_tol=1e-12)
assert 5.7 < contrast[0] < 5.8 and 9.99 < contrast[1] < 10.01
print(json.dumps({"doi":"10.1038/s41598-026-74791-y",
  "observed_published_approx_solar_depression_deg":[16,17],
  "published_zenith_mag_sqm_range":[Z_MIN,Z_MAX],
  "published_west_alt0_mag_sqm_range":[W_MIN,W_MAX],
  "NON_PAIRED_DELTA_MAG_ENVELOPE":[round(x,3) for x in delta],
  "NON_PAIRED_WEST_OVER_ZENITH_BRIGHTNESS_RATIO":[round(x,3) for x in contrast],
  "raw_pointwise_timeseries_acquired":False,"human_first_onset_pairs":0,
  "approved_science_model_sha":None, "prediction_error_seconds":None},indent=2))
