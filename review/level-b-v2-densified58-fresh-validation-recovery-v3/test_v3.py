#!/usr/bin/env python3
from __future__ import annotations
import copy, importlib.util, json, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
REC=ROOT/'review/level-b-v2-densified58-fresh-validation-recovery-v3/recovery-v3.json'
CON=ROOT/'review/level-b-v2-densified58-fresh-validation-recovery-v3/contract-v3.json'
CORE=ROOT/'review/level-b-v2-densified58-fresh-validation-recovery-v3/fresh_validation_v3.py'
MAN=ROOT/'experiments/level-b-v2-densified58-fresh-validation-recovery-v3/build_manifest_v3.py'
EXE=ROOT/'experiments/level-b-v2-densified58-fresh-validation-recovery-v3/executor_v3.py'
BASE=ROOT/'review/level-b-v2-densified58-fresh-validation-v1/contract-v1.json'

def mod(n,p):
    s=importlib.util.spec_from_file_location(n,p);assert s and s.loader;m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
core=mod('fv3',CORE); man=mod('mv3',MAN); exe=mod('ev3',EXE)

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=json.loads(REC.read_text());cls.c=json.loads(CON.read_text());cls.b=json.loads(BASE.read_text());cls.e=core.effective_contract(cls.r,ROOT)
    def test_frozen_science(self):
        for k in ('authorization','boundaries','failureSemantics','geometrySelection','modelAndEvaluation','runtimeIdentityRequired','sourceBindings'):self.assertEqual(self.e[k],self.b[k])
        be=copy.deepcopy(self.b['executionEnvelope']);ne=copy.deepcopy(self.e['executionEnvelope'])
        for x in (be,ne):x.pop('candidateScientificOrdinal');x.pop('reservedSeeds');x.pop('scientificOrdinalAllocated')
        self.assertEqual(be,ne)
    def test_ordinal25_refusal_is_pre_science_and_retired(self):
        o=self.r['ordinal25Refusal'];self.assertEqual(o['allocationMarkerCommentIds'],[5298386381,5298387062]);self.assertEqual(o['dispatchRunId'],31842973699);self.assertFalse(o['manifestEmitted']);self.assertFalse(o['matrixEmitted']);self.assertEqual(o['casesJobConclusion'],'skipped');self.assertEqual(o['syntaxCheckCount'],0);self.assertEqual(o['solverExecutionCount'],0);self.assertFalse(o['protectedValuesRead']);self.assertTrue(o['identityConsumed']);self.assertEqual(o['retiredSeeds'],list(range(2101000025,2101000049)))
    def test_logical_marker_and_atomic_lock_semantics(self):
        a=self.r['allocationSemantics'];self.assertTrue(a['atomicLockRequiredBeforeMarkerWrite']);self.assertTrue(a['allocationLockMustPointToExactAuthorizationHead']);self.assertTrue(a['duplicateByteIdenticalMarkerCommentsAllowed']);self.assertEqual(a['minimumExactMarkerCopies'],1);self.assertFalse(a['distinctMarkerBodiesForSameOrdinalAllowed']);self.assertTrue(a['dispatchRequiresLockAndLogicalMarker'])
        p=self.c['allocationProtocol'];self.assertTrue(p['atomicAllocationLockRefRequired']);self.assertEqual(p['markerCardinalitySemantics'],'ONE_LOGICAL_ALLOCATION_IDENTITY_ALLOWING_ONE_OR_MORE_BYTE_IDENTICAL_COMMENT_COPIES');self.assertEqual(p['minimumExactCopies'],1);self.assertTrue(p['anyDistinctOrdinal26AllocationBodyIsRefusal'])
    def test_ordinal26_identity_and_seeds(self):
        n=self.r['nextScientificIdentity'];self.assertEqual((n['scientificOrdinal'],n['authorizationBranch'],n['allocationLockBranch'],n['dispatchBranch']),(26,'authorization/level-b-v2-densified58-fresh-validation-ordinal26-v1','allocation/level-b-v2-densified58-fresh-validation-ordinal26-v1','dispatch/level-b-v2-densified58-fresh-validation-ordinal26-v1'));self.assertEqual(n['reservedSeeds'],list(range(2101000049,2101000073)))
        rows=core.expected_cases(self.e,self.r,ROOT);self.assertEqual(len(rows),24);self.assertEqual([x['seed'] for x in rows],list(range(2101000049,2101000073)));self.assertEqual(len({x['caseId'] for x in rows}),24);self.assertTrue(all(x['caseId'].startswith('v0070-o26-holdout-') for x in rows))
    def test_executor_v3_exact_branch(self):
        self.assertEqual(exe.BASE_EXECUTOR_GIT_BLOB_SHA,'5bf0477f0d5100dcb73da8027233e8415ce9021c');self.assertEqual(exe.BRANCH_RE.pattern,r'^dispatch/level-b-v2-densified58-fresh-validation-ordinal26-v1$');self.assertIsNotNone(exe.BRANCH_RE.fullmatch('dispatch/level-b-v2-densified58-fresh-validation-ordinal26-v1'));self.assertIsNone(exe.BRANCH_RE.fullmatch('dispatch/level-b-v2-densified58-fresh-validation-ordinal25-v1'))
    def test_manifest_is_inert_and_exact(self):
        m=man.build(ROOT,self.r);self.assertEqual((m['schemaVersion'],m['scientificOrdinalCandidate'],m['geometryCount'],m['caseCount'],m['configuredPhotonHistories']),(3,26,6,24,960_000_000));self.assertEqual([x['seed'] for x in m['cases']],list(range(2101000049,2101000073)));self.assertFalse(m['priorRefusals']['ordinal25ProtectedValuesRead']);self.assertEqual(m['priorRefusals']['ordinal25SolverExecutionCount'],0);self.assertTrue(all(v is False for v in m['closedUntilAuthorization'].values()));b=copy.deepcopy(m);h=b['manifestSha256'];b['manifestSha256']=None;self.assertEqual(h,man.canon(b))
    def test_review_surface_closed(self):
        self.assertTrue(all(v is False for v in self.r['reviewSurface'].values()));self.assertTrue(all(v is False for v in self.c['closedBoundaries'].values()))

if __name__=='__main__':unittest.main()
