from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path('.')


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def main() -> None:
    # Correct the two generator-escaping defects found by the earlier neutral builders.
    gp = ROOT / 'experiments/aerosol-optical-property-sensitivity-v1/execution-candidate/global_ordinal.py'
    gt = gp.read_text()
    old = r'b"\\0"'
    new = r'b"\0"'
    if gt.count(old) != 1:
        raise RuntimeError(f'blob separator escape count={gt.count(old)}')
    gt = gt.replace(old, new, 1)
    old = r'(?:\\s|$)'
    new = r'(?:\s|$)'
    if gt.count(old) != 1:
        raise RuntimeError(f'regex escape count={gt.count(old)}')
    gt = gt.replace(old, new, 1)
    gp.write_text(gt)
    gblob = git_blob_sha1(gp)

    # Harden control_surface against global sys.modules name pollution.
    cp = ROOT / 'experiments/aerosol-optical-property-sensitivity-v1/execution-candidate/control_surface.py'
    ct = cp.read_text()
    old = '''import json
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from freshness import (
    authorization_branch,
    consumed_marker,
    dispatch_branch,
    execution_key,
    matching_marker,
    positive_candidate_claims,
)
from global_ordinal import failed_authorization_history
'''
    new = f'''import hashlib
import importlib.util
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


def _git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\\0" + data).hexdigest()


def _load_bound_sibling(name: str, path: Path, expected_blob: str):
    if _git_blob_sha1(path) != expected_blob:
        raise RuntimeError(f"bound sibling byte drift: {{path.name}}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load bound sibling: {{path}}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_HERE = Path(__file__).resolve().parent
_freshness = _load_bound_sibling(
    "aops_control_surface_freshness", _HERE / "freshness.py",
    "3b4b087a211a5400164ea592ac1e947cff29631d",
)
_global_ordinal = _load_bound_sibling(
    "aops_control_surface_global_ordinal", _HERE / "global_ordinal.py",
    "{gblob}",
)
authorization_branch = _freshness.authorization_branch
consumed_marker = _freshness.consumed_marker
dispatch_branch = _freshness.dispatch_branch
execution_key = _freshness.execution_key
matching_marker = _freshness.matching_marker
positive_candidate_claims = _freshness.positive_candidate_claims
failed_authorization_history = _global_ordinal.failed_authorization_history
'''
    if ct.count(old) != 1:
        raise RuntimeError(f'control_surface import replacement count={ct.count(old)}')
    cp.write_text(ct.replace(old, new, 1))

    # Refresh review-freeze binding for the changed global ordinal wrapper.
    fp = ROOT / 'evidence/aerosol-optical-property-sensitivity-v1/review-freeze.json'
    freeze = json.loads(fp.read_text())
    freeze['globalOrdinalWrapperGitBlobSha1'] = gblob
    fp.write_text(json.dumps(freeze, indent=2, sort_keys=True) + '\n')

    # Refresh all transport bindings that changed.
    tp = ROOT / 'experiments/aerosol-optical-property-sensitivity-v1/transport-contract.v1.json'
    contract = json.loads(tp.read_text())
    for rel in (
        '.github/workflows/aops-v1-authorization-review.yml',
        '.github/workflows/aops-v1-dispatch-publisher.yml',
        'experiments/aerosol-optical-property-sensitivity-v1/execution-candidate/control_surface.py',
        'experiments/aerosol-optical-property-sensitivity-v1/execution-candidate/global_ordinal.py',
    ):
        contract['gitBlobBindings'][rel] = git_blob_sha1(ROOT / rel)
    tp.write_text(json.dumps(contract, indent=2, sort_keys=True) + '\n')

    # Regression for global-module pollution found only in the complete repository suite.
    (ROOT / 'tests/test_aops_v1_module_isolation_recovery.py').write_text('''from __future__ import annotations
import subprocess, sys, textwrap, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class ModuleIsolation(unittest.TestCase):
    def test_control_surface_ignores_poisoned_global_freshness_module(self):
        code=textwrap.dedent(r\'''\n            import importlib.util, sys, types\n            from pathlib import Path\n            fake=types.ModuleType('freshness')\n            fake.authorization_branch=lambda ordinal: 'authorization/WRONG-stage-ordinal-'+str(ordinal)\n            sys.modules['freshness']=fake\n            p=Path('experiments/aerosol-optical-property-sensitivity-v1/execution-candidate/control_surface.py').resolve()\n            spec=importlib.util.spec_from_file_location('aops_control_surface_isolation_test',p)\n            m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)\n            assert m.authorization_branch(36)=='authorization/aerosol-optical-property-sensitivity-v1-ordinal-36'\n        \''')
        subprocess.run([sys.executable,'-c',code],cwd=ROOT,check=True)
''')


if __name__ == '__main__':
    main()
