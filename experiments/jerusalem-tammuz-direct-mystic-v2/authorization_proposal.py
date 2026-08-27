#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

LANE_ID = "jerusalem-tammuz-direct-mystic-v2"
PURPOSE = LANE_ID
EXECUTION_KEY = "jerusalem-tammuz-direct-mystic-v2:diagnostic:1"
AUTHORIZATION_ORDINAL = 1
BATCH_ID = "jerusalem-tammuz-three-star-direct-mystic-v1"
APPLICATION_SHA = "e2d5b761206b6223526f6f79fcb0af5f6de3ba06"
CONSUMED_SMOKE_MAIN_SHA = "70913845f194b529b15a10c72d0ae8a9ec675ff1"
SMOKE_RUN_ID = 33011713466
SMOKE_AUDIT_ARTIFACT_ID = 9622825000
SMOKE_AUDIT_DIGEST = "sha256:bd13fae624385476c73094e8d3a0019d403689bbfba640248c0173f1451598de"
PACKAGE = Path("experiments/jerusalem-tammuz-direct-mystic-v2")
SOURCE = Path("experiments/jerusalem-tammuz-direct-mystic-v1")
PATHS = {
    "authorization": PACKAGE / "authorization.scientific.json",
    "lanePreregistration": PACKAGE / "lane.preregistration.json",
    "v2ExecutionGuard": PACKAGE / "execution_guard.py",
    "plan": PACKAGE / "execution_plan.py",
    "authorizationProposalBuilder": PACKAGE / "authorization_proposal.py",
    "executionWorkflow": Path(".github/workflows/jerusalem-tammuz-direct-mystic-v2-execution.yml"),
    "proposal": SOURCE / "manifest.proposal.json",
    "levelBEvidence": SOURCE / "level-b-event-evidence.json",
    "analysisContract": SOURCE / "analysis-contract.json",
    "executionAdapter": SOURCE / "execution_adapter.py",
    "analysisDriver": SOURCE / "analyze_direct_sky.py",
    "visibilityHelper": SOURCE / "compute_sky_only_visibility.mjs",
    "proposalAdapter": Path("experiments/mystic-batch-v1/cross_geometry_adapter.py"),
    "runtimeLock": Path("experiments/mystic-batch-v1/runtime-lock.micromamba.json"),
    "derivedChannels": Path("experiments/aerosol-family-challenge-v2/derived_channels.py"),
    "executor": Path("experiments/mystic-batch-v1/scientific_case_executor.py"),
    "aggregate": Path("experiments/mystic-batch-v1/scientific_aggregate.py"),
    "audit": Path("experiments/mystic-batch-v1/scientific_audit.py"),
    "smokeRecovery2Gate": Path("experiments/jerusalem-tishrei-elevated-site-smoke-v2-recovery2/gate.smoke-recovery2.json"),
    "genericExecutionAdapter": Path("experiments/mystic-batch-v1/cross_geometry_execution_adapter.py"),
    "elevationHelper": Path("experiments/mystic-batch-v1/twilight_surrogate_tier1_execution_adapter.py"),
    "duplicateRunAudit": Path("experiments/mystic-batch-v1/duplicate_run_audit.py"),
    "runtimeProbe": Path("experiments/mystic-batch-v1/runtime_probe.py"),
}
HUMAN_THRESHOLD = Path("scientific-tools/visibility-v3/human-threshold.mjs")

class ProposalError(RuntimeError): pass

def load(path:Path)->dict[str,Any]:
    value=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value,dict): raise ProposalError(f"expected JSON object: {path}")
    return value

def raw_sha256(path:Path)->str: return hashlib.sha256(path.read_bytes()).hexdigest()
def git(root:Path,*args:str)->str: return subprocess.check_output(["git",*args],cwd=root,text=True).strip()
def require_ancestor(root:Path,ancestor:str)->None:
    if subprocess.run(["git","merge-base","--is-ancestor",ancestor,"HEAD"],cwd=root,check=False).returncode!=0: raise ProposalError(f"HEAD does not contain required consumed smoke checkpoint {ancestor}")

