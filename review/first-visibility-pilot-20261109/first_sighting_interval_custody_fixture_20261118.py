#!/usr/bin/env python3
"""FVS V0 human first-star detection: result-blind interval-custody fixture.

RESEARCH PREPARATION ONLY. No enrolled volunteers, original observations,
authenticated atmosphere or certified model accuracy are bundled here.
This code refuses field outcomes without a pre-event source/consent/model lock.
Only first-human-seen checks count; instrument irradiance/SQM is NOT sighting.
"""
import datetime as dt
import hashlib
import json
import re
import sys
import unittest

SHA = re.compile(r"^[0-9a-f]{64}$")
GIT = re.compile(r"^[0-9a-f]{40}$")
VALID = {"NOT_SEEN","POSSIBLE","CONFIRMED","CONTINUOUS","OBSCURED","NOT_CHECKED","SESSION_END"}

def time(s):
    if not isinstance(s, str) or not s.endswith("Z"):
        raise ValueError("UTC required")
    return dt.datetime.fromisoformat(s[:-1]+"+00:00")

def evaluate(b, raw_log_bytes):
    """Record original brackets; NEVER authorizes model production/accuracy claims."""
    reasons=[]
    out={"status":"REFUSED","bracket":None,"interval_distance_seconds":None,
         "human_first_sightings_scientifically_validated":0,
         "physical_model_validated":False,"production_authorized":False,
         "reasons":reasons}
    e=b.get("enrollment",{})
    s=b.get("session",{})
    lock=b.get("prediction_lock",{})
    checks=b.get("checks",[])
    if b.get("protected_holdout") or b.get("previously_calibrated"):
        reasons.append("PROTECTED_OR_REUSED_SAMPLE")
    if b.get("source_class")!="PROSPECTIVE_UNAIDED_HUMAN":
        reasons.append("NOT_PROSPECTIVE_HUMAN_FIRST_SIGHTING")
    if e.get("consent_research") is not True or e.get("site_registered_private") is not True:
        reasons.append("NO_V0_CONSENT_OR_VERIFIED_SITE")
    if e.get("prediction_access") is not False or s.get("prediction_blind") is not True:
        reasons.append("PREDICTION_LEAK_OR_BLINDING_UNKNOWN")
    if len(checks)==0 or len(checks)>360:
        reasons.append("MISSING_OR_UNBOUNDED_HUMAN_CHECKS")
        return out
    if not GIT.fullmatch(str(lock.get("model_commit_sha",""))) or any(
        not SHA.fullmatch(str(lock.get(key,""))) for key in
        ["model_runtime_sha256","model_config_sha256","catalog_sha256",
         "site_private_manifest_sha256","selected_target_plan_sha256",
         "prediction_ciphertext_sha256","validation_metrics_sha256"]
    ) or lock.get("predictions_unavailable_to_observers") is not True:
        reasons.append("NO_EXACT_SEALED_PREDICTOR_AND_INPUTS")
    if s.get("target_plan_sha256") != lock.get("selected_target_plan_sha256"):
        reasons.append("TARGET_PLAN_DRIFT")
    if not isinstance(raw_log_bytes,bytes) or len(raw_log_bytes)>4_000_000 or not SHA.fullmatch(
        str(b.get("original_raw_log_sha256",""))
    ) or hashlib.sha256(raw_log_bytes).hexdigest()!=b.get("original_raw_log_sha256"):
        reasons.append("RAW_LOG_BYTES_HASH_NOT_VERIFIED")
    if b.get("private_owner_custody_verified") is not True:
        reasons.append("CONSENT_AND_SITE_PROVENANCE_NOT_VERIFIED")
    try:
        first=min(time(x["timestamp_utc"]) for x in checks)
        if not (time(e["consent_at_utc"]) < first and time(lock["lock_utc"]) < first):
            reasons.append("PREDICTION_OR_CONSENT_LOCK_AFTER_OBSERVATION")
        if time(s["session_start_utc"])>first:
            reasons.append("SESSION_STARTED_AFTER_CHECK")
        if not s.get("eye_adaptation_start_utc") or time(s["eye_adaptation_start_utc"])>first:
            reasons.append("UNRECORDED_VISUAL_ADAPTATION")
    except (KeyError,ValueError,TypeError):
        reasons.append("BAD_TIMESTAMPS")
    if s.get("participant_token")!=e.get("participant_token") or s.get("site_token")!=e.get("site_token"):
        reasons.append("SITE_OR_OBSERVER_IDENTITY_DRIFT")
    if s.get("time_zone_iana") is None or not isinstance(s.get("time_zone_iana"),str):
        reasons.append("NO_IANA_TIME_ZONE")
    if any(
        x.get("session_token")!=s.get("session_token") or x.get("target_catalog")!="HIP" or
        x.get("target_id")!=b.get("target_id") or x.get("detection") not in VALID or
        x.get("mode") not in ("naked_eye_direct","naked_eye_averted","unknown") or
        not isinstance(x.get("clock_error_bound_s"),(int,float)) or
        not 0<=x["clock_error_bound_s"]<=5
        for x in checks
    ):
        reasons.append("WRONG_TARGET_OPTICS_OR_CLOCK")
    if reasons:
        return out
    checks=sorted(checks,key=lambda x:time(x["timestamp_utc"]))
    last_no=first_yes=second_yes=None
    interruption=False
    for x in checks:
        k=x["detection"]
        if first_yes is not None:
            if k in ("NOT_SEEN","OBSCURED","NOT_CHECKED"):
                interruption=True
            elif not interruption and k in ("CONFIRMED","CONTINUOUS") and \
                 0<=(time(x["timestamp_utc"])-time(first_yes["timestamp_utc"])).total_seconds()<=120:
                second_yes=x
                break
            continue
        if k=="NOT_SEEN":
            last_no=x
            interruption=False
        elif k in ("OBSCURED","NOT_CHECKED"):
            interruption=True
        elif k=="CONFIRMED":
            first_yes=x
    if last_no is None or first_yes is None:
        reasons.append("CENSORED_NO_LAST_NO_OR_FIRST_YES")
        return out
    if any(x["detection"] in ("OBSCURED","NOT_CHECKED") and
           last_no["timestamp_utc"]<x["timestamp_utc"]<first_yes["timestamp_utc"]
           for x in checks):
        reasons.append("OBSTRUCTED_OR_MISSED_CHECK_IN_BRACKET")
        return out
    if second_yes is None:
        reasons.append("NO_UNINTERRUPTED_REPEAT_CONFIRMATION")
        return out
    width=(time(first_yes["timestamp_utc"])-time(last_no["timestamp_utc"])).total_seconds()
    if not 0<width<=120:
        reasons.append("BRACKET_OVER_120_SECONDS")
        return out
    conditions=b.get("conditions",[])
    if not any(c.get("session_token")==s.get("session_token") and c.get("cloud_near_target_oktas")==0 and
        c.get("cloud_type")=="clear" and c.get("nearby_light_changes")=="no" and
        abs((time(c["timestamp_utc"])-time(first_yes["timestamp_utc"])).total_seconds())<=300
        for c in conditions):
        reasons.append("MISSING_DIRECTIONAL_CLOUD_AND_LIGHT_METADATA")
        return out
    if any(c.get("session_token")==s.get("session_token") and
        last_no["timestamp_utc"]<=c.get("timestamp_utc","")<=first_yes["timestamp_utc"] and
        (c.get("cloud_near_target_oktas")!=0 or c.get("nearby_light_changes")!="no")
        for c in conditions):
        reasons.append("CHANGED_LIGHT_OR_CLOUD_IN_BRACKET")
        return out
    out["bracket"]={"last_no_utc":last_no["timestamp_utc"],
         "first_yes_utc":first_yes["timestamp_utc"],
         "second_yes_utc":second_yes["timestamp_utc"],
         "width_seconds":width}
    dep=b.get("sun_depression_at_first_yes_deg")
    alt=b.get("target_altitude_at_first_yes_deg")
    az=b.get("target_azimuth_at_first_yes_deg")
    if any(type(x) not in (int,float) for x in (dep,alt,az)) or not(
        2<=dep<=16 and 5<=alt<=80 and 0<=az<=360
    ) or b.get("independently_recomputed_geometry") is not True:
        reasons.append("NO_INDEPENDENT_ALLOWED_SOLAR_AND_STAR_GEOMETRY")
        return out
    if dep>10.5:
        out["status"]="OBSERVATION_BRACKET_ONLY_MODEL_UNSUPPORTED"
        reasons.append("10P5_TO_16_UNSUPPORTED")
        return out
    p=b.get("sealed_prediction_interval",{})
    if p.get("status")!="SUPPORTED_FROZEN":
        out["status"]="OBSERVATION_BRACKET_ONLY_NO_MODEL_PREDICTION"
        return out
    try:
        plo,phi=time(p["lo_utc"]),time(p["hi_utc"])
        if plo>phi: raise ValueError("prediction inverted")
        no,yes=time(last_no["timestamp_utc"]),time(first_yes["timestamp_utc"])
        out["interval_distance_seconds"]=max(
            (no-phi).total_seconds(),(plo-yes).total_seconds(),0)
        out["status"]="SYNTACTIC_INTERVAL_DIAGNOSTIC_ONLY"
    except (KeyError,ValueError,TypeError):
        reasons.append("INVALID_FROZEN_PREDICTION_INTERVAL")
    return out

