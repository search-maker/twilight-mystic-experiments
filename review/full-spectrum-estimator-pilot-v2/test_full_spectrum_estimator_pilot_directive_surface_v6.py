from __future__ import annotations
import hashlib, importlib.util, json, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def load(name,p):
 s=importlib.util.spec_from_file_location(name,p); assert s and s.loader; m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
norm=load('norm',ROOT/'normalize_full_spectrum_estimator_pilot_results_v6.py'); M=json.loads((ROOT/'full-spectrum-estimator-pilot-execution-manifest-v4.json').read_text()); R=json.loads((ROOT/'rendered-review-v5/renderer-review-report.json').read_text()); RC={r['caseId']:r for r in R['cases']}
def raw(c): return (ROOT/'rendered-review-v5'/c['caseId']/'input-resolved-review.txt').read_bytes()
class T(unittest.TestCase):
 def test_all_44_saved_inputs_match_report_surface_and_physics(self):
  self.assertEqual(len(M['cases']),44); self.assertEqual(set(RC),{c['caseId'] for c in M['cases']})
  for c in M['cases']:
   b=raw(c); self.assertEqual(hashlib.sha256(b).hexdigest(),RC[c['caseId']]['inputResolvedReviewSha256']); norm.verify_exact_directive_surface(b,c); self.assertEqual(norm.physical_fingerprint(b),RC[c['caseId']]['physicalFingerprintSha256'])
 def test_added_physical_directive_refused(self):
  c=M['cases'][0]
  for extra in (b'pressure 900\n',b'aerosol_modify tau set 0.1\n'):
   with self.assertRaises(ValueError): norm.verify_exact_directive_surface(raw(c)+extra,c)
 def test_duplicate_aod_refused(self):
  c=M['cases'][0]; b=raw(c); line=next(x for x in b.splitlines(keepends=True) if x.startswith(b'aerosol_set_tau_at_wvl '))
  with self.assertRaises(ValueError): norm.verify_exact_directive_surface(b.replace(line,line+line,1),c)
 def test_comments_and_blank_lines_allowed(self): norm.verify_exact_directive_surface(b'# comment\n\n'+raw(M['cases'][0]),M['cases'][0])
if __name__=='__main__': unittest.main()
