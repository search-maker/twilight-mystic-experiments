from __future__ import annotations

import hashlib
import json
import math
from itertools import product
from pathlib import Path
from typing import Any

STAGE_ID = "aerosol-family-challenge-v2"
DESIGN_SCHEMA_VERSION = 3
REPOSITORY_FULL_NAME = "search-maker/twilight-mystic-experiments"
PUBLIC_REPO_MAIN_SHA = "34edfef1bb9a236f15e6ed456c3e8ef8871a4fc9"
PUBLIC_REPO_MAIN_TREE_SHA = "a41d45750607bd30d44fc2cc9d43bdf494c3fd7e"
FAMILIES = {"rural": 1, "maritime": 4, "urban": 5, "tropospheric": 6}
SEASONS = {"spring-summer": 1, "fall-winter": 2}
SUN_DEPRESSION_DEG = (2.0, 4.0, 6.0, 8.0)
AOD550_VALUES = (0.10, 0.30)
REPLICATES = (1, 2, 3)
V2_GEOMETRY_TEMPLATES = (
    {"geometryId":"g02-early-near-low","geometryTag":"near-solar","targetAltitudeDeg":10.0,"relativeAzimuthDeg":30.0,"observerElevationM":0.0},
    {"geometryId":"g04-mid-perpendicular","geometryTag":"cross-solar","targetAltitudeDeg":30.0,"relativeAzimuthDeg":90.0,"observerElevationM":0.0},
    {"geometryId":"g06-late-opposite-high-aerosol","geometryTag":"opposite-solar","targetAltitudeDeg":45.0,"relativeAzimuthDeg":180.0,"observerElevationM":0.0},
)
V2_PHOTON_HISTORIES_PER_CASE = 20_000_000
SEED_DERIVATION_NAMESPACE = "aerosol-family-challenge-v2|group-seed|sha256-v1"
SEED_DOMAIN_MAX_EXCLUSIVE = 2_147_483_647

def _derive_candidate_seed_rows() -> tuple[dict[str,Any], ...]:
    rows=[]; used=set()
    for dep,geo,aod,rep in product(SUN_DEPRESSION_DEG,V2_GEOMETRY_TEMPLATES,AOD550_VALUES,REPLICATES):
        cell_id=f"afc2-d{dep:02.0f}-{geo['geometryId']}-aod{int(round(aod*100)):02d}"
        counter=0
        while True:
            material=f"{SEED_DERIVATION_NAMESPACE}|analysisCellId={cell_id}|replicate={rep}|counter={counter}"
            digest=hashlib.sha256(material.encode("utf-8")).digest()
            seed=(int.from_bytes(digest[:8],"big") % (SEED_DOMAIN_MAX_EXCLUSIVE-1))+1
            if seed not in used: break
            counter+=1
        used.add(seed)
        rows.append({"analysisCellId":cell_id,"replicate":rep,"collisionCounter":counter,"derivationMaterialSha256":hashlib.sha256(material.encode("utf-8")).hexdigest(),"seed":seed})
    return tuple(rows)

CANDIDATE_SEED_ROWS = _derive_candidate_seed_rows()
CANDIDATE_GROUP_SEEDS = tuple(row["seed"] for row in CANDIDATE_SEED_ROWS)
CANDIDATE_SEED_FIRST = CANDIDATE_GROUP_SEEDS[0]
CANDIDATE_SEED_LAST = CANDIDATE_GROUP_SEEDS[-1]
EXPECTED_ANALYSIS_CELL_COUNT=24
EXPECTED_GROUP_COUNT=72
EXPECTED_CASE_COUNT=576
EXPECTED_STATES_PER_GROUP=8
FULL_SPECTRUM_START_NM=380
FULL_SPECTRUM_STOP_NM=780
CALCULATION_GRID_STEP_NM=1
CALCULATION_GRID_NODE_COUNT=401
RAW_OUTPUT_GRID_STEP_NM=0.05
RAW_OUTPUT_GRID_NODE_COUNT=8001
NUMERICAL_METHOD="reference-vroom-1nm"
REQUIRED_OUTPUT_CHANNELS=("photopicLuminanceCdM2","scotopicLuminanceScotCdM2","scotopicPhotopicRatio","johnsonVEffectiveRadiance_mW_m2_nm_sr","rawSpectrum0p05nm380to780","mcStandardDeviationSpectrum0p05nm380to780")
PAIRING_FIELDS=("sunDepressionDeg","targetAltitudeDeg","relativeAzimuthDeg","observerElevationM","aod550","seed","photonHistories","numericalMethod")

