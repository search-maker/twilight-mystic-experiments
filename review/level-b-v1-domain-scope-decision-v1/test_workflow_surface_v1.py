#!/usr/bin/env python3
from pathlib import Path
p=Path(__file__).resolve().parents[2]/'.github/workflows/level-b-v1-domain-scope-decision-v1-review.yml'
t=p.read_text(encoding='utf-8')
low=t.lower()
assert 'pull_request:' in t
assert "github.head_ref == 'review/level-b-v1-domain-scope-decision-v1'" in t
assert 'workflow_'+'dispatch' not in low
assert '\npush:' not in low
for token in ('uv'+'spec','librad'+'tran','executor_'+'v1.py','--allow-'+'execution','setup-micro'+'mamba'):
    assert token not in low, token
assert 'upload-artifact' not in low
print('PASS: PR-only non-scientific workflow surface')
