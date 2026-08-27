from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

STAGE_ID = "aerosol-vertical-profile-sensitivity-v1"
STAGE_DIR = Path(__file__).resolve().parent
ROOT = STAGE_DIR.parents[1]
PROTOCOL_PATH = STAGE_DIR / "protocol.review.json"
TEMPLATE_PATH = STAGE_DIR / "opac_vertical_templates.py"
TRANSPORT_PATH = ROOT / "review" / "aerosol-vertical-profile-transport-v1" / "profile_transport.py"

EXPECTED_GIT_BLOBS = {
    "protocol.review.json": "5dddbac21e9ac395bd482d0d376577a6e5dd8bb0",
    "opac_vertical_templates.py": "8e8175ae771438b91fc9543b329175c193a215a4",
    "profile_transport.py": "af2d4d65371474c38791d79e2fcded696022d88d",
}


class ExecutionCandidateError(RuntimeError):
    pass


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def canonical_sha256(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def validate_review_bindings() -> dict[str, str]:
    actual = {
        "protocol.review.json": git_blob_sha(PROTOCOL_PATH),
        "opac_vertical_templates.py": git_blob_sha(TEMPLATE_PATH),
        "profile_transport.py": git_blob_sha(TRANSPORT_PATH),
    }
    if actual != EXPECTED_GIT_BLOBS:
        raise ExecutionCandidateError(f"review byte binding drift: expected={EXPECTED_GIT_BLOBS} actual={actual}")
    return actual


def load_protocol() -> dict[str, Any]:
    p = json.loads(PROTOCOL_PATH.read_text())
    if p.get("stageId") != STAGE_ID:
        raise ExecutionCandidateError("stage ID drift")
    if p.get("status") != "REVIEW_ONLY_PREREGISTRATION_EXECUTION_DISABLED_RESULTS_NOT_OPENED":
        raise ExecutionCandidateError("protocol no longer review-only")
    for key in (
        "scientificExecutionAuthorized",
        "solverExecutionAuthorized",
        "resultOpeningAuthorized",
        "candidateSeedsAllocated",
        "scientificOrdinalAllocated",
        "productionAuthorized",
    ):
        if p.get(key) is not False:
            raise ExecutionCandidateError(f"protocol crossed review boundary: {key}")
    if p.get("caseCardinality", {}).get("expectedCases") != 360:
        raise ExecutionCandidateError("expected case count drift")
    if p.get("caseCardinality", {}).get("commonRandomNumberGroups") != 72:
        raise ExecutionCandidateError("expected group count drift")
    return p


def _slug_float(value: float, scale: int = 1) -> str:
    scaled = round(float(value) * scale)
    return str(int(scaled)).replace("-", "m")


def aerosol_directives(state_id: str, aod550: float) -> list[str]:
    if state_id not in {row["stateId"] for row in load_protocol()["verticalProfileStates"]}:
        raise ExecutionCandidateError(f"unknown vertical state: {state_id}")
    if float(aod550) not in (0.10, 0.30):
        raise ExecutionCandidateError("AOD outside frozen design")
    tau_rel = f"profiles/{state_id}.tau"
    return [
        "aerosol_default",
        "aerosol_species_library OPAC",
        "aerosol_species_file continental_average",
        f"aerosol_file tau {tau_rel}",
        f"aerosol_set_tau_at_wvl 550 {float(aod550):.6f}",
    ]


def build_review_execution_skeleton() -> dict[str, Any]:
    bindings = validate_review_bindings()
    p = load_protocol()
    d = p["fixedNumericalAndPhysicalDesign"]
    states = [row["stateId"] for row in p["verticalProfileStates"]]
    if len(states) != 5 or len(set(states)) != 5:
        raise ExecutionCandidateError("vertical state cardinality drift")

    groups: list[dict[str, Any]] = []
    cases: list[dict[str, Any]] = []
    for dep in d["sunDepressionDeg"]:
        for aod in d["aod550"]:
            for geo in d["geometries"]:
                for replicate in d["replicates"]:
                    group_id = (
                        f"dep{_slug_float(dep, 10)}-aod{_slug_float(aod, 100)}-"
                        f"{geo['geometryId']}-rep{int(replicate)}"
                    )
                    group_case_ids = []
                    for state_id in states:
                        case_id = f"{group_id}--{state_id}"
                        group_case_ids.append(case_id)
                        cases.append({
                            "caseId": case_id,
                            "groupId": group_id,
                            "stateId": state_id,
                            "sunDepressionDeg": float(dep),
                            "aod550": float(aod),
                            "geometryId": geo["geometryId"],
                            "geometryTag": geo["geometryTag"],
                            "targetAltitudeDeg": float(geo["targetAltitudeDeg"]),
                            "relativeAzimuthDeg": float(geo["relativeAzimuthDeg"]),
                            "observerElevationM": float(d["observerElevationM"]),
                            "surfaceAlbedo": float(d["surfaceAlbedo"]),
                            "replicate": int(replicate),
                            "photonHistories": int(d["photonHistoriesPerCase"]),
                            "numericalMethod": d["numericalMethod"],
                            "wavelengthStartNm": int(d["wavelengthStartNm"]),
                            "wavelengthStopNm": int(d["wavelengthStopNm"]),
                            "calculationGridStepNm": int(d["calculationGridStepNm"]),
                            "aerosolDirectives": aerosol_directives(state_id, float(aod)),
                            "tauProfileRelativePath": f"profiles/{state_id}.tau",
                            "seed": None,
                            "seedStatus": "UNALLOCATED_REVIEW_ONLY",
                            "renderable": False,
                            "executionAuthorized": False,
                            "resultOpeningAuthorized": False,
                        })
                    groups.append({
                        "groupId": group_id,
                        "pairing": {
                            "sunDepressionDeg": float(dep),
                            "aod550": float(aod),
                            "geometryId": geo["geometryId"],
                            "targetAltitudeDeg": float(geo["targetAltitudeDeg"]),
                            "relativeAzimuthDeg": float(geo["relativeAzimuthDeg"]),
                            "observerElevationM": float(d["observerElevationM"]),
                            "replicate": int(replicate),
                        },
                        "stateIds": list(states),
                        "caseIds": group_case_ids,
                        "candidateSeed": None,
                        "seedStatus": "UNALLOCATED_REVIEW_ONLY",
                        "executionAuthorized": False,
                    })

    if len(groups) != 72 or len(cases) != 360:
        raise ExecutionCandidateError(f"case universe drift: groups={len(groups)} cases={len(cases)}")
    if len({row["groupId"] for row in groups}) != 72:
        raise ExecutionCandidateError("duplicate group IDs")
    if len({row["caseId"] for row in cases}) != 360:
        raise ExecutionCandidateError("duplicate case IDs")

    out = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "REVIEW_ONLY_EXECUTION_SKELETON_SEEDS_UNALLOCATED",
        "sourceProtocolGitBlob": bindings["protocol.review.json"],
        "sourceTemplateGeneratorGitBlob": bindings["opac_vertical_templates.py"],
        "sourceProfileTransportGitBlob": bindings["profile_transport.py"],
        "caseCount": len(cases),
        "groupCount": len(groups),
        "statesPerGroup": len(states),
        "seedCount": 0,
        "scientificOrdinal": None,
        "scientificExecutionAuthorized": False,
        "solverExecutionAuthorized": False,
        "resultOpeningAuthorized": False,
        "productionAuthorized": False,
        "groups": groups,
        "cases": cases,
    }
    out["canonicalSkeletonSha256"] = canonical_sha256(out)
    return out


if __name__ == "__main__":
    print(json.dumps(build_review_execution_skeleton(), indent=2, sort_keys=True))
