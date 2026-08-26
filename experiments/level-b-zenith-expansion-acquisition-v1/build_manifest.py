from __future__ import annotations
import copy, hashlib, json
from pathlib import Path

RUNTIME={
 'libRadtranVersion':'2.0.6-MYSTIC',
 'uvspecSha256':'2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3',
 'uvspecHelpSha256':'868aea5af762d968f6f62c4e1472916d25232ed9cab5be112d753b0823d20548',
 'libRadtranDataTreeSha256':'ad30b49177e9c84e46497d69faf0c75e466996b0d0003f1de210289ae9f847d7',
 'atmosphereSha256':'dab26290ed81c762ed0c607e5dc2d53393c1462a0c3a528bc5e3f5935191cfb5',
 'runtimeLockRawSha256':'3b5fbec964642b04c73a6423b3355dbcc4ba5e84f9614f6d74420491bacc20c5',
}

GEOMETRIES=[
 {'geometryId':'zenith-train-80-a','role':'boundary-training','sunDepressionDeg':7.5,'targetAltitudeDeg':80.0,'relativeAzimuthDeg':37.44,'observerElevationM':1938.776,'aod550':0.183058,'parentSupportAltitudeDeg':77.22222254539803,'parentSupportDistanceInOldCoordinates':0.037037032728026276},
 {'geometryId':'zenith-train-80-b','role':'boundary-training','sunDepressionDeg':5.25,'targetAltitudeDeg':80.0,'relativeAzimuthDeg':167.04,'observerElevationM':1020.408,'aod550':0.06157,'parentSupportAltitudeDeg':75.37037098141697,'parentSupportDistanceInOldCoordinates':0.06172838691444038},
 {'geometryId':'zenith-train-80-c','role':'boundary-training','sunDepressionDeg':10.5,'targetAltitudeDeg':80.0,'relativeAzimuthDeg':93.6,'observerElevationM':1173.469,'aod550':0.243802,'parentSupportAltitudeDeg':74.44444474016524,'parentSupportDistanceInOldCoordinates':0.07407407013113021},
 {'geometryId':'zenith-train-80-d','role':'boundary-training','sunDepressionDeg':9.75,'targetAltitudeDeg':80.0,'relativeAzimuthDeg':89.28,'observerElevationM':2201.166,'aod550':0.28719,'parentSupportAltitudeDeg':73.51851828923961,'parentSupportDistanceInOldCoordinates':0.08641975614347186},
 {'geometryId':'zenith-train-825-a','role':'zenith-extension-training','sunDepressionDeg':3.4,'targetAltitudeDeg':82.5,'relativeAzimuthDeg':45.0,'observerElevationM':1500.0,'aod550':0.24},
 {'geometryId':'zenith-train-825-b','role':'zenith-extension-training','sunDepressionDeg':6.6,'targetAltitudeDeg':82.5,'relativeAzimuthDeg':105.0,'observerElevationM':500.0,'aod550':0.08},
 {'geometryId':'zenith-train-825-c','role':'zenith-extension-training','sunDepressionDeg':9.4,'targetAltitudeDeg':82.5,'relativeAzimuthDeg':150.0,'observerElevationM':2250.0,'aod550':0.34},
 {'geometryId':'zenith-train-85-a','role':'zenith-extension-training','sunDepressionDeg':2.9,'targetAltitudeDeg':85.0,'relativeAzimuthDeg':90.0,'observerElevationM':2500.0,'aod550':0.20},
 {'geometryId':'zenith-train-85-b','role':'zenith-extension-training','sunDepressionDeg':5.0,'targetAltitudeDeg':85.0,'relativeAzimuthDeg':30.0,'observerElevationM':750.0,'aod550':0.38},
 {'geometryId':'zenith-train-85-c','role':'zenith-extension-training','sunDepressionDeg':8.6,'targetAltitudeDeg':85.0,'relativeAzimuthDeg':120.0,'observerElevationM':1750.0,'aod550':0.11},
 {'geometryId':'zenith-train-875-a','role':'zenith-extension-training','sunDepressionDeg':4.0,'targetAltitudeDeg':87.5,'relativeAzimuthDeg':160.0,'observerElevationM':0.0,'aod550':0.30},
 {'geometryId':'zenith-train-875-b','role':'zenith-extension-training','sunDepressionDeg':6.9,'targetAltitudeDeg':87.5,'relativeAzimuthDeg':60.0,'observerElevationM':1250.0,'aod550':0.14},
 {'geometryId':'zenith-train-875-c','role':'zenith-extension-training','sunDepressionDeg':10.0,'targetAltitudeDeg':87.5,'relativeAzimuthDeg':110.0,'observerElevationM':2000.0,'aod550':0.36},
 {'geometryId':'zenith-train-90-a','role':'zenith-training','sunDepressionDeg':3.2,'targetAltitudeDeg':90.0,'relativeAzimuthDeg':0.0,'observerElevationM':500.0,'aod550':0.18},
 {'geometryId':'zenith-train-90-b','role':'zenith-training','sunDepressionDeg':6.0,'targetAltitudeDeg':90.0,'relativeAzimuthDeg':0.0,'observerElevationM':1500.0,'aod550':0.08},
 {'geometryId':'zenith-train-90-c','role':'zenith-training','sunDepressionDeg':9.2,'targetAltitudeDeg':90.0,'relativeAzimuthDeg':0.0,'observerElevationM':2500.0,'aod550':0.28},
 {'geometryId':'zenith-invariance-90-az90','role':'zenith-azimuth-invariance-diagnostic','sunDepressionDeg':6.0,'targetAltitudeDeg':90.0,'relativeAzimuthDeg':90.0,'observerElevationM':1500.0,'aod550':0.08,'pairedWith':'zenith-train-90-b'},
 {'geometryId':'zenith-invariance-90-az180','role':'zenith-azimuth-invariance-diagnostic','sunDepressionDeg':6.0,'targetAltitudeDeg':90.0,'relativeAzimuthDeg':180.0,'observerElevationM':1500.0,'aod550':0.08,'pairedWith':'zenith-train-90-b'},
]

