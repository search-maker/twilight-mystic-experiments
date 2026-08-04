from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
GUARD_PATH = ROOT / "experiments/mystic-batch-v1/twilight_surrogate_tier1_ordinal2_execution_guard.py"
SPEC = importlib.util.spec_from_file_location("ordinal2_guard", GUARD_PATH)
assert SPEC and SPEC.loader
G = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(G)

BUNDLE_PATH = ROOT / "experiments/mystic-batch-v1/twilight_surrogate_tier1_ordinal2_evidence_bundle.py"
BSPEC = importlib.util.spec_from_file_location("ordinal2_bundle", BUNDLE_PATH)
assert BSPEC and BSPEC.loader
B = importlib.util.module_from_spec(BSPEC)
BSPEC.loader.exec_module(B)


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def manifests() -> tuple[dict, dict]:
    geometry_ids = [f"g{i:02d}" for i in range(1, 49)]
    source_cases = []
    recovered_cases = []
    for index in range(96):
        photons = 20_000_000 if index < 48 else 50_000_000 if index < 72 else 200_000_000
        case = {
            "ordinal": index + 1,
            "caseId": f"case-{index + 1:03d}",
            "groupId": geometry_ids[index // 2],
            "method": "alis",
            "block": 1 + index % 2,
            "seed": 10_000 + index,
            "photonHistories": photons,
            "alisSpectralImportanceSamplingNm": (500.0, 550.0, 600.0)[index % 3],
            "role": "surrogate-training" if index // 2 < 39 else "internal-holdout",
            "executionTierId": "tier-1-provisional",
        }
        source_cases.append(case)
        recovered_cases.append(dict(case, seed=20_000 + index))
    common = {
        "schemaVersion": 1,
        "stageId": "twilight-surrogate-tier-1-execution-v1",
        "proposalOnly": True,
        "scientificExecution": False,
        "successDoesNotAuthorizeProduction": True,
        "surrogateTrainingAutomaticallyAuthorized": False,
        "productionModelReady": False,
        "batchId": "fixture",
        "adapterId": "mystic-twilight-tier1-execution-v1",
        "bindings": {"x": "y"},
        "externalValidationAnchorIds": ["a1", "a2", "a3", "a4", "a5", "g01"],
        "frozenInputs": {"wavelengthDomainNm": [380.0, 780.0]},
        "internalHoldoutGeometryIds": geometry_ids[39:],
        "limits": {"maximumCases": 96, "maximumParallel": 8, "maximumConfiguredMcPhotonsSum": 6_960_000_000},
        "runtime": {"uvspecSha256": G.EXPECTED_UVSPEC_SHA},
        "source": {"runId": 1},
        "sourcePilotManifestRawSha256": "a" * 64,
        "sourceProposalStageId": "twilight-surrogate-tier-1-proposal-v1",
        "sourceTier1ProposalRawSha256": "b" * 64,
        "trainingGeometryIds": geometry_ids[:39],
        "geometries": [{"geometryId": item} for item in geometry_ids],
    }
    source = dict(common, cases=source_cases)
    recovered = dict(common, cases=recovered_cases)
    recovered["recovery"] = {
        "authorizationOrdinal": 2,
        "sourceAuthorizationOrdinal": 1,
        "executionKey": G.EXECUTION_KEY,
        "freshSeedsForAllCases": True,
        "firstAttemptOnly": True,
        "githubRerunPermitted": False,
        "scientificExecution": False,
        "executionAuthorized": False,
    }
    return source, recovered


class Ordinal2GuardTests(unittest.TestCase):
    def test_only_fresh_seeds_change(self) -> None:
        source, recovered = manifests()
        G.compare_manifests(source, recovered)
        recovered["cases"][0]["seed"] = source["cases"][0]["seed"]
        with self.assertRaisesRegex(G.GuardError, "case changed beyond seed|fresh-seed governance"):
            G.compare_manifests(source, recovered)

    def test_artifact_digest_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            specs = {
                "readiness": (30946826336, 8907433018, "twilight-surrogate-tier-1-ordinal2-atm-z-grid-readiness-v1", "sha256:1146005822c5fc7ef5ad17e27f9cc9b6d950baac38bdc9222e779d3adff9ceb0"),
                "combined": (30946822822, 8907417508, "twilight-surrogate-tier-1-atm-z-grid-combined-spectral-proof-v3", "sha256:4d41e0fab492010e45da37273de9826dfee874e88a79f239d4cecd9a29a8de89"),
                "source-audit": (30946825851, 8907419354, "twilight-surrogate-tier-1-libradtran-source-audit-v1", "sha256:4a7a673ec63416e4ecb7735f4e3f1b1e591c5a0fb657b2e6bae120c99f4a38ed"),
                "provenance": (30946822824, 8907428859, "twilight-surrogate-tier-1-libradtran-provenance-recovery-v1", "sha256:2428a148fbcac0e68fe9bec41ecf5f53b775373786f025da759297246e9b4467"),
            }
            for label, (run_id, artifact_id, name, digest) in specs.items():
                write(root / f"{label}-run.json", {"id": run_id, "conclusion": "success", "head_sha": G.EXPECTED_HEAD})
                write(root / f"{label}-artifacts.json", {"artifacts": [{"id": artifact_id, "name": name, "digest": digest, "expired": False}]})
            G.validate_metadata(root)
            readiness = json.loads((root / "readiness-artifacts.json").read_text())
            readiness["artifacts"][0]["digest"] = "sha256:" + "0" * 64
            write(root / "readiness-artifacts.json", readiness)
            with self.assertRaisesRegex(G.GuardError, "artifact 8907433018 mismatch"):
                G.validate_metadata(root)

    def test_governance_comments_are_required(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "comments.json"
            decision = "\n".join((
                "DECISION: APPROVE_BOUNDED_PACKAGE_RUNTIME_EXCEPTION",
                G.EXPECTED_CURRENT_SOURCE_SHA,
                G.EXPECTED_HISTORICAL_SOURCE_SHA,
                G.EXPECTED_PACKAGE_SHA,
                G.EXPECTED_UVSPEC_SHA,
                G.EXPECTED_RUNTIME_LOCK_SHA,
                "does **not** itself authorize scientific execution",
                "one-file-only, one-commit, unmerged authorization PR",
            ))
            review = "INDEPENDENT DECISION REVIEW — COMPLETE\nall six required acknowledgements are present\ndoes not authorize execution or dispatch"
            write(path, [{"id": G.DECISION_COMMENT_ID, "body": decision}, {"id": G.REVIEW_COMMENT_ID, "body": review}])
            G.validate_comments(path)
            write(path, [{"id": G.DECISION_COMMENT_ID, "body": "DECISION: APPROVE_BOUNDED_PACKAGE_RUNTIME_EXCEPTION"}])
            with self.assertRaisesRegex(G.GuardError, "decision incomplete"):
                G.validate_comments(path)

    def test_evidence_bundle_refuses_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a").mkdir()
            (root / "b").mkdir()
            (root / "a" / "same.json").write_text("{}\n")
            (root / "b" / "same.json").write_text("{}\n")
            with self.assertRaisesRegex(B.BundleError, "found 2"):
                B.one(root, "same.json")


if __name__ == "__main__":
    unittest.main()
