from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from itertools import product
from pathlib import Path
from typing import Any

STAGE_ID = "aerosol-family-challenge-v2-r8"
DESIGN_SCHEMA_VERSION = 1
REPOSITORY_FULL_NAME = "search-maker/twilight-mystic-experiments"
BASE_PACKAGE = Path(__file__).resolve().parent.parent / "aerosol-family-challenge-v2"
BASE_CORE_PATH = BASE_PACKAGE / "core.py"
BASE_DESIGN_PATH = BASE_PACKAGE / "design.review.json"
BASE_CORE_GIT_BLOB_SHA1 = "314216ab43b261e160a3ab4d368073206946cf13"
BASE_DESIGN_GIT_BLOB_SHA1 = "cbb066c2c2b4b9f9bcc1e9960637d91d6cedac6e"
BASE_ANALYSIS_CONTRACT_GIT_BLOB_SHA1 = "d2411cd7636d3d34a0b9132a48fbcea4ccf35d76"
PRIOR_R7_PACKAGE = Path(__file__).resolve().parent.parent / "aerosol-family-challenge-v2-r7"
PRIOR_R7_CORE_PATH = PRIOR_R7_PACKAGE / "core.py"
PRIOR_R7_DESIGN_PATH = PRIOR_R7_PACKAGE / "design.review.json"
PRIOR_R7_SEED_LEDGER_PATH = PRIOR_R7_PACKAGE / "candidate-seed-ledger.v2.json"
PRIOR_R7_CORE_GIT_BLOB_SHA1 = "77e3f1282b2e8161d8bd499aac478ab43605374e"
PRIOR_R7_DESIGN_GIT_BLOB_SHA1 = "6038e3a769e205e2e26b5d8fc950ceb8c594b9c5"
PRIOR_R7_SEED_LEDGER_GIT_BLOB_SHA1 = "22354b2c602acbece93bd875e2e0df759a23672c"
PRIOR_R7_SEED_CANONICAL_SHA256 = "bf5254ff59450ae935705966c51d367a003e97afbcff98a7622b1c310c3ace3b"
PRIOR_CONTINUATION_BINDING = {
    "stageId": "aerosol-family-challenge-v2-r7",
    "consumedScientificOrdinal": 31,
    "disposition": "DISPATCH_REF_CREATED_IDENTITY_CONSUMED_NO_ACTIONS_SCIENTIFIC_RUN",
    "corePath": "experiments/aerosol-family-challenge-v2-r7/core.py",
    "coreGitBlobSha": PRIOR_R7_CORE_GIT_BLOB_SHA1,
    "designPath": "experiments/aerosol-family-challenge-v2-r7/design.review.json",
    "designGitBlobSha": PRIOR_R7_DESIGN_GIT_BLOB_SHA1,
    "candidateSeedLedgerPath": "experiments/aerosol-family-challenge-v2-r7/candidate-seed-ledger.v2.json",
    "candidateSeedLedgerGitBlobSha": PRIOR_R7_SEED_LEDGER_GIT_BLOB_SHA1,
    "candidateSeedCanonicalSha256": PRIOR_R7_SEED_CANONICAL_SHA256,
    "seedDerivationNamespace": "aerosol-family-challenge-v2|group-seed|sha256-v2",
}
SEED_DERIVATION_NAMESPACE = "aerosol-family-challenge-v2|group-seed|sha256-v3"
SEED_DOMAIN_MAX_EXCLUSIVE = 2_147_483_647
REVIEW_PROOF_ARTIFACT_NAME = "aerosol-family-v2-r8-freeze-proof"
SEED_AUDIT_STAGE_ID = "aerosol-family-challenge-v2-r8-seed-audit"
DESIGN_STATUS = "R8_REVIEW_ONLY_CONTINUATION_PREREGISTRATION_COMPLETE_EXCEPT_DEFAULT_BRANCH_SEED_FRESHNESS_PROOF"
SEED_REVIEW_STATUS = "R8_DETERMINISTIC_CANDIDATE_SEEDS_REVIEW_PENDING_DEFAULT_BRANCH_STABLE_DOUBLE_ENUMERATION_PROOF"


