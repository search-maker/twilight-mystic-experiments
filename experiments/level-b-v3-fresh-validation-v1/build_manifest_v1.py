#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

CONTRACT_REL = Path('review/level-b-v3-fresh-validation-implementation-v1/contract-v1.json')
REQUIRED_MEMBERS = [
    'case-result.json','input-resolved.txt','runtime-report.json','prepared.json','randomseed',
    'syntax-stdout.txt','syntax-stderr.txt','solver-stdout.txt','solver-stderr.txt',
    'mc.flx.spc','mc.flx.std.spc','mc.rad.spc','mc.rad.std.spc','mc.flx.is.spc','mc.is.spc','mc0.rad','mc0.rad.std'
]

class Refusal(RuntimeError): pass

def req(c: bool, m: str) -> None:
    if not c: raise Refusal(m)

def load(path: Path) -> dict[str, Any]:
    v=json.loads(path.read_text(encoding='utf-8')); req(isinstance(v,dict),f'object required: {path}'); return v

def canon(v: Any) -> str:
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def selfhash(v: dict[str, Any]) -> str:
    b=copy.deepcopy(v); b['manifestSha256']=None; return canon(b)

def build(repo_root: Path) -> dict[str, Any]:
    p=load(repo_root/CONTRACT_REL)
    req((p.get('governance'),p.get('contractId'))==('MYSTIC-STATE-0072','level-b-v3-fresh-protected-validation-ordinal28-v1'),'contract identity drift')
    env=p['executionEnvelope']; rows=p['geometrySelection']['selectedGeometries']
    req(len(rows)==6 and env['reservedSeeds']==list(range(2110000001,2110000025)),'source/seed drift')
    cases=[]; cursor=0
    for g in rows:
        for block in range(1,5):
            cases.append({
                'caseId':f"{g['geometryId']}-b{block}",'geometryId':g['geometryId'],'block':block,
                'seed':env['reservedSeeds'][cursor],'photonHistories':40_000_000,
                'alisSpectralImportanceSamplingNm':550.0,'ordinalWithinValidation':cursor+1,
                'role':'protected-holdout','executionStage':'FRESH_PROTECTED_HOLDOUT_AFTER_LEVEL_B_V3_MODEL_FREEZE','method':'alis',
                'expectedOutputGrid':{'nodeCount':8001,'startNm':380.0,'stopNm':780.0,'canonicalTokenGridSha256':env['expectedOutputGrid']['canonicalTokenGridSha256']}
            }); cursor+=1
    geoms=[]
    for g in rows:
        geoms.append({'geometryId':g['geometryId'],**g['geometry'],'sourceId':g['sourceId'],'normalizedCoordinates':g['normalizedCoordinates'],'nearestTrainingDistance':g['nearestTrainingDistance'],'role':'protected-holdout','executionStage':'FRESH_PROTECTED_HOLDOUT_AFTER_LEVEL_B_V3_MODEL_FREEZE'})
    m={
      'schemaVersion':1,'manifestId':'level-b-v3-fresh-validation-execution-manifest-v1','manifestSha256':None,
      'status':'REVIEW_ONLY_FROZEN_FRESH_VALIDATION_MANIFEST_NO_AUTHORIZATION','governance':'MYSTIC-STATE-0072',
      'stageId':'LEVEL_B_V3_FRESH_PROTECTED_VALIDATION_ORDINAL28_V1','trainingOnly':False,
      'sourceContractId':p['contractId'],'scientificOrdinalCandidate':28,
      'runtimeIdentityRequired':p['runtimeIdentityRequired'],
      'runtimePackage':{'runner':'ubuntu-24.04','python':'3.12.4','exactPackageSpec':p['runtimeIdentityRequired']['exactPackageSpec'],'setupAction':'mamba-org/setup-micromamba@v2'},
      'frozenInputs':{'wavelengthDomainNm':[380.0,780.0],'molecularAbsorption':'crs','mcSpherical':'1D','albedo':0.15,'solarFlux':'atlas_plus_modtran','atmosphereProfile':'AFGLUS','observerElevationRepresentation':'ASCENDING_ATM_Z_GRID_BOTTOM_EQUALS_PHYSICAL_OBSERVER_ELEVATION','localSurfaceZoutKm':0.0,'altitudeShortcutAllowed':False,'mcElevationFileShortcutAllowed':False,'exactZeroPreserved':True,'epsilonSubstitutionAllowed':False},
      'geometryCount':6,'caseCount':24,'configuredPhotonHistories':960_000_000,'geometries':geoms,'cases':cases,
      'artifactContract':{'artifactNamePrefix':'level-b-v3-o28-case-','oneImmutableArtifactPerCase':True,'exactCaseArtifactUniverseRequired':True,'requiredMembers':REQUIRED_MEMBERS,'rawMemberSha256MapExact':True,'rawCaseResultSelfHashRequired':True,'githubZipDigestRequired':True,'fullSpectrumRequired':True,'fullSpectrumNodeCount':8001},
      'executionLimits':{'workflowAttemptExactly':1,'syntaxChecksPerCaseExactly':1,'solverExecutionsPerCaseExactly':1,'automaticRetryCountMaximum':0,'resumeAllowed':False,'githubRerunAllowed':False,'maxParallel':24},
      'closedUntilAuthorization':{'scientificOrdinalAllocated':False,'protectedHoldoutOpeningAuthorized':False,'holdoutValuesMayBeRead':False,'scientificSolverExecutionAuthorized':False,'productionPromotionAuthorized':False,'workerBLaneReactivated':False,'workerCLaneReactivated':False}
    }
    req([c['seed'] for c in cases]==list(range(2110000001,2110000025)),'manifest seed order drift')
    req(len({c['caseId'] for c in cases})==24,'case id collision')
    m['manifestSha256']=selfhash(m); return m

def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',type=Path,required=True); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    try:
        m=build(a.repo_root); a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(m,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8'); print(m['manifestSha256']); return 0
    except Exception as e:
        print(json.dumps({'status':'REFUSED','reason':str(e)},sort_keys=True)); return 2
if __name__=='__main__': raise SystemExit(main())