def fake():
    z="a"*64
    rows=[{"session_token":"test_session","target_catalog":"HIP","target_id":91262,
           "timestamp_utc":t,"detection":d,"mode":"naked_eye_averted","clock_error_bound_s":2}
        for t,d in [("2026-11-18T20:01:00Z","NOT_SEEN"),
                    ("2026-11-18T20:02:00Z","CONFIRMED"),
                    ("2026-11-18T20:02:20Z","CONFIRMED")]]
    return {"source_class":"PROSPECTIVE_UNAIDED_HUMAN","private_owner_custody_verified":True,
        "protected_holdout":False,"previously_calibrated":False,
        "original_raw_log_sha256":hashlib.sha256(b"FAKE LOG").hexdigest(),
        "enrollment":{"consent_research":True,"site_registered_private":True,
            "prediction_access":False,"consent_at_utc":"2026-11-18T19:00:00Z",
            "participant_token":"fake_observer","site_token":"fake_site"},
        "session":{"session_token":"test_session","session_start_utc":"2026-11-18T20:00:00Z",
            "participant_token":"fake_observer","site_token":"fake_site","prediction_blind":True,
            "target_plan_sha256":z,"time_zone_iana":"America/New_York",
            "eye_adaptation_start_utc":"2026-11-18T19:30:00Z"},
        "prediction_lock":{"lock_utc":"2026-11-18T19:55:00Z","model_commit_sha":"b"*40,
            **{k:z for k in ("model_runtime_sha256","model_config_sha256","catalog_sha256",
             "site_private_manifest_sha256","selected_target_plan_sha256","prediction_ciphertext_sha256",
             "validation_metrics_sha256")},"predictions_unavailable_to_observers":True},
        "checks":rows,"target_id":91262,"conditions":[{"session_token":"test_session",
            "timestamp_utc":"2026-11-18T20:02:00Z","cloud_near_target_oktas":0,
            "cloud_type":"clear","nearby_light_changes":"no"}],
        "sun_depression_at_first_yes_deg":6.5,"target_altitude_at_first_yes_deg":42,
        "target_azimuth_at_first_yes_deg":115,"independently_recomputed_geometry":True,
        "sealed_prediction_interval":{"status":"SUPPORTED_FROZEN",
            "lo_utc":"2026-11-18T20:01:20Z","hi_utc":"2026-11-18T20:01:50Z"}}