class Refusal(RuntimeError): pass

def dump(value:Any)->str: return json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+"\n"
def canonical_bytes(value:Any)->bytes: return json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def canonical_sha256(value:Any)->str: return hashlib.sha256(canonical_bytes(value)).hexdigest()
def raw_sha256(path:Path)->str: return hashlib.sha256(path.read_bytes()).hexdigest()
def git_blob_sha1(path:Path)->str:
    data=path.read_bytes(); return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def _finite(value:Any,name:str,lo:float,hi:float)->float:
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(float(value)): raise Refusal(f"{name} must be finite")
    x=float(value)
    if not lo<=x<=hi: raise Refusal(f"{name} outside [{lo}, {hi}]")
    return x

def validate_geometry_templates(value:Any)->list[dict[str,Any]]:
    if not isinstance(value,list) or value != [dict(x) for x in V2_GEOMETRY_TEMPLATES]: raise Refusal("v2 geometry templates changed from source-bound design")
    for row in value:
        _finite(row.get("targetAltitudeDeg"),"targetAltitudeDeg",0,90); _finite(row.get("relativeAzimuthDeg"),"relativeAzimuthDeg",0,180)
        if _finite(row.get("observerElevationM"),"observerElevationM",0,10000) != 0.0: raise Refusal("v2 source-bound geometries require observer elevation 0 m")
    return value

def validate_photon_schedule(v:Any)->dict[str,int]:
    if not isinstance(v,dict) or set(v)!={"2","4","6","8"}: raise Refusal("photon schedule must define exactly 2,4,6,8 degrees")
    if any(isinstance(x,bool) or not isinstance(x,int) or x!=V2_PHOTON_HISTORIES_PER_CASE for x in v.values()): raise Refusal("v2 review budget is uniformly 20M per case")
    return v

def validate_group_seeds(v:Any)->list[int]:
    if not isinstance(v,list) or len(v)!=EXPECTED_GROUP_COUNT: raise Refusal("exactly 72 explicit group seeds required")
    if any(isinstance(s,bool) or not isinstance(s,int) or not 0<s<2_147_483_647 for s in v): raise Refusal("invalid group seed")
    if len(set(v))!=EXPECTED_GROUP_COUNT: raise Refusal("group seeds must be unique between groups")
    if tuple(v)!=CANDIDATE_GROUP_SEEDS: raise Refusal("candidate seed ledger changed; version a new review design")
    if len(CANDIDATE_SEED_ROWS)!=72 or any(row["collisionCounter"]!=0 for row in CANDIDATE_SEED_ROWS): raise Refusal("deterministic candidate seed derivation changed")
    return v

