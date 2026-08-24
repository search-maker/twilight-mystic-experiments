import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'review/aerosol-scenario-interpolation-validation-v1/selected-model-v1.json'
EVALUATOR=ROOT/'review/aerosol-scenario-interpolation-validation-v1/evaluate_selected_model_v1.py'
SELECTOR=ROOT/'review/asiv-v1-training-selector-implementation/select_training_model_v1.py'

def load(p): return json.loads(p.read_text(encoding='utf-8'))
def git_blob(p):
    b=p.read_bytes(); return hashlib.sha1(f'blob {len(b)}\0'.encode()+b).hexdigest()

def test_asiv_selected_model_identity_is_frozen_from_verified_selection():
    m=load(MANIFEST); e=m['selectionEvidence']; s=m['selectedModelIdentity']; r=m['reconstructionBindings']; b=m['scientificBoundary']
    assert m['status']=='SELECTED_MODEL_IDENTITY_FROZEN_FROM_VERIFIED_TRAINING_ONLY_SELECTION'
    assert e['workflowRunId']==32688714382 and e['workflowRunAttempt']==1
    assert e['artifactId']==9506522699
    assert e['artifactDigest']=='sha256:39feb85806f821adbf57228335928a5e0cc65f6a1f50f0120d2e630473d553e7'
    assert e['independentlyDownloadedArtifactSha256']=='39feb85806f821adbf57228335928a5e0cc65f6a1f50f0120d2e630473d553e7'
    assert s['selectedCandidateId']=='IDW_COS_4D-k8-p2' and s['family']=='IDW_COS_4D' and s['neighbors']==8 and s['power']==2.0
    assert s['eligibleCandidateCount']==16
    assert s['selectedModelCanonicalSha256']=='0b11a1691bfd2d9e3f073c786044bacedd3e9210bcb0660c76f21c34128a61af'
    assert all(s['trainingCvGateChecks'].values())
    metrics=s['trainingCvMetrics']
    assert metrics['aggregateMeanAbsoluteLogContrastError']<=0.12
    assert metrics['medianAbsoluteLogContrastError']<=0.10
    assert metrics['p90AbsoluteLogContrastError']<=0.30
    assert metrics['worstAbsoluteLogContrastError']<=0.55
    assert metrics['maxOver12FieldsAbsoluteMeanSignedBias']<=0.08
    assert metrics['meanErrorImprovementVsNearestCellBaselineFraction']>=0.10
    assert git_blob(SELECTOR)==r['selectorGitBlobSha1']=='c65183f959244abc851de45e609bfc5a9b38cd67'
    assert b=={'trainingValuesAlreadyOpenedOrdinal38':True,'freshHoldoutValuesOpened':False,'ordinal39Allocated':False,'scientificSeedAllocated':False,'solverExecutionPerformed':False,'productionAuthorized':False,'starsvisibilityMutationAuthorized':False,'retuningAfterSelectionAllowed':False}

def test_asiv_evaluator_is_fixed_selected_model_only_and_zero_science():
    text=EVALUATOR.read_text(encoding='utf-8')
    assert "IDW_COS_4D-k8-p2" in text
    assert "selected model reconstruction hash mismatch" in text
    assert "ordinal39Allocated':False" in text
    assert 'candidates()' not in text
    assert 'fit_ridge' not in text and 'QUADRATIC_RIDGE' not in text
    assert 'uvspec' not in text.lower() and 'mystic' not in text.lower() and 'libradtran' not in text.lower()