def _git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


if _git_blob_sha1(BASE_CORE_PATH) != BASE_CORE_GIT_BLOB_SHA1:
    raise RuntimeError("R8 refuses: bound R6 core bytes changed")
if _git_blob_sha1(BASE_DESIGN_PATH) != BASE_DESIGN_GIT_BLOB_SHA1:
    raise RuntimeError("R8 refuses: bound R6 design bytes changed")

for _prior_path, _expected_blob in (
    (PRIOR_R7_CORE_PATH, PRIOR_R7_CORE_GIT_BLOB_SHA1),
    (PRIOR_R7_DESIGN_PATH, PRIOR_R7_DESIGN_GIT_BLOB_SHA1),
    (PRIOR_R7_SEED_LEDGER_PATH, PRIOR_R7_SEED_LEDGER_GIT_BLOB_SHA1),
):
    if _git_blob_sha1(_prior_path) != _expected_blob:
        raise RuntimeError(f"R8 refuses: bound prior R7 bytes changed: {_prior_path.name}")

_spec = importlib.util.spec_from_file_location("afc2_r6_bound_core", BASE_CORE_PATH)
if _spec is None or _spec.loader is None:
    raise RuntimeError("cannot load bound R6 core")
_r6 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_r6)

Refusal = _r6.Refusal
FAMILIES = _r6.FAMILIES
SEASONS = _r6.SEASONS
SUN_DEPRESSION_DEG = _r6.SUN_DEPRESSION_DEG
AOD550_VALUES = _r6.AOD550_VALUES
REPLICATES = _r6.REPLICATES
V2_GEOMETRY_TEMPLATES = _r6.V2_GEOMETRY_TEMPLATES
V2_PHOTON_HISTORIES_PER_CASE = _r6.V2_PHOTON_HISTORIES_PER_CASE
NUMERICAL_METHOD = _r6.NUMERICAL_METHOD
REQUIRED_OUTPUT_CHANNELS = _r6.REQUIRED_OUTPUT_CHANNELS
PAIRING_FIELDS = _r6.PAIRING_FIELDS
EXPECTED_GROUP_COUNT = _r6.EXPECTED_GROUP_COUNT
EXPECTED_CASE_COUNT = _r6.EXPECTED_CASE_COUNT
canonical_sha256 = _r6.canonical_sha256
canonical_bytes = _r6.canonical_bytes
raw_sha256 = _r6.raw_sha256
git_blob_sha1 = _r6.git_blob_sha1
dump = _r6.dump


def _derive_candidate_seed_rows() -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    used: set[int] = set()
    for dep, geo, aod, rep in product(SUN_DEPRESSION_DEG, V2_GEOMETRY_TEMPLATES, AOD550_VALUES, REPLICATES):
        cell_id = f"afc2-d{dep:02.0f}-{geo['geometryId']}-aod{int(round(aod * 100)):02d}"
        counter = 0
        while True:
            material = f"{SEED_DERIVATION_NAMESPACE}|analysisCellId={cell_id}|replicate={rep}|counter={counter}"
            digest = hashlib.sha256(material.encode("utf-8")).digest()
            seed = (int.from_bytes(digest[:8], "big") % (SEED_DOMAIN_MAX_EXCLUSIVE - 1)) + 1
            if seed not in used:
                break
            counter += 1
        used.add(seed)
        rows.append({
            "analysisCellId": cell_id,
            "replicate": rep,
            "collisionCounter": counter,
            "derivationMaterialSha256": hashlib.sha256(material.encode("utf-8")).hexdigest(),
            "seed": seed,
        })
    return tuple(rows)


CANDIDATE_SEED_ROWS = _derive_candidate_seed_rows()
CANDIDATE_GROUP_SEEDS = tuple(int(row["seed"]) for row in CANDIDATE_SEED_ROWS)
CANDIDATE_SEED_FIRST = CANDIDATE_GROUP_SEEDS[0]
CANDIDATE_SEED_LAST = CANDIDATE_GROUP_SEEDS[-1]


