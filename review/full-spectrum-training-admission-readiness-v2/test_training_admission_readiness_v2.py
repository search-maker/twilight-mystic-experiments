#!/usr/bin/env python3
from __future__ import annotations
import copy, hashlib, json, subprocess, tempfile
from pathlib import Path
H=Path(__file__).resolve().parent
V=H/'validate_training_admission_readiness_v2.py'
G=H/'test-fixtures/training-admission-gate-v1-minimal.json'
D=H/'test-fixtures/confirmation-decision-v1.json'
S=H/'test-fixtures/screening-analysis-v8-train-0037-minimal.json'
R=H/'full-spectrum-training-admission-readiness-v2.json'
def load(p): return json.loads(p.read_text())
def rehash(v,f):
    c=dict(v); c[f]=None; v[f]=hashlib.sha256(json.dumps(c,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def run(g,d,s,r):
    with tempfile.TemporaryDirectory() as td:
        ps=[]
        for n,v in [('g',g),('d',d),('s',s),('r',r)]:
            p=Path(td)/(n+'.json'); p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n'); ps.append(p)
        return subprocess.run(['python3',str(V),'--gate',str(ps[0]),'--decision',str(ps[1]),'--screening',str(ps[2]),'--readiness',str(ps[3])],capture_output=True,text=True)
g,d,s,r=map(load,[G,D,S,R]); assert run(g,d,s,r).returncode==0
cases=[]
m=copy.deepcopy(g); m['eligibleGeometryCount']=25; cases.append((m,d,s,r))
m=copy.deepcopy(g); m['continuationRequiredGeometryIds']=['train-0014']; cases.append((m,d,s,r))
m=copy.deepcopy(g); next(x for x in m['geometryReports'] if x['geometryId']=='train-0037')['channels']['scotopicLuminanceScotCdM2']['relativeStandardErrorOfMean']=0.08; cases.append((m,d,s,r))
m=copy.deepcopy(d); m['decisionSemantics']['confirmationValuesConvertedToTrainingEvidence']=True; rehash(m,'decisionSha256'); cases.append((g,m,s,r))
m=copy.deepcopy(s); m['screeningAnalysisV6']['geometryReports'][0]['methodReports'][0]['classification']='LOW_TWO_BLOCK_RSEM_SCREENING_CANDIDATE'; cases.append((g,d,m,r))
m=copy.deepcopy(s); m['modelSelectionAuthorized']=True; cases.append((g,d,m,r))
m=copy.deepcopy(r); m['currentUniverse']['allTrainingGeometriesHaveFinalTreatment']=True; rehash(m,'readinessSha256'); cases.append((g,d,s,m))
m=copy.deepcopy(r); next(x for x in m['geometryTreatments'] if x['geometryId']=='train-0014')['currentTrainingLabelAdmitted']=True; rehash(m,'readinessSha256'); cases.append((g,d,s,m))
m=copy.deepcopy(r); next(x for x in m['geometryTreatments'] if x['geometryId']=='train-0037')['confirmedConfiguration']={'importanceCenterNm':600}; rehash(m,'readinessSha256'); cases.append((g,d,s,m))
m=copy.deepcopy(r); next(x for x in m['geometryTreatments'] if x['geometryId']=='train-0009')['confirmedAlternateConfiguration']['replacesExistingTrainingEvidence']=True; rehash(m,'readinessSha256'); cases.append((g,d,s,m))
m=copy.deepcopy(r); m['hardBoundary']['modelFittingAuthorized']=True; rehash(m,'readinessSha256'); cases.append((g,d,s,m))
m=copy.deepcopy(r); m['geometryTreatments']=m['geometryTreatments'][:-1]; rehash(m,'readinessSha256'); cases.append((g,d,s,m))
m=copy.deepcopy(r); m['readinessSha256']='0'*64; cases.append((g,d,s,m))
for i,args in enumerate(cases,1): assert run(*args).returncode==2, i
print('13 mutation refusals + 1 exact pass: PASS')
