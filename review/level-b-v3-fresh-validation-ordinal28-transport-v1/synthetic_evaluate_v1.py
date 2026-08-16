#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / 'review/level-b-v3-fresh-validation-implementation-v1/fresh_validation_v1.py'
CONTRACT = ROOT / 'review/level-b-v3-fresh-validation-implementation-v1/contract-v1.json'
GRID_SHA = 'b5fae53c1cc88c7f3de6e3689bc25e4a36c54033d1d1bfd6169482f30cc5b477'


def module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'cannot load {path}')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def canon(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def frozen_tokens(grid_source: Path) -> list[str]:
    tokens=[]
    for line in grid_source.read_text(encoding='utf-8').splitlines():
        p=line.split()
        if p: tokens.append(p[0])
    assert len(tokens)==8001 and tokens[0]=='380.00000' and tokens[-1]=='780.00000'
    h=hashlib.sha256(('\n'.join(tokens)+'\n').encode()).hexdigest()
    assert h==GRID_SHA,(h,GRID_SHA)
    return tokens


def spectrum_text(tokens: list[str], scale: float) -> str:
    return '\n'.join(f'{token} {scale:.12e}' for token in tokens)+'\n'


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--materialized-dir',type=Path,required=True)
    ap.add_argument('--base-model-dir',type=Path,required=True)
    ap.add_argument('--representation-dir',type=Path,required=True)
    ap.add_argument('--repo-root',type=Path,required=True)
    ap.add_argument('--grid-source',type=Path,required=True)
    args=ap.parse_args()
    core=module('v3_o28_synthetic_evaluate_core',CORE)
    p=json.loads(CONTRACT.read_text(encoding='utf-8'))
    tokens=frozen_tokens(args.grid_source)
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)/'cases'; root.mkdir()
        for idx,c in enumerate(core.expected_cases(p)):
            d=root/c['caseId']; d.mkdir()
            # Use the frozen real MYSTIC/libRadtran wavelength-token sequence but
            # replace every radiance value with deterministic synthetic positives.
            # No scientific truth from the anchor artifact enters the fixture.
            y=spectrum_text(tokens,1.0 + 0.001*(idx%4))
            (d/'mc.rad.spc').write_text(y,encoding='utf-8')
            (d/'mc.rad.std.spc').write_text(spectrum_text(tokens,0.001),encoding='utf-8')
            r={'caseId':c['caseId'],'status':'COMPLETED','workflowRunAttempt':1,'retryPerformed':False,'resumePerformed':False,'githubRerun':False,'protectedHoldoutValueExposed':True,'syntheticFixture':True}
            r['contentSha256']=canon(r)
            (d/'case-result.json').write_text(json.dumps(r,indent=2,sort_keys=True)+'\n',encoding='utf-8')
        out=Path(td)/'synthetic-evaluation.json'
        result=core.evaluate(p,root,args.materialized_dir,args.base_model_dir,args.representation_dir,args.repo_root,out)
        assert result['scientificOrdinal']==28
        assert result['modelSha256']=='c4902eb3c2ba67b12dc4ef2b9cefb67c5963a6abc104708a73b2aab5dd0163b9'
        assert result['ordinal27ValuesRead'] is False and result['ordinal27MayInfluenceResult'] is False and result['retuningPerformed'] is False
        body=dict(result); h=body.pop('resultSha256')
        assert h==canon(body)
        assert len(result['records'])==6 and result['caseCount']==24
        print(json.dumps({'status':'PASS','syntheticEvaluationStatus':result['status'],'resultSha256':h,'recordCount':len(result['records']),'caseCount':result['caseCount'],'gridTokenSha256':GRID_SHA,'gridAnchorRadianceValuesUsed':False,'protectedScientificTruthUsed':False,'ordinal27ValuesRead':False},sort_keys=True))
    return 0

if __name__=='__main__': raise SystemExit(main())
