#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re, subprocess
from pathlib import Path
import importlib.util

HERE=Path(__file__).resolve().parent
SPEC=importlib.util.spec_from_file_location('validator',HERE/'validate_tier2_stage1_authorization_implementation_v1.py')
V=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(V)
TOKEN_RE=re.compile(rb'(?<![0-9_])[0-9_]{7,20}(?![0-9_])')

def sh(*args:str,cwd:Path)->bytes:
    return subprocess.check_output(args,cwd=cwd)
def normalized_candidate(token:bytes,candidates:set[int])->int|None:
    try:
        s=token.decode('ascii').replace('_','')
        if not s.isdigit(): return None
        n=int(s)
        return n if n in candidates else None
    except Exception:
        return None

def audit(repo_root:Path,review_path:Path)->dict:
    d=json.loads(review_path.read_text(encoding='utf-8')); V.validate(d)
    a=d['seedCollisionReviewAudit']
    first,last=a['candidateLedgerFirstSeed'],a['candidateLedgerLastSeed']
    candidates=set(range(first,last+1))
    if len(candidates)!=100: raise V.Refusal('candidate range cardinality drift')
    allowed=set(a['allowedTrackedSelfLedgerPaths'])
    files=[Path(x.decode()) for x in sh('git','ls-files','-z',cwd=repo_root).split(b'\0') if x]
    hits=[]; external=[]
    for rel in files:
        data=(repo_root/rel).read_bytes()
        for m in TOKEN_RE.finditer(data):
            seed=normalized_candidate(m.group(0),candidates)
            if seed is None: continue
            row={'path':rel.as_posix(),'seed':seed,'byteOffset':m.start(),'selfLedger':rel.as_posix() in allowed}
            hits.append(row)
            if not row['selfLedger']: external.append(row)
    missing=[p for p in allowed if p not in {x.as_posix() for x in files}]
    if missing: raise V.Refusal(f'missing self-ledger tracked paths: {missing}')
    if external: raise V.Refusal(f'external candidate seed collision(s): {external[:8]}')
    head=sh('git','rev-parse','HEAD',cwd=repo_root).decode().strip()
    return {'status':'PASSED_EXACT_HEAD_TRACKED_TREE_NEGATIVE_COLLISION_CHECK','repoHead':head,'trackedFileCount':len(files),'candidateSeedCount':len(candidates),'selfLedgerHitCount':sum(x['selfLedger'] for x in hits),'externalCollisionCount':0,'hits':hits,'authorizationPermitted':False,'artifactRunHistoryRecheckStillRequired':True}

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',type=Path,default=Path.cwd());ap.add_argument('--review',type=Path,required=True);ap.add_argument('--output',type=Path);args=ap.parse_args()
    try:
        out=audit(args.repo_root.resolve(),args.review.resolve())
        text=json.dumps(out,indent=2,sort_keys=True)+'\n'
        if args.output: args.output.write_text(text,encoding='utf-8')
        print(text,end=''); return 0
    except Exception as e:
        print(json.dumps({'status':'REFUSED','reason':str(e)},indent=2,sort_keys=True)); return 2
if __name__=='__main__': raise SystemExit(main())
