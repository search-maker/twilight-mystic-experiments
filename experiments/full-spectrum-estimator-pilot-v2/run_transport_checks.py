#!/usr/bin/env python3
from __future__ import annotations
import argparse, compileall, json, os, re, subprocess, sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
MODULES=['freshness.py','github_surface.py','package_evidence.py','authorization_guard.py','dispatch_guard.py','execution_guard.py','executor.py','run_transport_checks.py','test_transport_v6.py']
WORKFLOWS=['full-spectrum-estimator-pilot-v2-transport-review-v6.yml','full-spectrum-estimator-pilot-v2-authorization-review-v6.yml','full-spectrum-estimator-pilot-v2-ordinal14-execution-v6.yml']

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--repository-root',type=Path,required=True); a=ap.parse_args(); root=a.repository_root.resolve()
    env=os.environ.copy(); env['TRANSPORT_TEST_REPOSITORY_ROOT']=str(root)
    test=subprocess.run([sys.executable,'-m','unittest','-v',str(root/'experiments/full-spectrum-estimator-pilot-v2/test_transport_v6.py')],cwd=root,env=env,text=True,capture_output=True)
    sys.stdout.write(test.stdout); sys.stderr.write(test.stderr)
    if test.returncode: return test.returncode
    m=re.search(r'Ran (\d+) tests',test.stderr+test.stdout); count=int(m.group(1)) if m else None
    if count!=62: raise SystemExit(f'expected 62 v6 tests, observed {count}')
    for name in MODULES:
        if not compileall.compile_file(str(root/'experiments/full-spectrum-estimator-pilot-v2'/name),quiet=1,force=True): raise SystemExit(f'compile failed: {name}')
    try:
        import yaml
    except Exception as exc: raise SystemExit(f'PyYAML unavailable: {exc}')
    for name in WORKFLOWS:
        p=root/'.github/workflows'/name
        value=yaml.safe_load(p.read_text())
        if not isinstance(value,dict): raise SystemExit(f'workflow YAML did not parse to mapping: {name}')
    transport=(root/'.github/workflows'/WORKFLOWS[0]).read_text(); auth=(root/'.github/workflows'/WORKFLOWS[1]).read_text(); sci=(root/'.github/workflows'/WORKFLOWS[2]).read_text()
    for label,text in [('transport',transport),('authorization',auth)]:
        forbidden=('setup-micromamba','rubin-libradtran','command -v uvspec','--allow-execution','workflow_dispatch:','schedule:','repository_dispatch:')
        found=[x for x in forbidden if x in text]
        if found: raise SystemExit(f'{label} review execution surface violation: {found}')
    if 'workflow_dispatch:' in sci or 'schedule:' in sci or 'repository_dispatch:' in sci: raise SystemExit('scientific workflow exposes alternate trigger')
    static=subprocess.run([sys.executable,str(root/'experiments/full-spectrum-estimator-pilot-v2/package_evidence.py'),'verify-static','--repository-root',str(root)],cwd=root,text=True,capture_output=True)
    if static.returncode: sys.stderr.write(static.stderr); return static.returncode
    summary={'status':'TRANSPORT_V6_CHECKS_PASS','testsPassed':62,'pythonCompile':True,'workflowYamlParsed':3,'reviewWorkflowScientificExecutionSurface':False,'authorizationReviewScientificExecutionSurface':False,'scientificExecutionPerformed':False,'authorizationCreated':False,'dispatchCreated':False,'ordinalAllocatedReservedOrConsumed':False}
    print(json.dumps(summary,indent=2,sort_keys=True)); return 0
if __name__=='__main__': raise SystemExit(main())
