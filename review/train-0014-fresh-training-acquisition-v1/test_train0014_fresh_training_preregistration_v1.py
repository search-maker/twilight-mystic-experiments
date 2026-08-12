#!/usr/bin/env python3
import copy,hashlib,json,subprocess,tempfile,shutil
from pathlib import Path
H=Path(__file__).resolve().parent; V=H/'validate_train0014_fresh_training_preregistration_v1.py'
files={'preregistration':H/'train-0014-fresh-training-acquisition-preregistration-v1.json','decision':H/'test-fixtures/confirmation-decision-v1.json','readiness':H/'test-fixtures/training-readiness-v2.json','gate':H/'test-fixtures/training-admission-gate-v1-minimal.json','seed-audit':H/'test-fixtures/seed-audit-minimal.json','confirmation-manifest':H/'test-fixtures/confirmation-execution-manifest-v1.json','render-report':H/'test-fixtures/confirmation-render-report-v1.json'}
def load(k): return json.loads(files[k].read_text())
def rehash(v): c=dict(v); c['preregistrationSha256']=None; v['preregistrationSha256']=hashlib.sha256(json.dumps(c,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def run(vals,templates=None,source=None):
 with tempfile.TemporaryDirectory() as td:
  td=Path(td); args=['python3',str(V)]
  for k,v in vals.items():
   p=td/(k+'.json'); p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n'); args += ['--'+k,str(p)]
  src=td/'source.txt'; src.write_text(source if source is not None else (H/'test-fixtures/source-confirmation-template.txt').read_text()); args += ['--source-template',str(src)]
  tr=td/'templates'; shutil.copytree(templates or H/'rendered-review-v1',tr); args += ['--template-root',str(tr)]
  return subprocess.run(args,capture_output=True,text=True)
vals={k:load(k) for k in files}; assert run(vals).returncode==0
cases=[]
m=copy.deepcopy(vals); m['preregistration']['configuration']['importanceCenterNm']=500.0; rehash(m['preregistration']); cases.append(m)
m=copy.deepcopy(vals); m['preregistration']['caseDesign']['seeds'][0]=970001; m['preregistration']['caseDesign']['cases'][0]['seed']=970001; rehash(m['preregistration']); cases.append(m)
m=copy.deepcopy(vals); m['preregistration']['caseDesign']['automaticAdditionalBlocks']=True; rehash(m['preregistration']); cases.append(m)
m=copy.deepcopy(vals); m['preregistration']['trainingEvaluation']['historicalMaximumAcceptedRsem']=0.09; rehash(m['preregistration']); cases.append(m)
m=copy.deepcopy(vals); m['preregistration']['trainingEvaluation']['confirmationValuesIncludedInTrainingStatistics']=True; rehash(m['preregistration']); cases.append(m)
m=copy.deepcopy(vals); m['preregistration']['executionBoundary']['scientificExecutionAuthorized']=True; rehash(m['preregistration']); cases.append(m)
m=copy.deepcopy(vals); m['decision']['decisionSemantics']['globalEstimatorSelected']=True; c=dict(m['decision']); c['decisionSha256']=None; m['decision']['decisionSha256']=hashlib.sha256(json.dumps(c,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest(); cases.append(m)
m=copy.deepcopy(vals); m['readiness']['hardBoundary']['modelFittingAuthorized']=True; c=dict(m['readiness']); c['readinessSha256']=None; m['readiness']['readinessSha256']=hashlib.sha256(json.dumps(c,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest(); cases.append(m)
m=copy.deepcopy(vals); m['gate']['geometryReports']=[x for x in m['gate']['geometryReports'] if x['geometryId']!='train-0014']; cases.append(m)
for i,m in enumerate(cases,1): assert run(m).returncode==2,i
# template mutation and source-template mutation
with tempfile.TemporaryDirectory() as td:
 tr=Path(td)/'tr'; shutil.copytree(H/'rendered-review-v1',tr); p=tr/'train-0014-fs-acquire-alis-600-t1/input-template.txt'; p.write_text(p.read_text().replace('albedo 0.150000','albedo 0.160000')); assert run(vals,tr).returncode==2
assert run(vals,source=(H/'test-fixtures/source-confirmation-template.txt').read_text().replace('aerosol_set_tau_at_wvl 550 0.148347','aerosol_set_tau_at_wvl 550 0.2')).returncode==2
m=copy.deepcopy(vals); m['preregistration']['preregistrationSha256']='0'*64; assert run(m).returncode==2
print('12 mutation refusals + 1 exact pass: PASS')