def _load_base_design() -> dict[str, Any]:
    if _git_blob_sha1(BASE_DESIGN_PATH) != BASE_DESIGN_GIT_BLOB_SHA1:
        raise Refusal("bound R6 design bytes changed")
    value = json.loads(BASE_DESIGN_PATH.read_text())
    _r6.validate_design(value)
    return value


def validate_group_seeds(value: Any) -> list[int]:
    if not isinstance(value, list) or len(value) != EXPECTED_GROUP_COUNT:
        raise Refusal("R8 requires exactly 72 explicit group seeds")
    if any(isinstance(seed, bool) or not isinstance(seed, int) or not 0 < seed < SEED_DOMAIN_MAX_EXCLUSIVE for seed in value):
        raise Refusal("invalid R8 group seed")
    if len(set(value)) != EXPECTED_GROUP_COUNT:
        raise Refusal("R8 group seeds must be unique between groups")
    if tuple(value) != CANDIDATE_GROUP_SEEDS:
        raise Refusal("R8 candidate seed ledger changed; version another continuation review")
    if any(int(row["collisionCounter"]) != 0 for row in CANDIDATE_SEED_ROWS):
        raise Refusal("R8 deterministic candidate seed derivation changed")
    base_seeds = set(int(x) for x in _load_base_design()["groupSeeds"])
    if base_seeds.intersection(value):
        raise Refusal("R8 candidate seed overlaps R6 seed ledger")
    prior_ledger = json.loads(PRIOR_R7_SEED_LEDGER_PATH.read_text())
    if prior_ledger.get("candidateSeedCanonicalSha256") != PRIOR_R7_SEED_CANONICAL_SHA256:
        raise Refusal("R8 prior R7 seed canonical binding drift")
    if prior_ledger.get("namespace") != "aerosol-family-challenge-v2|group-seed|sha256-v2":
        raise Refusal("R8 prior R7 seed namespace drift")
    prior_seeds = set(int(x) for x in prior_ledger.get("candidateSeeds", []))
    if len(prior_seeds) != EXPECTED_GROUP_COUNT:
        raise Refusal("R8 prior R7 seed ledger cardinality drift")
    if prior_seeds.intersection(value):
        raise Refusal("R8 candidate seed overlaps consumed R7 seed ledger")
    return value


def validate_seed_freshness_review(value: Any, seeds: list[int], package_dir: Path) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("candidateOnly") is not True or value.get("authorizationPermitted") is not False:
        raise Refusal("R8 review seeds must remain candidate-only")
    exact = {
        "status": SEED_REVIEW_STATUS,
        "candidateSeedCount": 72,
        "candidateFirstSeed": seeds[0],
        "candidateLastSeed": seeds[-1],
        "candidateSeedCanonicalSha256": canonical_sha256(seeds),
        "proofBundleArtifactName": REVIEW_PROOF_ARTIFACT_NAME,
        "reviewFreezeAuditModeRequired": "review-freeze",
        "authorizationTimeAuditModeRequired": "authorization-recheck",
        "authorizationTimeExactHeadRecheckStillRequired": True,
        "repositoryGlobalDoubleEnumerationRequired": True,
        "repositoryGlobalEnumerationPassCountRequired": 2,
        "evidenceOnlyPreservationCommitRequiredBeforeAuthorization": True,
        "exactHeadTrackedTreeByteScanPassed": False,
        "repositoryGlobalCollisionSurfaceScanPassed": False,
    }
    for key, expected in exact.items():
        if value.get(key) != expected:
            raise Refusal(f"R8 seed review drift: {key}")
    deriv = value.get("candidateSeedDerivation")
    ledger_path = package_dir / "candidate-seed-ledger.v2.json"
    if not isinstance(deriv, dict) or deriv.get("namespace") != SEED_DERIVATION_NAMESPACE:
        raise Refusal("R8 seed derivation namespace drift")
    if deriv.get("ledgerPath") != "candidate-seed-ledger.v2.json" or deriv.get("allCollisionCountersZero") is not True:
        raise Refusal("R8 seed ledger binding drift")
    if not ledger_path.is_file() or deriv.get("ledgerRawSha256") != raw_sha256(ledger_path):
        raise Refusal("R8 design does not bind exact local seed ledger bytes")
    ledger = json.loads(ledger_path.read_text())
    if ledger.get("candidateSeeds") != seeds or ledger.get("namespace") != SEED_DERIVATION_NAMESPACE:
        raise Refusal("R8 candidate seed ledger content drift")
    if ledger.get("candidateSeedCanonicalSha256") != canonical_sha256(seeds) or ledger.get("allCollisionCountersZero") is not True:
        raise Refusal("R8 candidate seed ledger canonical binding drift")
    return value


