import hashlib
import importlib.util
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CONTRACT=ROOT/'review/asiv-v1-training-selector-implementation/selector-contract-v1.json'
SELECTOR=ROOT/'review/asiv-v1-training-selector-implementation/select_training_model_v1.py'
PROTOCOL=ROOT/'review/aerosol-scenario-interpolation-validation-v1/protocol.review.json'
WORKFLOW=ROOT/'.github/workflows/asiv-v1-training-selection.yml'

def load(p): return json.loads(p.read_text(encoding='utf-8'))
def git_blob(p):
    b=p.read_bytes(); return hashlib.sha1(f'blob {len(b)}\0'.encode()+b).hexdigest()
def module():
    s=importlib.util.spec_from_file_location('asiv_selector',SELECTOR); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

def test_asiv_selector_contract_binds_merged_protocol_and_is_zero_science():
    c=load(CONTRACT); p=load(PROTOCOL)
    assert c['status']=='REVIEW_ONLY_IMPLEMENTATION_NO_TRAINING_VALUES_OPENED_BY_REVIEW_NO_SCIENTIFIC_EXECUTION'
    assert c['sourceMainAtFreeze']=='c4a497778edc7d9888c0fe69139164c6125cabff'
    assert git_blob(PROTOCOL)==c['sourceBindings']['asivProtocol']['gitBlobSha1']=='27923f9d40d35b001c15b20b7909e3fcd12fd833'
    bind=c['sourceBindings']['afpfRecoveryArtifact']
    assert bind['artifactId']==9504775903
    assert bind['artifactDigest']=='sha256:fa824ff1e693682ee5b89aa108259452823e1f8f10818d82c34f5d01ba9dac0a'
    assert bind['analysisIndexRawSha256']=='e19b44b875d4c3e8082cdf89062d068c68e05ef1a896068ec59e48a80b9f4547'
    assert bind['analysisIndexCanonicalSha256']=='b7259c9675fc7f0f592218b37a69416a26518879400669775c2c0551bf3e013d'
    sel=p['trainingOnlyInterpolatorSelection']
    assert c['candidateSet']['candidateCount']==17
    assert c['candidateSet']['sameGlobalSpecForAll12Fields'] is True
    assert sel['crossValidation']=='EXACT_LEAVE_ONE_AFPF_ANALYSIS_CELL_OUT_24_FOLDS'
    assert c['eligibilityFromMergedProtocol']==sel['trainingEligibilityGates']
    assert c['authorization']=={'ordinal39Allocated':False,'scientificExecutionAuthorized':False,'solverExecutionAuthorized':False,'holdoutExecutionAuthorized':False,'productionAuthorized':False,'starsvisibilityMutationAuthorized':False}
    text=WORKFLOW.read_text(encoding='utf-8')
    assert 'workflow_dispatch:' not in text
    assert 'uvspec' not in text.lower() and 'mystic' not in text.lower() and 'libradtran' not in text.lower()
    assert 'GITHUB_RUN_ATTEMPT' in text and 'status/asiv-v1-training-selection-v1' in text

def test_asiv_selector_candidate_set_quantile_and_synthetic_models_are_deterministic():
    m=module(); specs=m.candidates()
    assert len(specs)==17 and len({x['candidateId'] for x in specs})==17
    assert m.qlinear([0,10],0.9)==9.0
    assert m.qlinear([0,1,2,3],0.5)==1.5
    # IDW exact-hit semantics and deterministic distance/cell-id ordering.
    train=[]
    for i,x in enumerate((0.0,0.25,0.5,0.75,1.0)):
        train.append({'cellId':f'c{i}','coord':(x,0.0,0.0,0.0),'target':[x+j*0.01 for j in range(12)]})
    model=m.fit_idw(train,4,1.0)
    assert m.pred_idw(model,(0.5,0.0,0.0,0.0))==train[2]['target']
    pred=m.pred_idw(model,(0.6,0.0,0.0,0.0)); assert len(pred)==12 and all(math.isfinite(x) for x in pred)
    # Ridge must recover a deterministic quadratic surface to tight numerical tolerance.
    ridge_train=[]
    for i in range(24):
        s=(i%4)/3; a=((i//4)%3)/2; c=((i//12)%2); o=((i*5)%7)/6
        coord=(s,a,c,o); b=m.basis4(coord)
        target=[]
        for k in range(12): target.append(sum((j+1)*(k+1)*1e-4*b[j] for j in range(15)))
        ridge_train.append({'cellId':f'r{i:02d}','coord':coord,'target':target})
    r=m.fit_ridge(ridge_train,1e-6); y=m.pred_ridge(r,(0.2,0.4,0.6,0.8)); assert len(y)==12 and all(math.isfinite(x) for x in y)

def test_asiv_selector_metrics_and_ranking_follow_frozen_protocol():
    m=module(); truth=[[0.1*j for j in range(12)] for _ in range(3)]; pred=[[x+0.01 for x in row] for row in truth]
    near=[[x+0.05 for x in row] for row in truth]; zero=[[0.0]*12 for _ in truth]
    met=m.metrics(pred,truth,near,zero)
    assert abs(met['aggregateMeanAbsoluteLogContrastError']-0.01)<1e-12
    assert met['meanErrorImprovementVsNearestCellBaselineFraction']>0.79
    c=load(CONTRACT); ok,checks=m.eligible(met,c['eligibilityFromMergedProtocol']); assert ok and all(checks.values())