def validate_source_bindings(v:Any)->dict[str,Any]:
    if not isinstance(v,dict): raise Refusal("sourceBindings missing")
    if v.get("repositoryFullName")!=REPOSITORY_FULL_NAME or v.get("publicRepoMainSha")!=PUBLIC_REPO_MAIN_SHA or v.get("publicRepoMainTreeSha")!=PUBLIC_REPO_MAIN_TREE_SHA: raise Refusal("repository source binding changed")
    expected={
      "geometryBasis":("experiments/mystic-batch-v1/manifest.cross-geometry-pilot.proposal.json","b006c33eb37bece85d1330d44d56450d9496a447"),
      "baseScientificAdapter":("experiments/mystic-batch-v1/scientific_adapter.py","f69418843b3265f72c620ad3ff56a2582da461f1"),
      "baseScientificCaseExecutor":("experiments/mystic-batch-v1/scientific_case_executor.py","df679e54e2c95aa25f772927b2424d21b555638c"),
      "scientificExecutionContract":("experiments/mystic-batch-v1/SCIENTIFIC_EXECUTION.md","bb4c5b04aef3b717cea27c686a43cd1dbca11803"),
      "runtimeLock":("experiments/mystic-batch-v1/runtime-lock.micromamba.json","8573f62829371a0eb866976a5062ea61dc0767b1"),
      "fullSpectrumExecutorBasis":("experiments/full-spectrum-estimator-pilot-v2/executor.py","4d4ee9af433157182185784ded162fb139c9fa2d"),
      "reviewedOneNmGrid":("review/full-spectrum-estimator-pilot-v2/wavelength-grid-1nm.dat","3bb3db96580d555ef758f57cabd6cac55b61cebb"),
      "derivedChannelImplementationBasis":("review/full-spectrum-estimator-pilot-v2/build_full_spectrum_training_handoff.py","9bc53956fc4a49935ba2957087d8bf4203b7e8be"),
      "fullSpectrumPostprocessGridContract":("experiments/full-spectrum-estimator-pilot-v2/postprocess-contract.ordinal16.v7.json","47e90aa128942276e1510305449bb3c58930032e"),
    }
    for key,(path,blob) in expected.items():
        row=v.get(key)
        if not isinstance(row,dict) or row.get("path")!=path or row.get("gitBlobSha")!=blob: raise Refusal(f"source binding changed: {key}")
    rt=v["runtimeLock"]
    required_rt={
      "rawSha256":"3b5fbec964642b04c73a6423b3355dbcc4ba5e84f9614f6d74420491bacc20c5",
      "exactPackageSpec":"rubin-libradtran=2.0.6=py312pl5321he9373c2_1",
      "uvspecSha256":"2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3",
      "uvspecHelpSha256":"868aea5af762d968f6f62c4e1472916d25232ed9cab5be112d753b0823d20548",
      "libRadtranDataTreeSha256":"ad30b49177e9c84e46497d69faf0c75e466996b0d0003f1de210289ae9f847d7",
      "atmosphereSha256":"dab26290ed81c762ed0c607e5dc2d53393c1462a0c3a528bc5e3f5935191cfb5",
    }
    for k,x in required_rt.items():
        if rt.get(k)!=x: raise Refusal(f"runtime identity binding changed: {k}")
    sem=v.get("libRadtran206AerosolSemantics")
    if not isinstance(sem,dict) or sem.get("hazeCodes")!=FAMILIES or sem.get("seasonCodes")!=SEASONS or sem.get("vulcanCode")!=1: raise Refusal("libRadtran aerosol semantics changed")
    fs=v.get("fullSpectrumNumericalMethod")
    if not isinstance(fs,dict) or fs.get("method")!=NUMERICAL_METHOD or fs.get("mcVroom")!="on": raise Refusal("full-spectrum numerical method changed")
    calc=fs.get("calculationGrid")
    raw=fs.get("expectedRawOutputGrid")
    if calc!={"startNm":380,"stopNm":780,"stepNm":1,"nodeCount":401} or raw!={"startNm":380.0,"stopNm":780.0,"stepNm":0.05,"nodeCount":8001,"pointToleranceNm":0.00005}: raise Refusal("full-spectrum calculation/output grid contract changed")
    return v

def validate_seed_freshness_review(v:Any,seeds:list[int])->dict[str,Any]:
    if not isinstance(v,dict) or v.get("candidateOnly") is not True or v.get("authorizationPermitted") is not False: raise Refusal("review seeds must remain candidate-only")
    if v.get("reviewMainSha")!=PUBLIC_REPO_MAIN_SHA or v.get("candidateFirstSeed")!=seeds[0] or v.get("candidateLastSeed")!=seeds[-1] or v.get("candidateSeedCount")!=72 or v.get("candidateSeedCanonicalSha256")!=canonical_sha256(seeds): raise Refusal("seed review does not bind design")
    if v.get("status")!="R6_DETERMINISTIC_CANDIDATE_SEEDS_REVIEW_PENDING_DEFAULT_BRANCH_STABLE_DOUBLE_ENUMERATION_PROOF": raise Refusal("seed review status drift")
    deriv=v.get("candidateSeedDerivation")
    if not isinstance(deriv,dict) or deriv.get("namespace")!=SEED_DERIVATION_NAMESPACE or deriv.get("allCollisionCountersZero") is not True or deriv.get("ledgerCandidateSeedCanonicalSha256")!=canonical_sha256(seeds) or not isinstance(deriv.get("ledgerRawSha256"),str) or len(deriv["ledgerRawSha256"])!=64: raise Refusal("candidate seed derivation binding changed")
    ledger_path=Path(__file__).resolve().parent/"candidate-seed-ledger.v1.json"
    if not ledger_path.is_file() or deriv.get("ledgerRawSha256")!=raw_sha256(ledger_path): raise Refusal("candidate seed derivation does not bind exact local ledger bytes")
    ledger=json.loads(ledger_path.read_text())
    if ledger.get("candidateSeeds")!=seeds or ledger.get("namespace")!=SEED_DERIVATION_NAMESPACE or ledger.get("allCollisionCountersZero") is not True: raise Refusal("candidate seed ledger local content drift")
    expected_surface=[
      "all repository branches metadata",
      "all repository Actions run metadata except the current audit run self-row",
      "all repository Actions artifact metadata except metadata produced by the current audit run itself",
      "all-state pull request metadata and bodies",
      "all-state issue metadata and bodies",
      "all repository issue comments",
      "all repository pull-review comments",
      "all repository commit comments",
      "all Issue #60 comments",
      "two complete external metadata enumerations must have identical canonical bytes",
    ]
    if v.get("repositoryGlobalSurfaceContractR6")!=expected_surface or v.get("rawHistoricalArtifactBytesRequiredForFreeze") is not False or v.get("authorizationTimeExactHeadRecheckStillRequired") is not True: raise Refusal("R6 repository-global seed surface contract drift")
    if v.get("repositoryGlobalDoubleEnumerationRequired") is not True or v.get("repositoryGlobalEnumerationPassCountRequired")!=2: raise Refusal("R6 stable double-enumeration contract drift")
    if v.get("currentAuditRunAndSameRunProofArtifactMetadataExcludedAsSelfEvidence") is not True: raise Refusal("R6 current-audit self-metadata exclusion contract drift")
    if v.get("defaultBranchWorkflowDispatchRequired") is not True or v.get("proofBundleArtifactName")!="aerosol-family-v2-r6-freeze-proof" or v.get("evidenceOnlyPreservationCommitRequiredBeforeAuthorization") is not True: raise Refusal("R6 proof persistence lifecycle drift")
    if v.get("exactHeadTrackedTreeByteScanPassed") is not False or v.get("repositoryGlobalCollisionSurfaceScanPassed") is not False: raise Refusal("review package must not claim final seed proof")
    return v

