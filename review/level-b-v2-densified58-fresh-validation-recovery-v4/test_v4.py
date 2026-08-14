#!/usr/bin/env python3
from __future__ import annotations
import copy,importlib.util,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
REC=ROOT/'review/level-b-v2-densified58-fresh-validation-recovery-v4/recovery-v4.json';CON=ROOT/'review/level-b-v2-densified58-fresh-validation-recovery-v4/contract-v4.json';CORE=ROOT/'review/level-b-v2-densified58-fresh-validation-recovery-v4/fresh_validation_v4.py';MAN=ROOT/'experiments/level-b-v2-densified58-fresh-validation-recovery-v4/build_manifest_v4.py';EXE=ROOT/'experiments/level-b-v2-densified58-fresh-validation-recovery-v4/executor_v4.py';AD=ROOT/'experiments/level-b-v2-densified58-fresh-validation-v1/adapter_v1.py';BASE=ROOT/'review/level-b-v2-densified58-fresh-validation-v1/contract-v1.json'
def mod(n,p):s=importlib.util.spec_from_file_location(n,p);assert s and s.loader;m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
core=mod('fv4test',CORE);man=mod('mv4test',MAN);exe=mod('ev4test',EXE);adapter=mod('av1o27',AD)
class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.r=json.loads(REC.read_text());cls.c=json.loads(CON.read_text());cls.b=json.loads(BASE.read_text());cls.e=core.effective_contract(cls.r,ROOT)
 def test_frozen_science(self):
  for k in ('authorization','boundaries','failureSemantics','geometrySelection','modelAndEvaluation','runtimeIdentityRequired','sourceBindings'):self.assertEqual(self.e[k],self.b[k])
  a=copy.deepcopy(self.b['executionEnvelope']);b=copy.deepcopy(self.e['executionEnvelope'])
  for x in (a,b):x.pop('candidateScientificOrdinal');x.pop('reservedSeeds');x.pop('scientificOrdinalAllocated')
  self.assertEqual(a,b)
 def test_ordinal26_path_refusal(self):
  o=self.r['ordinal26Refusal'];self.assertEqual(o['dispatchRunId'],31844855497);self.assertEqual(o['preflightArtifactId'],9235548762);self.assertEqual(o['preflightManifestZipMember'],'tmp/o26-manifest.json');self.assertEqual(o['caseManifestPathRequested'],'/tmp/v0070-o26-preflight/o26-manifest.json');self.assertEqual(o['caseJobCount'],24);self.assertEqual(o['terminalCaseFailureCount'],24);self.assertEqual(o['syntaxCheckCount'],0);self.assertEqual(o['solverExecutionCount'],0);self.assertFalse(o['protectedValuesRead']);self.assertTrue(o['identityConsumed']);self.assertEqual(o['retiredSeeds'],list(range(2101000049,2101000073)))
 def test_ordinal27_identity(self):
  n=self.r['nextScientificIdentity'];self.assertEqual((n['scientificOrdinal'],n['authorizationBranch'],n['allocationLockBranch'],n['dispatchBranch']),(27,'authorization/level-b-v2-densified58-fresh-validation-ordinal27-v1','allocation/level-b-v2-densified58-fresh-validation-ordinal27-v1','dispatch/level-b-v2-densified58-fresh-validation-ordinal27-v1'));self.assertEqual(n['reservedSeeds'],list(range(2101000073,2101000097)));rows=core.expected_cases(self.e,self.r,ROOT);self.assertEqual(len(rows),24);self.assertEqual([x['seed'] for x in rows],list(range(2101000073,2101000097)));self.assertTrue(all(x['caseId'].startswith('v0070-o27-holdout-') for x in rows))
 def test_manifest_adapter(self):
  m=man.build(ROOT,self.r);adapter.validate_manifest(m);self.assertEqual(m['manifestId'],'level-b-v2-densified58-fresh-validation-execution-manifest-v1');self.assertEqual((m['schemaVersion'],m['scientificOrdinalCandidate'],m['caseCount']),(4,27,24));self.assertEqual([x['seed'] for x in m['cases']],list(range(2101000073,2101000097)));self.assertTrue(all(v is False for v in m['closedUntilAuthorization'].values()));b=copy.deepcopy(m);h=b['manifestSha256'];b['manifestSha256']=None;self.assertEqual(h,man.canon(b))
 def test_executor_exact_branch(self):
  self.assertEqual(exe.BASE_EXECUTOR_GIT_BLOB_SHA,'5bf0477f0d5100dcb73da8027233e8415ce9021c');self.assertEqual(exe.BRANCH_RE.pattern,r'^dispatch/level-b-v2-densified58-fresh-validation-ordinal27-v1$');self.assertIsNotNone(exe.BRANCH_RE.fullmatch('dispatch/level-b-v2-densified58-fresh-validation-ordinal27-v1'));self.assertIsNone(exe.BRANCH_RE.fullmatch('dispatch/level-b-v2-densified58-fresh-validation-ordinal26-v1'))
 def test_artifact_path_contract(self):
  t=self.r['artifactTransportRecovery'];self.assertEqual(t['fixScope'],'CASE_DOWNLOAD_MANIFEST_PATH_ONLY');self.assertEqual(t['provenZipMember'],'tmp/o26-manifest.json');self.assertEqual(t['futureManifestZipMember'],'tmp/o27-manifest.json');self.assertEqual(t['futureDownloadedManifestPath'],'/tmp/v0070-o27-preflight/tmp/o27-manifest.json');self.assertFalse(t['flatteningAssumptionAllowed']);self.assertFalse(t['scientificPayloadChangeAuthorized'])
 def test_seed_ranges_disjoint(self):
  a=set(self.r['ordinal24Refusal']['retiredSeeds']);b=set(self.r['ordinal25Refusal']['retiredSeeds']);c=set(self.r['ordinal26Refusal']['retiredSeeds']);d=set(self.r['nextScientificIdentity']['reservedSeeds']);self.assertFalse(a&b or a&c or a&d or b&c or b&d or c&d)
 def test_review_closed(self):self.assertTrue(all(v is False for v in self.r['reviewSurface'].values()));self.assertTrue(all(v is False for v in self.c['closedBoundaries'].values()))
if __name__=='__main__':unittest.main()