def validate_lane(root:Path,paths:dict[str,Path])->None:
    lane=load(paths["lanePreregistration"])
    if lane.get("laneId")!=LANE_ID or lane.get("status")!="PREREGISTERED_NO_EXECUTION" or lane.get("scientificExecution") is not False: raise ProposalError("lane preregistration header changed")
    future=lane.get("futureAuthorization") or {}
    if future.get("executionKey")!=EXECUTION_KEY or future.get("authorizationOrdinal")!=AUTHORIZATION_ORDINAL or any(future.get(k) is not False for k in ("retryAllowed","resumeAllowed","rerunAllowed")): raise ProposalError("future one-shot authorization changed")
    source=lane.get("sourceScientificPayload") or {}
    expected={"applicationSha":APPLICATION_SHA,"sourceEvidenceRunId":33025015603,"sourceEvidenceArtifactId":9628151845,"sourceEvidenceArtifactDigest":"sha256:42ed5920f88428c768bc25f7203de7ea48173fe541f857f9fedcc42efaec1008","catalogBasis":"LIVE_DATE_TRANSFORMED_LEVEL_B_DIRECT_CATALOG_HANDOFF","caseCount":12,"photonHistoriesPerCase":20_000_000,"configuredPhotonHistoriesSum":240_000_000,"geometryCount":3,"fieldFactorBaseline":3.14,"aod550":0.18,"observerElevationM":800,"surfaceAlbedo":0.15,"mcSpherical":"1D","atmosphere":"AFGLUS","wavelengthDomainNm":[380,780]}
    stale={k:(source.get(k),v) for k,v in expected.items() if source.get(k)!=v}
    if stale or source.get("methods")!={"reference-vroom":6,"alis":6}: raise ProposalError(f"source payload changed: {stale}")
    boundary=lane.get("claimBoundary") or {}
    if boundary.get("noParameterTuning") is not True or boundary.get("productionAuthorized") is not False or boundary.get("pandoraOpened") is not False: raise ProposalError("claim boundary changed")
    smoke=lane.get("requiredInfrastructureSmoke") or {}
    if smoke.get("workflowRunId")!=SMOKE_RUN_ID or smoke.get("formalStatus")!="PASSED_AND_CONSUMED" or smoke.get("auditArtifactId")!=SMOKE_AUDIT_ARTIFACT_ID or smoke.get("auditArtifactDigest")!=SMOKE_AUDIT_DIGEST: raise ProposalError("required formal smoke provenance changed")
    gate=load(paths["smokeRecovery2Gate"])
    req={"stageId":"jerusalem-tishrei-elevated-site-smoke-v2-recovery2","enabled":False,"infrastructureExecution":False,"scientificExecution":False,"scientificDiagnostic":False,"scientificUseProhibited":True,"executionKey":"jerusalem-tishrei-elevated-site-smoke-v2:infrastructure:3","smokeOrdinal":3,"consumed":True}
    stale_gate={k:(gate.get(k),v) for k,v in req.items() if gate.get(k)!=v}
    note=str(gate.get("note",""))
    if stale_gate or str(SMOKE_RUN_ID) not in note or str(SMOKE_AUDIT_ARTIFACT_ID) not in note or SMOKE_AUDIT_DIGEST not in note: raise ProposalError(f"formal smoke gate changed: {stale_gate}")

