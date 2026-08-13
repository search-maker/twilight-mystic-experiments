#!/usr/bin/env python3
from pathlib import Path
p=Path(__file__).resolve().parents[2]/'.github/workflows/tier2-core-campaign-contract-v1-review.yml'
t=p.read_text(encoding='utf-8'); low=t.lower()
assert 'pull_request:' in t
assert "github.head_ref == 'review/tier2-core-campaign-contract-v1'" in t
assert 'workflow_'+'dispatch' not in low
assert '\npush:' not in low
for token in ('uv'+'spec','librad'+'tran','mc_'+'vroom','mc_'+'spectral_is','--allow-'+'execution','upload-'+'artifact'):
    assert token not in low, token
print('PASS: PR-only review workflow with no solver/dispatch surface')