def validate_design(design: dict[str, Any]) -> dict[str, Any]:
    package_dir = Path(__file__).resolve().parent
    if design.get("schemaVersion") != DESIGN_SCHEMA_VERSION or design.get("stageId") != STAGE_ID:
        raise Refusal("R8 design identity changed")
    if design.get("status") != DESIGN_STATUS:
        raise Refusal("R8 design status drift")
    if any(design.get(key) is not False for key in ("scientificExecutionAuthorized", "solverExecutionAuthorized", "resultsOpened")):
        raise Refusal("R8 review design opened forbidden boundary")
    if design.get("continuationReason") != "ORDINAL31_DISPATCH_REF_CONSUMED_WITHOUT_ACTIONS_RUN_AND_EXECUTION_PREFLIGHT_SOURCE_BINDING_DEFECT":
        raise Refusal("R8 continuation reason drift")
    if design.get("baseDesignPath") != "experiments/aerosol-family-challenge-v2/design.review.json" or design.get("baseDesignGitBlobSha") != BASE_DESIGN_GIT_BLOB_SHA1:
        raise Refusal("R8 base design binding drift")
    if design.get("baseCorePath") != "experiments/aerosol-family-challenge-v2/core.py" or design.get("baseCoreGitBlobSha") != BASE_CORE_GIT_BLOB_SHA1:
        raise Refusal("R8 base core binding drift")
    if design.get("baseAnalysisContractGitBlobSha") != BASE_ANALYSIS_CONTRACT_GIT_BLOB_SHA1:
        raise Refusal("R8 base analysis contract binding drift")
    if design.get("priorContinuationBinding") != PRIOR_CONTINUATION_BINDING:
        raise Refusal("R8 prior R7 continuation binding drift")
    if design.get("scientificScopeChange") != "NONE_SEEDS_AND_GOVERNANCE_IDENTITY_ONLY":
        raise Refusal("R8 scientific scope change is not explicitly none")
    seeds = validate_group_seeds(design.get("groupSeeds"))
    review = validate_seed_freshness_review(design.get("seedFreshnessReview"), seeds, package_dir)
    base = _load_base_design()
    return {"baseDesign": base, "groupSeeds": seeds, "seedFreshnessReview": review}


