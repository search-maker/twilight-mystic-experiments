from __future__ import annotations
import hashlib, importlib.util, json, math, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def load_module(name,path):
 s=importlib.util.spec_from_file_location(name,path); assert s and s.loader; m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
ana=load_module('ana_v5',ROOT/'analyze_full_spectrum_estimator_pilot_v5.py')
ACQ=json.loads((ROOT/'full-spectrum-estimator-pilot-preregistration-v2.json').read_text())
AP=json.loads((ROOT/'full-spectrum-estimator-pilot-screening-analysis-preregistration-v3.json').read_text())
ADM=json.loads((ROOT/'full-spectrum-training-admission-complete-v1.json').read_text())
BASE={g['geometryId']:g for g in ADM['geometryReports']}

def canon(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def synth_evidence(target_gid='train-0041',target_center=550.0,target_rsem=0.10,zero_case=None):
 rows=[]
 for c in ACQ['cases']:
  hist=BASE[c['geometryId']]
  # Use immutable full-history mean as center so the broad mean-ratio screen passes by construction.
  channels={}
  sign=-1.0 if c['replicate']==1 else 1.0
  d=0.02
  if c['geometryId']==target_gid and c['method']=='alis-alt-importance' and c['importanceCenterNm']==target_center: d=target_rsem
  for name in ana.PRIMARY:
   vals=[float(x) for x in hist['channels'][name]['values']]; m=sum(vals)/len(vals)
   x=m*(1+sign*d)
   channels[name]=0.0 if c['caseId']==zero_case else x
  rows.append({'caseId':c['caseId'],'geometryId':c['geometryId'],'method':c['method'],'importanceCenterNm':c['importanceCenterNm'],'replicate':c['replicate'],'seed':c['seed'],'photonHistories':c['photonHistories'],'channels':channels,'zeroHit':c['caseId']==zero_case})
 e={'schemaVersion':1,'evidenceId':'public-tier1-full-spectrum-estimator-pilot-normalized-evidence-v6','status':'NORMALIZED','protocolSha256':ana.ACQUISITION_PROTOCOL_SHA,'executionManifestSha256':ana.EXEC_SHA,'caseCount':44,'cases':rows,'holdoutValuesRead':False}
 e['evidenceSha256']=canon(e); return e

class T(unittest.TestCase):
 def test_analysis_protocol_hash_and_frozen_baseline_reproduces(self):
  self.assertEqual(AP['analysisProtocolSha256'],canon({k:v for k,v in AP.items() if k!='analysisProtocolSha256'}))
  frozen=ana.validate_analysis_protocol(AP,ACQ,ADM)
  self.assertEqual(set(frozen),set(ACQ['selectionBoundary']['selectedGeometryIds']))
  self.assertTrue(AP['historicalFirstTwoScreeningBaseline']['fullAdaptiveHistoryMayBeReportedAsContextButNotUsedInVarianceGainThreshold'])

 def test_like_for_like_regression_train0041(self):
  out=ana.analyze(ACQ,AP,ADM,synth_evidence())
  g=next(x for x in out['geometryReports'] if x['geometryId']=='train-0041')
  m=next(x for x in g['methodReports'] if x['method']=='alis-alt-importance' and x['importanceCenterNm']==550.0)
  self.assertGreater(max(m['statistics']['channels'][n]['descriptiveTwoBlockRsem'] for n in ana.PRIMARY),0.08)
  old_full=max(g['historicalChannels'][n]['rsem'] for n in ana.PRIMARY)
  self.assertGreater(0.10,0.5*old_full)  # v4 strong-gain rule would reject this 10% candidate.
  self.assertEqual(m['classification'],'SCREENING_VARIANCE_GAIN_ON_HISTORICAL_PROBLEM_CHANNELS')
  screen=m['sameNVarianceGainScreen']; self.assertTrue(screen['passed']); self.assertEqual(set(screen['historicalProblemChannels']),set(ana.PRIMARY))
  for n in ana.PRIMARY:
   self.assertLessEqual(screen['perChannel'][n]['varianceProxyRatio'],0.5)
  self.assertFalse(out['fullAdaptiveHistoricalRsemUsedForVarianceGainThreshold'])

 def test_first_two_and_full_history_are_distinct_contexts(self):
  frozen=ana.validate_analysis_protocol(AP,ACQ,ADM)['train-0041']
  sc=frozen['channels']['scotopicLuminanceScotCdM2']
  self.assertGreater(sc['firstTwoDescriptiveRsem'],0.40)
  self.assertLess(sc['fullHistoryRsem'],0.09)

 def test_fresh_zero_blocks_candidate(self):
  ev=synth_evidence(zero_case='train-0041-fs-alis-550-r1')
  out=ana.analyze(ACQ,AP,ADM,ev)
  g=next(x for x in out['geometryReports'] if x['geometryId']=='train-0041')
  m=next(x for x in g['methodReports'] if x['method']=='alis-alt-importance' and x['importanceCenterNm']==550.0)
  self.assertEqual(m['classification'],'NO_CLEAR_SCREENING_GAIN')
  self.assertEqual(m['statistics']['zeroHitCaseCount'],1)

 def test_tampered_analysis_protocol_refused(self):
  bad=json.loads(json.dumps(AP)); bad['screeningRules']['sameNVarianceGain']['maximumVarianceProxyRatioOnEveryFiniteHistoricalProblemChannel']=0.9
  with self.assertRaisesRegex(ValueError,'analysis protocol identity'):
   ana.analyze(ACQ,bad,ADM,synth_evidence())

if __name__=='__main__': unittest.main()
