#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,os,re,subprocess,sys
from pathlib import Path
from typing import Any
STAGE_ID="cross-geometry-final-convergence-v1"; SHA=re.compile(r"^[0-9a-f]{64}$"); ID=re.compile(r"^[a-z0-9][a-z0-9._:-]{2,159}$")
class Refusal(RuntimeError):
    def __init__(self,code:str,reason:str,detail:Any=None): super().__init__(reason);self.code=code;self.reason=reason;self.detail=detail

def load(p:Path)->dict[str,Any]:
    try:v=json.loads(p.read_text())
    except Exception as e:raise Refusal("json",f"cannot read {p}",str(e))
    if not isinstance(v,dict):raise Refusal("json",f"expected object {p}")
    return v
def digest(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(v:Any)->str:return json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+"\n"
def git(root:Path,*args:str)->str:return subprocess.check_output(["git",*args],cwd=root,text=True).strip()
def rel(p:Path,name:str)->str:
    if p.is_absolute() or ".." in p.parts:return (_ for _ in ()).throw(Refusal("path",f"invalid {name} path",str(p)))
    return p.as_posix()
def validate(root:Path,paths:dict[str,Path],authorization_ref:str,execution_key:str,ordinal:int,github_context:bool=True,one_purpose:bool=True)->dict[str,Any]:
    root=root.resolve(); r={k:rel(v,k) for k,v in paths.items()}; a={k:root/v for k,v in r.items()}
    for k,p in a.items():
        if not p.is_file():raise Refusal("missing",f"missing {k}",str(p))
    if not ID.fullmatch(execution_key):raise Refusal("key","invalid execution key")
    if ordinal<1:raise Refusal("ordinal","ordinal must be positive")
    if github_context:
        expected={"GITHUB_ACTIONS":"true","GITHUB_EVENT_NAME":"workflow_dispatch","GITHUB_RUN_ATTEMPT":"1"}; stale={k:(os.getenv(k),v) for k,v in expected.items() if os.getenv(k)!=v}
        if stale:raise Refusal("context","not first-attempt manual dispatch",stale)
    p=load(a["proposal"]); s=load(a["sourceScreening"]); c=load(a["sourceConvergence"]); prov=load(a["sourceProvenance"]); auth=load(a["authorization"]); tmpl=load(a["authorizationTemplate"])
    required={"schemaVersion":1,"stageId":STAGE_ID,"batchId":"cross-geometry-final-convergence-screening-v1","proposalOnly":True,"scientificExecution":False,"successDoesNotAuthorizeProduction":True}
    stale={k:(p.get(k),v) for k,v in required.items() if p.get(k)!=v}
    if stale:raise Refusal("proposal","proposal header changed",stale)
    if s.get("stageId")!="cross-geometry-stage-two-v1" or s.get("status")!="STAGE_TWO_SCREENING_ANALYZED":raise Refusal("source","wrong stage-two screening")
    if c.get("stageId")!="cross-geometry-convergence-v2" or c.get("status")!="REANALYZED_WITH_MEAN_UNCERTAINTY":raise Refusal("convergence","wrong convergence analysis")
    if prov.get("stageId")!=STAGE_ID or prov.get("status")!="SOURCE_STAGE_TWO_FROZEN":raise Refusal("provenance","wrong provenance")
    if p.get("sourceStageTwoScreeningRawSha256")!=digest(a["sourceScreening"]) or prov.get("sourceStageTwoScreeningRawSha256")!=digest(a["sourceScreening"]):raise Refusal("source-hash","screening hash changed")
    if p.get("sourceConvergenceV2RawSha256")!=digest(a["sourceConvergence"]) or prov.get("sourceConvergenceV2RawSha256")!=digest(a["sourceConvergence"]):raise Refusal("convergence-hash","convergence hash changed")
    expected_provenance={"sourceScientificRunId":30863907633,"sourceAuthorizationRef":"5f7a5a7f2f9270328315edda12580cd72fda4c51","sourceAuthorizationOrdinal":3,"sourceExecutionKey":"cross-geometry-stage-two-v1:screening:3","sourceScreeningArtifactId":8875564303,"sourceScreeningArtifactName":"cross-geometry-stage-two-v1-screening","sourceScreeningArtifactDigest":"sha256:3cbc3bfd2c0121de258b9c11d245e4e3d8f160e786a871a59515d405e64ee5de","sourceAggregateArtifactId":8875550285,"sourceAuditArtifactId":8875557534,"sourceCaseArtifactCount":16,"sourceCombinedCaseResultCount":40,"sourceCombinedConfiguredMcPhotonsSum":800_000_000,"authorizationCreated":False,"scientificExecution":False}
    stale_provenance={k:(prov.get(k),v) for k,v in expected_provenance.items() if prov.get(k)!=v}
    if stale_provenance:raise Refusal("provenance","source run/artifact changed",stale_provenance)
    cases=p.get("cases")
    if not isinstance(cases,list) or len(cases)!=26 or [x.get("ordinal") for x in cases]!=list(range(1,27)):raise Refusal("cases","case set changed")
    if sum(x.get("photonHistories",0) for x in cases)!=520_000_000 or any(x.get("photonHistories")!=20_000_000 for x in cases):raise Refusal("photons","photon accounting changed")
    if len({x.get("seed") for x in cases})!=26:raise Refusal("seeds","seeds duplicated")
    if {x.get("purpose") for x in cases}!={"continuation","alis-reference-diagnostic"}:raise Refusal("purpose","purpose set changed")
    limits=p.get("limits",{})
    if limits.get("maximumCases")!=26 or limits.get("maximumConfiguredMcPhotonsSum")!=520_000_000 or limits.get("maximumParallel")!=16 or limits.get("perCaseTimeoutSeconds")!=900:raise Refusal("limits","execution limits changed",limits)
    diagnostic=[x for x in cases if x.get("purpose")=="alis-reference-diagnostic"]
    continuation=[x for x in cases if x.get("purpose")=="continuation"]
    if len(diagnostic)!=18 or len(continuation)!=8:raise Refusal("design","purpose accounting changed")
    if {x.get("groupId") for x in diagnostic}!={"g01-reference-bridge","g06-late-opposite-high-aerosol"} or {x.get("alisSpectralImportanceSamplingNm") for x in diagnostic}!={500.0,550.0,600.0}:raise Refusal("design","diagnostic design changed")
    for group in ("g01-reference-bridge","g06-late-opposite-high-aerosol"):
        for ref in (500.0,550.0,600.0):
            subset=[x for x in diagnostic if x.get("groupId")==group and x.get("alisSpectralImportanceSamplingNm")==ref]
            if len(subset)!=3:raise Refusal("design","diagnostic replicate count changed",{"group":group,"referenceNm":ref,"count":len(subset)})
    disabled={"schemaVersion":1,"stageId":STAGE_ID,"authorized":False,"scientificExecution":False,"scientificDiagnostic":False,"authorizationOrdinal":0,"consumed":False,"exactAuthorizationParentCommit":None,"exactAuthorizationCommit":None}
    if any(tmpl.get(k)!=v for k,v in disabled.items()):raise Refusal("template","authorization template not disabled")
    if set(auth)!=set(tmpl):raise Refusal("schema","authorization schema changed")
    expected_auth={"schemaVersion":1,"stageId":STAGE_ID,"authorized":True,"scientificExecution":True,"scientificDiagnostic":True,"successDoesNotAuthorizeProduction":True,"executionKey":execution_key,"batchId":p["batchId"],"proposalPath":r["proposal"],"proposalRawSha256":digest(a["proposal"]),"sourceScreeningRawSha256":digest(a["sourceScreening"]),"sourceConvergenceV2RawSha256":digest(a["sourceConvergence"]),"sourceProvenanceRawSha256":digest(a["sourceProvenance"]),"authorizationTemplateRawSha256":digest(a["authorizationTemplate"]),"baseAdapterRawSha256":digest(a["baseAdapter"]),"executionAdapterRawSha256":digest(a["executionAdapter"]),"duplicateRunAuditRawSha256":digest(a["duplicateRunAudit"]),"runtimeProbeRawSha256":digest(a["runtimeProbe"]),"executionWorkflowRawSha256":digest(a["executionWorkflow"]),"runtimeLockRawSha256":digest(a["runtimeLock"]),"planRawSha256":digest(a["plan"]),"analysisDriverRawSha256":digest(a["analysisDriver"]),"convergenceModuleRawSha256":digest(a["convergenceModule"]),"executorRawSha256":digest(a["executor"]),"aggregateRawSha256":digest(a["aggregate"]),"auditRawSha256":digest(a["audit"]),"authorizationOrdinal":ordinal,"consumed":False,"exactAuthorizationCommit":None}
    stale={k:(auth.get(k),v) for k,v in expected_auth.items() if auth.get(k)!=v}
    if stale:raise Refusal("auth","authorization stale",stale)
    head=git(root,"rev-parse","HEAD"); parent=git(root,"rev-parse","HEAD^")
    if head!=authorization_ref:raise Refusal("ref","HEAD differs from authorization ref",{"head":head,"input":authorization_ref})
    if auth.get("exactAuthorizationParentCommit")!=parent:raise Refusal("parent","authorization parent mismatch")
    if one_purpose:
        changed=git(root,"diff","--name-only",parent,head).splitlines()
        if changed!=[r["authorization"]]:raise Refusal("one-purpose","authorization commit changed unexpected files",changed)
    return {"schemaVersion":1,"stageId":STAGE_ID,"status":"AUTHORIZED","batchId":p["batchId"],"executionKey":execution_key,"authorizationRef":head,"authorizationParentCommit":parent,"authorizationOrdinal":ordinal,"proposalRawSha256":digest(a["proposal"]),"executionAdapterRawSha256":digest(a["executionAdapter"]),"runtimeLockRawSha256":digest(a["runtimeLock"]),"executionWorkflowRawSha256":digest(a["executionWorkflow"]),"sourceScreeningRawSha256":digest(a["sourceScreening"]),"sourceConvergenceV2RawSha256":digest(a["sourceConvergence"]),"sourceProvenanceRawSha256":digest(a["sourceProvenance"]),"boundary":"authorized exact bounded final-convergence matrix; no production validity"}
def main()->int:
    q=argparse.ArgumentParser();q.add_argument("--repository-root",type=Path,default=Path("."));
    names=["authorization","authorization-template","proposal","source-screening","source-convergence","source-provenance","base-adapter","execution-adapter","duplicate-run-audit","runtime-probe","execution-workflow","runtime-lock","plan","analysis-driver","convergence-module","executor","aggregate","audit"]
    for n in names:q.add_argument("--"+n,type=Path,required=True)
    q.add_argument("--authorization-ref",required=True);q.add_argument("--execution-key",required=True);q.add_argument("--authorization-ordinal",type=int,required=True);q.add_argument("--output",type=Path,required=True);x=q.parse_args()
    mapping={"authorization":"authorization","authorization-template":"authorizationTemplate","proposal":"proposal","source-screening":"sourceScreening","source-convergence":"sourceConvergence","source-provenance":"sourceProvenance","base-adapter":"baseAdapter","execution-adapter":"executionAdapter","duplicate-run-audit":"duplicateRunAudit","runtime-probe":"runtimeProbe","execution-workflow":"executionWorkflow","runtime-lock":"runtimeLock","plan":"plan","analysis-driver":"analysisDriver","convergence-module":"convergenceModule","executor":"executor","aggregate":"aggregate","audit":"audit"}
    paths={mapping[n]:getattr(x,n.replace("-","_")) for n in names}
    try:
        result=validate(x.repository_root,paths,x.authorization_ref,x.execution_key,x.authorization_ordinal);x.output.parent.mkdir(parents=True,exist_ok=True);x.output.write_text(dump(result));print(dump(result),end="");return 0
    except Refusal as e:
        r={"schemaVersion":1,"stageId":STAGE_ID,"status":"REFUSED_BEFORE_SYNTAX_OR_SOLVER","code":e.code,"reason":e.reason,"detail":e.detail};x.output.parent.mkdir(parents=True,exist_ok=True);x.output.write_text(dump(r));print(dump(r),end="",file=sys.stderr);return 2
if __name__=="__main__":raise SystemExit(main())