def build_manifest(design: dict[str, Any]) -> dict[str, Any]:
    validated = validate_design(design)
    base = validated["baseDesign"]
    seeds = validated["groupSeeds"]
    cases: list[dict[str, Any]] = []
    groups: list[dict[str, Any]] = []
    index = 0
    geometries = [dict(row) for row in V2_GEOMETRY_TEMPLATES]
    photon_schedule = {str(key): int(value) for key, value in base["photonHistoriesBySunDepression"].items()}
    for dep, geo, aod, rep in product(SUN_DEPRESSION_DEG, geometries, AOD550_VALUES, REPLICATES):
        seed = seeds[index]
        index += 1
        cell_id = f"afc2-d{dep:02.0f}-{geo['geometryId']}-aod{int(round(aod * 100)):02d}"
        group_id = f"{cell_id}-r{rep}"
        ids: list[str] = []
        for family, haze in FAMILIES.items():
            for season, season_code in SEASONS.items():
                case_id = f"{group_id}-{family}-{season}"
                ids.append(case_id)
                cases.append({
                    "caseId": case_id,
                    "groupId": group_id,
                    "analysisCellId": cell_id,
                    "replicate": rep,
                    "sunDepressionDeg": dep,
                    "targetAltitudeDeg": geo["targetAltitudeDeg"],
                    "relativeAzimuthDeg": geo["relativeAzimuthDeg"],
                    "observerElevationM": geo["observerElevationM"],
                    "geometryId": geo["geometryId"],
                    "geometryTag": geo["geometryTag"],
                    "aod550": aod,
                    "albedo": 0.15,
                    "seed": seed,
                    "photonHistories": photon_schedule[f"{dep:g}"],
                    "aerosolFamily": family,
                    "aerosolHazeCode": haze,
                    "aerosolSeason": season,
                    "aerosolSeasonCode": season_code,
                    "aerosolVulcanCode": 1,
                    "numericalMethod": NUMERICAL_METHOD,
                    "calculationGrid": {"startNm": 380, "stopNm": 780, "stepNm": 1, "nodeCount": 401},
                    "expectedRawOutputGrid": {"startNm": 380.0, "stopNm": 780.0, "stepNm": 0.05, "nodeCount": 8001, "pointToleranceNm": 0.00005},
                    "requiredOutputChannels": list(REQUIRED_OUTPUT_CHANNELS),
                })
        groups.append({"groupId": group_id, "analysisCellId": cell_id, "replicate": rep, "seed": seed, "caseIds": ids})
    manifest = {
        "schemaVersion": 4,
        "stageId": STAGE_ID,
        "status": "REVIEW_MANIFEST_CANDIDATE_SEEDS_NOT_FRESHNESS_PROVEN",
        "proposalOnly": True,
        "scientificExecutionAuthorized": False,
        "solverExecutionAuthorized": False,
        "resultsOpened": False,
        "continuationReason": design["continuationReason"],
        "priorContinuationBinding": copy.deepcopy(design["priorContinuationBinding"]),
        "baseDesignGitBlobSha": BASE_DESIGN_GIT_BLOB_SHA1,
        "baseCoreGitBlobSha": BASE_CORE_GIT_BLOB_SHA1,
        "scientificScopeChange": "NONE_SEEDS_AND_GOVERNANCE_IDENTITY_ONLY",
        "sourceBindings": copy.deepcopy(base["sourceBindings"]),
        "seedFreshnessStatus": design["seedFreshnessReview"]["status"],
        "analysisCellCount": len({group["analysisCellId"] for group in groups}),
        "comparisonGroupCount": len(groups),
        "caseCount": len(cases),
        "statesPerGroup": 8,
        "configuredPhotonHistoriesTotal": sum(int(case["photonHistories"]) for case in cases),
        "numericalMethod": NUMERICAL_METHOD,
        "calculationGrid": {"startNm": 380, "stopNm": 780, "stepNm": 1, "nodeCount": 401},
        "expectedRawOutputGrid": {"startNm": 380.0, "stopNm": 780.0, "stepNm": 0.05, "nodeCount": 8001, "pointToleranceNm": 0.00005},
        "groups": groups,
        "cases": cases,
    }
    _r6.validate_manifest(manifest)
    return manifest


def validate_manifest(manifest: dict[str, Any]) -> None:
    _r6.validate_manifest(manifest)
    if manifest.get("stageId") != STAGE_ID or manifest.get("baseDesignGitBlobSha") != BASE_DESIGN_GIT_BLOB_SHA1:
        raise Refusal("R8 manifest continuation identity drift")
    if manifest.get("priorContinuationBinding") != PRIOR_CONTINUATION_BINDING:
        raise Refusal("R8 manifest prior-continuation binding drift")
    if manifest.get("scientificScopeChange") != "NONE_SEEDS_AND_GOVERNANCE_IDENTITY_ONLY":
        raise Refusal("R8 manifest scientific scope drift")


def write_manifest(design_path: Path, output: Path) -> dict[str, Any]:
    design = json.loads(design_path.read_text())
    manifest = build_manifest(design)
    output.write_text(dump(manifest), encoding="utf-8", newline="\n")
    return manifest