def build(repo_root:Path,application_root:Path)->dict[str,Any]:
    root=repo_root.resolve(); app=application_root.resolve(); require_ancestor(root,CONSUMED_SMOKE_MAIN_SHA)
    paths={k:root/v for k,v in PATHS.items()}
    for k,p in paths.items():
        if not p.is_file(): raise ProposalError(f"missing {k}: {p}")
    human=app/HUMAN_THRESHOLD
    if not human.is_file() or git(app,"rev-parse","HEAD")!=APPLICATION_SHA: raise ProposalError("application checkout/human threshold not exact")
    validate_lane(root,paths)
    disabled=load(paths["authorization"])
    if disabled.get("authorized") is not False or disabled.get("scientificExecution") is not False or disabled.get("authorizationOrdinal")!=0 or disabled.get("consumed") is not False: raise ProposalError("package authorization is not disabled")
    manifest=load(paths["proposal"]); evidence=load(paths["levelBEvidence"]); analysis=load(paths["analysisContract"])
    if manifest.get("batchId")!=BATCH_ID or manifest.get("proposalOnly") is not True or manifest.get("scientificExecution") is not False: raise ProposalError("proposal boundary changed")
    if (manifest.get("preregisteredEvent") or {}).get("sourceEvidence",{}).get("artifactId")!=9628151845: raise ProposalError("proposal source evidence changed")
    if evidence.get("applicationMainSha")!=APPLICATION_SHA or (evidence.get("source") or {}).get("transformedCatalogCount")!=7653: raise ProposalError("evidence provenance changed")
    if analysis.get("analysisId")!="jerusalem-tammuz-direct-mystic-level-b-comparison-v1" or analysis.get("scientificExecution") is not False: raise ProposalError("analysis contract changed")
    repaired=paths["executionAdapter"].read_text(encoding="utf-8")
    for token in ("EXPECTED_AOD550 = 0.18","EXPECTED_OBSERVER_ELEVATION_M = 800.0","atm_z_grid","zout 0.000000","mc_elevation_file"):
        if token not in repaired: raise ProposalError(f"reviewed Tammuz elevation adapter lost token: {token}")
    parent=git(root,"rev-parse","HEAD")
    proposed={
        "schemaVersion":1,"stageId":"cross-geometry-pilot-v1","scientificPurpose":PURPOSE,"laneId":LANE_ID,
        "authorized":True,"scientificExecution":True,"scientificDiagnostic":True,"successDoesNotAuthorizeProduction":True,
        "executionKey":EXECUTION_KEY,"batchId":BATCH_ID,"proposalPath":PATHS["proposal"].as_posix(),
        "requiredSmokeRunId":SMOKE_RUN_ID,"requiredSmokeAuditArtifactId":SMOKE_AUDIT_ARTIFACT_ID,"requiredSmokeAuditArtifactDigest":SMOKE_AUDIT_DIGEST,
        "authorizationOrdinal":AUTHORIZATION_ORDINAL,"consumed":False,"exactAuthorizationParentCommit":parent,"exactAuthorizationCommit":None,
        "note":"One-purpose Tammuz direct-MYSTIC v2 scientific authorization proposal. Exact transformed-row 12-case/240M science, F=3.14, AOD550=0.18, 800m atm_z_grid representation, runtime, seeds and analysis are hash-bound. Separate authorization commit and first-attempt dispatcher are required. Retry/resume/rerun prohibited. No production, tuning, real-sky, human-first-seeing, full-spectrum-Level-B or Pandora claim."
    }
    mapping={
        "proposalRawSha256":"proposal","levelBEvidenceRawSha256":"levelBEvidence","analysisContractRawSha256":"analysisContract","proposalAdapterRawSha256":"proposalAdapter","executionAdapterRawSha256":"executionAdapter","executionWorkflowRawSha256":"executionWorkflow","runtimeLockRawSha256":"runtimeLock","planRawSha256":"plan","analysisDriverRawSha256":"analysisDriver","visibilityHelperRawSha256":"visibilityHelper","derivedChannelsRawSha256":"derivedChannels","executorRawSha256":"executor","aggregateRawSha256":"aggregate","auditRawSha256":"audit","authorizationProposalBuilderRawSha256":"authorizationProposalBuilder","lanePreregistrationRawSha256":"lanePreregistration","v2ExecutionGuardRawSha256":"v2ExecutionGuard","smokeRecovery2GateRawSha256":"smokeRecovery2Gate","genericExecutionAdapterRawSha256":"genericExecutionAdapter","elevationHelperRawSha256":"elevationHelper","duplicateRunAuditRawSha256":"duplicateRunAudit","runtimeProbeRawSha256":"runtimeProbe"
    }
    for field,key in mapping.items(): proposed[field]=raw_sha256(paths[key])
    proposed["humanThresholdRawSha256"]=raw_sha256(human)
    return {"schemaVersion":1,"laneId":LANE_ID,"scientificPurpose":PURPOSE,"status":"TAMMUZ_V2_PROPOSAL_ONLY_NOT_AUTHORIZATION","executionAuthorizedByProposal":False,"proposedAuthorization":proposed,"boundary":"hash proposal only; no syntax check, uvspec process, MYSTIC solver, dispatch, tuning, production claim or Pandora"}

def dump(v:Any)->str: return json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+"\n"
def main()->int:
    p=argparse.ArgumentParser(); p.add_argument("--repository-root",type=Path,default=Path(".")); p.add_argument("--application-root",type=Path,required=True); p.add_argument("--output",type=Path,required=True); args=p.parse_args()
    try:
        result=build(args.repository_root,args.application_root); args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(dump(result),encoding="utf-8"); print(dump(result),end=""); return 0
    except Exception as exc:
        report={"schemaVersion":1,"laneId":LANE_ID,"scientificPurpose":PURPOSE,"status":"REFUSED","reason":str(exc)}; print(dump(report),end="",file=sys.stderr); return 2
if __name__=="__main__": raise SystemExit(main())
