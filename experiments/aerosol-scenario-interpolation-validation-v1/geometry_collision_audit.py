from __future__ import annotations
import argparse, ast, hashlib, importlib.util, json, math, os, re
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
PROTOCOL=ROOT/"review/aerosol-scenario-interpolation-validation-v1/protocol.review.json"
EXPECTED_PROTOCOL_BLOB="27923f9d40d35b001c15b20b7909e3fcd12fd833"
BASE=ROOT/"experiments/aerosol-family-challenge-v2/repository_global_seed_scan.py"
EXPECTED_BASE_BLOB="4c6d704fa24228284780bcb1dd7c52537b4c5b0d"
FIELDS=("sunDepressionDeg","targetAltitudeDeg","relativeAzimuthDeg","observerElevationM","aod550")
ALLOWED_SELF={"review/aerosol-scenario-interpolation-validation-v1/protocol.review.json"}
NUMBER_RE=re.compile(r"[-+]?(?:\d+\.\d+|\d+)(?:[eE][-+]?\d+)?")

def blob(path:Path)->str:
    b=path.read_bytes(); return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

if blob(PROTOCOL)!=EXPECTED_PROTOCOL_BLOB: raise RuntimeError("ASIV protocol byte drift")
if blob(BASE)!=EXPECTED_BASE_BLOB: raise RuntimeError("bound metadata enumerator byte drift")
spec=importlib.util.spec_from_file_location("asiv_geometry_metadata_base",BASE); base=importlib.util.module_from_spec(spec); spec.loader.exec_module(base)

def holdouts()->list[dict[str,Any]]:
    p=json.loads(PROTOCOL.read_text()); rows=p["freshHoldoutGeometrySelection"]["selectedGeometries"]
    if len(rows)!=8: raise RuntimeError("exact eight holdouts required")
    return [{"holdoutId":str(r["holdoutId"]),"geometry":{k:float(r["geometry"][k]) for k in FIELDS}} for r in rows]

def same(a:float,b:float)->bool: return math.isclose(float(a),float(b),rel_tol=0.0,abs_tol=1e-9)

def match_dict(d:dict[str,Any],targets:list[dict[str,Any]])->list[str]:
    g=d.get("geometry") if isinstance(d.get("geometry"),dict) else d
    if not all(k in g for k in FIELDS): return []
    try: vals={k:float(g[k]) for k in FIELDS}
    except (TypeError,ValueError): return []
    return [t["holdoutId"] for t in targets if all(same(vals[k],t["geometry"][k]) for k in FIELDS)]

def json_dicts(v:Any):
    if isinstance(v,dict):
        yield v
        for x in v.values(): yield from json_dicts(x)
    elif isinstance(v,list):
        for x in v: yield from json_dicts(x)

def py_dicts(path:Path):
    try: tree=ast.parse(path.read_text(encoding="utf-8"))
    except Exception: return
    for node in ast.walk(tree):
        if not isinstance(node,ast.Dict): continue
        try: value=ast.literal_eval(node)
        except Exception: continue
        if isinstance(value,dict): yield value

def tracked_scan(repo:Path,file_list:Path,targets:list[dict[str,Any]])->dict[str,Any]:
    rels=[Path(x.decode()) for x in file_list.read_bytes().split(b"\0") if x]; collisions=[]; selfrefs=[]
    for rel in rels:
        path=repo/rel; found=set()
        try:
            if rel.suffix.lower()==".json":
                for d in json_dicts(json.loads(path.read_text(encoding="utf-8"))): found.update(match_dict(d,targets))
            elif rel.suffix.lower()==".py":
                for d in py_dicts(path): found.update(match_dict(d,targets))
        except Exception: continue
        for hid in sorted(found):
            row={"surface":"tracked-tree-semantic-geometry-object","path":rel.as_posix(),"holdoutId":hid}
            (selfrefs if rel.as_posix() in ALLOWED_SELF else collisions).append(row)
    return {"trackedFileCount":len(rels),"allowedSelfReferenceCount":len(selfrefs),"allowedSelfReferences":selfrefs,"trackedGeometryCollisionCount":len(collisions),"trackedGeometryCollisions":collisions}

def row_numeric_match(row:Any,t:dict[str,Any])->bool:
    text=json.dumps(row,sort_keys=True,ensure_ascii=False,allow_nan=False); nums=[]
    for token in NUMBER_RE.findall(text):
        try: nums.append(float(token))
        except ValueError: pass
    return all(any(same(v,x) for x in nums) for v in t["geometry"].values())

def metadata_scan(context:dict[str,Any],targets:list[dict[str,Any]],current_run_id:int|None)->dict[str,Any]:
    filtered=base._without_current_audit_self_metadata(context,current_run_id); collisions=[]
    for key in ("branches","runs","artifacts","pulls","issues","issueComments","pullReviewComments","commitComments","issue60Comments"):
        for row in filtered[key]:
            for t in targets:
                if row_numeric_match(row,t): collisions.append({"surface":key,"id":str(row.get("id") or row.get("number") or row.get("name") or row.get("url") or ""),"holdoutId":t["holdoutId"]})
    return {"metadataGeometryCollisionCount":len(collisions),"metadataGeometryCollisions":collisions}

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--repo-root",type=Path,required=True); ap.add_argument("--file-list",type=Path,required=True); ap.add_argument("--repository",required=True); ap.add_argument("--current-run-id",type=int); ap.add_argument("--expected-branch-name",required=True); ap.add_argument("--expected-repo-head",required=True); ap.add_argument("--output",type=Path,required=True); a=ap.parse_args()
    token=os.environ.get("GITHUB_TOKEN")
    if not token: raise SystemExit("GITHUB_TOKEN required")
    targets=holdouts(); local=tracked_scan(a.repo_root,a.file_list,targets)
    first_raw=base.collect(a.repository,60,token); fence=base.build_snapshot_fence(first_raw,a.current_run_id); first=base.apply_snapshot_fence(first_raw,fence,a.current_run_id)
    second_raw=base.collect(a.repository,60,token); second=base.apply_snapshot_fence(second_raw,fence,a.current_run_id); stable=base.require_two_pass_stability(first,second,a.current_run_id)
    meta=metadata_scan(second,targets,a.current_run_id); final=base.final_expected_branch_head(a.repository,a.expected_branch_name,token)
    if final!=a.expected_repo_head: raise RuntimeError("audited branch moved during geometry audit")
    passed=local["trackedGeometryCollisionCount"]==0 and meta["metadataGeometryCollisionCount"]==0
    out={"schemaVersion":1,"stageId":"asiv-v1-repository-wide-geometry-collision-audit","status":"PASS_FRESH_HOLDOUT_GEOMETRY_NO_PRIOR_NONSELF_COLLISION" if passed else "FAIL_HOLDOUT_GEOMETRY_COLLISION_PROTOCOL_MUST_RETIRE","auditedMainHead":a.expected_repo_head,"holdoutGeometryCount":8,"holdoutIds":[t["holdoutId"] for t in targets],"repositoryMetadataDoubleEnumerationStable":True,"repositoryMetadataStableContextSha256":stable,**local,**meta,"protocolSelfDefinitionExcludedFromCollision":True,"rawHistoricalArtifactBytesRequired":False,"artifactGeometryCoverageRationale":"prior scientific geometry identities are repository-bound by reviewed manifests/contracts; tracked-tree semantic geometry objects are audited, while repository metadata is independently scanned for exact five-coordinate signatures","individualPointReplacementAllowed":False,"ordinal39Allocated":False,"solverExecutionPerformed":False}
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n"); return 0 if passed else 2
if __name__=="__main__": raise SystemExit(main())
