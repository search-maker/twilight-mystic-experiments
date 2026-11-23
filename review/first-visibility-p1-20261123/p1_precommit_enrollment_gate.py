#!/usr/bin/env python3
"""P1 pre-outcome enrollment/blinding STRUCTURAL receipt gate. No real consent authenticated."""
import argparse, copy, datetime as dt, json, re
from collections import Counter
from pathlib import Path
H64=re.compile(r"^[0-9a-f]{64}$"); H40=re.compile(r"^[0-9a-f]{40}$")
ID=re.compile(r"^[A-Za-z0-9_-]{4,64}$"); CAT=re.compile(r"^(HIP|HD|HR)-[1-9][0-9]*$")
LIMITS={"max_sites":2,"max_observers_per_site":2,"max_targets_per_site":3,
 "max_site_evenings":12,"max_calendar_days":30,"max_spend_usd":0,
 "min_confirmed_brackets_feasibility":8,
 "min_independent_site_evenings_feasibility":4,
 "max_bracket_seconds":60,"max_clock_error_seconds":5,
 "min_adaptation_seconds":600,"pilot_scientific_accuracy_accepted":False}
ROOT={"study_id","protocol_revision","protocol_sha256","schema_git_blob_sha",
 "validator_git_blob_sha","preregistered_utc","enrollment_open_utc","first_outcome_utc",
 "model_git_sha","model_science_acceptance_uri","model_science_approved",
 "catalog_sha256","ephemeris_sha256","input_sources_sha256","analysis_plan_sha256",
 "candidate_cases_sha256","site_selection_sha256","target_selection_sha256",
 "sealed_prediction_ciphertext_sha256","custodian_commit_receipt_sha256",
 "custodian_receipt_uri","custodian_verified","predictions_private_and_sealed",
 "site_selection","enrollments","limits","protected_holdouts_excluded",
 "actual_outcomes_received"}
S_KEYS={"site_token","permission_receipt_sha256","site_attestation_sha256",
 "site_permission_verified","target_catalog_ids","field_card_sha256"}
O_KEYS={"observer_token","site_token","consent_receipt_sha256","consent_verified",
 "consent_utc","enrolled_utc","field_card_sha256",
 "observer_no_prediction_ack","custodian_enrollment_receipt_sha256"}
HASHES=["protocol_sha256","catalog_sha256","ephemeris_sha256","input_sources_sha256",
 "analysis_plan_sha256","candidate_cases_sha256","site_selection_sha256",
 "target_selection_sha256","sealed_prediction_ciphertext_sha256",
 "custodian_commit_receipt_sha256"]
