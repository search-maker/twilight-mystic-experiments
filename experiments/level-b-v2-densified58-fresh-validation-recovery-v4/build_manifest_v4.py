#!/usr/bin/env python3
from __future__ import annotations
import argparse,copy,hashlib,importlib.util,json
from pathlib import Path
from typing import Any
CORE_REL=Path('review/level-b-v2-densified58-fresh-validation-recovery-v4/fresh_validation_v4.py');REC_REL=Path('review/level-b-v2-densified58-fresh-validation-recovery-v4/recovery-v4.json')
REQ=['case-result.json','input-resolved.txt','runtime-report.json','prepared.json','randomseed','syntax-stdout.txt','syntax-stderr.txt','solver-stdout.txt','solver-stderr.txt','mc.flx.spc','mc.flx.std.spc','mc.rad.spc','mc.rad.std.spc','mc.flx.is.spc','mc.is.spc','mc0.rad','mc0.rad.std']
class Refusal(RuntimeError):pass
def req(c,m):
    if not c:raise Refusal(m)
def canon(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def selfhash(v):b=copy.deepcopy(v);b['manifestSha256']=None;return canon(b)
def load(p):v=json.loads(p.read_text(encoding='utf-8'));req(isinstance(v,dict),f'object required: {p}');return v
def module(n,p):s=importlib.util.spec_from_file_location(n,p);req(s is not None and s.loader is not None,f'cannot load {p}');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def build(repo_root:Path,recovery:dict[str,Any])->dict[str,Any]:
    core=module('fv4_manifest',repo_root/CORE_REL);contract=core.effective_contract(recovery,repo_root);cases=[]
    for idx,c in enumerate(core.expected_cases(contract,recovery,repo_root),1):
        row=dict(c);row.update({'ordinalWithinValidation':idx,'role':'protected-holdout','executionStage':'FRESH_PROTECTED_HOLDOUT_AFTER_DENSIFIED58_MODEL_FREEZE','method':'alis','groupId':c['geometryId'],'expectedOutputGrid':{'nodeCount':8001,'startNm':380.0,'stopNm':780.0,'canonicalTokenGridSha256':'b5fae53c1cc88c7f3de6e3689bc25e4a36c54033d1d1bfd6169482f30cc5b477'}});cases.append(row)
    geoms=[]
    for s in contract['geometrySelection']['selectedGeometries']:geoms.append({'geometryId':s['geometryId'],**s['geometry'],'normalizedCoordinates':s['normalizedCoordinates'],'nearestTrainingDistance':s['nearestTrainingDistance'],'nearestOpenedOrdinal22GeometryDistance':s['nearestOpenedOrdinal22GeometryDistance'],'role':'protected-holdout','executionStage':'FRESH_PROTECTED_HOLDOUT_AFTER_DENSIFIED58_MODEL_FREEZE'})
    m={'schemaVersion':4,'manifestId':'level-b-v2-densified58-fresh-validation-execution-manifest-v1','manifestSha256':None,'status':'REVIEW_ONLY_FROZEN_FRESH_VALIDATION_MANIFEST_NO_AUTHORIZATION','governance':'MYSTIC-STATE-0070','stageId':'LEVEL_B_V2_DENSIFIED58_FRESH_PROTECTED_VALIDATION_V4_ORDINAL27_RECOVERY','trainingOnly':False,'sourceContractId':contract['contractId'],'sourceRecoveryId':recovery['recoveryId'],'scientificOrdinalCandidate':27,'priorRefusals':{'ordinal24DispatchRunId':31840757436,'ordinal25DispatchRunId':31842973699,'ordinal26DispatchRunId':31844855497,'ordinal24ProtectedValuesRead':False,'ordinal25ProtectedValuesRead':False,'ordinal26ProtectedValuesRead':False,'ordinal24SolverExecutionCount':0,'ordinal25SolverExecutionCount':0,'ordinal26SolverExecutionCount':0,'ordinal26PreflightArtifactId':9235548762,'ordinal26PreflightManifestZipMember':'tmp/o26-manifest.json'},'runtimeIdentityRequired':contract['runtimeIdentityRequired'],'runtimePackage':{'runner':'ubuntu-24.04','python':'3.12.4','exactPackageSpec':'rubin-libradtran=2.0.6=py312pl5321he9373c2_1','setupAction':'mamba-org/setup-micromamba@v2'},'frozenInputs':{'wavelengthDomainNm':[380.0,780.0],'molecularAbsorption':'crs','mcSpherical':'1D','albedo':0.15,'solarFlux':'atlas_plus_modtran','atmosphereProfile':'AFGLUS','observerElevationRepresentation':'ASCENDING_ATM_Z_GRID_BOTTOM_EQUALS_PHYSICAL_OBSERVER_ELEVATION','localSurfaceZoutKm':0.0,'altitudeShortcutAllowed':False,'mcElevationFileShortcutAllowed':False,'exactZeroPreserved':True,'epsilonSubstitutionAllowed':False},'geometryCount':6,'caseCount':24,'configuredPhotonHistories':960_000_000,'geometries':geoms,'cases':cases,'artifactContract':{'artifactNamePrefix':'level-b-v2-v0070-o27-case-','oneImmutableArtifactPerCase':True,'exactCaseArtifactUniverseRequired':True,'requiredMembers':REQ,'rawMemberSha256MapExact':True,'rawCaseResultSelfHashRequired':True,'githubZipDigestRequired':True,'fullSpectrumRequired':True,'fullSpectrumNodeCount':8001},'executionLimits':{'workflowAttemptExactly':1,'syntaxChecksPerCaseExactly':1,'solverExecutionsPerCaseExactly':1,'automaticRetryCountMaximum':0,'resumeAllowed':False,'githubRerunAllowed':False,'maxParallel':24},'closedUntilAuthorization':{'scientificOrdinalAllocated':False,'protectedHoldoutOpeningAuthorized':False,'holdoutValuesMayBeRead':False,'scientificSolverExecutionAuthorized':False,'productionPromotionAuthorized':False,'workerBLaneReactivated':False,'workerCLaneReactivated':False}}
    req([c['seed'] for c in cases]==list(range(2101000073,2101000097)),'seed order drift');req(len({c['caseId'] for c in cases})==24,'case collision');m['manifestSha256']=selfhash(m);return m

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',type=Path,required=True);ap.add_argument('--recovery',type=Path,default=REC_REL);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    try:m=build(a.repo_root,load(a.recovery));a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(m,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8');print(m['manifestSha256']);return 0
    except Exception as e:print(json.dumps({'status':'REFUSED','reason':str(e)},sort_keys=True));return 2
if __name__=='__main__':raise SystemExit(main())
