from __future__ import annotations
import argparse, json, re
from pathlib import Path

TOKEN_RE = re.compile(rb'(?<![0-9_])[0-9_]{7,20}(?![0-9_])')


def load_candidates(path: Path) -> set[int]:
    value=json.loads(path.read_text())
    seeds=value.get('candidateSeeds') if isinstance(value,dict) else None
    if not isinstance(seeds,list) or len(seeds)!=72 or len(set(seeds))!=72 or any(isinstance(x,bool) or not isinstance(x,int) or not 0<x<2_147_483_647 for x in seeds):
        raise ValueError('candidate seed ledger must contain exactly 72 unique positive signed-32-bit seeds')
    return set(seeds)


def load_self_ledger_policy(path: Path) -> tuple[set[str], set[str]]:
    ledger=json.loads(path.read_text())
    if ledger.get('schemaVersion') == 1:
        return set(ledger.get('allowedTrackedSelfLedgerPaths',[])), set()
    if ledger.get('schemaVersion') == 2:
        required=set(ledger.get('requiredTrackedSelfLedgerPaths',[]))
        future=set(ledger.get('futureEvidenceSelfLedgerPaths',[]))
        if required & future:
            raise ValueError('required and future self-ledger paths must be disjoint')
        return required, future
    raise ValueError('unsupported seed self-ledger schema')


def scan(root: Path, file_list: Path, candidates: set[int], allow: set[str]) -> dict:
    if len(candidates)!=72:
        raise ValueError('exactly 72 candidate seeds required')
    rels=[Path(x.decode()) for x in file_list.read_bytes().split(b'\0') if x]
    hits=[]; external=[]
    for rel in rels:
        data=(root/rel).read_bytes()
        for m in TOKEN_RE.finditer(data):
            raw=m.group(0).decode().replace('_','')
            if not raw.isdigit(): continue
            n=int(raw)
            if n not in candidates: continue
            row={'path':rel.as_posix(),'seed':n,'byteOffset':m.start(),'selfLedger':rel.as_posix() in allow}
            hits.append(row)
            if not row['selfLedger']: external.append(row)
    return {'trackedFileCount':len(rels),'candidateSeedCount':len(candidates),'selfLedgerHitCount':sum(x['selfLedger'] for x in hits),'trackedTreeExternalCollisionCount':len(external),'exactHeadTrackedTreeByteScanPassed':not external,'hits':hits}


def scan_with_policy(root: Path, file_list: Path, candidates: set[int], required: set[str], future: set[str]) -> dict:
    allow=required | future
    out=scan(root,file_list,candidates,allow)
    tracked={Path(x.decode()).as_posix() for x in file_list.read_bytes().split(b'\0') if x}
    missing_required=sorted(required-tracked)
    out['missingAllowedSelfLedgerPaths']=missing_required
    out['requiredSelfLedgerPathsPresent']=not missing_required
    out['futureEvidenceSelfLedgerPathsDeclared']=sorted(future)
    out['futureEvidenceSelfLedgerPathsAbsent']=sorted(future-tracked)
    out['futureEvidenceSelfLedgerPathsPresent']=sorted(future & tracked)
    out['futureEvidenceSelfLedgerPathCountPresent']=len(future & tracked)
    out['exactHeadTrackedTreeByteScanPassed']=out['exactHeadTrackedTreeByteScanPassed'] and not missing_required
    return out


def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',type=Path,required=True); ap.add_argument('--file-list',type=Path,required=True); ap.add_argument('--candidate-seed-ledger',type=Path,required=True); ap.add_argument('--allow-self-ledger-json',type=Path,required=True); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    required,future=load_self_ledger_policy(a.allow_self_ledger_json)
    candidates=load_candidates(a.candidate_seed_ledger)
    out=scan_with_policy(a.repo_root,a.file_list,candidates,required,future)
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    return 0 if out['exactHeadTrackedTreeByteScanPassed'] else 2
if __name__=='__main__': raise SystemExit(main())
