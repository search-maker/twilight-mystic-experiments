#!/usr/bin/env python3
from pathlib import Path
t=(Path(__file__).resolve().parents[2]/'.github/workflows/artifact-pipeline-replay-result-v1-review.yml').read_text();l=t.lower()
assert 'pull_request:' in t and "github.head_ref == 'review/artifact-pipeline-replay-result-v1'" in t
assert 'workflow_'+'dispatch' not in l and '\npush:' not in l
for q in ('uv'+'spec','librad'+'tran','mc_'+'vroom','--allow-'+'execution','upload-'+'artifact'): assert q not in l,q
assert 'actions: read' in t
print('PASS: metadata-only PR review workflow; no solver/dispatch/upload surface')
