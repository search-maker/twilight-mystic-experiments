#!/usr/bin/env python3
import json,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
E=json.loads((ROOT/'expected-runtime-identity.v1.json').read_text())['runtimeIdentity']
probe={'schemaVersion':1,'stageId':'mystic-batch-v1','status':'RUNTIME_IDENTITY_CAPTURED','scientificSolverExecuted':False,'syntaxCheckExecuted':False,'uvspecSha256':E['uvspecSha256'],'uvspecHelpSha256':E['uvspecHelpSha256'],'libRadtranDataTreeSha256':E['libRadtranDataTreeSha256'],'libRadtranDataFileCount':E['libRadtranDataFileCount'],'libRadtranDataByteCount':E['libRadtranDataByteCount'],'atmosphereSha256':E['atmosphereSha256'],'runtimeLockRawSha256':E['runtimeLockRawSha256'],'python':E['python'],'pythonImplementation':E['pythonImplementation'],'architecture':E['architecture'],'runnerImage':E['runnerImage'],'runnerArch':E['runnerArch']}
with tempfile.TemporaryDirectory() as d:
    d=Path(d); (d/'p.json').write_text(json.dumps(probe)); out=d/'out.json'
    r=subprocess.run(['python3',str(ROOT/'runtime_capture_v1.py'),'--probe',str(d/'p.json'),'--expected',str(ROOT/'expected-runtime-identity.v1.json'),'--output',str(out)],capture_output=True,text=True); assert r.returncode==0,r.stdout+r.stderr; assert json.loads(out.read_text())==E
    bad=dict(probe); bad['uvspecSha256']='0'*64; (d/'bad.json').write_text(json.dumps(bad)); r=subprocess.run(['python3',str(ROOT/'runtime_capture_v1.py'),'--probe',str(d/'bad.json'),'--expected',str(ROOT/'expected-runtime-identity.v1.json'),'--output',str(d/'badout.json')],capture_output=True,text=True); assert r.returncode==2
print('runtime capture tests: PASS')