def utc(s):
 if not isinstance(s,str) or not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ",s):
  raise ValueError("exact UTC-Z seconds required")
 return dt.datetime.strptime(s,"%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
def valid(m):
 e=[]
 if not isinstance(m,dict): return {"structural_ready":False,"errors":["NOT_OBJECT"],"observations":0}
 e+=["MISSING_"+k for k in sorted(ROOT-set(m))]
 e+=["PUBLIC_FIELD_FORBIDDEN_"+k for k in sorted(set(m)-ROOT)]
 for k in HASHES:
  if not isinstance(m.get(k),str) or not H64.fullmatch(m[k]):e.append("MISSING_OR_INVALID_HASH_"+k)
 for k in ["schema_git_blob_sha","validator_git_blob_sha","model_git_sha"]:
  if not isinstance(m.get(k),str) or not H40.fullmatch(m[k]):e.append("MISSING_OR_INVALID_SHA_"+k)
 for k in ["model_science_acceptance_uri","custodian_receipt_uri"]:
  if not isinstance(m.get(k),str) or not m[k].startswith("https://"):e.append("MISSING_URI_"+k)
 for k in ["model_science_approved","custodian_verified","predictions_private_and_sealed"]:
  if m.get(k) is not True:e.append("REQUIRES_EXTERNAL_VERIFICATION_"+k)
 if m.get("study_id")!="P1-PROSPECTIVE-NAKED-EYE-2026":e.append("WRONG_STUDY")
 if m.get("protocol_revision")!="pilot-0.1-candidate":e.append("REVISION_MISMATCH")
 if m.get("limits")!=LIMITS:e.append("FINITE_LIMITS_CHANGED")
 if m.get("protected_holdouts_excluded")!=["TAYLOR_ANN_ARBOR","JERUSALEM"]:
  e.append("PROTECTED_HOLDOUTS_NOT_EXCLUDED")
 if m.get("first_outcome_utc") is not None or m.get("actual_outcomes_received") is not False:
  e.append("NOT_A_PREOUTCOME_RECORD")
 try:
  frozen,opened=utc(m.get("preregistered_utc")),utc(m.get("enrollment_open_utc"))
  if opened<=frozen:e.append("FREEZE_NOT_BEFORE_ENROLLMENT")
 except (ValueError,TypeError):e.append("MISSING_FREEZE_OR_OPEN_UTC")
 ss=m.get("site_selection")
 oo=m.get("enrollments")
 if not isinstance(ss,list) or not (1<=len(ss)<=2):e.append("NO_1_TO_2_SITES");ss=[]
 if not isinstance(oo,list) or not (1<=len(oo)<=4):e.append("NO_1_TO_4_OBSERVERS");oo=[]
 site_ids=set(); cards={}
 for s in ss:
  if not isinstance(s,dict) or set(s)!=S_KEYS:e.append("INVALID_SITE_RECORD");continue
  k=s.get("site_token")
  if not isinstance(k,str) or not ID.fullmatch(k):e.append("INVALID_SITE_TOKEN");continue
  if k in site_ids:e.append("DUPLICATE_SITE")
  site_ids.add(k);cards[k]=s.get("field_card_sha256")
  if s.get("site_permission_verified") is not True:e.append("SITE_PERMISSION_UNVERIFIED")
  for f in ("permission_receipt_sha256","site_attestation_sha256","field_card_sha256"):
   if not isinstance(s.get(f),str) or not H64.fullmatch(s[f]):e.append("SITE_HASH_MISSING_"+f)
  ts=s.get("target_catalog_ids")
  if not isinstance(ts,list) or not(1<=len(ts)<=3) or any(not isinstance(t,str) or not CAT.fullmatch(t) for t in ts) or len(set(ts))!=len(ts):
   e.append("INVALID_FROZEN_CATALOG_TARGET_LIST")
 obs=set(); counts=Counter()
 for o in oo:
  if not isinstance(o,dict) or set(o)!=O_KEYS:e.append("INVALID_OBSERVER_RECORD");continue
  k=o.get("observer_token");s=o.get("site_token")
  if not isinstance(k,str) or not ID.fullmatch(k):e.append("INVALID_OBSERVER_TOKEN")
  if k in obs:e.append("DUPLICATE_OBSERVER")
  obs.add(k)
  if s not in site_ids:e.append("OBSERVER_UNSELECTED_SITE")
  counts[s]+=1
  if o.get("consent_verified") is not True:e.append("CONSENT_UNVERIFIED")
  if o.get("observer_no_prediction_ack") is not True:e.append("PREDICTION_BLIND_ACK_MISSING")
  for f in ("consent_receipt_sha256","field_card_sha256","custodian_enrollment_receipt_sha256"):
   if not isinstance(o.get(f),str) or not H64.fullmatch(o[f]):e.append("OBSERVER_HASH_MISSING_"+f)
  if s in cards and o.get("field_card_sha256")!=cards[s]:e.append("FIELD_CARD_NOT_FROZEN")
  try:
   if utc(o["consent_utc"])>utc(o["enrolled_utc"]):e.append("CONSENT_AFTER_ENROLLMENT")
   if utc(o["enrolled_utc"])<utc(m["enrollment_open_utc"]):e.append("ENROLLMENT_BEFORE_OPEN")
  except (ValueError,TypeError,KeyError):e.append("INVALID_ENROLLMENT_UTC")
 if any(n>2 for n in counts.values()):e.append("SITE_OBSERVER_CAP_EXCEEDED")
 return {"structural_ready":not e,"errors":sorted(set(e)),"site_tokens":len(ss),
  "observer_tokens":len(oo),"observations":0,"scientific_accuracy_certified":False,
  "external_original_receipt_verification":"REQUIRED_EVEN_IF_STRUCTURAL_READY"}
def selftest():
 h="a"*64
 m={k:None for k in ROOT}
 for k in HASHES:m[k]=h
 m.update(study_id="P1-PROSPECTIVE-NAKED-EYE-2026",protocol_revision="pilot-0.1-candidate",
  schema_git_blob_sha="4fcc5747a6d6242737bd2b44808b83f79fa62e95",
  validator_git_blob_sha="dc7823f7b7b3fd7a7d1cdbbb2d7005f8bda05de4",
  preregistered_utc="2026-11-23T16:00:00Z",enrollment_open_utc="2026-11-24T16:00:00Z",
  model_git_sha="b"*40,model_science_approved=True,custodian_verified=True,
  predictions_private_and_sealed=True,model_science_acceptance_uri="https://example.invalid/FAKE",
  custodian_receipt_uri="https://example.invalid/FAKE",actual_outcomes_received=False,
  protected_holdouts_excluded=["TAYLOR_ANN_ARBOR","JERUSALEM"],limits=LIMITS,
  site_selection=[dict(site_token="SITE_A",permission_receipt_sha256=h,site_attestation_sha256=h,
    site_permission_verified=True,target_catalog_ids=["HIP-91262"],field_card_sha256=h)],
  enrollments=[dict(observer_token="OBS_01",site_token="SITE_A",consent_receipt_sha256=h,
    consent_verified=True,consent_utc="2026-11-24T15:00:00Z",
    enrolled_utc="2026-11-24T16:10:00Z",field_card_sha256=h,
    observer_no_prediction_ack=True,custodian_enrollment_receipt_sha256=h)])
 assert valid(m)["structural_ready"]
 for k,v,expect in [
  ("model_git_sha",None,"MISSING_OR_INVALID_SHA_model_git_sha"),
  ("preregistered_utc","2026-11-25T16:00:00Z","FREEZE_NOT_BEFORE_ENROLLMENT"),
  ("custodian_verified",False,"REQUIRES_EXTERNAL_VERIFICATION_custodian_verified"),
  ("actual_outcomes_received",True,"NOT_A_PREOUTCOME_RECORD"),
  ("protected_holdouts_excluded",[],"PROTECTED_HOLDOUTS_NOT_EXCLUDED")]:
  n=copy.deepcopy(m);n[k]=v;assert expect in valid(n)["errors"]
 n=copy.deepcopy(m);n["predicted_first_visible_utc"]="LEAK";assert any(x.startswith("PUBLIC_FIELD_FORBIDDEN") for x in valid(n)["errors"])
 n=copy.deepcopy(m);n["enrollments"][0]["consent_verified"]=False
 assert "CONSENT_UNVERIFIED" in valid(n)["errors"]
 n=copy.deepcopy(m);n["enrollments"][0]["field_card_sha256"]="c"*64
 assert "FIELD_CARD_NOT_FROZEN" in valid(n)["errors"]
 print("9/9 synthetic structural controls PASS; 0 genuine consent/model/sightings certified")
if __name__=="__main__":
 p=argparse.ArgumentParser()
 p.add_argument("--selftest",action="store_true")
 p.add_argument("--manifest",type=Path)
 a=p.parse_args()
 if a.selftest:selftest()
 else:
  if a.manifest is None:p.error("--manifest needed")
  result=valid(json.loads(a.manifest.read_text(encoding="utf-8")))
  print(json.dumps(result,indent=2))
  raise SystemExit(0 if result["structural_ready"] else 2)
