#!/usr/bin/env python3
from __future__ import annotations
import argparse, copy, hashlib, json
from pathlib import Path
from typing import Any

CAMPAIGN_ID='public-tier2-v1-core-campaign-contract-v1'
CAMPAIGN_SHA='5043929fdf13aaf90c9face0c380b514999a52a7226079807969a74469764f93'
IMPLEMENTATION_ID='public-tier2-v1-core-stage1-authorization-implementation-v1'
IMPLEMENTATION_SHA='e7d688754333d9b1d1a7266fec995e821f0c78abaa5631987e3fa8e2526c6fed'
MANIFEST_ID='public-tier2-v1-core-stage1-execution-manifest-v1'
STATUS='REVIEW_ONLY_FROZEN_STAGE1_EXECUTION_MANIFEST_NO_AUTHORIZATION'
RUNTIME={
 'libRadtranVersion':'2.0.6-MYSTIC',
 'uvspecSha256':'2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3',
 'uvspecHelpSha256':'868aea5af762d968f6f62c4e1472916d25232ed9cab5be112d753b0823d20548',
 'libRadtranDataTreeSha256':'ad30b49177e9c84e46497d69faf0c75e466996b0d0003f1de210289ae9f847d7',
 'atmosphereSha256':'dab26290ed81c762ed0c607e5dc2d53393c1462a0c3a528bc5e3f5935191cfb5',
 'runtimeLockRawSha256':'3b5fbec964642b04c73a6423b3355dbcc4ba5e84f9614f6d74420491bacc20c5',
}
REQUIRED_MEMBERS=[
 'case-result.json','input-resolved.txt','runtime-report.json','prepared.json','randomseed',
 'syntax-stdout.txt','syntax-stderr.txt','solver-stdout.txt','solver-stderr.txt',
 'mc.flx.spc','mc.flx.std.spc','mc.rad.spc','mc.rad.std.spc','mc.flx.is.spc','mc.is.spc','mc0.rad','mc0.rad.std'
]

class Refusal(RuntimeError): pass
def req(c:bool,m:str)->None:
    if not c: raise Refusal(m)
def canon(v:Any)->bytes: return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def selfhash(v:dict[str,Any],field:str)->str:
    x=copy.deepcopy(v); x[field]=None; return hashlib.sha256(canon(x)).hexdigest()
def load(p:Path)->dict[str,Any]:
    x=json.loads(p.read_text(encoding='utf-8')); req(isinstance(x,dict),f'object required: {p}'); return x

def expected_all_cases(campaign:dict[str,Any])->list[dict[str,Any]]:
    geoms=campaign.get('geometryManifest'); req(isinstance(geoms,list) and len(geoms)==25,'campaign geometry universe drift')
    out=[]; seed=1_900_000_001
    for g in sorted(geoms,key=lambda x:x['geometryId']):
        for block in range(1,5):
            out.append({
                'caseId':f"tier2-core-v1-{g['geometryId']}-b{block}",
                'geometryId':g['geometryId'],'role':g['role'],'executionStage':g['executionStage'],
                'block':block,'seed':seed,'photonHistories':g['photonHistoriesPerBlock'],
                'alisSpectralImportanceSamplingNm':g['alisSpectralImportanceSamplingNm'],
                'scientificValuesReadableBeforeRequiredFreeze':False if g['role']=='protected-holdout' else True,
            }); seed+=1
    return out

