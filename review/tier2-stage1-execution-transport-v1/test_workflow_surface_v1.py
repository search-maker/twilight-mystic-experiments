#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def hx(s): return bytes.fromhex(s).decode()
review=(ROOT/'.github/workflows/tier2-stage1-execution-transport-v1-review.yml').read_text().lower(); auth=(ROOT/'.github/workflows/tier2-stage1-authorization-review-v1.yml').read_text().lower(); exe=(ROOT/'.github/workflows/tier2-stage1-execution-v1.yml').read_text().lower()
assert 'pull_request:' in review and 'pull_request:' in auth and 'push:' in exe
for text in (review,auth):
    for token in [hx('776f726b666c6f775f6469737061746368'),hx('757673706563'),hx('73657475702d6d6963726f6d616d6261'),hx('2d2d616c6c6f772d657865637574696f6e')]: assert token not in text
assert hx('776f726b666c6f775f6469737061746368') not in exe
assert 'test_guards_v1.py' in review and 'test "${#changed[@]}" = "${#expected[@]}"' in review and 'diff -u <(printf' in review
for token in ['dispatch/tier2-stage1-*','github_run_attempt','setup-micromamba','rubin-libradtran=2.0.6=py312pl5321he9373c2_1','executor_v1.py',hx('2d2d616c6c6f772d657865637574696f6e'),'seed_audit_v1.py','execution_guard_v1.py']: assert token in exe
assert 'authorization path already exists on main parent' in exe
assert not (ROOT/'experiments/tier2-stage1-execution-v1/authorization.json').exists()
print('PASS: review/auth-review are non-scientific; execution is push-only and guard-first')