def validate_design(d:dict[str,Any])->dict[str,Any]:
    if d.get("schemaVersion")!=DESIGN_SCHEMA_VERSION or d.get("stageId")!=STAGE_ID: raise Refusal("design identity changed")
    if d.get("historicalV1SourceBytesRecovered") is not False or d.get("historicalV1LockStatus")!="PREREGISTERED_NOT_RUN" or d.get("geometryAndBudgetAreHistoricalV1Recovery") is not False: raise Refusal("historical v1 provenance boundary changed")
    if any(d.get(k) is not False for k in ("scientificExecutionAuthorized","solverExecutionAuthorized","resultsOpened")): raise Refusal("review design opened forbidden boundary")
    if tuple(float(x) for x in d.get("sunDepressionDeg",[]))!=SUN_DEPRESSION_DEG or tuple(float(x) for x in d.get("aod550",[]))!=AOD550_VALUES or tuple(int(x) for x in d.get("replicates",[]))!=REPLICATES: raise Refusal("factorial design changed")
    src=validate_source_bindings(d.get("sourceBindings")); geo=validate_geometry_templates(d.get("geometryTemplates")); ph=validate_photon_schedule(d.get("photonHistoriesBySunDepression")); seeds=validate_group_seeds(d.get("groupSeeds")); review=validate_seed_freshness_review(d.get("seedFreshnessReview"),seeds)
    if tuple(d.get("requiredOutputChannels",[]))!=REQUIRED_OUTPUT_CHANNELS: raise Refusal("output channel contract changed")
    return {"sourceBindings":src,"geometryTemplates":geo,"photonSchedule":ph,"groupSeeds":seeds,"seedFreshnessReview":review}