def build(campaign:dict[str,Any],implementation:dict[str,Any])->dict[str,Any]:
    req(campaign.get('campaignContractId')==CAMPAIGN_ID and campaign.get('contractSha256')==CAMPAIGN_SHA,'campaign identity drift')
    req(implementation.get('implementationId')==IMPLEMENTATION_ID and implementation.get('implementationSha256')==IMPLEMENTATION_SHA,'implementation identity drift')
    scope=implementation.get('stage1Scope') or {}; ids=scope.get('trainingGeometryIds')
    req(isinstance(ids,list) and len(ids)==19 and scope.get('trainingCaseCount')==76 and scope.get('configuredPhotonHistories')==2_120_000_000,'stage1 scope drift')
    req(scope.get('protectedHoldoutValuesReadable') is False and scope.get('protectedHoldoutExecutionAuthorized') is False,'holdout boundary drift')
    all_cases=expected_all_cases(campaign); req(len(all_cases)==100 and all_cases[0]['seed']==1_900_000_001 and all_cases[-1]['seed']==1_900_000_100,'full seed ledger drift')
    geoms=[copy.deepcopy(g) for g in campaign['geometryManifest'] if g['geometryId'] in set(ids)]
    req([g['geometryId'] for g in geoms]==ids and all(g['role']=='surrogate-training' and g['executionStage']=='TRAINING_ACQUISITION' for g in geoms),'training geometry selection drift')
    cases=[]
    for i,c in enumerate([x for x in all_cases if x['geometryId'] in set(ids)],start=1):
        row=copy.deepcopy(c); row['ordinalWithinStage1']=i; row['groupId']=row['geometryId']; row['method']='alis';
        row['expectedOutputGrid']={'nodeCount':8001,'startNm':380.0,'stepNm':0.05,'stopNm':780.0}
        cases.append(row)
    req(len(cases)==76 and len({c['seed'] for c in cases})==76,'stage1 case/seed count drift')
    req(hashlib.sha256(canon([{k:c[k] for k in ('caseId','geometryId','role','executionStage','block','seed','photonHistories','alisSpectralImportanceSamplingNm','scientificValuesReadableBeforeRequiredFreeze')} for c in cases])).hexdigest()=='8651ec7e9b430c418cc5717afa221513e2a4ebff55f2caefddf8730c20a1ee89','stage1 derived case hash drift')
    req(hashlib.sha256(canon([{'caseId':c['caseId'],'seed':c['seed']} for c in cases])).hexdigest()=='a5905c464fee13dc388ca57310f29fcd97379f7974a71cd50d745abe096b61ad','stage1 derived seed hash drift')
    req(sum(c['photonHistories'] for c in cases)==2_120_000_000,'stage1 photon accounting drift')
    full_seed_ledger=[{'caseId':c['caseId'],'seed':c['seed'],'role':c['role']} for c in all_cases]
    m={
      'schemaVersion':1,'manifestId':MANIFEST_ID,'manifestSha256':None,'status':STATUS,
      'governance':'MYSTIC-STATE-0067','stageId':'TRAINING_ACQUISITION','trainingOnly':True,
      'sourceBindings':{'campaignContractSha256':CAMPAIGN_SHA,'stage1ImplementationSha256':IMPLEMENTATION_SHA},
      'runtimeIdentityRequired':RUNTIME,
      'runtimePackage':{'runner':'ubuntu-24.04','python':'3.12.4','exactPackageSpec':'rubin-libradtran=2.0.6=py312pl5321he9373c2_1','setupAction':'mamba-org/setup-micromamba@v2'},
      'frozenInputs':{
        'wavelengthDomainNm':[380.0,780.0],'expectedOutputGrid':{'nodeCount':8001,'stepNm':0.05},
        'molecularAbsorption':'crs','mcSpherical':'1D','albedo':0.15,'solarFlux':'atlas_plus_modtran','atmosphereProfile':'AFGLUS',
        'observerElevationRepresentation':'ASCENDING_ATM_Z_GRID_BOTTOM_EQUALS_PHYSICAL_OBSERVER_ELEVATION','localSurfaceZoutKm':0.0,
        'altitudeShortcutAllowed':False,'mcElevationFileShortcutAllowed':False,'exactZeroPreserved':True,'epsilonSubstitutionAllowed':False,
      },
      'geometryCount':19,'caseCount':76,'configuredPhotonHistories':2_120_000_000,
      'geometries':geoms,'cases':cases,
      'fullCampaignSeedLedger':full_seed_ledger,
      'fullCampaignSeedLedgerSha256':hashlib.sha256(canon(full_seed_ledger)).hexdigest(),
      'artifactContract':{
        'artifactNamePrefix':'tier2-stage1-case-','oneImmutableArtifactPerCase':True,'exactCaseArtifactUniverseRequired':True,
        'requiredMembers':REQUIRED_MEMBERS,'rawMemberSha256MapExact':True,'rawCaseResultSelfHashRequired':True,
        'githubZipDigestRequired':True,'transportBindingBeforeByteOpening':True,'unexpectedExtraMembersRefused':True,
        'fullSpectrumRequired':True,'fullSpectrumWavelengthRangeNm':[380.0,780.0],'fullSpectrumNodeCount':8001,
      },
      'executionLimits':{'workflowAttemptExactly':1,'syntaxChecksPerCaseExactly':1,'solverExecutionsPerCaseExactly':1,'automaticRetryCountMaximum':0,'resumeAllowed':False,'githubRerunAllowed':False,'maxParallel':76},
      'closedBoundaries':{'authorizationIssued':False,'dispatchIssued':False,'scientificOrdinalAllocated':False,'protectedHoldoutOpeningAuthorized':False,'modelFittingAuthorized':False,'modelSelectionAuthorized':False,'productionPromotionAuthorized':False,'stage2Included':False},
    }
    m['manifestSha256']=selfhash(m,'manifestSha256'); return m

def main()->int:
    p=argparse.ArgumentParser(); p.add_argument('--campaign',type=Path,required=True); p.add_argument('--implementation',type=Path,required=True); p.add_argument('--output',type=Path,required=True); a=p.parse_args()
    try:
        m=build(load(a.campaign),load(a.implementation)); a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(m,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8'); print(m['manifestSha256']); return 0
    except Exception as e: print(json.dumps({'status':'REFUSED','reason':str(e)})); return 2
if __name__=='__main__': raise SystemExit(main())
