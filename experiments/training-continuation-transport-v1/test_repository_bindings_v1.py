#!/usr/bin/env python3
from pathlib import Path
import subprocess,sys,tempfile,json
HERE=Path(__file__).resolve().parent; REPO=HERE.parents[1]
def run(v,p):
    with tempfile.TemporaryDirectory() as td:
        out=Path(td)/'m.json'; cmd=[sys.executable,str(HERE/'build_execution_manifest_v1.py'),'--repository-root',str(REPO),'--variant',v,'--preregistration',str(REPO/p),'--contract',str(HERE/'transport-contract.v1.json'),'--analysis-contract',str(HERE/'analysis-contract.v1.json'),'--output',str(out)]; r=subprocess.run(cmd,capture_output=True,text=True); assert r.returncode==0,(r.stdout,r.stderr); m=json.loads(out.read_text()); return m
m1=run('train0014','review/train-0014-fresh-training-acquisition-v1/train-0014-fresh-training-acquisition-preregistration-v1.json'); assert m1['caseCount']==4 and m1['totalPhotonHistories']==200000000
m2=run('train0037','review/train-0037-targeted-estimator-comparison-v1/train-0037-targeted-estimator-comparison-preregistration-v1.json'); assert m2['caseCount']==12 and m2['totalPhotonHistories']==1200000000
print('PASS: exact merged preregistration/template binding')
