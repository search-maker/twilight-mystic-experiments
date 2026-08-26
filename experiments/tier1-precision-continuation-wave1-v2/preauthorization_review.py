#!/usr/bin/env python3
"""Generate a deterministic review-only packet; never allocate or dispatch."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

MAIN = "82cec0ed538c5ef182797e1f33224f80c8443c03"
WAVE1_HEAD = "3b6fc114ba7d4a71def7e602f6e94d7913883e30"
PREREG_SHA = "bcbb2376e6d7b9a3e3cefc52cd071857a98496dc5d0a8aebce2f512ac6ddf38a"
TEMPLATE_SHA = "8db81c9b4ed13076f7510300cc3b54e7d1e952ef036846aa219a0709d7504b00"
DIMS = {"authorizationOrdinal","executionKey","authorizationRef","runTitle","branchPath","authorizationFilePath","seed","actionsRun","pullRequest","issueComment"}
CANDIDATE = {
    "authorizationOrdinal": 3,
    "executionKey": "twilight-surrogate-tier-1-v1:numerical:3",
    "runTitle": "Tier-1 precision continuation wave 1 ordinal 3",
    "futureAuthorizationBranch": "authorization/tier1-precision-continuation-wave1-ordinal3-v2",
    "futureAuthorizationFile": "experiments/tier1-precision-continuation-wave1-v2/authorization.ordinal3.json",
    "status": "UNALLOCATED_REVIEW_ONLY",
}

class Refusal(ValueError): pass

def must(ok, msg):
    if not ok: raise Refusal(msg)

def sha(raw): return hashlib.sha256(raw).hexdigest()
def load(path):
    raw = Path(path).read_bytes(); value = json.loads(raw)
    must(isinstance(value, dict), f"{path} must be a JSON object")
    return value, raw

def build(prereg_path, template_path, snapshot_path, prereg_sha=PREREG_SHA, template_sha=TEMPLATE_SHA):
    p, p_raw = load(prereg_path); t, t_raw = load(template_path); s, s_raw = load(snapshot_path)
    must(sha(p_raw) == prereg_sha, "preregistration raw SHA-256 drift")
    must(sha(t_raw) == template_sha, "template raw SHA-256 drift")
    for key in ("authorizationOrdinal","authorizationRef","executionKey"):
        must(p.get(key) is None, f"preregistration {key} must remain null")
    must(p.get("authorizationEnabled") is False and p.get("dispatchEnabled") is False and p.get("workflowDispatchEnabled") is False, "preregistration authorization/dispatch must remain disabled")
    must(p.get("scientificExecution") is False and p.get("proposalOnly") is True, "preregistration must remain proposal-only")
    must(p.get("blocks") == [3,4] and p.get("caseCount") == 40 and p.get("geometryCount") == 20, "wave-1 scope changed")
    must(p.get("maximumConfiguredPhotonHistories") == 5_100_000_000, "photon budget changed")
    must(p.get("roleCounts") == {"internalHoldoutCases":6,"internalHoldoutGeometries":3,"surrogateTrainingCases":34,"surrogateTrainingGeometries":17}, "role counts changed")
    must(all(p.get("preservation",{}).get(k) is True for k in ("evidenceBindingsUnchanged","geometryInputsUnchanged","historicalArtifactsImmutable","originalBlocksB1B2Preserved","photonScheduleUnchanged","rolesUnchanged","thresholdsUnchanged","zeroHitHandlingUnchanged")), "preservation proof changed")
    proof = p.get("seedProof",{})
    must(proof.get("allWave1SeedsUnique") is True and proof.get("historicalOverlap") == [] and proof.get("historicalSeedCount") == 196 and proof.get("wave1SeedCount") == 40, "seed proof changed")
    cases = p.get("cases")
    must(isinstance(cases,list) and len(cases) == 40, "exact 40-case universe required")
    seeds=[]; groups={}; photons=0; roles={"surrogate-training":0,"internal-holdout":0}; wave=[]
    for c in cases:
        must(c.get("proposalOnly") is True and c.get("block") in (3,4), "case boundary changed")
        must(c.get("role") in roles and isinstance(c.get("seed"),int) and isinstance(c.get("photonHistories"),int), "case fields invalid")
        seeds.append(c["seed"]); photons += c["photonHistories"]; roles[c["role"]] += 1
        groups.setdefault(c["groupId"],set()).add(c["block"])
        wave.append({"caseId":c["caseId"],"block":c["block"],"role":c["role"],"seed":c["seed"]})
    must(len(set(seeds)) == 40 and len(groups) == 20 and all(v == {3,4} for v in groups.values()), "case/seed universe changed")
    must(photons == 5_100_000_000 and roles == {"surrogate-training":34,"internal-holdout":6}, "budget/role split changed")
    must(t.get("enabled") is False and t.get("dispatch") is False and t.get("automaticDispatch") is False and t.get("workflowDispatchEnabled") is False and t.get("solverExecutionAuthorized") is False and t.get("githubRerunAllowed") is False, "template boundary opened")
    for key in ("authorizationOrdinal","authorizationRef","authorizationCommit","executionKey"):
        must(t.get(key) is None, f"template {key} must remain null")
    must(s.get("status") == "REVIEW_ONLY_SNAPSHOT" and s.get("candidateIdentity") == CANDIDATE, "snapshot identity changed")
    must(set(s.get("checkedDimensions",[])) == DIMS, "duplicate-search coverage incomplete")
    f=s.get("findings",{}); collisions=f.get("globalOrdinalCollisions")
    must(isinstance(collisions,list) and any(x.get("authorizationOrdinal") == 3 for x in collisions), "ordinal 3 collision evidence required")
    for k in ("tier1ExecutionKeyCollisions","authorizationRefCollisions","runTitleCollisions","branchPathCollisions","authorizationFilePathCollisions","wave1SeedCollisions"):
        must(f.get(k) == [], f"unexpected {k}")
    return {
      "schemaVersion":1,
      "status":"BLOCKED_GLOBAL_ORDINAL_COLLISION_REVIEW_ONLY",
      "source":{"repository":"search-maker/twilight-mystic-experiments","mainSha":MAIN,"mergedWave1HeadSha":WAVE1_HEAD,"preregistrationRawSha256":sha(p_raw),"disabledTemplateRawSha256":sha(t_raw),"duplicateSnapshotRawSha256":sha(s_raw)},
      "scope":{"geometryCount":20,"blocks":[3,4],"caseCount":40,"maximumConfiguredPhotonHistories":5_100_000_000,"roleCounts":p["roleCounts"],"preservation":p["preservation"]},
      "wave1Seeds":wave,"seedProof":proof,"candidateIdentity":CANDIDATE,
      "candidateDecision":{"allocated":False,"authorizationRefCreated":False,"dispatchEnabled":False,"reason":"literal ordinal 3 collides with historical repository records; fail closed pending explicit ordinal-scope decision","globalOrdinalCollisions":collisions},
      "authoritativeIdentity":{"authorizationOrdinal":None,"executionKey":None,"authorizationRef":None,"authorizationCommit":None,"runTitle":None,"enabled":False,"dispatch":False,"workflowDispatchEnabled":False,"solverExecutionAuthorized":False},
      "duplicateSearch":{"checkedDimensions":sorted(DIMS),"sources":s.get("sources",[]),"findings":f},
      "boundary":"no allocation, authorization ref, dispatch, solver execution, retry, training, holdout opening, Tier-2, or production action"
    }

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--preregistration",type=Path,required=True); ap.add_argument("--authorization-template",type=Path,required=True); ap.add_argument("--duplicate-snapshot",type=Path,required=True); ap.add_argument("--output",type=Path,required=True); a=ap.parse_args()
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(build(a.preregistration,a.authorization_template,a.duplicate_snapshot),sort_keys=True,separators=(",",":"))+"\n")
if __name__ == "__main__": main()
