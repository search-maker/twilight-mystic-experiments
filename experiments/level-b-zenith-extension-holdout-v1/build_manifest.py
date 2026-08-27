#!/usr/bin/env python3
from __future__ import annotations
import copy, hashlib, json
from pathlib import Path

PKG=Path(__file__).resolve().parent
EXPECTED='4a0a91e07c6a1f2c9f4870da70eda55664231e645d4050e78f72b46e22eb6394'
GEOMS=[
('zenith-holdout-01',4.7,81.25,20.0,200.0,.22),('zenith-holdout-02',7.8,83.75,155.0,2300.0,.12),
('zenith-holdout-03',3.6,86.25,100.0,1100.0,.35),('zenith-holdout-04',8.9,88.75,45.0,1800.0,.19),
('zenith-holdout-05',4.4,90.0,0.0,300.0,.31),('zenith-holdout-06',7.7,90.0,0.0,2200.0,.09),
('zenith-holdout-07',9.7,84.5,80.0,700.0,.27),('zenith-holdout-08',5.7,87.0,130.0,1400.0,.40)]

def canon(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def build():
 g=[{'geometryId':i,'sunDepressionDeg':s,'targetAltitudeDeg':a,'relativeAzimuthDeg':az,'observerElevationM':e,'aod550':o,'role':'protected-holdout'} for i,s,a,az,e,o in GEOMS]
 cases=[];seed=2240000001;ordinal=1
 for x in g:
  for b in range(1,5):
   cases.append({'ordinal':ordinal,'caseId':f"{x['geometryId']}-b{b}",'geometryId':x['geometryId'],'groupId':x['geometryId'],'role':'protected-holdout','block':b,'seed':seed,'photonHistories':40000000,'method':'alis','alisSpectralImportanceSamplingNm':550.0,'executionStage':'ZENITH_EXTENSION_PROTECTED_HOLDOUT','expectedOutputGrid':{'startNm':380.0,'stopNm':780.0,'stepNm':0.05,'nodeCount':8001}});seed+=1;ordinal+=1
 m={'schemaVersion':1,'manifestId':'level-b-zenith-extension-holdout-v1','status':'FROZEN_PROTECTED_HOLDOUT_EXECUTION_PACKAGE_MODEL_HASH_ALREADY_FROZEN','executionKey':'level-b-zenith-extension-holdout-v1:scientific:1','scientificExecution':True,'trainingOnly':False,'protectedHoldout':True,'sourceModelCanonicalSha256':'f9202b45a6540416b3cb021425b40da27e2c9adc966edd81d3608c55826a162a','sourceOldValidatedV3ModelCanonicalSha256':'c4902eb3c2ba67b12dc4ef2b9cefb67c5963a6abc104708a73b2aab5dd0163b9','sourceHoldoutDesignSha256':'2a4853910c4b3eac09bccb0995c92bb2427cae5eee1291663e47469517ffa05a','sourceTrainingModelPath':'review/level-b-zenith-extension-training-v1/training-only-model-v1.json','geometryCount':8,'caseCount':32,'configuredPhotonHistories':1280000000,'geometries':g,'cases':cases,'frozenInputs':{'albedo':0.15,'atmosphereProfile':'AFGLUS','mcSpherical':'1D','molecularAbsorption':'crs','solarFlux':'atlas_plus_modtran','wavelengthDomainNm':[380.0,780.0],'expectedOutputGrid':{'nodeCount':8001,'stepNm':0.05},'observerElevationRepresentation':'ASCENDING_ATM_Z_GRID_BOTTOM_EQUALS_PHYSICAL_OBSERVER_ELEVATION','localSurfaceZoutKm':0.0,'altitudeShortcutAllowed':False,'mcElevationFileShortcutAllowed':False,'exactZeroPreserved':True,'epsilonSubstitutionAllowed':False},'runtimeIdentityRequired':{'atmosphereSha256':'dab26290ed81c762ed0c607e5dc2d53393c1462a0c3a528bc5e3f5935191cfb5','libRadtranDataTreeSha256':'ad30b49177e9c84e46497d69faf0c75e466996b0d0003f1de210289ae9f847d7','libRadtranVersion':'2.0.6-MYSTIC','runtimeLockRawSha256':'3b5fbec964642b04c73a6423b3355dbcc4ba5e84f9614f6d74420491bacc20c5','uvspecHelpSha256':'868aea5af762d968f6f62c4e1472916d25232ed9cab5be112d753b0823d20548','uvspecSha256':'2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3'},'runtimePackage':{'exactPackageSpec':'rubin-libradtran=2.0.6=py312pl5321he9373c2_1','python':'3.12.4','runner':'ubuntu-24.04'},'executionLimits':{'workflowAttemptExactly':1,'automaticRetryCountMaximum':0,'githubRerunAllowed':False,'resumeAllowed':False,'solverExecutionsPerCaseExactly':1,'syntaxChecksPerCaseExactly':1,'perCaseTimeoutMinutes':30,'maxParallel':8},'freshHoldoutGates':{'primaryAggregateMeanAbsoluteLogErrorMax':0.25,'positiveChannelAbsoluteMeanSignedLogBiasMax':0.08,'positiveChannelMedianAbsoluteLogErrorMax':0.15,'positiveChannelWorstAbsoluteLogErrorMax':0.35,'positiveChannelWorstUncertaintyNormalizedErrorMax':3.0,'surrogateLogErrorBudgetOneSigma':0.12,'validatedSupportNearestDistanceMaxInclusive':0.75,'allEightFrozenHoldoutGeometriesMustBeSupported':True,'allGatesMustPass':True,'noRetuningAfterHoldoutOpening':True},'closedBoundaries':{'modelRefitAuthorizedByThisRun':False,'productionPromotionAuthorized':False,'supportExpansionAuthorizedByThisRun':False,'lunarBackgroundIncluded':False,'naturalBackgroundIncluded':False,'artificialBackgroundIncluded':False},'successDoesNotAuthorizeProduction':True,'successDoesNotAuthorizeSupportExpansion':True,'manifestSha256':None}
 x=copy.deepcopy(m);x['manifestSha256']=None;m['manifestSha256']=hashlib.sha256(canon(x)).hexdigest();assert m['manifestSha256']==EXPECTED
 return m
if __name__=='__main__':
 m=build();(PKG/'manifest.json').write_text(json.dumps(m,indent=2,sort_keys=True,allow_nan=False)+'\n');print(json.dumps({'manifestSha256':m['manifestSha256'],'caseCount':m['caseCount'],'configuredPhotonHistories':m['configuredPhotonHistories']},sort_keys=True))
