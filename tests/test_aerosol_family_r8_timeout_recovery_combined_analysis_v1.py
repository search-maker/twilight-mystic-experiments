from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
STAGE='aerosol-family-challenge-v2-r8-timeout-recovery-v1'
PKG=ROOT/'experiments'/STAGE
EVIDENCE=ROOT/'evidence'/STAGE
WORKFLOW=ROOT/'.github/workflows/aerosol-family-v2-r8-timeout-recovery-v1-combined-analysis.yml'

def load():
    p=PKG/'combined_aggregate.py'
    s=importlib.util.spec_from_file_location('afc2_combined_test',p)
    assert s and s.loader
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

c=load()

class CombinedAnalysisTests(unittest.TestCase):
    def synthetic(self):
        cases=[]
        fams=('rural','maritime','urban','tropospheric'); seasons=('spring-summer','fall-winter')
        affected=c.AFFECTED_GROUP
        for i in range(568):
            cases.append({'caseId':f'keep-{i}','groupId':f'g-{i}','seed':1000+i})
        for fam in fams:
            for sea in seasons:
                cases.append({
                    'caseId':f'{affected}-{fam}-{sea}','groupId':affected,
                    'analysisCellId':'afc2-d04-g06-late-opposite-high-aerosol-aod10','replicate':2,
                    'seed':798398324,'photonHistories':20000000,'aerosolFamily':fam,'aerosolSeason':sea,
                    'sunDepressionDeg':4.0,'targetAltitudeDeg':45.0,'relativeAzimuthDeg':180.0,
                    'observerElevationM':0.0,'aod550':0.1,'albedo':0.15,
                    'aerosolHazeCode':{'rural':1,'maritime':4,'urban':5,'tropospheric':6}[fam],
                    'aerosolSeasonCode':{'spring-summer':1,'fall-winter':2}[sea],
                    'aerosolVulcanCode':1,'numericalMethod':'reference-vroom-1nm',
                    'geometryId':'g06-late-opposite-high-aerosol','geometryTag':'opposite-solar',
                })
        source={'stageId':'aerosol-family-challenge-v2-r8','cases':cases,'groups':[]}
        rec={'stageId':'aerosol-family-challenge-v2-r8-timeout-recovery-v1','cases':[]}
        synthetic_fresh_seed=123456789
        for r in cases[-8:]:
            x=dict(r);x['seed']=synthetic_fresh_seed;x['sourceOrdinal34Seed']=798398324;rec['cases'].append(x)
        return source,rec,synthetic_fresh_seed

    def test_effective_replaces_only_group_seed_and_keeps_576(self):
        s,r,fresh=self.synthetic();e=c.build_effective_manifest(s,r)
        self.assertEqual(576,len(e['cases']))
        affected=[x for x in e['cases'] if x['groupId']==c.AFFECTED_GROUP]
        self.assertEqual(8,len(affected));self.assertEqual({fresh},{x['seed'] for x in affected})
        self.assertEqual(568,len([x for x in e['cases'] if x['groupId']!=c.AFFECTED_GROUP]))

    def test_rejects_partial_replacement(self):
        s,r,_=self.synthetic();r['cases'].pop()
        with self.assertRaises(c.CombinedRefusal): c.build_effective_manifest(s,r)

    def test_rejects_physics_change(self):
        s,r,_=self.synthetic();r['cases'][0]['aod550']=0.3
        with self.assertRaises(c.CombinedRefusal): c.build_effective_manifest(s,r)

    def test_run_binding_refuses_rerun(self):
        source={'id':c.SOURCE_RUN_ID,'run_attempt':1,'head_sha':c.SOURCE_HEAD}
        rec={'id':999,'run_attempt':2,'conclusion':'success','head_branch':'dispatch/aerosol-family-challenge-v2-r8-timeout-recovery-v1-ordinal-35'}
        with self.assertRaises(c.CombinedRefusal): c.validate_run_bindings(source,rec)

    def test_freeze_hashes_match_review_transport(self):
        f=json.loads((EVIDENCE/'combined-analysis.freeze.json').read_text())
        for key,path in (
            ('contractRawSha256',PKG/'combined-analysis.review.json'),
            ('implementationRawSha256',PKG/'combined_aggregate.py'),
            ('workflowRawSha256',WORKFLOW),
        ):
            self.assertEqual(f[key],hashlib.sha256(path.read_bytes()).hexdigest(),key)
        self.assertEqual(f['testRawSha256'],hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'testRawSha256')
        self.assertFalse(f['scientificResultOpeningAuthorizedAtFreeze'])
        self.assertTrue(f['conditionalResultOpeningRuleFrozen'])
        self.assertFalse(f['scientificSolverExecutionAuthorized'])

    def test_workflow_is_one_use_conditional_and_has_no_solver_runtime(self):
        text=WORKFLOW.read_text()
        self.assertIn('workflow_run:',text);self.assertIn('AFC2 R8 timeout recovery v1 scientific execution',text)
        self.assertIn("github.event.workflow_run.conclusion == 'success'",text);self.assertIn('github.event.workflow_run.run_attempt == 1',text)
        self.assertIn('Refuse duplicate combined-analysis identity before opening results',text)
        self.assertNotIn('setup-micromamba@',text);self.assertNotIn('uvspec',text);self.assertNotIn('--allow-execution',text)
        self.assertIn('GITHUB_RUN_ATTEMPT',text);self.assertIn('COMPLETE_EXACT_8_FRESH_REPLACEMENT_CASE_ARTIFACT_UNIVERSE',text)
        self.assertNotIn('workflow_dispatch:',text)

    def test_contract_freezes_conditional_opening_before_results(self):
        d=json.loads((PKG/'combined-analysis.review.json').read_text())
        self.assertFalse(d['scientificResultOpeningAuthorizedAtFreeze'])
        t=d['scientificResultOpeningTransition']
        self.assertTrue(t['automaticAfterCondition']);self.assertEqual('workflow_run_completed',t['trigger'])
        self.assertEqual(1,t['requiredRecoveryRunAttempt']);self.assertEqual('success',t['requiredRecoveryConclusion'])
        self.assertEqual('COMPLETE_EXACT_8_FRESH_REPLACEMENT_CASE_ARTIFACT_UNIVERSE',t['requiredAcquisitionStatus'])

if __name__=='__main__': unittest.main()