def validate_seed_audit_for_freeze(audit: dict[str, Any], design_path: Path, design: dict[str, Any]) -> dict[str, Any]:
    seeds = validate_group_seeds(design.get("groupSeeds"))
    if audit.get("schemaVersion") != 2 or audit.get("stageId") != SEED_AUDIT_STAGE_ID:
        raise Refusal("R8 seed audit identity drift")
    if audit.get("status") != "PASSED_EXACT_HEAD_TRACKED_TREE_AND_REPOSITORY_GLOBAL_COLLISION_SURFACES_NEGATIVE_CHECK":
        raise Refusal("R8 seed freshness proof is incomplete")
    head = audit.get("repositoryHead")
    if audit.get("repositoryFullName") != REPOSITORY_FULL_NAME or not isinstance(head, str) or len(head) != 40:
        raise Refusal("R8 seed audit exact-head binding invalid")
    base = _load_base_design()
    if audit.get("sourceBaseMainSha") != base["sourceBindings"]["publicRepoMainSha"]:
        raise Refusal("R8 seed audit source-base binding changed")
    if audit.get("candidateSeedCount") != 72 or audit.get("candidateFirstSeed") != seeds[0] or audit.get("candidateLastSeed") != seeds[-1]:
        raise Refusal("R8 seed audit candidate endpoints drift")
    if audit.get("candidateSeedCanonicalSha256") != canonical_sha256(seeds):
        raise Refusal("R8 seed audit candidate canonical hash drift")
    if audit.get("auditedDesignRawSha256") != raw_sha256(design_path):
        raise Refusal("R8 seed audit does not bind exact continuation design bytes")
    ledger_path = design_path.parent / "candidate-seed-ledger.v2.json"
    if audit.get("candidateSeedLedgerRawSha256") != raw_sha256(ledger_path) or audit.get("candidateSeedDerivationNamespace") != SEED_DERIVATION_NAMESPACE:
        raise Refusal("R8 seed audit does not bind exact candidate ledger")
    if audit.get("auditMode") != "review-freeze" or audit.get("priorReviewProofArtifactCount") != 0 or audit.get("reviewProofIdentityFresh") is not True:
        raise Refusal("R8 freeze requires fresh one-use review-freeze audit")
    if audit.get("reviewProofArtifactName") != REVIEW_PROOF_ARTIFACT_NAME:
        raise Refusal("R8 review proof artifact identity drift")
    if audit.get("futureEvidenceSelfLedgerPathCountPresent") != 0:
        raise Refusal("R8 future evidence paths already exist before first freeze")
    if audit.get("auditedBranchName") != "main" or audit.get("auditedBranchHeadShaObserved") != head or audit.get("auditedBranchHeadMatchesRepositoryHead") is not True:
        raise Refusal("R8 seed audit is not bound to exact main head")
    if audit.get("exactHeadTrackedTreeByteScanPassed") is not True or audit.get("repositoryGlobalCollisionSurfaceScanPassed") is not True or audit.get("externalCollisionCount") != 0:
        raise Refusal("R8 seed collision proof incomplete or nonzero")
    if audit.get("repositoryGlobalDoubleEnumerationStable") is not True or audit.get("repositoryGlobalEnumerationPassCount") != 2:
        raise Refusal("R8 repository-global seed audit was not stable double enumeration")
    for key in ("allStatePullRequestsInspected", "allStateIssuesInspected", "allRepositoryIssueCommentsInspected", "allRepositoryPullReviewCommentsInspected", "allRepositoryCommitCommentsInspected"):
        if audit.get(key) is not True:
            raise Refusal(f"R8 seed audit omitted required surface: {key}")
    if not isinstance(audit.get("excludedCurrentAuditRunId"), int) or int(audit["excludedCurrentAuditRunId"]) <= 0:
        raise Refusal("R8 seed audit current-run exclusion missing")
    if audit.get("authorizationPermitted") is not False:
        raise Refusal("R8 seed audit cannot authorize execution")
    return audit
