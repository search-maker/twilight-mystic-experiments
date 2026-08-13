#!/usr/bin/env python3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
WF=ROOT/'.github/workflows/train-0014-fresh-training-admission-decision-v1-review.yml'
text=WF.read_text(encoding='utf-8')
assert "if: github.head_ref == 'review/train0014-fresh-training-admission-decision-v1'" in text
assert "test \"$GITHUB_RUN_ATTEMPT\" = 1" in text
assert '31662184272' in text and '9166569024' in text
assert '98d78438add36b7aaebefe53a26af8ee1b5f2ead5ba6507eb49faa95420d4838' in text
assert 'a5c73eeac21c7db40ded50842653d03f0ec0ee63287fcf5694083ee3692c8135' in text
for forbidden in ('workflow_'+'dispatch','mamba-'+'org/setup-micromamba','uv'+'spec','mys'+'tic','libRad'+'tran','executor_'+'v1.py','--allow-'+'execution'):
    assert forbidden.lower() not in text.lower(), forbidden
assert 'actions/upload-artifact' not in text
print('PASS')
