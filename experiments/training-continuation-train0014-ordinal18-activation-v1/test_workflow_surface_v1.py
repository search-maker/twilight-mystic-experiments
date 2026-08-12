#!/usr/bin/env python3
from pathlib import Path
R=Path(__file__).resolve().parents[2]; W=R/'.github/workflows'
act=(W/'training-continuation-train0014-ordinal18-activation-review.yml').read_text(); auth=(W/'training-continuation-train0014-ordinal18-authorization-review.yml').read_text(); exe=(W/'training-continuation-train0014-ordinal18-execution.yml').read_text()
for text,name in ((act,'activation'),(auth,'authorization')):
 assert 'pull_request:' in text and 'workflow_dispatch:' not in text and 'schedule:' not in text, name
 assert '--allow-execution' not in text and 'executor_v1.py' not in text, name
 assert '${{ GITHUB_REPOSITORY }}' not in text, name
assert 'ref: ${{ github.event.pull_request.head.sha }}' in auth
assert '$GITHUB_SHA' not in auth and "os.environ['GITHUB_SHA']" not in auth
assert '/tmp/branches-preauth.json' in auth and "!='authorization/training-continuation-train0014-ordinal18'" in auth
assert 'push:' in exe and 'dispatch/training-continuation-train0014-ordinal18' in exe
assert 'workflow_dispatch:' not in exe and 'schedule:' not in exe
assert '--allow-execution' in exe and 'executor_v1.py' in exe
assert 'GITHUB_RUN_ATTEMPT' in exe and 'training-continuation-train0014-case-' in exe
print('workflow surface tests: PASS')
