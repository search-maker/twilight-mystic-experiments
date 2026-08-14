from __future__ import annotations
import importlib.util, json, pathlib, tempfile, unittest
ROOT=pathlib.Path(__file__).resolve().parents[2]
def mod(name,path):
 s=importlib.util.spec_from_file_location(name,path); assert s and s.loader; m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
core=mod('stage2_core',ROOT/'review/tier2-stage2-protected-holdout-v1/stage2_v1.py'); builder=mod('stage2_builder',ROOT/'experiments/tier2-stage2-execution-v1/build_manifest_v1.py'); executor=mod('stage2_executor',ROOT/'experiments/tier2-stage2-execution-v1/executor_v1.py')
P=json.loads((ROOT/'review/tier2-stage2-protected-holdout-v1/contract-v1.json').read_text())
class Tests(unittest.TestCase):
 def test_contract_and_sources(self): core.validate_review_sources(ROOT,P)
 def test_exact_case_seed_and_photon_universe(self):
  cs=core.expected_cases(P); self.assertEqual(len(cs),24); self.assertEqual(len({x['seed'] for x in cs}),24); self.assertEqual(sum(x['photonHistories'] for x in cs),720_000_000); self.assertEqual([x['seed'] for x in cs[:4]],[1900000001,1900000002,1900000003,1900000004]); self.assertEqual([x['seed'] for x in cs[-4:]],[1900000085,1900000086,1900000087,1900000088])
 def test_manifest(self):
  m=builder.build(ROOT,P); self.assertEqual((m['geometryCount'],m['caseCount'],m['configuredPhotonHistories']),(6,24,720_000_000)); self.assertTrue(all(x['role']=='protected-holdout' for x in m['cases'])); self.assertEqual(m['manifestSha256'],builder.selfhash(m))
 def test_frozen_grid_parser_accepts_solver_serialization(self):
  with tempfile.TemporaryDirectory() as td:
   p=pathlib.Path(td)/'x.spc'; p.write_text('\n'.join(f'{380+0.05*i:.5f} 1.0' for i in range(8001))+'\n'); wl,y=executor.parse_full_spectrum(p); self.assertEqual((len(wl),wl[0],wl[-1]),(8001,380.0,780.0)); self.assertEqual(len(y),8001)
 def test_grid_token_mutation_refuses(self):
  with tempfile.TemporaryDirectory() as td:
   rows=[f'{380+0.05*i:.5f} 1.0' for i in range(8001)]; rows[200]='390.00001 1.0'; p=pathlib.Path(td)/'x.spc'; p.write_text('\n'.join(rows)+'\n');
   with self.assertRaises(executor.Refusal): executor.parse_full_spectrum(p)
 def test_review_boundaries_closed(self):
  b=P['boundaries']; self.assertFalse(any(b.values())); self.assertTrue(P['modelAndEvaluation']['noRetuningAfterHoldoutOpening']); self.assertFalse(P['modelAndEvaluation']['p90OrP95PrincipalMetricAllowed'])
if __name__=='__main__':unittest.main()
