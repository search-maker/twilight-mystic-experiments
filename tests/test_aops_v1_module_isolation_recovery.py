from __future__ import annotations
import subprocess, sys, textwrap, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class ModuleIsolation(unittest.TestCase):
    def test_control_surface_ignores_poisoned_global_freshness_module(self):
        code=textwrap.dedent(r'''
            import importlib.util, sys, types
            from pathlib import Path
            fake=types.ModuleType('freshness')
            fake.authorization_branch=lambda ordinal: 'authorization/WRONG-stage-ordinal-'+str(ordinal)
            sys.modules['freshness']=fake
            p=Path('experiments/aerosol-optical-property-sensitivity-v1/execution-candidate/control_surface.py').resolve()
            spec=importlib.util.spec_from_file_location('aops_control_surface_isolation_test',p)
            m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
            assert m.authorization_branch(36)=='authorization/aerosol-optical-property-sensitivity-v1-ordinal-36'
        ''')
        subprocess.run([sys.executable,'-c',code],cwd=ROOT,check=True)