HOLDOUTS=[
 {'geometryId':'zenith-holdout-01','sunDepressionDeg':4.7,'targetAltitudeDeg':81.25,'relativeAzimuthDeg':20.0,'observerElevationM':200.0,'aod550':0.22},
 {'geometryId':'zenith-holdout-02','sunDepressionDeg':7.8,'targetAltitudeDeg':83.75,'relativeAzimuthDeg':155.0,'observerElevationM':2300.0,'aod550':0.12},
 {'geometryId':'zenith-holdout-03','sunDepressionDeg':3.6,'targetAltitudeDeg':86.25,'relativeAzimuthDeg':100.0,'observerElevationM':1100.0,'aod550':0.35},
 {'geometryId':'zenith-holdout-04','sunDepressionDeg':8.9,'targetAltitudeDeg':88.75,'relativeAzimuthDeg':45.0,'observerElevationM':1800.0,'aod550':0.19},
 {'geometryId':'zenith-holdout-05','sunDepressionDeg':4.4,'targetAltitudeDeg':90.0,'relativeAzimuthDeg':0.0,'observerElevationM':300.0,'aod550':0.31},
 {'geometryId':'zenith-holdout-06','sunDepressionDeg':7.7,'targetAltitudeDeg':90.0,'relativeAzimuthDeg':0.0,'observerElevationM':2200.0,'aod550':0.09},
 {'geometryId':'zenith-holdout-07','sunDepressionDeg':9.7,'targetAltitudeDeg':84.5,'relativeAzimuthDeg':80.0,'observerElevationM':700.0,'aod550':0.27},
 {'geometryId':'zenith-holdout-08','sunDepressionDeg':5.7,'targetAltitudeDeg':87.0,'relativeAzimuthDeg':130.0,'observerElevationM':1400.0,'aod550':0.40},
]

def canon(v):
    return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def selfhash(v,field):
    x=copy.deepcopy(v); x[field]=None; return hashlib.sha256(canon(x)).hexdigest()