class OfflineTests(unittest.TestCase):
    def test_twenty_one_reasons_not_claimed(self):
        x=fake()
        r=evaluate(x,b"FAKE LOG")
        self.assertEqual(r["status"],"SYNTACTIC_INTERVAL_DIAGNOSTIC_ONLY")
        self.assertEqual(r["interval_distance_seconds"],0)
        self.assertFalse(r["physical_model_validated"])
    def test_synthetic_origin_rejected(self):
        x=fake();x["source_class"]="SYNTHETIC"
        self.assertEqual(evaluate(x,b"FAKE LOG")["status"],"REFUSED")
    def test_no_consent(self):
        x=fake();x["enrollment"]["consent_research"]=False
        self.assertIn("NO_V0_CONSENT_OR_VERIFIED_SITE",evaluate(x,b"FAKE LOG")["reasons"])
    def test_no_prediction_lock(self):
        x=fake();x["prediction_lock"]["model_commit_sha"]=None
        self.assertIn("NO_EXACT_SEALED_PREDICTOR_AND_INPUTS",evaluate(x,b"FAKE LOG")["reasons"])
    def test_late_lock(self):
        x=fake();x["prediction_lock"]["lock_utc"]="2026-11-18T20:03:00Z"
        self.assertIn("PREDICTION_OR_CONSENT_LOCK_AFTER_OBSERVATION",evaluate(x,b"FAKE LOG")["reasons"])
    def test_hash_mismatch(self):
        self.assertIn("RAW_LOG_BYTES_HASH_NOT_VERIFIED",evaluate(fake(),b"WRONG")["reasons"])
    def test_no_prior_no(self):
        x=fake();x["checks"].pop(0)
        self.assertIn("CENSORED_NO_LAST_NO_OR_FIRST_YES",evaluate(x,b"FAKE LOG")["reasons"])
    def test_cloud(self):
        x=fake();x["conditions"][0]["cloud_near_target_oktas"]=4
        self.assertIn("MISSING_DIRECTIONAL_CLOUD_AND_LIGHT_METADATA",evaluate(x,b"FAKE LOG")["reasons"])
    def test_no_repeat(self):
        x=fake();x["checks"].pop()
        self.assertIn("NO_UNINTERRUPTED_REPEAT_CONFIRMATION",evaluate(x,b"FAKE LOG")["reasons"])
    def test_optical_aid(self):
        x=fake();x["checks"][1]["mode"]="optical_aid_contaminated"
        self.assertIn("WRONG_TARGET_OPTICS_OR_CLOCK",evaluate(x,b"FAKE LOG")["reasons"])
    def test_unsupported_late_twilight(self):
        x=fake();x["sun_depression_at_first_yes_deg"]=12
        r=evaluate(x,b"FAKE LOG")
        self.assertEqual(r["status"],"OBSERVATION_BRACKET_ONLY_MODEL_UNSUPPORTED")
        self.assertIsNone(r["interval_distance_seconds"])
    def test_nonoverlap_distance(self):
        x=fake();x["sealed_prediction_interval"]["lo_utc"]="2026-11-18T20:02:30Z"
        x["sealed_prediction_interval"]["hi_utc"]="2026-11-18T20:02:50Z"
        self.assertEqual(evaluate(x,b"FAKE LOG")["interval_distance_seconds"],30)
    def test_protected(self):
        x=fake();x["protected_holdout"]=True
        self.assertIn("PROTECTED_OR_REUSED_SAMPLE",evaluate(x,b"FAKE LOG")["reasons"])

if __name__=="__main__":
    if len(sys.argv)==2 and sys.argv[1]=="--self-test":
        unittest.main(argv=[sys.argv[0]],verbosity=2)
    elif len(sys.argv)==4 and sys.argv[1]=="--private-json" and sys.argv[3].startswith("--raw="):
        with open(sys.argv[3][6:],"rb") as f: raw=f.read(4_000_001)
        with open(sys.argv[2],encoding="utf-8") as f: data=json.load(f)
        print(json.dumps(evaluate(data,raw),indent=2))
    else:
        sys.exit("Usage: python fixture.py --self-test | --private-json bundle.json --raw=private_original.log")
