from __future__ import annotations
import hashlib,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
class T(unittest.TestCase):
 def test_dependencies_present(self):
  for rel in ('build_full_spectrum_training_handoff.py','wavelength-grid-1nm.dat','normalize_full_spectrum_estimator_pilot_results_v6.py','full-spectrum-estimator-pilot-execution-manifest-v4.json','rendered-review-v5/renderer-review-report.json','full-spectrum-estimator-pilot-preauthorization-contract-v2.json','full_spectrum_estimator_pilot_preauthorization_guard_v2.py','reference/full-spectrum-estimator-pilot-preregistration-v1.json','reference/full-spectrum-estimator-pilot-execution-manifest-v1.json'): self.assertTrue((ROOT/rel).is_file(),rel)
 def test_grid_bytes(self):
  p=ROOT/'wavelength-grid-1nm.dat'; self.assertEqual(p.read_text(),''.join(f'{i}\n' for i in range(380,781))); self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),'488f6bd90c35a6f5aeffe1ef230186ae87002d42747af4fe94f07d82c5eef692')
 def test_tests_are_repository_relative(self): self.assertEqual([p.name for p in ROOT.glob('test_*.py') if ('/'+'mnt'+'/'+'data') in p.read_text()],[])
if __name__=='__main__': unittest.main()
