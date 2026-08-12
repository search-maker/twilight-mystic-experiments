#!/usr/bin/env python3
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent; sys.path.insert(0,str(HERE))
from common_v1 import *
from preauthorization_guard_v1 import build

def main():
    c=load(HERE/'transport-contract.v1.json')
    branches=[{'name':'dispatch/full-spectrum-estimator-confirmation-v1-ordinal17'}]
    runs=[{'id':1,'event':'push','head_branch':'dispatch/full-spectrum-estimator-confirmation-v1-ordinal17','name':'x','display_title':'x'}]
    arts=[]
    r=build(c,'train0014',branches,runs,arts)
    assert r['latestConsumedScientificOrdinal']==17 and r['nextAvailableScientificOrdinalIfAllocatedLater']==18
    assert r['authorizationOrdinalAllocated'] is False and r['scientificExecutionAuthorized'] is False
    bad=branches+[{'name':'dispatch/training-continuation-train0014-ordinal18'}]
    try:
        build(c,'train0014',bad,runs,arts); raise AssertionError('branch collision accepted')
    except Refusal: pass
    badruns=runs+[{'id':99,'event':'push','head_branch':'dispatch/training-continuation-train0037-ordinal19','name':'Training continuation train0037','display_title':'x'}]
    try:
        build(c,'train0037',branches,badruns,arts); raise AssertionError('run collision accepted')
    except Refusal: pass
    print('PASS: preauthorization preview/refusal tests')
if __name__=='__main__': main()
