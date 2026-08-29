from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("avps_v2_aggregator_under_test", HERE / "aggregator.py")
assert SPEC is not None and SPEC.loader is not None
AGG = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AGG
SPEC.loader.exec_module(AGG)


class DummyDerived:
    RAW_POINT_TOLERANCE_NM = 1e-9

    @staticmethod
    def validate_raw_grid(wavelengths, values):
        assert len(wavelengths) == len(values) == 8001

    @staticmethod
    def derive_channels(wavelengths, values):
        return {"photopicLuminanceCdM2": values[0], "scotopicLuminanceScotCdM2": values[-1]}


def _expected_case():
    return {
        "caseId": "avps-v2-synthetic",
        "groupId": "group-synthetic",
        "sunDepressionDeg": 6.0,
        "geometryId": "g1",
        "geometryTag": "synthetic",
        "targetAltitudeDeg": 30.0,
        "relativeAzimuthDeg": 90.0,
        "observerElevationM": 0,
        "aod550": 0.15,
        "replicate": 1,
        "stateId": "opac-profile-continental-average",
        "seed": 1234567,
        "photonHistories": 20_000_000,
        "numericalMethod": "MYSTIC_1D_SPHERICAL_BACKWARD",
    }


def _write_artifact(root: Path, *, legacy_aerosol_file: bool = False):
    expected = _expected_case()
    state = expected["stateId"]
    profile_rel = f"profiles/{state}.four-species.dat"
    (root / "profiles").mkdir(parents=True)

    # The production path uses exact authorized profile bytes. This synthetic unit
    # test temporarily replaces the expected hash with the hash of a tiny fixture.
    profile = root / profile_rel
    profile.write_text("0.0 1 1 1 1\n")
    AGG.EXPECTED_PROFILE_SHA256[state] = AGG.sha256_file(profile)

    directive = f"aerosol_species_file {profile_rel} INSO WASO SOOT SUSO\n"
    if legacy_aerosol_file:
        directive += "aerosol_file profiles/legacy.tau\n"
    (root / "case.inp").write_text(directive)

    for name in AGG.FIXED_RAW_MEMBERS:
        path = root / name
        if path.exists():
            continue
        if name in ("mc.rad.spc", "mc.rad.std.spc"):
            rows = [f"{380.0 + i * 0.05:.2f} {1.0 + i * 1e-6:.8f}" for i in range(8001)]
            path.write_text("\n".join(rows) + "\n")
        else:
            path.write_text(f"synthetic {name}\n")

    wl, rad = AGG.parse_spectrum(root / "mc.rad.spc")
    channels = DummyDerived.derive_channels(wl, rad)
    raw_hashes = {name: AGG.sha256_file(root / name) for name in AGG.FIXED_RAW_MEMBERS}
    raw_hashes[profile_rel] = AGG.sha256_file(profile)
    result = {
        "schemaVersion": 1,
        "stageId": AGG.STAGE,
        "status": "COMPLETED",
        **expected,
        "scientificOrdinal": AGG.EXPECTED_ORDINAL,
        "executionKey": AGG.EXPECTED_EXECUTION_KEY,
        "workflowRunId": 777,
        "workflowRunAttempt": 1,
        "syntaxCheckCount": 1,
        "solverExecutionCount": 1,
        "retryPerformed": False,
        "resumePerformed": False,
        "githubRerun": False,
        "processGroupIsolation": True,
        "authorizationHead": AGG.EXPECTED_AUTH_HEAD,
        "candidateSeedCanonicalSha256": AGG.EXPECTED_SEED_CANONICAL,
        "fourAliasDataTreeSha256": AGG.EXPECTED_FOUR_ALIAS_TREE,
        "fourSpeciesProfileRelativePath": profile_rel,
        "fourSpeciesProfileSha256": raw_hashes[profile_rel],
        "channels": channels,
        "rawMemberSha256ByRelativePath": raw_hashes,
        "resultOpeningAuthorized": False,
        "productionAuthorized": False,
    }
    result["contentSha256"] = AGG.canonical_sha256(result)
    (root / "case-result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return expected, result


def test_review_summary_is_zero_runtime_and_result_closed():
    summary = AGG.review_summary(Path.cwd())
    assert summary["status"] == "REVIEW_ONLY_V2_AGGREGATOR_PARITY_PASS_NO_SOLVER_RESULTS_CLOSED"
    assert summary["caseCount"] == 360
    assert summary["groupCount"] == 72
    assert summary["explicitFourSpeciesProfileRequiredPerCase"] is True
    assert summary["partialResultsMayBeInterpreted"] is False
    assert summary["resultOpeningAuthorized"] is False
    assert summary["solverExecutionPerformed"] is False
    assert summary["dispatchCreated"] is False
    assert summary["productionAuthorized"] is False


def test_validate_case_result_accepts_explicit_four_species_fixture(tmp_path: Path):
    expected, result = _write_artifact(tmp_path)
    channels = AGG.validate_case_result(result, expected, workflow_run_id=777, derived=DummyDerived, artifact_root=tmp_path)
    assert channels == result["channels"]


def test_validate_case_result_refuses_legacy_aerosol_file(tmp_path: Path):
    expected, result = _write_artifact(tmp_path, legacy_aerosol_file=True)
    # Re-hash the deliberately altered input so the refusal is specifically the
    # forbidden transport directive, not an unrelated raw-hash mismatch.
    result["rawMemberSha256ByRelativePath"]["case.inp"] = AGG.sha256_file(tmp_path / "case.inp")
    result["contentSha256"] = AGG.canonical_sha256({k: v for k, v in result.items() if k != "contentSha256"})
    with pytest.raises(AGG.AggregateRefusal, match="legacy aerosol_file"):
        AGG.validate_case_result(result, expected, workflow_run_id=777, derived=DummyDerived, artifact_root=tmp_path)


def test_validate_case_result_refuses_result_opening(tmp_path: Path):
    expected, result = _write_artifact(tmp_path)
    result["resultOpeningAuthorized"] = True
    result["contentSha256"] = AGG.canonical_sha256({k: v for k, v in result.items() if k != "contentSha256"})
    with pytest.raises(AGG.AggregateRefusal, match="result/production boundary crossed"):
        AGG.validate_case_result(result, expected, workflow_run_id=777, derived=DummyDerived, artifact_root=tmp_path)
