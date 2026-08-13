#!/usr/bin/env python3
from __future__ import annotations
import copy, importlib.util, json
from pathlib import Path

HERE=Path(__file__).resolve().parent
SPEC=importlib.util.spec_from_file_location('validator',HERE/'validate_train0014_fresh_training_admission_decision_v1.py')
assert SPEC and SPEC.loader
v=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(v)
DEC=HERE/'train-0014-fresh-training-admission-decision-v1.json'

def load(): return json.loads(DEC.read_text())
def rehash(d):
    d=copy.deepcopy(d); d['decisionSha256']=None; d['decisionSha256']=v.canon(d); return d
def must_refuse(d):
    try: v.validate_decision(d)
    except v.Refusal: return
    raise AssertionError('expected refusal')

def main():
    d=load(); v.validate_decision(d)
    # Hash-only corruption refuses.
    x=copy.deepcopy(d); x['decisionSha256']='0'*64; must_refuse(x)
    # Rehashed semantic mutations independently refuse.
    mutations=[]
    x=copy.deepcopy(d); x['decisionSemantics']['freshOrdinal18ValuesAdmittedAsTrainingLabels']=False; mutations.append(x)
    x=copy.deepcopy(d); x['decisionSemantics']['modelFittingAuthorized']=True; mutations.append(x)
    x=copy.deepcopy(d); x['decisionSemantics']['confirmationValuesAdmittedAsTrainingLabels']=True; mutations.append(x)
    x=copy.deepcopy(d); x['decisionSemantics']['historicalTrain0014ValuesCombinedWithFreshEvidence']=True; mutations.append(x)
    x=copy.deepcopy(d); x['frozenInterpretation']['sourceClassification']='FRESH_TRAINING_PRECISION_AT_FINAL_TARGET'; mutations.append(x)
    x=copy.deepcopy(d); x['frozenInterpretation']['exactZeroObserved']=True; mutations.append(x)
    x=copy.deepcopy(d); x['frozenInterpretation']['admittedTrainingLabel']['statistics']['scotopicLuminanceScotCdM2']['rsem']=0.0800001; mutations.append(x)
    x=copy.deepcopy(d); x['frozenInterpretation']['admittedTrainingLabel']['statistics']['photopicLuminanceCdM2']['mean']*=1.001; mutations.append(x)
    x=copy.deepcopy(d); x['frozenInterpretation']['admittedTrainingLabel']['sourceSeeds'][0]=1700000002; mutations.append(x)
    x=copy.deepcopy(d); x['frozenInterpretation']['admittedTrainingLabel']['confirmationValuesIncluded']=True; mutations.append(x)
    x=copy.deepcopy(d); x['frozenInterpretation']['admittedTrainingLabel']['historicalTrainingValuesIncluded']=True; mutations.append(x)
    x=copy.deepcopy(d); x['frozenInterpretation']['currentUniverseAfterDecision']['admittedTrainingGeometryCount']=26; mutations.append(x)
    x=copy.deepcopy(d); x['frozenInterpretation']['currentUniverseAfterDecision']['remainingContinuationRequiredGeometryIds']=[]; mutations.append(x)
    x=copy.deepcopy(d); x['nextBoundary']['freshScientificOrdinal19Allocated']=True; mutations.append(x)
    x=copy.deepcopy(d); x['sourceBindings']['salvageV2Artifact']['artifactId']=9166569025; mutations.append(x)
    x=copy.deepcopy(d); x['sourceBindings']['analysisSha256']='1'*64; mutations.append(x)
    for m in mutations: must_refuse(rehash(m))
    print(json.dumps({'status':'PASS','mutationRefusals':len(mutations),'decisionSha256':d['decisionSha256']},sort_keys=True))
if __name__=='__main__': main()
