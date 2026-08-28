from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

STAGE_ID = "aerosol-vertical-profile-sensitivity-v2"
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PROTOCOL_PATH = HERE / "protocol.review.json"
V1_PROTOCOL_PATH = ROOT / "experiments/aerosol-vertical-profile-sensitivity-v1/protocol.review.json"
V1_SCIENTIFIC_REVIEW_PATH = ROOT / "experiments/aerosol-vertical-profile-sensitivity-v1/SCIENTIFIC_REVIEW.md"
V1_TEMPLATE_PATH = ROOT / "experiments/aerosol-vertical-profile-sensitivity-v1/opac_vertical_templates.py"
WAVELENGTH_GRID_PATH = ROOT / "experiments/aerosol-family-challenge-v2-r8/wavelength-grid-1nm.dat"

EXPECTED_BLOBS = {
    "protocol.review.json": "d790fb3fa2d214d1f430f4417b17212a8e5038a8",
    "v1Protocol": "5dddbac21e9ac395bd482d0d376577a6e5dd8bb0",
    "v1ScientificReview": "a92152a3cd3ab01b940460ec40fb8e4f1952f504",
    "v1TemplateGenerator": "8e8175ae771438b91fc9543b329175c193a215a4",
    "wavelengthGrid": "3bb3db96580d555ef758f57cabd6cac55b61cebb",
}
EXPECTED_PROFILE_SHA256 = {
    "opac-profile-continental-average": "ceed598f7681951cd0e6208b267beb5b41a52ab10311f37ce76f925700caff3d",
    "opac-profile-maritime-clean": "487b67bd7dbe89d12d032fdf2b33cab545e16a2e0697170648317f1a76362a67",
    "opac-profile-desert": "2b4d2e03c6ae3143d9bb05d2da49f57f75172dc1f24d34f7d4a4939bf9952fef",
    "opac-profile-arctic": "98f2fa5428c830764252fd0a2662b0f5c957fc027ffcb7bdc0a5e500dfd7d3d6",
    "opac-profile-antarctic": "ee063c6dca68cf9a31d8bb9d993f1fed5cb34c8bb056ac180c97171b5d6b4f19",
}
SPECIES = ("INSO", "WASO", "SOOT", "SUSO")
FRESH_SEED_PLACEHOLDER = "<UNALLOCATED_FRESH_AVPS_V2_GROUP_SEED>"


class PreregistrationError(RuntimeError):
    pass