def build():
    cases=[]; seed=2_230_000_001; ordinal=1
    for g in GEOMETRIES:
        photons=50_000_000 if g['sunDepressionDeg'] >= 9.0 else 20_000_000
        for block in range(1,5):
            cases.append({
              'ordinal':ordinal,'caseId':f"{g['geometryId']}-b{block}",'geometryId':g['geometryId'],
              'groupId':g['geometryId'],'role':g['role'],'executionStage':'ZENITH_EXTENSION_ACQUISITION',
              'block':block,'seed':seed,'photonHistories':photons,'method':'alis',
              'alisSpectralImportanceSamplingNm':550.0,
              'expectedOutputGrid':{'nodeCount':8001,'startNm':380.0,'stepNm':0.05,'stopNm':780.0},
              'scientificValuesReadableBeforeModelFreeze':True,
            }); seed+=1; ordinal+=1
    total=sum(c['photonHistories'] for c in cases)
    assert len(GEOMETRIES)==18 and len(cases)==72 and len({c['seed'] for c in cases})==72
    assert cases[0]['seed']==2_230_000_001 and cases[-1]['seed']==2_230_000_072
    assert total==2_040_000_000
    manifest={
      'schemaVersion':1,'manifestId':'level-b-zenith-expansion-acquisition-v1','manifestSha256':None,
      'status':'FROZEN_ONE_SHOT_ACQUISITION_PACKAGE_NO_EXECUTION_WITHOUT_SEPARATE_DISPATCH_PR',
      'executionKey':'level-b-zenith-expansion-acquisition-v1:scientific:1',
      'trainingOnly':True,'scientificExecution':True,'successDoesNotAuthorizeProduction':True,
      'successDoesNotAuthorizeSupportExpansion':True,'sourceModelCanonicalSha256':'c4902eb3c2ba67b12dc4ef2b9cefb67c5963a6abc104708a73b2aab5dd0163b9',
      'sourceRepresentationSha256':'2491ac91ed924f2ba69b37ea20f48d63f51d41146cd9fe50e0bd63bfb315a763',
      'runtimeIdentityRequired':RUNTIME,
      'runtimePackage':{'runner':'ubuntu-24.04','python':'3.12.4','exactPackageSpec':'rubin-libradtran=2.0.6=py312pl5321he9373c2_1'},
      'frozenInputs':{
        'wavelengthDomainNm':[380.0,780.0],'expectedOutputGrid':{'nodeCount':8001,'stepNm':0.05},
        'molecularAbsorption':'crs','mcSpherical':'1D','albedo':0.15,'solarFlux':'atlas_plus_modtran','atmosphereProfile':'AFGLUS',
        'observerElevationRepresentation':'ASCENDING_ATM_Z_GRID_BOTTOM_EQUALS_PHYSICAL_OBSERVER_ELEVATION','localSurfaceZoutKm':0.0,
        'altitudeShortcutAllowed':False,'mcElevationFileShortcutAllowed':False,'exactZeroPreserved':True,'epsilonSubstitutionAllowed':False,
        'zenithAzimuthCanonicalizationForTraining':'EXACT_ALTITUDE_90_TRAINING_USES_RELATIVE_AZIMUTH_0_ONLY',
      },
      'design':{
        'oldValidatedPhysicalAltitudeRangeDeg':[5.0,80.0], 'proposedPhysicalAltitudeRangeDeg':[5.0,90.0],
        'newAcquisitionAltitudeRangeDeg':[80.0,90.0],
        'boundary80AnchorCount':4,'newTrainingGeometryCount':16,'zenithInvarianceDiagnosticGeometryCount':2,
        'boundary80AnchorsDerivedByAltitudeOnlyExtensionFromExistingHighAltitudeSupportCoordinates':True,
        'holdoutDesignPath':'experiments/level-b-zenith-expansion-acquisition-v1/holdout-design.review.json',
        'holdoutsExecutedInThisManifest':False,
      },
      'geometryCount':len(GEOMETRIES),'caseCount':len(cases),'configuredPhotonHistories':total,
      'geometries':GEOMETRIES,'cases':cases,
      'executionLimits':{'workflowAttemptExactly':1,'syntaxChecksPerCaseExactly':1,'solverExecutionsPerCaseExactly':1,'automaticRetryCountMaximum':0,'resumeAllowed':False,'githubRerunAllowed':False,'maxParallel':12,'perCaseTimeoutMinutes':30},
      'closedBoundaries':{'modelRefitAuthorizedByThisRun':False,'supportExpansionAuthorizedByThisRun':False,'holdoutExecutionAuthorized':False,'productionPromotionAuthorized':False,'lunarBackgroundIncluded':False,'naturalBackgroundIncluded':False,'artificialBackgroundIncluded':False},
    }
    manifest['manifestSha256']=selfhash(manifest,'manifestSha256')
    holdout={
      'schemaVersion':1,'designId':'level-b-zenith-expansion-protected-holdout-design-v1','designSha256':None,
      'status':'FROZEN_BEFORE_ACQUISITION_RESULTS_NO_EXECUTION_NO_VALUES','sourceModelCanonicalSha256':manifest['sourceModelCanonicalSha256'],
      'geometryCount':len(HOLDOUTS),'geometries':HOLDOUTS,
      'selectionRules':{'selectedBeforeAcquisitionResults':True,'modelPredictionsMayNotInfluenceSelection':True,'trainingResultsMayNotInfluenceSelection':True,'individualReplacementAfterOpeningForbidden':True},
      'execution':{'authorized':False,'seedsAllocated':False,'scientificOrdinalAllocated':False,'minimumBlocksPerGeometry':4,'photonHistoriesPerBlock':40_000_000,'noRetuningAfterOpening':True},
      'requiredGatesBeforeAnySupportExpansion':{
        'exactZenithAzimuthInvariance':True,'continuityAt80DegAgainstFrozenV3':True,'independentHoldoutPass':True,
        'oldDomainNoRegression5To80Deg':True,'noSilentExtrapolation':True,
      },
    }
    holdout['designSha256']=selfhash(holdout,'designSha256')
    return manifest,holdout

if __name__=='__main__':
    out=Path(__file__).resolve().parent
    m,h=build()
    (out/'manifest.json').write_text(json.dumps(m,indent=2,sort_keys=True,allow_nan=False)+'\n')
    (out/'holdout-design.review.json').write_text(json.dumps(h,indent=2,sort_keys=True,allow_nan=False)+'\n')
    print(m['manifestSha256'])
    print(h['designSha256'])
