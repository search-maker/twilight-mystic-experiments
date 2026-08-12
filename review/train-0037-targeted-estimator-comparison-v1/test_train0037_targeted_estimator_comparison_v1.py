#!/usr/bin/env python3
import copy,hashlib,json,subprocess,tempfile,shutil
from pathlib import Path
H=Path(__file__).resolve().parent; V=H/'validate_train0037_targeted_estimator_comparison_v1.py'
files={'preregistration':H/'train-0037-targeted-estimator-comparison-preregistration-v1.json','decision':H/'test-fixtures/confirmation-decision-v1.json','readiness':H/'test-fixtures/training-readiness-v2.json','gate':H/'test-fixtures/training-admission-gate-v1-minimal.json','screening':H/'test-fixtures/train-0037-screening-report-v8-minimal.json','seed-audit':H/'test-fixtures/seed-audit-minimal.json'}
def load(k): return json.loads(files[k].read_text())
def rehash(v): c=copy.deepcopy(v); c['preregistrationSha256']=None; v['preregistrationSha256']=hashlib.sha256(json.dumps(c,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def run(vals,templates=None,s500=None,s600=None):
 with tempfile.TemporaryDirectory() as td:
  td=Path(td); args=['python3',str(V)]
  for k,v in vals.items():
   p=td/(k+'.json'); p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n'); args += ['--'+k,str(p)]
  a=td/'500.txt'; a.write_text(s500 if s500 is not None else (H/'test-fixtures/source-train-0037-alis-500-r1-template.txt').read_text()); args += ['--source-500',str(a)]
  b=td/'600.txt'; b.write_text(s600 if s600 is not None else (H/'test-fixtures/source-train-0037-alis-600-r1-template.txt').read_text()); args += ['--source-600',str(b)]
  tr=td/'templates'; shutil.copytree(templates or H/'rendered-review-v1',tr); args += ['--template-root',str(tr)]
  return subprocess.run(args,capture_output=True,text=True)
vals={k:load(k) for k in files}; assert run(vals).returncode==0
cases=[]
m=copy.deepcopy(vals); m['preregistration']['comparisonDesign']['importanceCentersNm']=[500.0,600.0]; rehash(m['preregistration']); cases.append(m)
m=copy.deepcopy(vals); m['preregistration']['comparisonDesign']['seeds'][0]=970001; m['preregistration']['comparisonDesign']['cases'][0]['seed']=970001; rehash(m['preregistration']); cases.append(m)
m=copy.deepcopy(vals); m['preregistration']['comparisonDesign']['automaticAdditionalBlocks']=True; rehash(m['preregistration']); cases.append(m)
m=copy.deepcopy(vals); m['preregistration']['comparisonEvaluation']['historicalMaximumAcceptedRsem']=0.09; rehash(m['preregistration']); cases.append(m)
m=copy.deepcopy(vals); m['preregistration']['comparisonEvaluation']['automaticCenterSelection']=True; rehash(m['preregistration']); cases.append(m)
m=copy.deepcopy(vals); m['preregistration']['comparisonEvaluation']['comparisonValuesAdmittedAsTrainingLabels']=True; rehash(m['preregistration']); cases.append(m)
m=copy.deepcopy(vals); m['preregistration']['comparisonEvaluation']['independentVroomReferenceIncluded']=True; rehash(m['preregistration']); cases.append(m)
m=copy.deepcopy(vals); m['preregistration']['executionBoundary']['scientificExecutionAuthorized']=True; rehash(m['preregistration']); cases.append(m)
m=copy.deepcopy(vals); m['decision']['decisionSemantics']['globalEstimatorSelected']=True; c=copy.deepcopy(m['decision']); c['decisionSha256']=None; m['decision']['decisionSha256']=hashlib.sha256(json.dumps(c,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest(); cases.append(m)
m=copy.deepcopy(vals); m['readiness']['hardBoundary']['modelFittingAuthorized']=True; c=copy.deepcopy(m['readiness']); c['readinessSha256']=None; m['readiness']['readinessSha256']=hashlib.sha256(json.dumps(c,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest(); cases.append(m)
m=copy.deepcopy(vals); m['gate']['continuationRequiredGeometryIds']=['train-0014']; cases.append(m)
m=copy.deepcopy(vals); m['screening']['geometryReport']['methodReports'][0]['classification']='LOW_TWO_BLOCK_RSEM_SCREENING_CANDIDATE'; cases.append(m)
m=copy.deepcopy(vals); m['preregistration']['preregistrationSha256']='0'*64; cases.append(m)
for i,m in enumerate(cases,1): assert run(m).returncode==2,(i,run(m).stdout,run(m).stderr)
with tempfile.TemporaryDirectory() as td:
 tr=Path(td)/'tr'; shutil.copytree(H/'rendered-review-v1',tr); p=tr/'train-0037-fs-compare-alis-550-c1/input-template.txt'; p.write_text(p.read_text().replace('albedo 0.150000','albedo 0.160000')); assert run(vals,tr).returncode==2
assert run(vals,s500=(H/'test-fixtures/source-train-0037-alis-500-r1-template.txt').read_text().replace('aerosol_set_tau_at_wvl 550 0.185950','aerosol_set_tau_at_wvl 550 0.2')).returncode==2
print('15 mutation refusals + 1 exact pass: PASS')
