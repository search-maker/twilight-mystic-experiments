#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
PREREG = REPO_ROOT / 'review/full-spectrum-estimator-confirmation-v1/full-spectrum-estimator-confirmation-preregistration-v1.json'
CONTRACT = HERE / 'analysis-contract.v1.json'

def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module

an = load_module('confirmation_analysis_v1_under_test', HERE / 'analyze_confirmation_v1.py')
norm = load_module('confirmation_normalizer_v1_under_test', HERE / 'normalize_confirmation_results_v1.py')

class FakeV6:
    PHYSICAL_FINGERPRINTS = {'g': 'fp'}
    @staticmethod
    def verify_runtime(value): return None
    @staticmethod
    def parse_directives(raw): return {}
    @staticmethod
    def verify_exact_directive_surface(raw, case): return None
    @staticmethod
    def verify_input(value, case): return None
    @staticmethod
    def physical_fingerprint(raw): return 'fp'
    @staticmethod
    def channels(wl, rad):
        return {'photopicLuminanceCdM2': float(rad[0]), 'scotopicLuminanceScotCdM2': float(rad[0]) * 2.0, 'johnsonVEffectiveRadiance_mW_m2_nm_sr': float(rad[0]) * 3.0}

class FakeV7:
    @staticmethod
    def parse_spectrum_v7(raw, node_count, step):
        value = float(raw.decode().strip()); return [380.0, 780.0], [value, value]

def build_case_zip(path: Path, *, tamper_result_hash: bool = False):
    case = {'caseId':'case-1','candidateId':'cand-1','geometryId':'g','method':'alis-alt-importance','numericalMethod':{'mc_spectral_is_nm':500.0},'confirmationBlock':1,'replicate':1,'seed':1600000001,'photonHistories':100}
    required = ['case-result.json','input-resolved.txt','runtime-report.json','prepared.json','mc.rad.spc','mc.rad.std.spc']
    payload = {'input-resolved.txt':b'dummy-input\n','runtime-report.json':b'{}\n','mc.rad.spc':b'1.0','mc.rad.std.spc':b'0.1'}
    prepared = {'schemaVersion':1,'stageId':'full-spectrum-estimator-confirmation-v1-prepared','caseId':'case-1','candidateId':'cand-1','geometryId':'g','method':'alis-alt-importance','confirmationBlock':1,'seed':1600000001,'photonHistories':100,'inputResolvedSha256':norm.raw_sha(payload['input-resolved.txt']),'executionManifestSha256':norm.MANIFEST_SHA}
    payload['prepared.json']=(json.dumps(prepared,sort_keys=True,separators=(',',':'))+'\n').encode()
    raw_hashes={name:norm.raw_sha(raw) for name,raw in payload.items()}
    result={'schemaVersion':1,'stageId':'full-spectrum-estimator-confirmation-v1','status':'COMPLETED','caseId':'case-1','candidateId':'cand-1','confirmationBlock':1,'workflowRunAttempt':1,'syntaxCheckCount':1,'solverExecutionCount':1,'retryPerformed':False,'resumePerformed':False,'githubRerun':False,'syntaxExitCode':0,'solverExitCode':0,'syntaxTimedOut':False,'solverTimedOut':False,'seed':1600000001,'photonHistories':100,'inputResolvedSha256':raw_hashes['input-resolved.txt'],'runtimeReportRawSha256':raw_hashes['runtime-report.json'],'radianceOutputSha256':raw_hashes['mc.rad.spc'],'stdRadianceOutputSha256':raw_hashes['mc.rad.std.spc'],'rawMemberSha256ByBasename':raw_hashes}
    result['contentSha256']=norm.canon(result)
    if tamper_result_hash: result['contentSha256']='0'*64
    payload['case-result.json']=(json.dumps(result,sort_keys=True,separators=(',',':'))+'\n').encode()
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_STORED) as zf:
        for name in required: zf.writestr('case-1/'+name,payload[name])
    return case,required

def synthetic_evidence(prereg: dict, patterns: dict[str,list[float]]) -> dict:
    rows=[]
    for frozen in prereg['caseDesign']['cases']:
        values=patterns.get(frozen['candidateId'],[0.98,1.00,1.02,1.01]); value=values[frozen['confirmationBlock']-1]
        channels={'photopicLuminanceCdM2':value,'scotopicLuminanceScotCdM2':value*2.0,'johnsonVEffectiveRadiance_mW_m2_nm_sr':value*3.0}
        zero_map={k:v==0.0 for k,v in channels.items()}
        rows.append({'caseId':frozen['caseId'],'candidateId':frozen['candidateId'],'geometryId':frozen['geometryId'],'method':frozen['method'],'importanceCenterNm':frozen['importanceCenterNm'],'confirmationBlock':frozen['confirmationBlock'],'seed':frozen['seed'],'photonHistories':frozen['photonHistories'],'channels':channels,'zeroHitByChannel':zero_map,'anyPrimaryChannelZeroHit':any(zero_map.values())})
    evidence={'schemaVersion':1,'evidenceId':an.EVIDENCE_ID,'evidenceSha256':None,'status':'CONFIRMATION_EVIDENCE_NORMALIZED','analysisContractSha256':an.CONTRACT_SHA,'executionManifestSha256':an.MANIFEST_SHA,'acquisitionManifestSha256':'a'*64,'sourceRunId':123456,'sourceRunAttempt':1,'sourceOrdinal':17,'caseCount':24,'cases':rows,'primaryChannels':list(an.PRIMARY_CHANNELS),'outputGridAdapter':{'nodeCount':8001,'startNm':380.0,'stopNm':780.0,'nominalStepNm':0.05,'maxPointDeviationNm':0.00005},'exactZeroPreserved':True,'epsilonSubstitutionPerformed':False,'scientificSolverReexecutedDuringNormalization':False,'holdoutValuesRead':False}
    evidence['evidenceSha256']=an.self_hash(evidence,'evidenceSha256'); return evidence

class ConfirmationAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract=json.loads(CONTRACT.read_text()); cls.prereg=json.loads(PREREG.read_text())
        an.validate_contract(cls.contract); an.validate_prereg(cls.prereg); norm.validate_contract(cls.contract); norm.validate_code_identity()

    def test_contract_is_frozen_and_zero_downstream_authorization(self):
        self.assertEqual(self.contract['contractSha256'],an.CONTRACT_SHA); self.assertTrue(all(v is False for v in self.contract['downstreamBoundary'].values()))

    def test_confirmation_zip_parser_accepts_exact_attempt_one_case(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'case.zip'; case,required=build_case_zip(path)
            row=norm.normalize_case_zip(path,case,required,v6_module=FakeV6,v7_module=FakeV7)
            self.assertEqual(row['caseId'],'case-1'); self.assertFalse(row['anyPrimaryChannelZeroHit']); self.assertEqual(row['channels']['photopicLuminanceCdM2'],1.0)

    def test_confirmation_zip_parser_refuses_tampered_case_result_hash(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'case.zip'; case,required=build_case_zip(path,tamper_result_hash=True)
            with self.assertRaisesRegex(norm.NormalizationRefusal,'self-hash mismatch'): norm.normalize_case_zip(path,case,required,v6_module=FakeV6,v7_module=FakeV7)

    def test_target_classification(self):
        result=an.analyze(self.prereg,synthetic_evidence(self.prereg,{}),self.contract)
        self.assertEqual(result['classificationCounts']['CONFIRMED_AT_HISTORICAL_FINAL_TARGET'],6); self.assertFalse(result['automaticGlobalEstimatorSelectionPerformed'])

    def test_within_historical_maximum_classification(self):
        cid=self.prereg['candidates'][0]['candidateId']; result=an.analyze(self.prereg,synthetic_evidence(self.prereg,{cid:[0.88,0.96,1.04,1.12]}),self.contract)
        report=next(r for r in result['candidateReports'] if r['candidateId']==cid); self.assertEqual(report['classification'],'CONFIRMED_WITHIN_HISTORICAL_MAXIMUM')

    def test_precision_not_established_classification(self):
        cid=self.prereg['candidates'][0]['candidateId']; result=an.analyze(self.prereg,synthetic_evidence(self.prereg,{cid:[0.7,0.9,1.1,1.3]}),self.contract)
        report=next(r for r in result['candidateReports'] if r['candidateId']==cid); self.assertEqual(report['classification'],'CONFIRMATION_PRECISION_NOT_ESTABLISHED')

    def test_exact_zero_prevents_confirmation_without_epsilon(self):
        cid=self.prereg['candidates'][0]['candidateId']; result=an.analyze(self.prereg,synthetic_evidence(self.prereg,{cid:[0.0,1.0,1.0,1.0]}),self.contract)
        report=next(r for r in result['candidateReports'] if r['candidateId']==cid); self.assertEqual(report['classification'],'CONFIRMATION_PRECISION_NOT_ESTABLISHED'); self.assertTrue(report['statisticsByPrimaryChannel']['photopicLuminanceCdM2']['anyExactZero'])

    def test_screening_case_cannot_replace_confirmation_case(self):
        evidence=synthetic_evidence(self.prereg,{}); evidence['cases'][0]['caseId']=self.prereg['candidates'][0]['pilotCaseIds'][0]; evidence['evidenceSha256']=an.self_hash(evidence,'evidenceSha256')
        with self.assertRaisesRegex(an.AnalysisRefusal,'non-confirmation/missing cases'): an.analyze(self.prereg,evidence,self.contract)

    def test_duplicate_confirmation_block_refused(self):
        evidence=synthetic_evidence(self.prereg,{}); candidate=self.prereg['candidates'][0]['candidateId']; rows=[r for r in evidence['cases'] if r['candidateId']==candidate]; rows[1]['confirmationBlock']=1; evidence['evidenceSha256']=an.self_hash(evidence,'evidenceSha256')
        with self.assertRaisesRegex(an.AnalysisRefusal,'mismatch'): an.analyze(self.prereg,evidence,self.contract)

    def test_tampered_evidence_self_hash_refused(self):
        evidence=synthetic_evidence(self.prereg,{}); evidence['evidenceSha256']='0'*64
        with self.assertRaisesRegex(an.AnalysisRefusal,'self-hash mismatch'): an.analyze(self.prereg,evidence,self.contract)

if __name__=='__main__': unittest.main()
