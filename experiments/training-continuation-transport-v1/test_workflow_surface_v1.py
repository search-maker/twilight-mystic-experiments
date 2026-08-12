#!/usr/bin/env python3
from pathlib import Path
import argparse,json

def main():
    p=argparse.ArgumentParser(); p.add_argument('--workflow',type=Path,required=True); a=p.parse_args()
    text=a.workflow.read_text()
    assert '\n  pull_'+'request:' in text
    for forbidden in ('\n  pu'+'sh:','\n  workflow_'+'dispatch:','\n  sche'+'dule:','uv'+'spec','executor_'+'v1.py --'):
        assert forbidden not in text, forbidden
    repo=a.workflow.parents[2]
    assert not list((repo/'.github/workflows').glob('training-continuation-*-execution*.yml'))
    c=json.loads((repo/'experiments/training-continuation-transport-v1/transport-contract.v1.json').read_text())
    assert c['workflowSurface']['scientificExecutionWorkflowIncluded'] is False
    assert c['workflowSurface']['solverInvocationFromReviewWorkflow'] is False
    assert all(v is False for v in c['transportBoundary'].values())
    print('PASS: PR-only transport workflow; no scientific execution workflow or solver invocation')
if __name__=='__main__': main()
