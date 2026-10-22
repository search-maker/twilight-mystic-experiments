from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODULE_PATH = HERE / "phase_b.py"
spec = importlib.util.spec_from_file_location("avps_post360_phase_b", MODULE_PATH)
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)


def expect_refusal(fn, needle: str) -> None:
    try:
        fn()
    except m.PhaseBRefusal as exc:
        if needle not in str(exc):
            raise AssertionError(f"wrong refusal: {exc}")
    else:
        raise AssertionError("expected PhaseBRefusal")


def receipt_fixture() -> dict:
    r = {
        "schemaVersion": 1,
        "stageId": "aerosol-vertical-profile-sensitivity-v1-post360-phase-a",
        "status": "PHASE_A_EXACT360_AGGREGATE_VERIFIED_RESULTS_STILL_CLOSED",
        "authorizationParent": m.AUTHORIZATION_PARENT,
        "authorizationHead": m.AUTHORIZATION_HEAD,
        "scientificOrdinal": 40,
        "sourceWorkflowRunId": 33139545997,
        "sourceWorkflowHead": "6d0e0e0f1dd1deabaf8bb155ee7e323c5ba8673d",
        "gate0MetadataArtifactId": 9676069031,
        "gate0MetadataArtifactDigest": "sha256:70dedcd16209dea74a9ed67a1dc7377c123f1a62fd18741b1e15692702011fc8",
        "gate0MetadataInnerSha256": "323f458b43a031c50f2c2f74971594801608a5cdf437839c8760b42c19bdb92e",
        "protocolReviewPr": 579,
        "protocolReviewHead": m.PROTOCOL_REVIEW_HEAD,
        "caseArtifactCount": 360,
        "sourceAcquisitionContentSha256": m.PHASE_A_ACQUISITION_CONTENT_SHA256,
        "analysisInputContentSha256": m.PHASE_A_ANALYSIS_INPUT_CONTENT_SHA256,
        "analysisInputRawSha256": m.PHASE_A_ANALYSIS_INPUT_RAW_SHA256,
        "caseContentsDownloadedForVerification": True,
        "aggregateResultsCalled": True,
        "openResultsCalled": False,
        "scientificInterpretationPerformed": False,
        "resultOpeningAuthorized": False,
    }
    r["contentSha256"] = m.canonical_sha256(r)
    return r


def main() -> None:
    assert m.AUTHORIZATION_PARENT == "99ade7798627e67921139697ba1a004fa8a304bb"
    assert m.AUTHORIZATION_HEAD == "338ee82c8e088e929f45782b1f7ac1c3aaaaa533"
    assert m.SCIENTIFIC_ORDINAL == 40
    assert m.PHASE_A_RUN_ID == 33170006532
    assert m.PHASE_A_RUN_HEAD == "17537a2a5d60d7836eb9a1e01169a5bab5c70ea2"
    assert m.PHASE_A_ARTIFACT_ID == 9685308839
    assert m.PHASE_A_ARTIFACT_DIGEST == "sha256:68216d6a4982618d8cf9238948f0cbeb651bc9cde7ce53e688b5b1b11d204148"
    assert m.PHASE_A_RECEIPT_CONTENT_SHA256 == "c14ef76e6280bdd34172202c63e8a319b4044cdb647e348926c02d03160198e4"
    assert m.PHASE_A_ANALYSIS_INPUT_CONTENT_SHA256 == "c58907c2f838396417edcfe87d306c130b92374b649790ff25537f3ac049bdc8"
    assert m.PHASE_A_ANALYSIS_INPUT_RAW_SHA256 == "b1c2d82e53c91606854c6ae0fea4d6e08d959dd3ee26ac080d0ee62ad4a4096b"
    assert m.PHASE_A_ACQUISITION_CONTENT_SHA256 == "b3d4ac428ced54e217721507c36e349511ef0b4478f5815af7fe557fed005541"
    assert m.OPEN_RESULTS_GIT_BLOB_SHA1 == "4a6842e83cbd1525bf603c5e09e92317a63b6af9"
    assert m.ANALYSIS_GIT_BLOB_SHA1 == "dd2b7fb9cd4cc660338f1694841a0be5b4bf4a4d"
    assert m.EXECUTION_CONTRACT_GIT_BLOB_SHA1 == "230874923004115ff21f218bb0ce4d2e038d3a98"

    r = receipt_fixture()
    assert r["contentSha256"] == m.PHASE_A_RECEIPT_CONTENT_SHA256
    m.validate_phase_a_receipt(r)
    for key in ("openResultsCalled", "scientificInterpretationPerformed", "resultOpeningAuthorized"):
        bad = dict(r)
        bad[key] = True
        expect_refusal(lambda b=bad: m.validate_phase_a_receipt(b), key)

    source = MODULE_PATH.read_text()
    assert "opener.open_results(" in source
    assert '"resultOpeningPerformed": True' in source
    assert '"scientificInterpretationPerformed": False' in source
    assert '"taylorOrJerusalemScoringPerformed": False' in source
    assert '"levelBMappingPerformed": False' in source
    assert '"productionRoutingChanged": False' in source
    assert "pValuesPermitted" in source
    assert "confidenceIntervalsPermitted" in source
    assert "epsilonSubstitutionPermitted" in source
    print("AVPS post360 Phase B wrapper tests: PASS")


if __name__ == "__main__":
    main()
