#!/usr/bin/env python3
"""Only SYNTHETIC structural/join tests, NEVER a real star-sighting observation."""
import json, pathlib
from jsonschema import Draft202012Validator

HERE = pathlib.Path(__file__).parent
schema = json.loads((HERE / "matched_directional_condition_sidecar_20261120.schema.json").read_text())
Draft202012Validator.check_schema(schema)
validator = Draft202012Validator(schema)
H = "a" * 64
T = "2026-11-20T20:00:00Z"
synthetic = {key: None for key in schema["required"]}
synthetic.update(
    record_type="MATCHED_DIRECTIONAL_CONDITION",
    sidecar_version="FVS-V0-MATCHED-CONDITION-20261120-PROPOSAL",
    protocol_id="FVS-PILOT-20261109-V0",
    check_token="check_001", session_token="session_001",
    participant_token="observer_001", site_token="site_001",
    target_catalog="HIP", target_id=12345, timestamp_utc=T,
    original_check_source_sha256=H, original_conditions_source_sha256=H,
    target_alt_deg=30.0, target_az_deg=180.0, geometry_source_sha256=H,
    cloud_at_target_oktas=0, cloud_evidence="direct_visual_target",
    target_obstruction="CLEAR", local_light_change="NO",
    adaptation_reset_since_previous_check="NO", last_bright_light_utc=None,
    interobserver_cue="NONE", cue_logged_source_sha256=None,
    aerosol_status="UNKNOWN", sky_instrument_type="NONE",
    source_provenance_status="ORIGINAL_HASHED"
)
# The following is an invented SYNTHETIC validator witness, not a field log.
counter = 0
def check(label, row, should_pass):
    global counter
    actual = validator.is_valid(row)
    assert actual == should_pass, (label, actual, list(validator.iter_errors(row)))
    counter += 1
    print("PASS:", label)
def matched(source, raw_check):
    cols = ("session_token", "check_token", "target_catalog", "target_id", "timestamp_utc")
    return tuple(source[k] for k in cols) == tuple(raw_check[k] for k in cols)
check("empty-dataset schema accepts isolated synthetic witnessed row", synthetic, True)
check("UNKNOWN aerosol cannot acquire an assumed AOD", dict(synthetic, aod550_value=0.15), False)
check("must retain original CHECK source SHA", dict(synthetic, original_check_source_sha256=None), False)
check("cannot erase target star identity", dict(synthetic, target_id=None), False)
check("ZENITH_ONLY instrument cannot point at 45 degrees", dict(synthetic, sky_instrument_type="ZENITH_ONLY", sky_point_alt_deg=45, sky_point_az_deg=180, sky_measurement_utc=T, sky_radiance_value=9.0, sky_radiance_units="mag/arcsec2", sky_instrument_source_sha256=H, sky_calibration_sha256=H, sky_fov_deg=20), False)
check("DIRECTIONAL sensor must retain calibration source", dict(synthetic, sky_instrument_type="DIRECTIONAL_SQM", sky_point_alt_deg=30, sky_point_az_deg=180, sky_measurement_utc=T, sky_radiance_value=9.0, sky_radiance_units="mag/arcsec2", sky_instrument_source_sha256=None, sky_calibration_sha256=None, sky_fov_deg=20), False)
field = {k:synthetic[k] for k in ("session_token","check_token","target_catalog","target_id","timestamp_utc")}
assert matched(synthetic,field); counter+=1; print("PASS: matched star/check/UTC")
assert not matched(synthetic,dict(field,target_id=54321)); counter+=1; print("PASS: reject mismatched star")
assert not matched(synthetic,dict(field,timestamp_utc="2026-11-20T20:00:01Z")); counter+=1; print("PASS: reject mismatched timestamp")
print("TOTAL",counter,"SYNTHETIC-only tests passed. Human first-sighting validation is NOT COMPUTABLE.")
