#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from typing import Any

def canon(v:Any)->str:
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def verified_selfhash(v:dict[str,Any],field:str)->bool:
    supplied=v.get(field)
    return isinstance(supplied,str) and supplied==canon({k:x for k,x in v.items() if k!=field})

def main()->int:
    p=argparse.ArgumentParser(); p.add_argument('--manifest',type=Path,required=True); p.add_argument('--aggregate',type=Path,required=True); p.add_argument('--audit',type=Path,required=True); p.add_argument('--output',type=Path,required=True); a=p.parse_args()
    try:
        m=json.loads(a.manifest.read_text()); g=json.loads(a.aggregate.read_text()); u=json.loads(a.audit.read_text())
        if m.get('caseCount')!=76 or m.get('geometryCount')!=19 or m.get('trainingOnly') is not True: raise RuntimeError('manifest stage1 identity drift')
        if g.get('status')!='TRAINING_ACQUISITION_COMPLETE_NO_FITTING' or u.get('status')!='PASSED': raise RuntimeError('upstream stage1 evidence incomplete')
        if not verified_selfhash(g,'aggregateSha256') or not verified_selfhash(u,'auditSha256'): raise RuntimeError('upstream aggregate/audit selfhash drift')
        if g.get('holdoutValuesRead') is not False or u.get('holdoutValuesRead') is not False or g.get('protectedHoldoutRecordCount')!=0 or u.get('protectedHoldoutRecordCount')!=0: raise RuntimeError('holdout boundary violated')
        if g.get('manifestSha256')!=m.get('manifestSha256') or u.get('manifestSha256')!=m.get('manifestSha256') or u.get('aggregateSha256')!=g.get('aggregateSha256'): raise RuntimeError('evidence binding drift')
        if u.get('caseCountAudited')!=76 or u.get('trainingGeometryCount')!=19 or u.get('independentlyRecomputedFullSpectra')!=76 or u.get('independentlyRecomputedGeometryRecords')!=19 or u.get('failureCount')!=0: raise RuntimeError('independent audit completeness drift')
        rows=g.get('records') or []
        if len(rows)!=19 or any(x.get('role')!='surrogate-training' for x in rows): raise RuntimeError('training handoff role universe drift')
        if u.get('geometryRecordsCanonicalSha256')!=canon(rows): raise RuntimeError('audited geometry-record hash drift')
        if u.get('exactZeroCaseIds')!=g.get('rawExactZeroCaseIds'): raise RuntimeError('audited exact-zero case set drift')
        if g.get('modelFittingAuthorized') is not False or g.get('modelSelectionAuthorized') is not False or u.get('modelFittingAuthorized') is not False or u.get('modelSelectionAuthorized') is not False: raise RuntimeError('downstream model boundary drift')
        out={'schemaVersion':1,'stageId':'public-tier2-v1-core-stage1-training-handoff-v1','status':'TRAINING_DATASET_EVIDENCE_FROZEN_PENDING_SEPARATE_TRAINING_ONLY_SPECTRAL_ADEQUACY_GATE','manifestSha256':m['manifestSha256'],'aggregateSha256':g['aggregateSha256'],'auditSha256':u['auditSha256'],'trainingGeometryCount':19,'trainingCaseCount':76,'protectedHoldoutRecordCount':0,'holdoutValuesRead':False,'rawExactZeroCaseIds':g['rawExactZeroCaseIds'],'records':rows,'modelFittingAuthorized':False,'modelSelectionAuthorized':False,'protectedHoldoutOpeningAuthorized':False,'nextRequiredGate':'TRAINING_ONLY_SPECTRAL_ADEQUACY_GATE_AND_MODEL_REPRESENTATION_OOD_DOD_FREEZE_BEFORE_STAGE2'}
        out['handoffSha256']=canon(out); a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(out,indent=2,sort_keys=True,allow_nan=False)+'\n'); print(out['handoffSha256']); return 0
    except Exception as e:
        o={'schemaVersion':1,'stageId':'public-tier2-v1-core-stage1-training-handoff-v1','status':'REFUSED','reason':str(e),'holdoutValuesRead':False,'protectedHoldoutRecordCount':0,'modelFittingAuthorized':False,'protectedHoldoutOpeningAuthorized':False}; a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(o,indent=2,sort_keys=True)+'\n'); print(json.dumps(o)); return 2
if __name__=='__main__': raise SystemExit(main())
