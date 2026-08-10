#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json
from pathlib import Path
from typing import Any
ROOT=Path('/mnt/data')
EXEC=ROOT/'full-spectrum-estimator-pilot-execution-manifest-v4.json'
RENDER=ROOT/'full-spectrum-estimator-pilot-rendered-review-v5/renderer-review-report.json'
OUT=ROOT/'full-spectrum-estimator-pilot-acquisition-contract-v4.json'
def canon(v:Any)->str: return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def raw(p:Path)->str: return hashlib.sha256(p.read_bytes()).hexdigest()
e=json.loads(EXEC.read_text()); r=json.loads(RENDER.read_text())
if e['manifestSha256']!='be81c717cd943415ac51dc2b5356010b3d584b5279228c525d2defccc4680e0f': raise SystemExit('exec drift')
if r['executionManifestSha256']!=e['manifestSha256'] or r['reportSha256']!='f6658e9d7a19fb5c6ec7acfc2a6be12b608445e9a75aee100c80426cba31efa1': raise SystemExit('renderer drift')
rb={c['caseId']:c for c in r['cases']}
rows=[]
for c in e['cases']:
 rr=rb[c['caseId']]
 required=list(e['artifactContract']['requiredMembersByMethod'][c['method']])
 rows.append({
  'caseId':c['caseId'],'geometryId':c['geometryId'],'method':c['method'],'seed':c['seed'],'photonHistories':c['photonHistories'],
  'artifactName':f"full-spectrum-estimator-pilot-v2-case-{c['caseId']}",
  'requiredMemberBasenames':required,'requiredMemberBasenamesSha256':canon(required),
  'reviewedInputResolvedSha256':rr['inputResolvedReviewSha256'],'reviewedInputTemplateSha256':rr['inputTemplateSha256'],
  'historicalPhysicalFingerprintSha256':rr['physicalFingerprintSha256'],'historicalSourceInputSha256':rr['historicalSourceInputSha256'],
 })
body={
 'schemaVersion':1,
 'contractId':'public-tier1-full-spectrum-estimator-pilot-acquisition-contract-v4',
 'status':'REVIEW_ONLY_EXACT_44_ARTIFACT_CONTRACT_NO_RESULTS',
 'protocolId':e['protocolId'],'protocolSha256':e['protocolSha256'],
 'executionManifestId':e['manifestId'],'executionManifestSha256':e['manifestSha256'],'executionManifestRawSha256':raw(EXEC),
 'rendererId':r['rendererId'],'rendererReportSelfHash':r['reportSha256'],'rendererReportRawSha256':raw(RENDER),
 'expectedArtifactCount':44,'expectedArtifacts':rows,'expectedArtifactsCanonicalSha256':canon(rows),
 'transportRules':{
  'githubArtifactIdRequired':True,'githubZipDigestRequired':True,'downloadedZipSha256MustEqualGithubDigest':True,
  'transportMetadataMustBeFrozenBeforeOpeningZipBytes':True,'artifactExpiredMustBeFalse':True,'exactArtifactNameRequired':True,
  'exactRequiredMemberBasenameSetRequired':True,'duplicateMemberBasenamesRefused':True,'unexpectedExtraMembersRefused':True,
  'caseResultSelfHashRequired':True,'caseResultExactRawMemberSha256MapRequired':True,'allEmbeddedRawMemberHashesRecomputed':True,
  'randomseedFileMustEqualManifestSeed':True,'all44ArtifactsRequiredBeforeNormalization':True,'partialAcquisitionRejected':True,
 },
 'executionEvidenceRules':{
  'workflowRunAttemptExactly':1,'syntaxCheckCountExactly':1,'solverExecutionCountExactly':1,
  'syntaxExitCodeExactly':0,'solverExitCodeExactly':0,'syntaxTimedOut':False,'solverTimedOut':False,
  'retryPerformed':False,'resumePerformed':False,'githubRerun':False,'caseStatusRequired':'COMPLETED',
  'seedAndPhotonCountMustMatchManifest':True,'preparedRecordMustBindCaseInputAndManifest':True,
 },
 'resultOpeningBoundary':{
  'pilotResultsOpened':False,'artifactBytesOpened':False,'modelFittingAuthorized':False,'holdoutOpeningAuthorized':False,
  'tier2Authorized':False,'productionAuthorization':False,
 },
 'notes':[
  'ALIS exact case artifacts contain 17 basenames, including four ALIS auxiliary spectra; VROOM exact case artifacts contain 14 basenames, including the frozen 1-nm wavelength grid.',
  'Syntax/solver stdout and stderr, randomseed, prepared record, runtime identity, flux spectra, primary radiance/std spectra, and all method-specific members are hash-bound by case-result.json.',
  'The reviewed input hash is a preexecution identity check. Runtime-resolved absolute paths may be regenerated only by the frozen renderer under the exact runtime identity; scientific directives/fingerprint must remain exact.',
  'This contract defines acquisition/evidence completeness only and grants no scientific execution authorization.'
 ],
 'authorizationPermitted':False,'scientificExecutionAuthorized':False,'solverExecutionPerformed':False,
}
body['contractSha256']=canon(body)
OUT.write_text(json.dumps(body,indent=2,sort_keys=True,allow_nan=False)+'\n')
print(json.dumps({'contractSha256':body['contractSha256'],'rawSha256':raw(OUT),'caseCount':len(rows),'alisCaseCount':sum(x['method']=='alis-alt-importance' for x in rows),'vroomCaseCount':sum(x['method']=='reference-vroom-1nm' for x in rows)},indent=2))
