#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re, subprocess
from pathlib import Path
TOKEN_RE=re.compile(rb'(?<![0-9_])[0-9_]{7,20}(?![0-9_])')
class Refusal(RuntimeError): pass
def req(c,m):
    if not c: raise Refusal(m)
def sh(*args,cwd): return subprocess.check_output(args,cwd=cwd)
def norm(raw,candidates):
    try:
        s=raw.decode('ascii').replace('_',''); return int(s) if s.isdigit() and int(s) in candidates else None
    except Exception:return None
def audit(repo_root:Path,contract:dict,authorization_path:str|None=None):
    s=contract['seedAudit']; first=s['candidateFirstSeed']; last=s['candidateLastSeed']; candidates=set(range(first,last+1)); req(len(candidates)==100,'candidate seed cardinality drift')
    allowed=set(s['allowedTrackedSelfLedgerPaths']);
    if authorization_path: allowed.add(authorization_path)
    files=[Path(x.decode()) for x in sh('git','ls-files','-z',cwd=repo_root).split(b'\0') if x]; present={p.as_posix() for p in files}; missing=sorted(allowed-present); req(not missing,f'missing self-ledger paths: {missing}')
    hits=[]; external=[]
    for rel in files:
        data=(repo_root/rel).read_bytes()
        for m in TOKEN_RE.finditer(data):
            seed=norm(m.group(0),candidates)
            if seed is None: continue
            row={'path':rel.as_posix(),'seed':seed,'byteOffset':m.start(),'selfLedger':rel.as_posix() in allowed}; hits.append(row)
            if not row['selfLedger']: external.append(row)
    req(not external,f'external candidate seed collision(s): {external[:10]}')
    head=sh('git','rev-parse','HEAD',cwd=repo_root).decode().strip()
    return {'schemaVersion':1,'status':'PASSED_EXACT_HEAD_TRACKED_TREE_100_SEED_NEGATIVE_COLLISION_CHECK','repoHead':head,'trackedFileCount':len(files),'candidateSeedCount':100,'selfLedgerHitCount':sum(1 for x in hits if x['selfLedger']),'externalCollisionCount':0,'hits':hits,'authorizationPermittedByThisAudit':False,'runHistoryArtifactGovernanceRecheckStillRequired':True}
def main():
    p=argparse.ArgumentParser(); p.add_argument('--repo-root',type=Path,default=Path.cwd()); p.add_argument('--contract',type=Path,required=True); p.add_argument('--authorization-path'); p.add_argument('--output',type=Path,required=True); a=p.parse_args()
    try:o=audit(a.repo_root.resolve(),json.loads(a.contract.read_text()),a.authorization_path); a.output.write_text(json.dumps(o,indent=2,sort_keys=True)+'\n'); print(o['status']); return 0
    except Exception as e: print(json.dumps({'status':'REFUSED','reason':str(e)},sort_keys=True)); return 2
if __name__=='__main__': raise SystemExit(main())
