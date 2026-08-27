#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

STAGE_ID = "cross-geometry-pilot-v1"
LANE_ID = "jerusalem-tammuz-direct-mystic-v2"
PURPOSE = LANE_ID
BATCH_ID = "jerusalem-tammuz-three-star-direct-mystic-v1"
EXECUTION_KEY = "jerusalem-tammuz-direct-mystic-v2:diagnostic:1"
AUTHORIZATION_ORDINAL = 1
EXPECTED_CASES = 12
EXPECTED_PHOTONS = 240_000_000
EXPECTED_EVENT_DEP = 4.8882245305886585
EXPECTED_AOD550 = 0.18
EXPECTED_ELEVATION_M = 800.0
EXPECTED_FIELD_FACTOR = 3.14
EXPECTED_ALBEDO = 0.15
EXPECTED_ALIS_IS_NM = 405.0
EXPECTED_APPLICATION_SHA = "e2d5b761206b6223526f6f79fcb0af5f6de3ba06"
EXPECTED_HUMAN_THRESHOLD_GIT_BLOB_SHA1 = "bb4cd0ff02159ecffe276022cec9d292c7a434a3"
EXPECTED_DERIVED_CHANNELS_GIT_BLOB_SHA1 = "ccfd04d4c21188966351f4257e92893d7ce340c7"
EXPECTED_EVIDENCE_RUN_ID = 33025015603
EXPECTED_EVIDENCE_ARTIFACT_ID = 9628151845
EXPECTED_EVIDENCE_DIGEST = "sha256:42ed5920f88428c768bc25f7203de7ea48173fe541f857f9fedcc42efaec1008"
CONSUMED_SMOKE_MAIN_SHA = "70913845f194b529b15a10c72d0ae8a9ec675ff1"
SMOKE_RUN_ID = 33011713466
SMOKE_AUDIT_ARTIFACT_ID = 9622825000
SMOKE_AUDIT_DIGEST = "sha256:bd13fae624385476c73094e8d3a0019d403689bbfba640248c0173f1451598de"
SMOKE_GATE = Path("experiments/jerusalem-tishrei-elevated-site-smoke-v2-recovery2/gate.smoke-recovery2.json")
GENERIC_EXECUTION_ADAPTER = Path("experiments/mystic-batch-v1/cross_geometry_execution_adapter.py")
ELEVATION_HELPER = Path("experiments/mystic-batch-v1/twilight_surrogate_tier1_execution_adapter.py")
DUPLICATE_RUN_AUDIT = Path("experiments/mystic-batch-v1/duplicate_run_audit.py")
RUNTIME_PROBE = Path("experiments/mystic-batch-v1/runtime_probe.py")
LANE_PREREG = Path("experiments/jerusalem-tammuz-direct-mystic-v2/lane.preregistration.json")
EXPECTED_RUN_NAME = "run-name: MYSTIC batch v1 | key=${{ inputs.execution_key }} | auth=${{ inputs.authorization_ref }} | ordinal=${{ inputs.authorization_ordinal }}"
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._:-]{2,159}$")
EXPECTED_RUNTIME = {
    "uvspecSha256": "2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3",
    "uvspecHelpSha256": "868aea5af762d968f6f62c4e1472916d25232ed9cab5be112d753b0823d20548",
    "libRadtranDataTreeSha256": "ad30b49177e9c84e46497d69faf0c75e466996b0d0003f1de210289ae9f847d7",
    "atmosphereSha256": "dab26290ed81c762ed0c607e5dc2d53393c1462a0c3a528bc5e3f5935191cfb5",
    "runtimeLockRawSha256": "3b5fbec964642b04c73a6423b3355dbcc4ba5e84f9614f6d74420491bacc20c5",
}
EXPECTED_GEOMETRIES = {
    "tammuz-alkaid-hr5191": {"catalogId":"HR 5191","alt":71.09332700558907,"relAz":78.75404006373856},
    "tammuz-alioth-hr4905": {"catalogId":"HR 4905","alt":65.83570230161766,"relAz":53.77036225185543},
    "tammuz-regulus-hr3982": {"catalogId":"HR 3982","alt":44.24794686376737,"relAz":46.8700290856782},
}

