#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
class Refusal(RuntimeError): pass
def req(c,m):
    if not c: raise Refusal(m)
def main():
    p=Path('review/mystic-state-0069-execution-transport-v1/implementation-v1.json'); x=json.loads(p.read_text())
    req((x.get('schemaVersion'),x.get('implementationId'),x.get('status'),x.get('governance'))==(1,'mystic-state-0069-execution-transport-v1','REVIEW_ONLY_EXECUTION_TRANSPORT_NO_AUTHORIZATION','MYSTIC-STATE-0069'),'implementation identity drift')
    req(x.get('sourceMainAfterPreregistration')=='db4671381b0cfa3c59cf2759e0793d408d4b87a2','source main drift')
    q=x.get('preregistration') or {}; req((q.get('gitBlobSha'),q.get('protocolCanonicalSha256'),q.get('scientificOrdinal'),q.get('geometryCount'),q.get('caseCount'),q.get('configuredPhotonHistories'))==('d47bceb9b415ca8ebf14f6014207fd1310b4809c','9dbc150881b11481d7d0e267cb14d9507051d15442c21853b3256875db5d3c64',23,14,28,560000000),'prereg binding drift')
    r=x.get('reviewedExecutionReferences') or {}; req(r.get('tier2Stage1ManifestCanonicalSha256')=='7351a47582ca0a328059256566b24ce10c0e6ff5d802f53ff35e133540a83819','base manifest drift'); req(r.get('canonicalWavelengthTokenStreamSha256')=='b5fae53c1cc88c7f3de6e3689bc25e4a36c54033d1d1bfd6169482f30cc5b477','token stream drift')
    i=x.get('identity') or {}; req((i.get('authorizationBranch'),i.get('dispatchBranch'))==('authorization/mystic-state-0069-ordinal23-v1','dispatch/mystic-state-0069-ordinal23-v1'),'branch identity drift'); req(i.get('workflowRunAttemptExactly')==1 and i.get('authorizationCommitMustBeDirectChildOfLiveMain') is True and i.get('dispatchMustPointToExactAuthorizedCommit') is True,'identity guard drift')
    e=x.get('execution') or {}; req((e.get('exactCaseCount'),e.get('exactGeometryCount'),e.get('photonHistoriesPerCase'),e.get('configuredPhotonHistories'))==(28,14,20000000,560000000),'execution accounting drift'); req(e.get('exactSyntaxChecksPerCase')==1 and e.get('exactMysticInvocationsPerCase')==1 and e.get('githubRerunRetryResumeAllowed') is False and e.get('adaptiveContinuationAllowed') is False,'one-use guard drift')
    b=x.get('reviewBoundaries') or {}
    for k in ('scientificExecutionAuthorizedOnThisPullRequest','authorizationFileMayExistOnThisPullRequest','ordinal22ValuesMayBeRead','protectedValidationAuthorized','modelFitAuthorized','productionPromotionAuthorized','workerBLaneReactivated','workerCLaneReactivated'): req(b.get(k) is False,f'closed boundary opened: {k}')
    print('VALID_MYSTIC_STATE_0069_EXECUTION_TRANSPORT_IMPLEMENTATION')
if __name__=='__main__': main()
