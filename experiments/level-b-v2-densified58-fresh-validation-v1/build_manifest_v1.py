#!/usr/bin/env python3
from __future__ import annotations
import argparse, copy, hashlib, importlib.util, json
from pathlib import Path

CONTRACT_REL=Path('review/level-b-v2-densified58-fresh-validation-v1/contract-v1.json')
CORE_REL=Path('review/level-b-v2-densified58-fresh-validation-implementation-v1/fresh_validation_v1.py')
REQUIRED=['case-result.json','input-resolved.txt','runtime-report.json','prepared.json','randomseed','syntax-stdout.txt','syntax-stderr.txt','solver-stdout.txt','solver-stderr.txt','mc.flx.spc','mc.flx.std.spc','mc.rad.spc','mc.rad.std.spc','mc.flx.is.spc','mc.is.spc','mc0.rad','mc0.rad.std']

class Refusal(RuntimeError): pass
def req(c,m):
    if not c: raise Refusal(m)
def canon(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def selfhash(v):
    x=copy.deepcopy(v); x['manifestSha256']=None; return canon(x)
def load(p):
    x=json.loads(Path(p).read_text()); req(isinstance(x,dict),'object required'); return x
def module(path):
    s=importlib.util.spec_from_file_location('fresh_validation_core',path); req(s is not None and s.loader is not None,'core load failure'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

def build(root:Path,contract:dict):
    core=module(root/CORE_REL); core.validate_contract(contract)
    cases=[]
    for i,c in enumerate(core.expected_cases(contract),1):
        row=dict(c); row.update({'ordinalWithinValidation':i,'role':'protected-holdout','executionStage':'FRESH_PROTECTED_HOLDOUT_AFTER_DENSIFIED58_MODEL_FREEZE','method':'alis','groupId':c['geometryId'],'expectedOutputGrid':{'nodeCount':8001,'startNm':380.0,'stopNm':780.0,'canonicalTokenGridSha256':'b5fae53c1cc88c7f3de6e3689bc25e4a36c54033d1d1bfd6169482f30cc5b477'}}); cases.append(row)
    geoms=[]
    for g in contract['geometrySelection']['selectedGeometries']:
        row={'geometryId':g['geometryId'],**g['geometry'],'normalizedCoordinates':g['normalizedCoordinates'],'nearestTrainingDistance':g['nearestTrainingDistance'],'nearestOpenedOrdinal22GeometryDistance':g['nearestOpenedOrdinal22GeometryDistance'],'role':'protected-holdout','executionStage':'FRESH_PROTECTED_HOLDOUT_AFTER_DENSIFIED58_MODEL_FREEZE'}; geoms.append(row)
    m={'schemaVersion':1,'manifestId':'level-b-v2-densified58-fresh-validation-execution-manifest-v1','manifestSha256':None,'status':'REVIEW_ONLY_FROZEN_FRESH_VALIDATION_MANIFEST_NO_AUTHORIZATION','governance':'MYSTIC-STATE-0070','stageId':'LEVEL_B_V2_DENSIFIED58_FRESH_PROTECTED_VALIDATION_V1','trainingOnly':False,'sourceContractId':contract['contractId'],'runtimeIdentityRequired':contract['runtimeIdentityRequired'],'runtimePackage':{'runner':'ubuntu-24.04','python':'3.12.4','exactPackageSpec':'rubin-libradtran=2.0.6=py312pl5321he9373c2_1','setupAction':'mamba-org/setup-micromamba@v2'},'frozenInputs':{'wavelengthDomainNm':[380.0,780.0],'molecularAbsorption':'crs','mcSpherical':'1D','albedo':0.15,'solarFlux':'atlas_plus_modtran','atmosphereProfile':'AFGLUS','observerElevationRepresentation':'ASCENDING_ATM_Z_GRID_BOTTOM_EQUALS_PHYSICAL_OBSERVER_ELEVATION','localSurfaceZoutKm':0.0,'altitudeShortcutAllowed':False,'mcElevationFileShortcutAllowed':False,'exactZeroPreserved':True,'epsilonSubstitutionAllowed':False},'geometryCount':6,'caseCount':24,'configuredPhotonHistories':960000000,'geometries':geoms,'cases':cases,'artifactContract':{'artifactNamePrefix':'level-b-v2-v0070-case-','oneImmutableArtifactPerCase':True,'exactCaseArtifactUniverseRequired':True,'requiredMembers':REQUIRED,'rawMemberSha256MapExact':True,'rawCaseResultSelfHashRequired':True,'githubZipDigestRequired':True,'fullSpectrumRequired':True,'fullSpectrumNodeCount':8001},'executionLimits':{'workflowAttemptExactly':1,'syntaxChecksPerCaseExactly':1,'solverExecutionsPerCaseExactly':1,'automaticRetryCountMaximum':0,'resumeAllowed':False,'githubRerunAllowed':False,'maxParallel':24},'closedUntilAuthorization':{'scientificOrdinalAllocated':False,'protectedHoldoutOpeningAuthorized':False,'holdoutValuesMayBeRead':False,'scientificSolverExecutionAuthorized':False,'productionPromotionAuthorized':False,'workerBLaneReactivated':False,'workerCLaneReactivated':False}}
    m['manifestSha256']=selfhash(m); return m

def main():
    p=argparse.ArgumentParser(); p.add_argument('--repo-root',type=Path,required=True); p.add_argument('--contract',type=Path,required=True); p.add_argument('--output',type=Path,required=True); a=p.parse_args()
    try:
        m=build(a.repo_root,load(a.contract)); a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(m,indent=2,sort_keys=True,allow_nan=False)+'\n'); print(m['manifestSha256']); return 0
    except Exception as e:
        print(json.dumps({'status':'REFUSED','reason':str(e)},sort_keys=True)); return 2
if __name__=='__main__': raise SystemExit(main())