def git_blob_sha1(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


def validate_bindings() -> dict[str, str]:
    actual = {
        "protocol.review.json": git_blob_sha1(PROTOCOL_PATH),
        "v1Protocol": git_blob_sha1(V1_PROTOCOL_PATH),
        "v1ScientificReview": git_blob_sha1(V1_SCIENTIFIC_REVIEW_PATH),
        "v1TemplateGenerator": git_blob_sha1(V1_TEMPLATE_PATH),
        "wavelengthGrid": git_blob_sha1(WAVELENGTH_GRID_PATH),
    }
    if actual != EXPECTED_BLOBS:
        raise PreregistrationError(f"frozen binding drift: expected={EXPECTED_BLOBS} actual={actual}")
    return actual


def load_protocol() -> dict[str, Any]:
    validate_bindings()
    p = json.loads(PROTOCOL_PATH.read_text())
    if p.get("stageId") != STAGE_ID:
        raise PreregistrationError("stage ID drift")
    if p.get("status") != "REVIEW_ONLY_REPLACEMENT_PREREGISTRATION_RENDERER_VALIDATED_SEEDS_AND_ORDINAL_UNALLOCATED":
        raise PreregistrationError("review status drift")
    for key in (
        "scientificExecutionAuthorized",
        "solverExecutionAuthorized",
        "resultOpeningAuthorized",
        "candidateSeedsAllocated",
        "scientificOrdinalAllocated",
        "productionAuthorized",
    ):
        if p.get(key) is not False:
            raise PreregistrationError(f"review crossed boundary: {key}")
    if p.get("caseCardinality", {}).get("expectedCases") != 360:
        raise PreregistrationError("case-count contract drift")
    if p.get("caseCardinality", {}).get("commonRandomNumberGroups") != 72:
        raise PreregistrationError("group-count contract drift")
    if p.get("freshIdentity", {}).get("seedNamespace") != "aerosol-vertical-profile-sensitivity-v2|group-seed|sha256-v1":
        raise PreregistrationError("fresh seed namespace drift")
    profiles = {
        row["stateId"]: row["fourSpeciesProfileSha256"]
        for row in p.get("verticalProfileStates", [])
    }
    if profiles != EXPECTED_PROFILE_SHA256:
        raise PreregistrationError("exact rendered-profile hash binding drift")
    return p


def _slug(value: float, scale: int, width: int) -> str:
    return f"{int(round(float(value) * scale)):0{width}d}"


def aerosol_directives(state_id: str, aod550: float) -> list[str]:
    if state_id not in EXPECTED_PROFILE_SHA256:
        raise PreregistrationError(f"unknown v2 state: {state_id}")
    if float(aod550) not in (0.10, 0.30):
        raise PreregistrationError("AOD outside frozen v2 screen")
    lines = [
        "aerosol_default",
        "aerosol_species_library OPAC",
        f"aerosol_species_file profiles/{state_id}.four-species.dat {' '.join(SPECIES)}",
        f"aerosol_set_tau_at_wvl 550 {float(aod550):.6f}",
    ]
    if any(line.startswith("aerosol_file ") for line in lines):
        raise PreregistrationError("forbidden custom tau directive leaked into v2")
    if sum(line.startswith("aerosol_species_file ") for line in lines) != 1:
        raise PreregistrationError("v2 requires exactly one explicit four-species profile")
    return lines


def preseed_science_surface(case: dict[str, Any]) -> list[str]:
    if case.get("seed") is not None or case.get("seedStatus") != "UNALLOCATED_REVIEW_ONLY":
        raise PreregistrationError("pre-seed science surface refuses allocated seed")
    dep = float(case["sunDepressionDeg"])
    alt = float(case["targetAltitudeDeg"])
    az = float(case["relativeAzimuthDeg"])
    lines = [
        "data_files_path <EXACT_FOUR_ALIAS_DATA_TREE>/",
        "atmosphere_file <EXACT_FOUR_ALIAS_DATA_TREE>/atmmod/afglus.dat",
        "source solar <EXACT_FOUR_ALIAS_DATA_TREE>/solar_flux/atlas_plus_modtran",
        "mol_abs_param crs",
        "wavelength_grid_file <REPOSITORY>/experiments/aerosol-family-challenge-v2-r8/wavelength-grid-1nm.dat",
        "wavelength 380 780",
        f"sza {90.0 + dep:.6f}",
        "phi0 0.000000",
        "rte_solver mystic",
        "mc_spherical 1D",
        f"mc_photons {int(case['photonHistories'])}",
        "mc_vroom on",
        "mc_std",
        f"mc_randomseed {FRESH_SEED_PLACEHOLDER}",
        "mc_basename <CASE_OUTPUT_DIR>/mc",
        f"albedo {float(case['surfaceAlbedo']):.6f}",
        *case["aerosolDirectives"],
        "zout 0.000000",
        f"umu {-math.sin(math.radians(alt)):.8f}",
        f"phi {az:.6f}",
        "quiet",
    ]
    if any(line.startswith("aerosol_file ") for line in lines):
        raise PreregistrationError("forbidden aerosol_file directive in pre-seed surface")
    if lines.count(FRESH_SEED_PLACEHOLDER) != 0:
        raise PreregistrationError("seed placeholder must be embedded only in mc_randomseed directive")
    if lines.count(f"mc_randomseed {FRESH_SEED_PLACEHOLDER}") != 1:
        raise PreregistrationError("fresh seed placeholder cardinality drift")
    return lines


def build_review_skeleton() -> dict[str, Any]:
    bindings = validate_bindings()
    p = load_protocol()
    design = p["fixedNumericalAndPhysicalDesign"]
    states = [row["stateId"] for row in p["verticalProfileStates"]]
    if states != list(EXPECTED_PROFILE_SHA256):
        raise PreregistrationError("state order drift")

    groups: list[dict[str, Any]] = []
    cases: list[dict[str, Any]] = []
    for dep in design["sunDepressionDeg"]:
        for aod in design["aod550"]:
            for geo in design["geometries"]:
                for replicate in design["replicates"]:
                    group_id = (
                        f"avps-v2-dep{_slug(dep, 10, 3)}-aod{_slug(aod, 100, 3)}-"
                        f"{geo['geometryId']}-rep{int(replicate)}"
                    )
                    group_case_ids: list[str] = []
                    for state_id in states:
                        case_id = f"{group_id}--{state_id}"
                        if not case_id.startswith("avps-v2-"):
                            raise PreregistrationError("fresh case namespace drift")
                        row = {
                            "caseId": case_id,
                            "groupId": group_id,
                            "stateId": state_id,
                            "sunDepressionDeg": float(dep),
                            "aod550": float(aod),
                            "geometryId": geo["geometryId"],
                            "geometryTag": geo["geometryTag"],
                            "targetAltitudeDeg": float(geo["targetAltitudeDeg"]),
                            "relativeAzimuthDeg": float(geo["relativeAzimuthDeg"]),
                            "observerElevationM": float(design["observerElevationM"]),
                            "surfaceAlbedo": float(design["surfaceAlbedo"]),
                            "replicate": int(replicate),
                            "photonHistories": int(design["photonHistoriesPerCase"]),
                            "numericalMethod": design["numericalMethod"],
                            "wavelengthStartNm": int(design["wavelengthStartNm"]),
                            "wavelengthStopNm": int(design["wavelengthStopNm"]),
                            "calculationGridStepNm": int(design["calculationGridStepNm"]),
                            "aerosolDirectives": aerosol_directives(state_id, float(aod)),
                            "profileRelativePath": f"profiles/{state_id}.four-species.dat",
                            "profileSha256": EXPECTED_PROFILE_SHA256[state_id],
                            "seed": None,
                            "seedStatus": "UNALLOCATED_REVIEW_ONLY",
                            "scientificOrdinal": None,
                            "renderable": False,
                            "executionAuthorized": False,
                            "resultOpeningAuthorized": False,
                        }
                        surface = preseed_science_surface(row)
                        row["preSeedScienceSurface"] = surface
                        row["preSeedScienceSurfaceSha256"] = canonical_sha256(surface)
                        cases.append(row)
                        group_case_ids.append(case_id)
                    groups.append({
                        "groupId": group_id,
                        "caseIds": group_case_ids,
                        "stateIds": list(states),
                        "candidateSeed": None,
                        "seedStatus": "UNALLOCATED_REVIEW_ONLY",
                        "scientificOrdinal": None,
                        "executionAuthorized": False,
                    })

    if len(groups) != 72 or len(cases) != 360:
        raise PreregistrationError(f"v2 universe drift groups={len(groups)} cases={len(cases)}")
    if len({row["groupId"] for row in groups}) != 72:
        raise PreregistrationError("duplicate v2 group IDs")
    if len({row["caseId"] for row in cases}) != 360:
        raise PreregistrationError("duplicate v2 case IDs")
    if len({row["preSeedScienceSurfaceSha256"] for row in cases}) != 120:
        raise PreregistrationError("distinct pre-seed science surface cardinality drift")
    if any(row["seed"] is not None or row["scientificOrdinal"] is not None for row in cases):
        raise PreregistrationError("review skeleton contains seed/ordinal")

    out = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "REVIEW_ONLY_V2_SKELETON_360_CASES_FRESH_IDENTITIES_SEEDS_AND_ORDINAL_UNALLOCATED",
        "sourceBindings": bindings,
        "rendererEvidence": p["sourceEvidence"],
        "fourAliasDataTreeSha256": p["fixedOpticalFamily"]["fourAliasDataTreeSha256"],
        "profileSha256": dict(EXPECTED_PROFILE_SHA256),
        "seedNamespace": p["freshIdentity"]["seedNamespace"],
        "caseCount": len(cases),
        "groupCount": len(groups),
        "statesPerGroup": 5,
        "distinctPreSeedScienceSurfaceCount": 120,
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
    print(json.dumps(build_review_skeleton(), indent=2, sort_keys=True))
