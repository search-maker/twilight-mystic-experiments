from __future__ import annotations
import argparse, json, re
from pathlib import Path

TOKEN_RE=re.compile(rb'(?<![0-9_])[0-9_]{7,20}(?![0-9_])')

def candidates(path: Path)->set[int]:
    x=json.loads(path.read_text()); s=x.get("candidateSeeds") if isinstance(x,dict) else None
    if not isinstance(s,list) or len(s)!=24 or len(set(s))!=24 or any(isinstance(v,bool) or not isinstance(v,int) or not 0<v<2_147_483_647 for v in s):
        raise ValueError("candidate seed ledger must contain exactly 24 unique positive signed-32-bit seeds")
    return set(s)

def policy(path: Path)->set[str]:
    x=json.loads(path.read_text())
    if x.get("schemaVersion")!=1: raise ValueError("seed self-ledger policy schema drift")
    paths=set(x.get("allowedTrackedSelfLedgerPaths",[]))
    if not paths: raise ValueError("self-ledger paths required")
    return paths

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--repo-root",type=Path,required=True); ap.add_argument("--file-list",type=Path,required=True)
    ap.add_argument("--candidate-seed-ledger",type=Path,required=True); ap.add_argument("--allow-self-ledger-json",type=Path,required=True); ap.add_argument("--output",type=Path,required=True); a=ap.parse_args()
    c=candidates(a.candidate_seed_ledger); allow=policy(a.allow_self_ledger_json)
    rels=[Path(x.decode()) for x in a.file_list.read_bytes().split(b"\0") if x]; tracked={p.as_posix() for p in rels}; missing=sorted(allow-tracked)
    hits=[]; external=[]
    for rel in rels:
        data=(a.repo_root/rel).read_bytes()
        for m in TOKEN_RE.finditer(data):
            raw=m.group(0).decode().replace("_","")
            if not raw.isdigit() or int(raw) not in c: continue
            row={"path":rel.as_posix(),"seed":int(raw),"byteOffset":m.start(),"selfLedger":rel.as_posix() in allow}; hits.append(row)
            if not row["selfLedger"]: external.append(row)
    out={"schemaVersion":1,"stageId":"asiv-v1-tracked-tree-seed-scan","candidateSeedCount":24,"trackedFileCount":len(rels),"selfLedgerHitCount":sum(bool(x["selfLedger"]) for x in hits),"trackedTreeExternalCollisionCount":len(external),"requiredSelfLedgerPathsPresent":not missing,"missingAllowedSelfLedgerPaths":missing,"exactHeadTrackedTreeByteScanPassed":not external and not missing,"hits":hits}
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n"); return 0 if out["exactHeadTrackedTreeByteScanPassed"] else 2
if __name__=="__main__": raise SystemExit(main())
