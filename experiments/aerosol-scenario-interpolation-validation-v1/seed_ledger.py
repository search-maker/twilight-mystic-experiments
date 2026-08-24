from __future__ import annotations
import hashlib, importlib.util, json
from pathlib import Path
from typing import Any

STAGE_ID="aerosol-scenario-interpolation-validation-v1"
NAMESPACE=STAGE_ID+"|group-seed|sha256-v1"
MIN_SEED=10_000_000
MAX_EXCLUSIVE=2_147_483_647
SPAN=MAX_EXCLUSIVE-MIN_SEED
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PROTOCOL=ROOT/"review/aerosol-scenario-interpolation-validation-v1/protocol.review.json"
EXPECTED_PROTOCOL_BLOB="27923f9d40d35b001c15b20b7909e3fcd12fd833"
LEDGER=HERE/"candidate-seed-ledger.v1.json"

class Refusal(RuntimeError): pass

def git_blob(path: Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def canonical_sha(value: Any)->str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()

def group_ids()->list[str]:
    if git_blob(PROTOCOL)!=EXPECTED_PROTOCOL_BLOB: raise Refusal("ASIV protocol byte drift")
    p=json.loads(PROTOCOL.read_text())
    rows=p["freshHoldoutGeometrySelection"]["selectedGeometries"]
    if len(rows)!=8: raise Refusal("exact eight holdouts required")
    ids=[str(x["holdoutId"]) for x in rows]
    if ids!=[f"asiv-holdout-{i:02d}" for i in range(1,9)]: raise Refusal("holdout identity drift")
    return [f"{hid}|replicate={rep}" for hid in ids for rep in (1,2,3)]

def derive_rows()->list[dict[str,Any]]:
    out=[]; used=set()
    for gid in group_ids():
        counter=0
        while True:
            material=f"{NAMESPACE}|groupId={gid}|counter={counter}"
            digest=hashlib.sha256(material.encode()).hexdigest()
            seed=(int(digest[:16],16)%SPAN)+MIN_SEED
            if seed not in used: break
            counter+=1
        if not MIN_SEED<=seed<MAX_EXCLUSIVE: raise Refusal("seed escaped signed-32-bit scanner domain")
        used.add(seed)
        out.append({"groupId":gid,"collisionCounter":counter,"derivationMaterialSha256":digest,"seed":seed})
    if len(out)!=24 or len(used)!=24: raise Refusal("ASIV candidate seed cardinality drift")
    return out

def build()->dict[str,Any]:
    rows=derive_rows(); seeds=[int(x["seed"]) for x in rows]
    return {
      "schemaVersion":1,"stageId":STAGE_ID+"-candidate-seeds",
      "status":"CANDIDATE_ONLY_NOT_APPLIED_NOT_AUTHORIZED","namespace":NAMESPACE,
      "derivation":"seed=(uint64_be(SHA256(namespace|groupId|counter)[0:8]) % (MAX_EXCLUSIVE-MIN_SEED)) + MIN_SEED; increment counter only for within-ledger collision",
      "scannerCompatibility":{"minimumSeedInclusive":MIN_SEED,"maximumSeedExclusive":MAX_EXCLUSIVE,"allCandidateSeedsHaveAtLeastSevenDecimalDigits":True},
      "candidateSeedCount":24,"candidateSeeds":seeds,"candidateRows":rows,
      "candidateMinSeed":min(seeds),"candidateMaxSeed":max(seeds),
      "allCollisionCountersZero":all(x["collisionCounter"]==0 for x in rows),
      "candidateSeedCanonicalSha256":canonical_sha(seeds),"candidateRowsCanonicalSha256":canonical_sha(rows),
      "appliedToCaseSkeletons":False,"candidateSeedFreshnessProven":False,
      "scientificOrdinalAllocated":False,"authorizationPermitted":False,
      "solverExecutionAuthorized":False,"resultOpeningAuthorized":False,
    }

def validate()->dict[str,Any]:
    got=json.loads(LEDGER.read_text())
    want=build()
    if got!=want: raise Refusal("ASIV candidate ledger differs from deterministic derivation")
    return got

if __name__=="__main__":
    x=validate()
    print(json.dumps({"status":"PASS_ASIV_CANDIDATE_LEDGER_DETERMINISTIC_NOT_AUTHORIZED","candidateSeedCount":x["candidateSeedCount"],"candidateSeedCanonicalSha256":x["candidateSeedCanonicalSha256"],"allCollisionCountersZero":x["allCollisionCountersZero"]},sort_keys=True))
