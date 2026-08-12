#!/usr/bin/env python3
import copy,hashlib,json,subprocess,tempfile
from pathlib import Path
H=Path(__file__).resolve().parent; V=H/'validate_precision_exhausted_treatment_v1.py'
files={'protocol':H/'full-spectrum-precision-exhausted-treatment-protocol-v1.json','decision':H/'test-fixtures/confirmation-decision-v1.json','readiness':H/'test-fixtures/training-readiness-v2.json','gate':H/'test-fixtures/training-admission-gate-v1-treatment-minimal.json','screening':H/'test-fixtures/ordinal16-exhausted-geometry-screening-minimal.json','confirmation':H/'test-fixtures/ordinal17-exhausted-geometry-confirmation-minimal.json'}
def load(k): return json.loads(files[k].read_text())
def rehash(v): c=copy.deepcopy(v); c['protocolSha256']=None; v['protocolSha256']=hashlib.sha256(json.dumps(c,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def run(vals):
 with tempfile.TemporaryDirectory() as td:
  args=['python3',str(V)]
  for k,v in vals.items():
   p=Path(td)/(k+'.json'); p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n'); args += ['--'+k,str(p)]
  return subprocess.run(args,capture_output=True,text=True)
vals={k:load(k) for k in files}; assert run(vals).returncode==0
cases=[]
m=copy.deepcopy(vals); m['protocol']['treatmentUniverse']['precisionExhaustedGeometryIds']=m['protocol']['treatmentUniverse']['precisionExhaustedGeometryIds'][:-1]; rehash(m['protocol']); cases.append(m)
m=copy.deepcopy(vals); m['protocol']['treatmentUniverse']['treatments'][0]['admittedForFitting']=True; rehash(m['protocol']); cases.append(m)
m=copy.deepcopy(vals); m['protocol']['treatmentUniverse']['treatments'][3]['treatmentClass']='FINITE_UNDERPRECISION_CONTINUED_REFUSAL'; rehash(m['protocol']); cases.append(m)
m=copy.deepcopy(vals); m['protocol']['treatmentUniverse']['treatments'][5]['treatmentClass']='FINITE_UNDERPRECISION_CONTINUED_REFUSAL'; rehash(m['protocol']); cases.append(m)
m=copy.deepcopy(vals); m['protocol']['treatmentUniverse']['treatments'][9]['valuesUsedAsNoisyLabels']=True; rehash(m['protocol']); cases.append(m)
m=copy.deepcopy(vals); m['protocol']['globalSemantics']['epsilonSubstitutionAllowed']=True; rehash(m['protocol']); cases.append(m)
m=copy.deepcopy(vals); m['protocol']['globalSemantics']['noisyLabelLikelihoodFrozen']=True; rehash(m['protocol']); cases.append(m)
m=copy.deepcopy(vals); m['protocol']['remainingTrainingBoundary']['modelFittingAuthorized']=True; rehash(m['protocol']); cases.append(m)
m=copy.deepcopy(vals); m['protocol']['executionBoundary']['holdoutValidationOpeningAuthorized']=True; rehash(m['protocol']); cases.append(m)
m=copy.deepcopy(vals); m['gate']['precisionExhaustedGeometryIds']=m['gate']['precisionExhaustedGeometryIds'][:-1]; cases.append(m)
m=copy.deepcopy(vals); [x for x in m['gate']['geometryReports'] if x['geometryId']=='train-0039'][0]['channels']['photopicLuminanceCdM2']['zeroHitBlockCount']=0; cases.append(m)
m=copy.deepcopy(vals); [r.__setitem__('classification','NO_CLEAR_SCREENING_GAIN') for r in [x for x in m['screening']['geometryReports'] if x['geometryId']=='train-0023'][0]['methodReports']]; cases.append(m)
m=copy.deepcopy(vals); [x for x in m['confirmation']['candidateReports'] if x['geometryId']=='train-0047'][0]['statisticsByPrimaryChannel']['photopicLuminanceCdM2']['anyExactZero']=False; cases.append(m)
m=copy.deepcopy(vals); m['decision']['decisionSemantics']['confirmationValuesConvertedToTrainingEvidence']=True; c=copy.deepcopy(m['decision']); c['decisionSha256']=None; m['decision']['decisionSha256']=hashlib.sha256(json.dumps(c,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest(); cases.append(m)
m=copy.deepcopy(vals); m['protocol']['protocolSha256']='0'*64; cases.append(m)
for i,m in enumerate(cases,1): assert run(m).returncode==2,(i,run(m).stdout)
print('15 mutation refusals + 1 exact pass: PASS')
