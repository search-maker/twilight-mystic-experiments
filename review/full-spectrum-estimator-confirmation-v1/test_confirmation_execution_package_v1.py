#!/usr/bin/env python3
from __future__ import annotations
import argparse, copy, importlib.util, json, os, subprocess, tempfile
from pathlib import Path

HERE=Path(__file__).resolve().parent

def load_module(name,path):
    s=importlib.util.spec_from_file_location(name,path); assert s and s.loader; m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

def load(p): return json.loads(Path(p).read_text())
def norm_template(raw:bytes)->list[str]:
    out=[]
    for line in raw.decode().splitlines():
        parts=line.split()
        if parts and parts[0]=='mc_randomseed': out.append('mc_randomseed <IDENTITY>')
        elif parts and parts[0]=='mc_basename': out.append('mc_basename <IDENTITY>')
        else: out.append(line)
    return out

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--repository-root',type=Path,required=True); a=ap.parse_args(); root=a.repository_root.resolve()
    review=root/'review/full-spectrum-estimator-confirmation-v1'
    prereg=review/'full-spectrum-estimator-confirmation-preregistration-v1.json'
    pilot=root/'review/full-spectrum-estimator-pilot-v2/full-spectrum-estimator-pilot-execution-manifest-v4.json'
    builder=review/'build_confirmation_execution_manifest_v1.py'; renderer=review/'render_confirmation_inputs_v1.py'; executor_path=review/'executor_confirmation_v1.py'
    with tempfile.TemporaryDirectory() as td:
        t=Path(td); manifest=t/'manifest.json'; templates=t/'templates'; report=t/'render-report.json'
        subprocess.run(['python',str(builder),'--repository-root',str(root),'--preregistration',str(prereg),'--pilot-manifest',str(pilot),'--output',str(manifest)],check=True)
        subprocess.run(['python',str(renderer),'--repository-root',str(root),'--execution-manifest',str(manifest),'--output-dir',str(templates),'--report',str(report)],check=True)
        m=load(manifest); p=load(pilot); rr=load(report); by={r['caseId']:r for r in p['cases']}
        assert m['caseCount']==24 and rr['caseCount']==24 and rr['scientificExecutionPerformed'] is False
        assert m['executionBoundary']=={'scientificExecutionAuthorized':False,'authorizationOrdinalAllocated':False,'dispatchBranchAllocated':False,'executionWorkflowPresent':False,'modelFittingAuthorized':False,'modelSelectionAuthorized':False,'holdoutValidationOpeningAuthorized':False,'tier2Authorized':False,'productionPromotionAuthorized':False}
        for row in m['cases']:
            src=copy.deepcopy(by[row['sourcePilotCaseId']]); exp=copy.deepcopy(src)
            exp['caseId']=row['caseId']; exp['replicate']=row['replicate']; exp['seed']=row['seed']; exp['requiredCommonDirectives']['mc_randomseed']=row['seed']
            for key in ('confirmationBlock','candidateId','sourcePilotCaseId','sourcePilotCasePair','sourcePilotInputTemplateSha256'): exp[key]=row[key]
            assert row==exp, f'case derivation drift: {row["caseId"]}'
            source_path=root/'review/full-spectrum-estimator-pilot-v2/rendered-review-v5'/row['sourcePilotCaseId']/'input-template.txt'
            out_path=templates/row['caseId']/'input-template.txt'
            assert norm_template(source_path.read_bytes())==norm_template(out_path.read_bytes()), f'unexpected template change: {row["caseId"]}'
        ex=load_module('confirmation_executor_v1',executor_path)
        data_dir=t/'fake-libradtran-data'; output_root=t/'resolved-output'
        for row in m['cases']:
            template_raw=(templates/row['caseId']/'input-template.txt').read_bytes()
            resolved=ex.resolve_template(template_raw,data_dir=data_dir,output_root=output_root)
            ex.validate_resolved_input(root,resolved,row)
        old=dict(os.environ)
        try:
            os.environ['GITHUB_ACTIONS']='true'; os.environ['GITHUB_EVENT_NAME']='push'; os.environ['GITHUB_RUN_ATTEMPT']='1'; os.environ['GITHUB_REF_NAME']='dispatch/full-spectrum-estimator-confirmation-v1-ordinal999999'
            ex.validate_execution_context('dispatch/full-spectrum-estimator-confirmation-v1-ordinal999999')
            refused=False
            try: ex.validate_execution_context('dispatch/full-spectrum-estimator-pilot-v2-ordinal16')
            except ex.ExecutionRefusal: refused=True
            assert refused
        finally:
            os.environ.clear(); os.environ.update(old)
        assert not (root/'.github/workflows/full-spectrum-estimator-confirmation-v1-execution.yml').exists()
    print(json.dumps({'status':'PASSED','caseCount':24,'scientificExecutionPerformed':False,'executionWorkflowPresent':False},indent=2,sort_keys=True)); return 0
if __name__=='__main__': raise SystemExit(main())