def build_manifest(d:dict[str,Any])->dict[str,Any]:
    v=validate_design(d); cases=[]; groups=[]; i=0
    for dep,geo,aod,rep in product(SUN_DEPRESSION_DEG,v["geometryTemplates"],AOD550_VALUES,REPLICATES):
        seed=v["groupSeeds"][i]; i+=1
        cell_id=f"afc2-d{dep:02.0f}-{geo['geometryId']}-aod{int(round(aod*100)):02d}"
        gid=f"{cell_id}-r{rep}"; ids=[]
        for fam,haze in FAMILIES.items():
            for season,scode in SEASONS.items():
                cid=f"{gid}-{fam}-{season}"; ids.append(cid)
                cases.append({"caseId":cid,"groupId":gid,"analysisCellId":cell_id,"replicate":rep,"sunDepressionDeg":dep,"targetAltitudeDeg":geo["targetAltitudeDeg"],"relativeAzimuthDeg":geo["relativeAzimuthDeg"],"observerElevationM":geo["observerElevationM"],"geometryId":geo["geometryId"],"geometryTag":geo["geometryTag"],"aod550":aod,"albedo":0.15,"seed":seed,"photonHistories":v["photonSchedule"][f"{dep:g}"],"aerosolFamily":fam,"aerosolHazeCode":haze,"aerosolSeason":season,"aerosolSeasonCode":scode,"aerosolVulcanCode":1,"numericalMethod":NUMERICAL_METHOD,"calculationGrid":{"startNm":380,"stopNm":780,"stepNm":1,"nodeCount":401},"expectedRawOutputGrid":{"startNm":380.0,"stopNm":780.0,"stepNm":0.05,"nodeCount":8001,"pointToleranceNm":0.00005},"requiredOutputChannels":list(REQUIRED_OUTPUT_CHANNELS)})
        groups.append({"groupId":gid,"analysisCellId":cell_id,"replicate":rep,"seed":seed,"caseIds":ids})
    m={"schemaVersion":3,"stageId":STAGE_ID,"status":"REVIEW_MANIFEST_CANDIDATE_SEEDS_NOT_FRESHNESS_PROVEN","proposalOnly":True,"scientificExecutionAuthorized":False,"solverExecutionAuthorized":False,"resultsOpened":False,"historicalV1SourceBytesRecovered":False,"historicalV1LockStatus":"PREREGISTERED_NOT_RUN","geometryAndBudgetAreHistoricalV1Recovery":False,"sourceBindings":v["sourceBindings"],"seedFreshnessStatus":d["seedFreshnessReview"]["status"],"analysisCellCount":len({g["analysisCellId"] for g in groups}),"comparisonGroupCount":len(groups),"caseCount":len(cases),"statesPerGroup":8,"configuredPhotonHistoriesTotal":sum(x["photonHistories"] for x in cases),"numericalMethod":NUMERICAL_METHOD,"calculationGrid":{"startNm":380,"stopNm":780,"stepNm":1,"nodeCount":401},"expectedRawOutputGrid":{"startNm":380.0,"stopNm":780.0,"stepNm":0.05,"nodeCount":8001,"pointToleranceNm":0.00005},"groups":groups,"cases":cases}
    validate_manifest(m); return m

def validate_manifest(m:dict[str,Any])->None:
    if m.get("caseCount")!=576 or m.get("comparisonGroupCount")!=72 or m.get("analysisCellCount")!=24 or m.get("statesPerGroup")!=8 or m.get("configuredPhotonHistoriesTotal")!=11_520_000_000: raise Refusal("manifest universe/budget changed")
    if m.get("numericalMethod")!=NUMERICAL_METHOD or m.get("calculationGrid")!={"startNm":380,"stopNm":780,"stepNm":1,"nodeCount":401}: raise Refusal("spectrum calculation method changed")
    if m.get("expectedRawOutputGrid")!={"startNm":380.0,"stopNm":780.0,"stepNm":0.05,"nodeCount":8001,"pointToleranceNm":0.00005}: raise Refusal("raw output spectrum grid changed")
    if any(m.get(k) is not False for k in ("scientificExecutionAuthorized","solverExecutionAuthorized","resultsOpened")): raise Refusal("review manifest opened forbidden boundary")
    cases=m.get("cases");
    if not isinstance(cases,list) or len(cases)!=576 or len({x.get("caseId") for x in cases})!=576: raise Refusal("case universe invalid")
    by={}
    for c in cases: by.setdefault(c["groupId"],[]).append(c)
    if len(by)!=72: raise Refusal("group universe invalid")
    expected=set(product(FAMILIES,SEASONS)); seeds=[]
    for gid,rows in by.items():
        if len(rows)!=8 or {(x["aerosolFamily"],x["aerosolSeason"]) for x in rows}!=expected: raise Refusal(f"{gid}: state universe invalid")
        a=rows[0]
        for f in PAIRING_FIELDS:
            if any(x.get(f)!=a.get(f) for x in rows): raise Refusal(f"{gid}: pairing invariant drift: {f}")
        for x in rows:
            if x["aerosolHazeCode"]!=FAMILIES[x["aerosolFamily"]] or x["aerosolSeasonCode"]!=SEASONS[x["aerosolSeason"]] or x["aerosolVulcanCode"]!=1: raise Refusal("aerosol directive code drift")
        seeds.append(a["seed"])
    if len(set(seeds))!=72: raise Refusal("seed reused across groups")
    cells={}
    for gid,rows in by.items():
        anchor=rows[0]
        cells.setdefault(anchor.get("analysisCellId"),[]).append((anchor.get("replicate"),gid))
    if len(cells)!=24: raise Refusal("analysis cell universe invalid")
    for cell_id, entries in cells.items():
        if sorted(rep for rep,_ in entries)!=[1,2,3]: raise Refusal(f"{cell_id}: analysis cell must contain replicates 1,2,3")

