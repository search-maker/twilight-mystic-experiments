from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'experiments/aerosol-scenario-interpolation-validation-v1'

def mod(name,path):
    s=importlib.util.spec_from_file_location(name,path); assert s and s.loader; m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

def blob(path):
    b=path.read_bytes(); return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()

def test_asiv_execution_core_review_boundary_and_transport():
    c=json.loads((STAGE/'execution-contract.review.json').read_text())
    assert c['status']=='FROZEN_REVIEW_ONLY_EXECUTION_CORE_NO_AUTHORIZATION'
    assert (c['expectedHoldoutCount'],c['expectedGroupCount'],c['expectedCaseCount'],c['configuredPhotonHistories'])==(8,24,120,2_400_000_000)
    for k in ('scientificOrdinalAllocated','authorizationCreated','dispatchCreated','scientificExecutionAuthorized','solverExecutionAuthorized','resultOpeningAuthorized','activeScientificWorkflowAddedByThisPackage'): assert c[k] is False
    assert c['frozenExternalBindings']['asivProtocol']['gitBlobSha1']=='27923f9d40d35b001c15b20b7909e3fcd12fd833'
    assert blob(ROOT/c['frozenExternalBindings']['asivProtocol']['path'])=='27923f9d40d35b001c15b20b7909e3fcd12fd833'
    t=mod('asiv_transport_test',STAGE/'execution_transport.py'); d=t.build_seedless_design(ROOT)
    assert d['status']=='REVIEW_ONLY_SEEDLESS_NON_RENDERABLE_NO_AUTHORIZATION'
    assert (d['holdoutCount'],d['groupCount'],d['caseCount'],d['statesPerGroup'])==(8,24,120,5)
    assert all(x['seed'] is None and x['renderable'] is False and x['executionAuthorized'] is False for x in d['groups'])
    assert all(x['seed'] is None and x['renderable'] is False and x['executionAuthorized'] is False for x in d['cases'])
    assert len({x['groupId'] for x in d['groups']})==24 and len({x['caseId'] for x in d['cases']})==120
    assert d['groups'][0]['groupId']=='asiv-holdout-01|replicate=1' and d['groups'][-1]['groupId']=='asiv-holdout-08|replicate=3'

def test_asiv_adapter_extends_only_aod_and_elevation_surface():
    a=mod('asiv_adapter_test',STAGE/'adapter.py'); a.verify_reference_bindings(ROOT)
    native=a.aerosol_block('native-rural-ss',0.35625)
    desert=a.aerosol_block('opac-desert-spheroids',0.09375)
    assert native==['aerosol_default','aerosol_haze 1','aerosol_vulcan 1','aerosol_season 1','aerosol_set_tau_at_wvl 550 0.356250']
    assert desert==['aerosol_default','aerosol_species_library OPAC','aerosol_species_file desert_spheroids','aerosol_set_tau_at_wvl 550 0.093750']
    assert blob(ROOT/'experiments/aerosol-full-phase-function-sensitivity-v1/adapter.py')=='3f68deb867c8975b00780fcbc503db95d068f338'
    assert blob(ROOT/'experiments/mystic-batch-v1/twilight_surrogate_tier1_execution_adapter.py')=='b00252709ca9ea41c6bf8b3ab59f8cdb8a2fc7bd'

def test_asiv_scalar_truth_requires_exact_120_and_crn_pairing():
    t=mod('asiv_transport_truth_test',STAGE/'execution_transport.py'); a=mod('asiv_analysis_truth_test',STAGE/'analysis.py'); d=t.build_seedless_design(ROOT)
    rows=[]
    state_factor={'native-rural-ss':1.0,'opac-continental-average':1.05,'opac-maritime-clean':0.97,'opac-desert':1.12,'opac-desert-spheroids':1.08}
    group_seed={g['groupId']:10_000_000+i for i,g in enumerate(d['groups'],start=1)}
    for c in d['cases']:
        f=state_factor[c['stateId']]; base=0.001*(1+0.01*c['replicate'])
        rows.append({**c,'seed':group_seed[c['groupId']],'status':'COMPLETED','workflowRunAttempt':1,'solverExecutionCount':1,'syntaxCheckCount':1,'retryPerformed':False,'resumePerformed':False,'githubRerun':False,'channels':{'photopicLuminanceCdM2':base*f,'scotopicLuminanceScotCdM2':base*2*f,'johnsonVEffectiveRadiance_mW_m2_nm_sr':base*0.2*f}})
    truth=a.build_scalar_truth(rows)
    assert truth['status']=='COMPLETE_EXACT_120_CASE_SCALAR_TRUTH'
    assert truth['finiteThreeReplicateStateVsNativeChannelRows']==96
    assert len(truth['holdouts'])==8 and all(len(h['replicates'])==3 for h in truth['holdouts'])
    assert all(h['stateVsNative']['continental_vs_native']['photopicLuminanceCdM2']['status']=='FINITE_THREE_REPLICATES' for h in truth['holdouts'])

def test_asiv_envelope_and_level_b_freeze_are_pre_result_and_no_spectral_pass_claim():
    c=json.loads((STAGE/'execution-contract.review.json').read_text())
    e=c['scenarioEnvelopeEndpointDefinition']; assert e['endpoints']==['minimum_log_contrast','maximum_log_contrast'] and e['aggregateEndpointCount']==48 and e['frozenBeforeHoldoutOpening'] is True
    assert c['resultOpeningGate']['scalarTruthRowCount']==96 and c['resultOpeningGate']['levelBTruthRowCount']==32
    assert c['resultOpeningGate']['spectralDiagnosticIsProductionPassClaim'] is False and c['resultOpeningGate']['epsilonSubstitutionPermitted'] is False
    js=(STAGE/'level_b_runner.mjs').read_text(); assert 'bb4cd0ff02159ecffe276022cec9d292c7a434a3' in js and 'meanAbsoluteDeltaErrorMag<=0.12' in js and 'fullSpectrum' not in js
