#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path
CENTER={'aod550':0.154132,'observerElevationM':612.245,'relativeAzimuthDeg':51.84,'sunDepressionDeg':4.25,'targetAltitudeDeg':8.703703820838767}
IDS=[f'train-{n:04d}' for n in range(101,115)]
OPENED={'train-0050','train-0060','train-0065','train-0070','train-0080','train-0090'}
SEEDS=list(range(2100000101,2100000129))
DOMAIN={'sunDepressionDeg':(2.0,10.5),'targetAltitudeDeg':(5.0,80.0),'relativeAzimuthDeg':(0.0,180.0),'observerElevationM':(0.0,2500.0),'aod550':(0.05,0.4)}
class Refusal(RuntimeError): pass
def req(c,m):
    if not c: raise Refusal(m)
def canon(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def load(p):
    x=json.loads(Path(p).read_text()); req(isinstance(x,dict),'object required'); return x
def validate_audit(a):
    req((a.get('schemaVersion'),a.get('auditId'),a.get('governance'),a.get('status'))==(1,'mystic-state-0069-training-only-local-continuity-audit-v1','MYSTIC-STATE-0069','TRAINING_ONLY_DIAGNOSTIC_NO_FIT_NO_PROTECTED_VALUES'),'audit identity drift')
    got=a.get('auditCanonicalSha256'); req(got==canon({k:v for k,v in a.items() if k!='auditCanonicalSha256'}),'audit hash drift')
    req(a.get('targetGeometryId')=='train-0036' and a.get('targetGeometry')==CENTER,'target identity drift')
    req(a.get('blockingPcaCoefficientIndex')==1,'blocking coefficient drift')
    req(abs(a.get('targetNormalizedCoefficient')-3.177414090177827)<1e-15,'target coefficient drift')
    req(abs(a.get('targetNormalizedSourceStandardError')-0.020499891116065407)<1e-15,'target SE drift')
    req(a.get('nearestTrainingGeometryId')=='train-0066','nearest identity drift')
    req(abs(a.get('nearestTrainingDistanceFrozenV1IdwCoordinates')-0.42544071812827466)<1e-15,'nearest distance drift')
    req(a.get('targetHasMaximumNearestAbsoluteCoefficientJump') is True and a.get('targetHasMaximumNearestJumpPerUnitDistance') is True,'local maximum evidence drift')
    d=a.get('deterministicSphericalEarthDiagnostics') or {}; req(d.get('valuesUsedForPointPlacement') is False,'diagnostic physical features became placement inputs')
def validate_protocol(p,a):
    req((p.get('schemaVersion'),p.get('protocolId'),p.get('status'),p.get('governance'))==(1,'mystic-state-0069-local-training-densification-v1','REVIEW_ONLY_PREREGISTRATION_NO_SCIENTIFIC_EXECUTION_ON_PR','MYSTIC-STATE-0069'),'protocol identity drift')
    got=p.get('protocolCanonicalSha256'); req(got==canon({k:v for k,v in p.items() if k!='protocolCanonicalSha256'}),'protocol hash drift')
    req(p.get('sourceMainAtFreeze')=='d49b0e29a4e312b920ad98e3873bbcc2501a830c','source main drift')
    s=p.get('sourceEvidence') or {}; req(s.get('terminal0068ResultGitBlobSha')=='70161120e96afa3bbfd7a16239f8233ad159e266','terminal result blob drift'); req(s.get('trainingAuditCanonicalSha256')==a['auditCanonicalSha256'],'audit binding drift'); req(s.get('ordinal22ValuesUsed') is False,'ordinal22 boundary opened')
    c=p.get('center') or {}; req(c.get('geometryId')=='train-0036' and c.get('geometry')==CENTER,'center drift')
    d=p.get('design') or {}; geoms=d.get('geometries') or []; req(d.get('kind')=='FIXED_LOCAL_STAR_PLUS_SUN_ALT_INTERACTION_CORNERS' and d.get('newGeometryCount')==14,'design identity drift'); req([g.get('geometryId') for g in geoms]==IDS,'geometry IDs/order drift'); req(d.get('geometryIds')==IDS,'geometry identity list drift'); req(d.get('adaptivePointAdditionAllowed') is False and d.get('openedProtectedGeometryOrValueMayInfluencePlacement') is False,'adaptive/protected placement opened'); req(not set(IDS)&OPENED,'opened ID collision')
    seen=set()
    for row in geoms:
        g=row.get('geometry') or {}; key=tuple(float(g[k]) for k in sorted(DOMAIN)); req(key not in seen,'duplicate geometry'); seen.add(key)
        for k,(lo,hi) in DOMAIN.items(): req(lo<=float(g[k])<=hi,f'domain violation {row.get("geometryId")} {k}')
    e=p.get('execution') or {}; cases=e.get('cases') or []; req((e.get('proposedFreshScientificOrdinal'),e.get('caseCount'),e.get('blocksPerGeometry'),e.get('photonHistoriesPerCase'),e.get('totalConfiguredPhotonHistories'))==(23,28,2,20000000,560000000),'execution budget drift'); req(e.get('seedRangeInclusive')==[SEEDS[0],SEEDS[-1]],'seed range drift'); req([c.get('seed') for c in cases]==SEEDS,'seed list drift'); req(len(set(SEEDS))==28 and max(SEEDS)<2147483647,'seed validity drift'); req(sum(int(c['photonHistories']) for c in cases)==560000000,'history total drift')
    for i,row in enumerate(geoms):
        pair=cases[2*i:2*i+2]; req([x.get('geometryId') for x in pair]==[row['geometryId'],row['geometryId']],'case geometry drift'); req([x.get('block') for x in pair]==[1,2],'block drift'); req(all(x.get('role')=='surrogate-training' and x.get('method')=='alis' and x.get('alisSpectralImportanceSamplingNm')==550.0 for x in pair),'case physics drift')
    req(e.get('githubRerunRetryResumeAllowed') is False and e.get('runAttemptRequired')==1 and e.get('adaptiveContinuationAllowed') is False,'execution retry/adaptation opened')
    post=p.get('postExecution') or {}; req(post.get('newRepresentationOrModelFitAuthorizedByThisProtocol') is False and post.get('separateRepresentationFreezeRequired') is True and post.get('protectedValidationAuthorized') is False,'post-execution boundary drift')
    for k,v in (p.get('absoluteBoundaries') or {}).items(): req(v is False,f'absolute boundary opened {k}')
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--protocol',required=True); ap.add_argument('--audit',required=True); a=ap.parse_args(); audit=load(a.audit); validate_audit(audit); p=load(a.protocol); validate_protocol(p,audit); print('VALID_MYSTIC_STATE_0069_LOCAL_DENSIFICATION_PREREGISTRATION')
if __name__=='__main__': main()