def write_manifest(design_path:Path,out:Path)->dict[str,Any]:
    d=json.loads(design_path.read_text()); m=build_manifest(d); out.write_text(dump(m),encoding='utf-8',newline='\n'); return m

def validate_seed_audit_for_freeze(a:dict[str,Any],design_path:Path,d:dict[str,Any])->dict[str,Any]:
    seeds=validate_group_seeds(d.get("groupSeeds"))
    if a.get("schemaVersion")!=2 or a.get("stageId")!="aerosol-family-challenge-v2-seed-audit" or a.get("status")!="PASSED_EXACT_HEAD_TRACKED_TREE_AND_REPOSITORY_GLOBAL_COLLISION_SURFACES_NEGATIVE_CHECK": raise Refusal("seed freshness proof is incomplete")
    head=a.get("repositoryHead")
    if a.get("repositoryFullName")!=REPOSITORY_FULL_NAME or not isinstance(head,str) or len(head)!=40 or any(ch not in "0123456789abcdef" for ch in head): raise Refusal("seed audit exact-head binding invalid")
    if a.get("sourceBaseMainSha")!=PUBLIC_REPO_MAIN_SHA: raise Refusal("seed audit source-base binding changed")
    if a.get("candidateSeedCount")!=72 or a.get("candidateFirstSeed")!=seeds[0] or a.get("candidateLastSeed")!=seeds[-1] or a.get("candidateSeedCanonicalSha256")!=canonical_sha256(seeds): raise Refusal("seed audit does not bind candidate ledger")
    if a.get("auditedDesignRawSha256")!=raw_sha256(design_path): raise Refusal("seed audit does not bind exact design bytes")
    ledger_path=design_path.parent/"candidate-seed-ledger.v1.json"
    if not ledger_path.is_file(): raise Refusal("candidate seed ledger file missing")
    ledger=json.loads(ledger_path.read_text())
    if ledger.get("candidateSeeds")!=seeds or ledger.get("namespace")!=SEED_DERIVATION_NAMESPACE: raise Refusal("candidate seed ledger content drift")
    if a.get("candidateSeedLedgerRawSha256")!=raw_sha256(ledger_path) or a.get("candidateSeedDerivationNamespace")!=SEED_DERIVATION_NAMESPACE: raise Refusal("seed audit does not bind exact candidate seed ledger")
    if a.get("auditMode")!="review-freeze" or a.get("priorReviewProofArtifactCount")!=0 or a.get("reviewProofIdentityFresh") is not True or a.get("futureEvidenceSelfLedgerPathCountPresent")!=0: raise Refusal("freeze requires a fresh review-freeze seed audit with no prior proof artifact or preserved freeze evidence")
    if a.get("auditedBranchName")!=d.get("sourceBindings",{}).get("publicRepoDefaultBranch") or a.get("auditedBranchHeadShaObserved")!=head or a.get("auditedBranchHeadMatchesRepositoryHead") is not True: raise Refusal("seed audit is not bound to the exact default-branch head")
    if a.get("exactHeadTrackedTreeByteScanPassed") is not True or a.get("repositoryGlobalCollisionSurfaceScanPassed") is not True or a.get("externalCollisionCount")!=0: raise Refusal("seed collision proof incomplete or nonzero")
    if a.get("repositoryGlobalDoubleEnumerationStable") is not True or a.get("repositoryGlobalEnumerationPassCount")!=2 or not isinstance(a.get("repositoryGlobalStableContextSha256"),str) or len(a.get("repositoryGlobalStableContextSha256"))!=64: raise Refusal("repository-global seed audit was not a stable double enumeration")
    for key in ("allStatePullRequestsInspected","allStateIssuesInspected","allRepositoryIssueCommentsInspected","allRepositoryPullReviewCommentsInspected","allRepositoryCommitCommentsInspected"):
        if a.get(key) is not True: raise Refusal(f"seed audit omitted required repository-global surface: {key}")
    if not isinstance(a.get("excludedCurrentAuditRunId"),int) or a.get("excludedCurrentAuditRunId")<=0: raise Refusal("seed audit current-run exclusion binding missing")
    if a.get("authorizationPermitted") is not False: raise Refusal("seed audit cannot authorize execution")
    return a
