from __future__ import annotations
import hashlib, json, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent; REF=ROOT/'reference'
def canon(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
class T(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.p1=json.loads((REF/'full-spectrum-estimator-pilot-preregistration-v1.json').read_text()); cls.p2=json.loads((ROOT/'full-spectrum-estimator-pilot-preregistration-v2.json').read_text()); cls.m1=json.loads((REF/'full-spectrum-estimator-pilot-execution-manifest-v1.json').read_text()); cls.m4=json.loads((ROOT/'full-spectrum-estimator-pilot-execution-manifest-v4.json').read_text())
 def test_current_hashes(self):
  self.assertEqual(self.p2['protocolSha256'],canon({k:v for k,v in self.p2.items() if k!='protocolSha256'})); self.assertEqual(self.m4['manifestSha256'],canon({k:v for k,v in self.m4.items() if k!='manifestSha256'}))
 def test_v1_reference_matches_superseded_protocol(self):
  s=self.p2['supersedesProtocol']; self.assertFalse(s['executionOccurred']); self.assertFalse(s['pilotResultValuesOpened']); self.assertEqual(s['protocolSha256'],self.p1['protocolSha256']); self.assertEqual(s['rawSha256'],hashlib.sha256((REF/'full-spectrum-estimator-pilot-preregistration-v1.json').read_bytes()).hexdigest())
 def test_scientific_design_unchanged(self):
  for k in ('cases','selectedGeometries','methods','candidateSeedRange','seedPolicy','caseCount','configuredPhotonHistoriesSum','source','selectionBoundary','executionBoundary'): self.assertEqual(self.p1[k],self.p2[k],k)
  self.assertEqual(self.m1['cases'],self.m4['cases']); self.assertEqual(self.m1['runtimeIdentityRequired'],self.m4['runtimeIdentityRequired']); self.assertEqual(self.m4['caseCount'],44); self.assertEqual(self.m4['configuredPhotonHistoriesSum'],5_600_000_000)
 def test_statistical_correction_and_confirmation_boundary(self):
  a=self.p2['analysisPlan']; self.assertFalse(a['twoBlockUncertaintyInterpretation']['inferentialPValueOrZScoreAllowed']); self.assertTrue(a['twoBlockUncertaintyInterpretation']['rsemIsDescriptiveScreenOnly']); self.assertEqual(a['grossMeanConsistencyScreen']['closedInterval'],[0.5,2.0]); self.assertFalse(a['grossMeanConsistencyScreen']['statisticalEquivalenceClaim']); self.assertNotIn('maximumCompatibilityZ',a)
  c=a['confirmationBoundary']; self.assertFalse(c['screeningBlocksMayEnterFinalConfirmationPrecisionGate']); self.assertEqual(c['firstConfirmationFreshIndependentBlocksPerChosenMethod'],4); self.assertTrue(c['confirmationRequiresSeparatePreregistrationBeforeThoseValuesAreOpened']); self.assertFalse(c['automaticExtensionBeyondFirstConfirmation'])
 def test_v4_artifact_hardening_not_authorization(self):
  a=self.m4['artifactContract']; self.assertTrue(a['exactDirectiveSurfaceRequired']); self.assertTrue(a['historicalPhysicalFingerprintRequired']); self.assertIn('wavelength-grid-1nm.dat',a['requiredMembersByMethod']['reference-vroom-1nm'])
  for k in ('authorizationEnabled','dispatchPerformed','fittingAuthorized','holdoutOpeningAuthorized','productionAuthorization','scientificExecutionPerformed'): self.assertFalse(self.m4['executionBoundary'][k])
if __name__=='__main__': unittest.main()