class Refusal(RuntimeError):
    def __init__(self, code: str, reason: str, detail: Any | None = None) -> None:
        super().__init__(reason); self.code=code; self.reason=reason; self.detail=detail
    def as_dict(self) -> dict[str, Any]:
        return {"schemaVersion":1,"stageId":STAGE_ID,"laneId":LANE_ID,"scientificPurpose":PURPOSE,"status":"REFUSED_BEFORE_SYNTAX_OR_SOLVER","code":self.code,"reason":self.reason,"detail":self.detail}

def load_json(path: Path) -> dict[str, Any]:
    try: value=json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc: raise Refusal("json",f"cannot read JSON: {path}",str(exc)) from exc
    if not isinstance(value,dict): raise Refusal("json-shape",f"expected object: {path}")
    return value

def raw_sha256(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def git(root: Path,*args:str)->str: return subprocess.check_output(["git",*args],cwd=root,text=True).strip()
def near(actual: Any, expected: float, tol: float=1e-12)->bool: return isinstance(actual,(int,float)) and not isinstance(actual,bool) and math.isfinite(float(actual)) and abs(float(actual)-expected)<=tol

def require_file(root: Path, rel: str, name: str)->Path:
    p=Path(rel)
    if p.is_absolute() or ".." in p.parts: raise Refusal("path",f"invalid {name} path",rel)
    q=root/p
    if not q.is_file(): raise Refusal("missing-file",f"missing {name}",rel)
    return q

def require_ancestor(root: Path, ancestor: str)->None:
    if subprocess.run(["git","merge-base","--is-ancestor",ancestor,"HEAD"],cwd=root,check=False).returncode!=0:
        raise Refusal("smoke-checkpoint","authorization does not descend from consumed formal smoke checkpoint",ancestor)

def git_blob_sha1(root: Path, rel: str)->str:
    try: return git(root,"rev-parse",f"HEAD:{Path(rel).as_posix()}")
    except Exception as exc: raise Refusal("git-blob",f"cannot resolve Git blob for {rel}",str(exc)) from exc

def load_module(name: str,path:Path):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise Refusal("module",f"cannot load {path}")
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

def require_exact_path(value: Any, root: str, path: str, code: str, case_id: str)->None:
    expected={"root":root,"path":path}
    if value!=expected: raise Refusal(code,"normalized data path changed",{"caseId":case_id,"actual":value,"expected":expected})

def validate(args: argparse.Namespace)->dict[str,Any]:
    root=args.repository_root.resolve(); app_root=args.application_root.resolve()
    expected_context={"GITHUB_ACTIONS":"true","GITHUB_EVENT_NAME":"workflow_dispatch","GITHUB_RUN_ATTEMPT":"1"}
    stale={k:(os.getenv(k),v) for k,v in expected_context.items() if os.getenv(k)!=v}
    if stale: raise Refusal("github-context","not exact first-attempt workflow_dispatch context",stale)
    if args.application_sha!=EXPECTED_APPLICATION_SHA or git(app_root,"rev-parse","HEAD")!=EXPECTED_APPLICATION_SHA: raise Refusal("application-sha","application checkout is not exact frozen SHA")
    if args.execution_key!=EXECUTION_KEY or not ID_RE.fullmatch(args.execution_key): raise Refusal("execution-key","wrong or invalid execution key",args.execution_key)
    if args.authorization_ordinal!=AUTHORIZATION_ORDINAL: raise Refusal("authorization-ordinal","wrong authorization ordinal",args.authorization_ordinal)
    require_ancestor(root,CONSUMED_SMOKE_MAIN_SHA)

    paths={
        "authorization":args.authorization,"proposal":args.proposal,"evidence":args.evidence,"analysisContract":args.analysis_contract,
        "proposalAdapter":args.proposal_adapter,"executionAdapter":args.execution_adapter,"executionWorkflow":args.execution_workflow,
        "runtimeLock":args.runtime_lock,"plan":args.plan,"analysisDriver":args.analysis_driver,"visibilityHelper":args.visibility_helper,
        "derivedChannels":args.derived_channels,"executor":args.executor,"aggregate":args.aggregate,"audit":args.audit,
        "authorizationProposalBuilder":args.authorization_proposal_builder,
    }
    abs_paths={k:require_file(root,v,k) for k,v in paths.items()}
    human_threshold=require_file(app_root,args.human_threshold,"humanThreshold")
    fixed={
        "lanePreregistration":root/LANE_PREREG,"v2ExecutionGuard":Path(__file__).resolve(),"smokeRecovery2Gate":root/SMOKE_GATE,
        "genericExecutionAdapter":root/GENERIC_EXECUTION_ADAPTER,"elevationHelper":root/ELEVATION_HELPER,
        "duplicateRunAudit":root/DUPLICATE_RUN_AUDIT,"runtimeProbe":root/RUNTIME_PROBE,
    }
    for k,p in fixed.items():
        if not p.is_file(): raise Refusal("missing-file",f"missing fixed dependency {k}",str(p))

    if git_blob_sha1(app_root,args.human_threshold)!=EXPECTED_HUMAN_THRESHOLD_GIT_BLOB_SHA1: raise Refusal("human-threshold-git-blob","frozen human threshold Git blob mismatch")
    if git_blob_sha1(root,args.derived_channels)!=EXPECTED_DERIVED_CHANNELS_GIT_BLOB_SHA1: raise Refusal("derived-channels-git-blob","frozen derived-channel Git blob mismatch")

    auth=load_json(abs_paths["authorization"]); manifest=load_json(abs_paths["proposal"]); evidence=load_json(abs_paths["evidence"]); contract=load_json(abs_paths["analysisContract"]); lane=load_json(fixed["lanePreregistration"]); smoke=load_json(fixed["smokeRecovery2Gate"])
    if lane.get("laneId")!=LANE_ID or lane.get("status")!="PREREGISTERED_NO_EXECUTION" or lane.get("scientificExecution") is not False: raise Refusal("lane","wrong lane preregistration")
    future=lane.get("futureAuthorization") or {}
    if future.get("executionKey")!=EXECUTION_KEY or future.get("authorizationOrdinal")!=AUTHORIZATION_ORDINAL or future.get("retryAllowed") is not False or future.get("resumeAllowed") is not False or future.get("rerunAllowed") is not False: raise Refusal("lane-authorization","future one-shot identity changed",future)
    boundary=lane.get("claimBoundary") or {}
    if boundary.get("noParameterTuning") is not True or boundary.get("productionAuthorized") is not False or boundary.get("pandoraOpened") is not False: raise Refusal("lane-boundary","claim boundary changed",boundary)
    source=lane.get("sourceScientificPayload") or {}
    source_expected={"applicationSha":EXPECTED_APPLICATION_SHA,"sourceEvidenceRunId":EXPECTED_EVIDENCE_RUN_ID,"sourceEvidenceArtifactId":EXPECTED_EVIDENCE_ARTIFACT_ID,"sourceEvidenceArtifactDigest":EXPECTED_EVIDENCE_DIGEST,"catalogBasis":"LIVE_DATE_TRANSFORMED_LEVEL_B_DIRECT_CATALOG_HANDOFF","caseCount":12,"photonHistoriesPerCase":20_000_000,"configuredPhotonHistoriesSum":EXPECTED_PHOTONS,"geometryCount":3,"fieldFactorBaseline":EXPECTED_FIELD_FACTOR,"aod550":EXPECTED_AOD550,"observerElevationM":800,"surfaceAlbedo":EXPECTED_ALBEDO,"mcSpherical":"1D","atmosphere":"AFGLUS","wavelengthDomainNm":[380,780]}
    source_stale={k:(source.get(k),v) for k,v in source_expected.items() if source.get(k)!=v}
    if source_stale or source.get("methods")!={"reference-vroom":6,"alis":6}: raise Refusal("lane-source","source payload changed",source_stale)

    smoke_required={"stageId":"jerusalem-tishrei-elevated-site-smoke-v2-recovery2","enabled":False,"infrastructureExecution":False,"scientificExecution":False,"scientificDiagnostic":False,"scientificUseProhibited":True,"executionKey":"jerusalem-tishrei-elevated-site-smoke-v2:infrastructure:3","smokeOrdinal":3,"consumed":True}
    smoke_stale={k:(smoke.get(k),v) for k,v in smoke_required.items() if smoke.get(k)!=v}
    note=str(smoke.get("note",""))
    if smoke_stale or str(SMOKE_RUN_ID) not in note or str(SMOKE_AUDIT_ARTIFACT_ID) not in note or SMOKE_AUDIT_DIGEST not in note: raise Refusal("smoke","formal 800m infrastructure smoke is not exact consumed PASS",smoke_stale)

    if manifest.get("stageId")!=STAGE_ID or manifest.get("batchId")!=BATCH_ID or manifest.get("proposalOnly") is not True or manifest.get("scientificExecution") is not False: raise Refusal("manifest-header","wrong source manifest boundary")
    event=manifest.get("preregisteredEvent") or {}; sem=event.get("threeStarSemantics") or {}; atm=event.get("atmosphere") or {}
    if not near(event.get("sunDepressionDeg"),EXPECTED_EVENT_DEP) or not near(atm.get("aod550"),EXPECTED_AOD550) or not near(sem.get("fieldFactorBaseline"),EXPECTED_FIELD_FACTOR): raise Refusal("event","event depression/AOD/F changed",event)
    if sem.get("requiredCount")!=3 or sem.get("stabilitySeconds")!=60 or sem.get("magnitudeBasis")!="effective" or not near(sem.get("magnitudeThreshold"),1.7): raise Refusal("event-semantics","Three-Star semantics changed",sem)
    src=event.get("sourceEvidence") or {}
    if src.get("workflowRunId")!=EXPECTED_EVIDENCE_RUN_ID or src.get("artifactId")!=EXPECTED_EVIDENCE_ARTIFACT_ID or src.get("artifactDigest")!=EXPECTED_EVIDENCE_DIGEST or src.get("catalogBasis")!="LIVE_DATE_TRANSFORMED_LEVEL_B_DIRECT_CATALOG_HANDOFF": raise Refusal("source-evidence","Tammuz source evidence changed",src)
    runtime=manifest.get("runtime") or {}; runtime_stale={k:(runtime.get(k),v) for k,v in EXPECTED_RUNTIME.items() if runtime.get(k)!=v}
    if runtime_stale: raise Refusal("runtime","frozen runtime changed",runtime_stale)
    frozen=manifest.get("frozenInputs") or {}
    if frozen.get("wavelengthDomainNm")!=[380,780] or frozen.get("molecularAbsorption")!="crs" or frozen.get("mcSpherical")!="1D" or not near(frozen.get("alisSpectralImportanceSamplingNm"),EXPECTED_ALIS_IS_NM) or not near(frozen.get("albedo"),EXPECTED_ALBEDO): raise Refusal("rt-contract","frozen RT inputs changed",frozen)

    adapter=load_module("tammuz_proposal_adapter",abs_paths["proposalAdapter"])
    try: adapter.validate_manifest(manifest)
    except Exception as exc: raise Refusal("manifest-adapter","proposal adapter rejected manifest",str(exc)) from exc
    geometries=manifest.get("geometries"); cases=manifest.get("cases"); limits=manifest.get("limits") or {}
    if not isinstance(geometries,list) or len(geometries)!=3 or not isinstance(cases,list) or len(cases)!=12: raise Refusal("shape","expected 3 geometries / 12 cases")
    by_gid={g.get("geometryId"):g for g in geometries if isinstance(g,dict)}
    if set(by_gid)!=set(EXPECTED_GEOMETRIES): raise Refusal("geometry-ids","wrong geometry IDs",sorted(by_gid))
    for gid,exp in EXPECTED_GEOMETRIES.items():
        g=by_gid[gid]
        if (g.get("target") or {}).get("catalogId")!=exp["catalogId"] or not near(g.get("sunDepressionDeg"),EXPECTED_EVENT_DEP) or not near(g.get("targetAltitudeDeg"),exp["alt"]) or not near(g.get("relativeAzimuthDeg"),exp["relAz"]) or not near(g.get("observerElevationM"),800) or not near(g.get("aod550"),EXPECTED_AOD550): raise Refusal("geometry","frozen geometry changed",gid)
    if limits!={"maximumCases":12,"maximumParallel":6,"maximumConfiguredMcPhotonsSum":EXPECTED_PHOTONS,"perCaseTimeoutSeconds":900}: raise Refusal("limits","limits changed",limits)
    if [c.get("ordinal") for c in cases]!=list(range(1,13)) or len({c.get("caseId") for c in cases})!=12 or len({c.get("seed") for c in cases})!=12: raise Refusal("case-identity","case identity changed")
    if sum(int(c.get("photonHistories",0)) for c in cases)!=EXPECTED_PHOTONS or any(c.get("photonHistories")!=20_000_000 for c in cases): raise Refusal("photons","photon accounting changed")
    if Counter(c.get("method") for c in cases)!=Counter({"alis":6,"reference-vroom":6}): raise Refusal("methods","method count changed")
    groups=defaultdict(list)
    for c in cases: groups[c.get("groupId")].append(c)
    if set(groups)!=set(by_gid): raise Refusal("groups","case group set changed")
    for gid,group in groups.items():
        if len(group)!=4:
            raise Refusal("group-size","wrong per-geometry case count",gid)
        for method in ("alis","reference-vroom"):
            if sorted(c.get("block") for c in group if c.get("method")==method)!=[1,2]: raise Refusal("blocks","wrong replicate blocks",{"group":gid,"method":method})
    for c in cases:
        try:
            rc,g=adapter.resolve_case(manifest,c["caseId"]); inp=adapter.normalized_inputs(manifest,rc,g)
        except Exception as exc: raise Refusal("normalized","cannot resolve frozen case",{"case":c.get("caseId"),"reason":str(exc)}) from exc
        if not near(inp.get("sunDepressionDeg"),EXPECTED_EVENT_DEP) or not near(inp.get("observerElevationM"),800) or not near(inp.get("aod550"),EXPECTED_AOD550) or not near(inp.get("albedo"),EXPECTED_ALBEDO) or not near(inp.get("alisSpectralImportanceSamplingNm"),405): raise Refusal("normalized-physics","normalized physics drift",c["caseId"])
        if inp.get("mcSpherical")!="1D" or inp.get("molecularAbsorption")!="crs" or inp.get("wavelengthDomainNm")!=[380,780]: raise Refusal("normalized-rt","normalized RT drift",c["caseId"])
        require_exact_path(inp.get("atmosphere"),"libRadtranData","atmmod/afglus.dat","normalized-atmosphere",c["caseId"])
        require_exact_path(inp.get("solarFlux"),"libRadtranData","solar_flux/atlas_plus_modtran","normalized-solar",c["caseId"])

    if evidence.get("applicationMainSha")!=EXPECTED_APPLICATION_SHA or (evidence.get("source") or {}).get("workflowRunId")!=EXPECTED_EVIDENCE_RUN_ID or (evidence.get("source") or {}).get("artifactId")!=EXPECTED_EVIDENCE_ARTIFACT_ID or (evidence.get("source") or {}).get("artifactDigest")!=EXPECTED_EVIDENCE_DIGEST or (evidence.get("source") or {}).get("transformedCatalogCount")!=7653: raise Refusal("evidence","frozen evidence provenance changed")
    evidence_by={s.get("catalogId"):s for s in evidence.get("stars",[]) if isinstance(s,dict)}
    if set(evidence_by)!={"HR 5191","HR 4905","HR 3982"}: raise Refusal("evidence-stars","evidence star set changed")
    for gid,exp in EXPECTED_GEOMETRIES.items():
        s=evidence_by[exp["catalogId"]]; g=by_gid[gid]
        if not near((s.get("eventGeometry") or {}).get("targetAltitudeDeg"),g.get("targetAltitudeDeg")) or not near((s.get("eventGeometry") or {}).get("relativeAzimuthDeg"),g.get("relativeAzimuthDeg")): raise Refusal("evidence-geometry","manifest/evidence geometry mismatch",exp["catalogId"])
        spectral=((s.get("skyChannels") or {}).get("spectral") or {})
        if spectral.get("available") is not False or spectral.get("reason")!="VALIDATED_V3_PRIMARY_PROVIDER_SPECTRAL_RUNTIME_NOT_IMPLEMENTED": raise Refusal("spectral-boundary","Level-B spectral boundary changed",exp["catalogId"])
    if evidence_by["HR 3982"].get("completingStar") is not True: raise Refusal("completing-star","Regulus no longer completing")

    if contract.get("analysisId")!="jerusalem-tammuz-direct-mystic-level-b-comparison-v1" or contract.get("scientificExecution") is not False or not near((contract.get("skyOnlyVisibilitySubstitution") or {}).get("fieldFactor"),3.14): raise Refusal("analysis","analysis contract changed")
    if (contract.get("levelBComparison") or {}).get("rawCatalogReconstructionAllowed") is not False or (contract.get("levelBComparison") or {}).get("fullSpectrumLevelBValidationClaimAllowed") is not False: raise Refusal("analysis-boundary","analysis boundary changed")

    auth_required={"stageId":STAGE_ID,"scientificPurpose":LANE_ID,"laneId":LANE_ID,"authorized":True,"scientificExecution":True,"scientificDiagnostic":True,"successDoesNotAuthorizeProduction":True,"executionKey":EXECUTION_KEY,"batchId":BATCH_ID,"proposalPath":args.proposal,"authorizationOrdinal":AUTHORIZATION_ORDINAL,"consumed":False,"requiredSmokeRunId":SMOKE_RUN_ID,"requiredSmokeAuditArtifactId":SMOKE_AUDIT_ARTIFACT_ID,"requiredSmokeAuditArtifactDigest":SMOKE_AUDIT_DIGEST}
    auth_stale={k:(auth.get(k),v) for k,v in auth_required.items() if auth.get(k)!=v}
    if auth_stale: raise Refusal("authorization","one-purpose authorization fields changed",auth_stale)
    head=git(root,"rev-parse","HEAD"); parents=git(root,"rev-list","--parents","-n","1","HEAD").split()
    if head!=args.authorization_ref or auth.get("exactAuthorizationCommit")!=head or len(parents)!=2 or auth.get("exactAuthorizationParentCommit")!=parents[1]: raise Refusal("authorization-commit","authorization commit/parent binding changed",{"head":head,"parents":parents})
    changed=git(root,"diff","--name-only",parents[1],head).splitlines()
    if changed!=[Path(args.authorization).as_posix()]: raise Refusal("one-purpose-commit","authorization commit must change exactly one file",changed)

    hash_map={
        "proposalRawSha256":abs_paths["proposal"],"levelBEvidenceRawSha256":abs_paths["evidence"],"analysisContractRawSha256":abs_paths["analysisContract"],"proposalAdapterRawSha256":abs_paths["proposalAdapter"],"executionAdapterRawSha256":abs_paths["executionAdapter"],"executionWorkflowRawSha256":abs_paths["executionWorkflow"],"runtimeLockRawSha256":abs_paths["runtimeLock"],"planRawSha256":abs_paths["plan"],"analysisDriverRawSha256":abs_paths["analysisDriver"],"visibilityHelperRawSha256":abs_paths["visibilityHelper"],"derivedChannelsRawSha256":abs_paths["derivedChannels"],"humanThresholdRawSha256":human_threshold,"executorRawSha256":abs_paths["executor"],"aggregateRawSha256":abs_paths["aggregate"],"auditRawSha256":abs_paths["audit"],"authorizationProposalBuilderRawSha256":abs_paths["authorizationProposalBuilder"],"lanePreregistrationRawSha256":fixed["lanePreregistration"],"v2ExecutionGuardRawSha256":fixed["v2ExecutionGuard"],"smokeRecovery2GateRawSha256":fixed["smokeRecovery2Gate"],"genericExecutionAdapterRawSha256":fixed["genericExecutionAdapter"],"elevationHelperRawSha256":fixed["elevationHelper"],"duplicateRunAuditRawSha256":fixed["duplicateRunAudit"],"runtimeProbeRawSha256":fixed["runtimeProbe"]}
    hash_stale={k:(auth.get(k),raw_sha256(p)) for k,p in hash_map.items() if auth.get(k)!=raw_sha256(p)}
    if hash_stale: raise Refusal("hash-bindings","authorization hash bindings stale",hash_stale)

    workflow_text=abs_paths["executionWorkflow"].read_text(encoding="utf-8")
    if EXPECTED_RUN_NAME not in workflow_text: raise Refusal("run-name","execution workflow lost exact duplicate-audit run-name")
    if "fetch-depth: 0" not in workflow_text: raise Refusal("authorization-checkout","execution workflow must fetch full authorization ancestry")
    repaired=abs_paths["executionAdapter"].read_text(encoding="utf-8")
    for token in ("EXPECTED_AOD550 = 0.18","EXPECTED_OBSERVER_ELEVATION_M = 800.0","atm_z_grid","zout 0.000000","mc_elevation_file"):
        if token not in repaired: raise Refusal("elevation-repair","reviewed Tammuz 800m adapter drifted",token)

    return {
        "schemaVersion":1,"stageId":STAGE_ID,"laneId":LANE_ID,"scientificPurpose":PURPOSE,
        "status":"AUTHORIZED_TAMMUZ_V2_AFTER_FORMAL_SMOKE_PASS","batchId":BATCH_ID,
        "authorizationRef":head,"authorizationOrdinal":AUTHORIZATION_ORDINAL,"executionKey":EXECUTION_KEY,
        "proposalRawSha256":raw_sha256(abs_paths["proposal"]),"executionAdapterRawSha256":raw_sha256(abs_paths["executionAdapter"]),"runtimeLockRawSha256":raw_sha256(abs_paths["runtimeLock"]),"executionWorkflowRawSha256":raw_sha256(abs_paths["executionWorkflow"]),
        "requiredSmokeRunId":SMOKE_RUN_ID,"requiredSmokeAuditArtifactId":SMOKE_AUDIT_ARTIFACT_ID,"requiredSmokeAuditArtifactDigest":SMOKE_AUDIT_DIGEST,
        "caseCount":12,"configuredMcPhotonsSum":EXPECTED_PHOTONS,
        "boundary":"one-purpose Tammuz authorization verified before syntax or solver; exact transformed-row 12-case/240M science, F=3.14, AOD550=0.18 and reviewed 800m atm_z_grid representation preserved; no retry/resume/rerun or production authorization",
    }

def dump(v:Any)->str: return json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+"\n"
def main()->int:
    p=argparse.ArgumentParser(); p.add_argument("--repository-root",type=Path,default=Path(".")); p.add_argument("--application-root",type=Path,required=True); p.add_argument("--application-sha",required=True)
    for name in ("authorization","proposal","evidence","analysis-contract","proposal-adapter","execution-adapter","execution-workflow","runtime-lock","plan","analysis-driver","visibility-helper","derived-channels","executor","aggregate","audit","authorization-proposal-builder"): p.add_argument(f"--{name}",required=True)
    p.add_argument("--human-threshold",required=True); p.add_argument("--authorization-ref",required=True); p.add_argument("--execution-key",required=True); p.add_argument("--authorization-ordinal",type=int,required=True); p.add_argument("--output",type=Path,required=True); args=p.parse_args()
    try:
        report=validate(args); args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(dump(report),encoding="utf-8"); print(dump(report),end=""); return 0
    except Exception as exc:
        report=exc.as_dict() if isinstance(exc,Refusal) else Refusal("unexpected",str(exc)).as_dict(); args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(dump(report),encoding="utf-8"); print(dump(report),end="",file=sys.stderr); return 2
if __name__=="__main__": raise SystemExit(main())
