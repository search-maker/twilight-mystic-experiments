from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "modeling" / "surrogate-training-v2"
MAIN_SHA = "b42c97c0a32749902b8e75f3689526be70f309d1"


def module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, PACKAGE / filename)
    assert spec and spec.loader
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


handoff = module("surrogate_training_v2_handoff", "tier1_handoff.py")


def dump(value) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def fake_hash(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def geometry(index: int) -> dict[str, float | str]:
    return {
        "geometryId": f"t1g{index:02d}",
        "sunDepressionDeg": 2.0 + (index % 16),
        "targetAltitudeDeg": 5.0 + (index * 7) % 80,
        "relativeAzimuthDeg": float((index * 11) % 181),
        "observerElevationM": float((index * 137) % 2501),
        "aod550": 0.05 + 0.01 * (index % 30),
        "executionTierId": "tier-1-provisional",
    }


def write(path: Path, value) -> Path:
    path.write_text(dump(value))
    return path


class HandoffFixture:
    def __init__(self, root: Path):
        self.root = root
        training_ids = [f"t1g{i:02d}" for i in range(1, 40)]
        holdout_ids = [f"t1g{i:02d}" for i in range(40, 49)]
        geometries = [geometry(i) for i in range(1, 49)]
        photon_schedule = [20_000_000] * 3 + [50_000_000] * 48 + [100_000_000] * 45
        cases = []
        ordinal = 0
        for index, geometry_id in enumerate(training_ids + holdout_ids, start=1):
            role = "surrogate-training" if geometry_id in training_ids else "internal-holdout"
            for block in (1, 2):
                ordinal += 1
                cases.append(
                    {
                        "ordinal": ordinal,
                        "caseId": f"{geometry_id}-b{block}",
                        "groupId": geometry_id,
                        "method": "alis",
                        "block": block,
                        "seed": 900_000 + ordinal,
                        "photonHistories": photon_schedule[ordinal - 1],
                        "alisSpectralImportanceSamplingNm": (500.0, 550.0, 600.0)[ordinal % 3],
                        "role": role,
                        "executionTierId": "tier-1-provisional",
                    }
                )
        self.manifest = {
            "schemaVersion": 1,
            "stageId": "twilight-surrogate-tier-1-execution-v1",
            "batchId": "synthetic-tier1-handoff",
            "proposalOnly": True,
            "scientificExecution": False,
            "successDoesNotAuthorizeProduction": True,
            "surrogateTrainingAutomaticallyAuthorized": False,
            "productionModelReady": False,
            "trainingGeometryIds": training_ids,
            "internalHoldoutGeometryIds": holdout_ids,
            "geometries": geometries,
            "cases": cases,
        }
        self.paths: dict[str, Path] = {}
        self.paths["manifest"] = write(root / "manifest.json", self.manifest)
        self.plan = {
            "schemaVersion": 1,
            "stageId": "mystic-batch-v1",
            "batchId": self.manifest["batchId"],
            "scientificExecution": True,
            "scientificDiagnostic": True,
            "successDoesNotAuthorizeProduction": True,
            "manifestRawSha256": handoff.raw_sha256(self.paths["manifest"]),
            "caseCount": 96,
            "configuredMcPhotonsSum": 6_960_000_000,
            "cases": [{key: item[key] for key in (
                "ordinal", "caseId", "groupId", "method", "block", "seed",
                "photonHistories", "alisSpectralImportanceSamplingNm", "role", "executionTierId"
            )} for item in cases],
        }
        self.paths["plan"] = write(root / "plan.json", self.plan)
        case_hashes = {item["caseId"]: fake_hash(item["caseId"]) for item in cases}
        self.summary = {
            "schemaVersion": 1,
            "stageId": "mystic-batch-v1",
            "status": "COMPLETED",
            "classification": "BATCH_NUMERICALLY_COMPLETE",
            "scientificDiagnostic": True,
            "successDoesNotAuthorizeProduction": True,
            "manifestRawSha256": handoff.raw_sha256(self.paths["manifest"]),
            "caseCountPlanned": 96,
            "caseCountCompleted": 96,
            "caseCountFailed": 0,
            "syntaxCheckCount": 96,
            "solverExecutionCount": 96,
            "configuredMcPhotonsSum": 6_960_000_000,
            "completedConfiguredMcPhotonsSum": 6_960_000_000,
            "structuralFailures": [],
            "failedCases": [],
            "caseIndex": [
                {"caseId": item["caseId"], "path": f"cases/{item['caseId']}/case-result.json", "caseResultSha256": case_hashes[item["caseId"]]}
                for item in cases
            ],
        }
        self.paths["summary"] = write(root / "batch-summary.json", self.summary)
        self.audit = {
            "schemaVersion": 1,
            "stageId": "mystic-batch-v1",
            "status": "PASSED",
            "batchClassification": "BATCH_NUMERICALLY_COMPLETE",
            "successDoesNotAuthorizeProduction": True,
            "planRawSha256": handoff.raw_sha256(self.paths["plan"]),
            "aggregateRawSha256": handoff.raw_sha256(self.paths["summary"]),
            "caseResultCount": 96,
            "caseResultHashes": case_hashes,
            "failures": [],
        }
        self.paths["audit"] = write(root / "audit.json", self.audit)
        geometry_by_id = {item["geometryId"]: item for item in geometries}
        points = []
        for index, geometry_id in enumerate(training_ids + holdout_ids, start=1):
            mean = 0.001 + index * 0.0001
            role = "surrogate-training" if geometry_id in training_ids else "internal-holdout"
            points.append(
                {
                    "geometryId": geometry_id,
                    "geometry": geometry_by_id[geometry_id],
                    "role": role,
                    "classification": "PRECISION_TARGET_MET",
                    "statistics": {
                        "blockCount": 2,
                        "meanCdM2": mean,
                        "sampleStdCdM2": mean * 0.02,
                        "relativeStandardErrorOfMean": 0.01414213562373095,
                        "nodeMeanRadiance": [mean * (0.8 + node * 0.02) for node in range(15)],
                    },
                    "caseIds": [f"{geometry_id}-b1", f"{geometry_id}-b2"],
                    "eligibleForProvisionalFit": role == "surrogate-training",
                    "eligibleForInternalHoldout": role == "internal-holdout",
                }
            )
        self.analysis = {
            "schemaVersion": 1,
            "stageId": "twilight-surrogate-tier-1-analysis-v1",
            "status": "TIER_1_ANALYZED",
            "geometryCount": 48,
            "caseCount": 96,
            "configuredMcPhotonsSum": 6_960_000_000,
            "adaptiveContinuationRequiredGeometryIds": [],
            "allPointsWithinMaximumRsem": True,
            "points": points,
            "surrogateTrainingAutomaticallyAuthorized": False,
            "productionModelReady": False,
            "observationValidationRequired": True,
        }
        self.paths["analysis"] = write(root / "analysis.json", self.analysis)
        self.dataset = {
            "schemaVersion": 1,
            "stageId": "twilight-surrogate-tier-1-analysis-v1",
            "status": "TIER_1_NUMERICAL_DATASET_COMPLETE",
            "records": points,
            "trainingRecordCount": 39,
            "internalHoldoutRecordCount": 9,
            "adaptiveContinuationRequiredGeometryIds": [],
            "surrogateTrainingAutomaticallyAuthorized": False,
            "observationValidationRequired": True,
        }
        self.paths["dataset"] = write(root / "dataset-v1.json", self.dataset)
        hard_ids = ["g02-early-near-low", "g03-early-perpendicular-high", "g04-mid-perpendicular", "g05-mid-opposite-low", "g06-late-opposite-high-aerosol"]
        soft_ids = ["g01-reference-bridge"]
        anchors = []
        for index, anchor_id in enumerate(hard_ids + soft_ids, start=1):
            point = geometry(index)
            point.pop("geometryId")
            point.pop("executionTierId")
            mean = 0.01 + index * 0.001
            anchors.append(
                {
                    "groupId": anchor_id,
                    "geometry": point,
                    "methods": {"alis": {"meanCdM2": mean, "nodeMeanRadiance": [mean * (0.8 + node * 0.02) for node in range(15)]}},
                    "anchorStrength": "hard" if anchor_id in hard_ids else "soft-diagnostic",
                    "eligibleForTraining": False,
                    "eligibleForModelAcceptance": anchor_id in hard_ids,
                }
            )
        self.reference = {
            "schemaVersion": 1,
            "stageId": "twilight-model-readiness-v1",
            "status": "REFERENCE_ANCHORS_VALIDATED",
            "anchorCount": 6,
            "trainingAutomaticallyAuthorized": False,
            "hardValidationAnchorIds": hard_ids,
            "softDiagnosticAnchorIds": soft_ids,
            "anchors": anchors,
        }
        self.paths["reference"] = write(root / "reference.json", self.reference)
        self.source_run = {"id": 12345, "status": "completed", "conclusion": "success", "run_attempt": 1, "head_sha": "a" * 40}
        self.paths["source_run"] = write(root / "source-run.json", self.source_run)
        self.artifacts = {"artifacts": [
            {"id": 1, "name": "tier1-cases", "digest": "sha256:" + fake_hash("cases"), "expired": False},
            {"id": 2, "name": "tier1-analysis", "digest": "sha256:" + fake_hash("analysis"), "expired": False},
        ]}
        self.paths["artifacts"] = write(root / "artifacts.json", self.artifacts)

    def rewrite(self, key: str, value) -> None:
        write(self.paths[key], value)

    def build(self, output: Path, *, synthetic_only: bool = True, source_guard: Path | None = None):
        return handoff.build(
            self.paths["manifest"], self.paths["plan"], self.paths["summary"], self.paths["audit"],
            self.paths["analysis"], self.paths["dataset"], self.paths["reference"], self.paths["source_run"],
            self.paths["artifacts"], output, exact_main_sha=MAIN_SHA, synthetic_only=synthetic_only,
            source_guard_path=source_guard,
        )


class Tier1HandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.fixture = HandoffFixture(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_complete_handoff_is_deterministic_and_synthetic_only(self):
        first = self.fixture.build(self.root / "first")
        second = self.fixture.build(self.root / "second")
        for key in first:
            self.assertEqual(first[key].read_bytes(), second[key].read_bytes())
        dataset = json.loads(first["dataset"].read_text())
        envelope = json.loads(first["envelope"].read_text())
        self.assertEqual(len(dataset["records"]), 48)
        self.assertEqual(len(dataset["trainingGeometryIds"]), 39)
        self.assertEqual(len(dataset["internalHoldoutGeometryIds"]), 9)
        self.assertTrue(envelope["syntheticOnly"])
        self.assertFalse(envelope["scientificExecution"])
        self.assertFalse(envelope["authorizationPermitted"])
        self.assertFalse(envelope["tier2AutomaticallyPermitted"])
        self.assertFalse(envelope["productionPromotionAuthorized"])

    def test_real_handoff_binds_accepted_guard_descriptor_plan_and_artifact_list(self):
        self.fixture.plan.update(
            {
                "executionKey": "twilight-surrogate-tier-1-v1:numerical:3",
                "authorizationOrdinal": 3,
                "authorizationRef": "e" * 40,
            }
        )
        self.fixture.rewrite("plan", self.fixture.plan)
        self.fixture.audit["planRawSha256"] = handoff.raw_sha256(self.fixture.paths["plan"])
        self.fixture.rewrite("audit", self.fixture.audit)
        self.fixture.source_run["head_sha"] = MAIN_SHA
        self.fixture.rewrite("source_run", self.fixture.source_run)
        guard = {
            "schemaVersion": 2,
            "stageId": "surrogate-training-v2-real-tier1-handoff-guard-v2",
            "status": "REAL_TIER1_HANDOFF_SOURCE_ACCEPTED",
            "sourceRunId": self.fixture.source_run["id"],
            "sourceRunHeadSha": MAIN_SHA,
            "sourceExecutionKey": self.fixture.plan["executionKey"],
            "sourceAuthorizationOrdinal": 3,
            "sourceAuthorizationRef": "e" * 40,
            "sourcePlanRawSha256": handoff.raw_sha256(self.fixture.paths["plan"]),
            "sourceManifestRawSha256": handoff.raw_sha256(self.fixture.paths["manifest"]),
            "sourceArtifactListRawSha256": handoff.raw_sha256(self.fixture.paths["artifacts"]),
            "sourceDescriptorRawSha256": "d" * 64,
            "sourceRunAttempt": 1,
            "sourceArtifactCount": 100,
            "caseArtifactCount": 96,
            "surrogateTrainingAuthorized": False,
            "internalHoldoutOpeningAuthorized": False,
            "tier2Authorized": False,
            "productionPromotionAuthorized": False,
        }
        guard_path = write(self.root / "source-guard.json", guard)
        result = self.fixture.build(self.root / "real", synthetic_only=False, source_guard=guard_path)
        envelope = json.loads(result["envelope"].read_text())
        self.assertEqual(envelope["bindings"]["sourceDescriptorRawSha256"], "d" * 64)
        self.assertEqual(envelope["bindings"]["sourcePlanRawSha256"], guard["sourcePlanRawSha256"])
        self.assertEqual(
            envelope["bindings"]["sourceArtifactListGuardRawSha256"],
            guard["sourceArtifactListRawSha256"],
        )
        self.assertEqual(envelope["bindings"]["sourceGuardRawSha256"], handoff.raw_sha256(guard_path))

        guard["sourceExecutionKey"] = "twilight-surrogate-tier-1-v1:numerical:4"
        write(guard_path, guard)
        with self.assertRaisesRegex(handoff.HandoffRefusal, "accepted real-source guard"):
            self.fixture.build(self.root / "real-mismatch", synthetic_only=False, source_guard=guard_path)

    def test_refuses_aggregate_and_audit_failures(self):
        self.fixture.summary["caseCountCompleted"] = 95
        self.fixture.rewrite("summary", self.fixture.summary)
        with self.assertRaisesRegex(handoff.HandoffRefusal, "aggregate boundary changed"):
            self.fixture.build(self.root / "bad-summary")
        self.fixture = HandoffFixture(self.root)
        self.fixture.audit["status"] = "FAILED"
        self.fixture.rewrite("audit", self.fixture.audit)
        with self.assertRaisesRegex(handoff.HandoffRefusal, "audit boundary changed"):
            self.fixture.build(self.root / "bad-audit")

    def test_refuses_counts_photons_and_duplicate_seed(self):
        self.fixture.manifest["cases"].pop()
        self.fixture.rewrite("manifest", self.fixture.manifest)
        with self.assertRaisesRegex(handoff.HandoffRefusal, "case count"):
            self.fixture.build(self.root / "bad-count")
        self.fixture = HandoffFixture(self.root)
        self.fixture.manifest["cases"][0]["photonHistories"] += 1
        self.fixture.rewrite("manifest", self.fixture.manifest)
        with self.assertRaisesRegex(handoff.HandoffRefusal, "photon accounting"):
            self.fixture.build(self.root / "bad-photons")
        self.fixture = HandoffFixture(self.root)
        self.fixture.manifest["cases"][1]["seed"] = self.fixture.manifest["cases"][0]["seed"]
        self.fixture.rewrite("manifest", self.fixture.manifest)
        with self.assertRaisesRegex(handoff.HandoffRefusal, "seed duplicated"):
            self.fixture.build(self.root / "bad-seed")

    def test_refuses_role_geometry_and_wavelength_drift(self):
        self.fixture.manifest["cases"][0]["role"] = "internal-holdout"
        self.fixture.rewrite("manifest", self.fixture.manifest)
        with self.assertRaisesRegex(handoff.HandoffRefusal, "role drift"):
            self.fixture.build(self.root / "bad-role")
        self.fixture = HandoffFixture(self.root)
        self.fixture.analysis["points"][0]["geometry"]["aod550"] += 0.01
        self.fixture.dataset["records"] = self.fixture.analysis["points"]
        self.fixture.rewrite("analysis", self.fixture.analysis)
        self.fixture.rewrite("dataset", self.fixture.dataset)
        with self.assertRaisesRegex(handoff.HandoffRefusal, "geometry changed"):
            self.fixture.build(self.root / "bad-geometry")
        self.fixture = HandoffFixture(self.root)
        self.fixture.manifest["cases"][0]["alisSpectralImportanceSamplingNm"] = 575.0
        self.fixture.rewrite("manifest", self.fixture.manifest)
        with self.assertRaisesRegex(handoff.HandoffRefusal, "wavelength changed"):
            self.fixture.build(self.root / "bad-wavelength")

    def test_refuses_continuation_required(self):
        self.fixture.analysis["adaptiveContinuationRequiredGeometryIds"] = ["t1g01"]
        self.fixture.analysis["allPointsWithinMaximumRsem"] = False
        self.fixture.analysis["points"][0]["classification"] = "ADAPTIVE_CONTINUATION_REQUIRED"
        self.fixture.dataset["adaptiveContinuationRequiredGeometryIds"] = ["t1g01"]
        self.fixture.dataset["status"] = "TIER_1_NUMERICAL_DATASET_PARTIAL_PRECISION"
        self.fixture.dataset["records"] = self.fixture.analysis["points"]
        self.fixture.rewrite("analysis", self.fixture.analysis)
        self.fixture.rewrite("dataset", self.fixture.dataset)
        with self.assertRaises(handoff.HandoffRefusal):
            self.fixture.build(self.root / "continuation")

    def test_refuses_unresolved_zero_hit_geometry(self):
        geometry_id = self.fixture.analysis["points"][0]["geometryId"]
        case_id = self.fixture.analysis["points"][0]["caseIds"][0]
        self.fixture.analysis["adaptiveContinuationRequiredGeometryIds"] = [geometry_id]
        self.fixture.analysis["zeroHitGeometryIds"] = [geometry_id]
        self.fixture.analysis["allPointsWithinMaximumRsem"] = False
        self.fixture.analysis["points"][0].update(
            {
                "classification": "ADAPTIVE_CONTINUATION_REQUIRED",
                "numericalStatus": "NUMERICAL_ZERO_HIT_UNDERCONVERGED",
                "scientificallyEligible": False,
                "zeroHitCaseIds": [case_id],
            }
        )
        self.fixture.dataset["status"] = "TIER_1_NUMERICAL_DATASET_PARTIAL_PRECISION"
        self.fixture.dataset["adaptiveContinuationRequiredGeometryIds"] = [geometry_id]
        self.fixture.dataset["zeroHitGeometryIds"] = [geometry_id]
        self.fixture.dataset["scientificallyEligible"] = False
        self.fixture.dataset["records"] = self.fixture.analysis["points"]
        self.fixture.rewrite("analysis", self.fixture.analysis)
        self.fixture.rewrite("dataset", self.fixture.dataset)
        with self.assertRaises(handoff.HandoffRefusal):
            self.fixture.build(self.root / "zero-hit-continuation")

    def test_eligible_v2_source_requires_exact_analysis_bindings(self):
        self.fixture.summary.update(
            {
                "schemaVersion": 2,
                "executionComplete": True,
                "scientificallyEligible": False,
                "scientificEligibilityPendingPrecisionAnalysis": True,
                "zeroHitCaseCount": 0,
                "zeroHitDiagnostics": [],
                "continuationRequiredGeometryIds": [],
            }
        )
        self.fixture.rewrite("summary", self.fixture.summary)
        self.fixture.audit.update(
            {
                "schemaVersion": 2,
                "executionComplete": True,
                "scientificallyEligible": False,
                "zeroHitDiagnostics": [],
                "incompleteGeometryEnteredTrainingEligibility": False,
                "aggregateRawSha256": handoff.raw_sha256(self.fixture.paths["summary"]),
            }
        )
        self.fixture.rewrite("audit", self.fixture.audit)
        bindings = {
            "manifestRawSha256": handoff.raw_sha256(self.fixture.paths["manifest"]),
            "aggregateRawSha256": handoff.raw_sha256(self.fixture.paths["summary"]),
            "auditRawSha256": handoff.raw_sha256(self.fixture.paths["audit"]),
            "caseResultRawSha256ByCaseId": self.fixture.audit["caseResultHashes"],
        }
        self.fixture.analysis.update(
            {
                "schemaVersion": 2,
                "stageId": "twilight-surrogate-tier-1-analysis-v2",
                "executionComplete": True,
                "scientificallyEligible": True,
                "zeroHitGeometryIds": [],
                "sourceBindings": bindings,
            }
        )
        for point in self.fixture.analysis["points"]:
            point.update(
                {
                    "numericalStatus": "NUMERICALLY_CONVERGED",
                    "executionComplete": True,
                    "scientificallyEligible": True,
                    "zeroHitCaseIds": [],
                }
            )
        self.fixture.dataset.update(
            {
                "schemaVersion": 2,
                "stageId": "twilight-surrogate-tier-1-analysis-v2",
                "executionComplete": True,
                "scientificallyEligible": True,
                "zeroHitGeometryIds": [],
                "sourceBindings": bindings,
                "records": self.fixture.analysis["points"],
            }
        )
        self.fixture.rewrite("analysis", self.fixture.analysis)
        self.fixture.rewrite("dataset", self.fixture.dataset)
        result = self.fixture.build(self.root / "eligible-v2")
        self.assertTrue(result["dataset"].is_file())

        self.fixture.analysis["sourceBindings"] = {**bindings, "auditRawSha256": "f" * 64}
        self.fixture.rewrite("analysis", self.fixture.analysis)
        with self.assertRaisesRegex(handoff.HandoffRefusal, "source bindings changed"):
            self.fixture.build(self.root / "tampered-v2-bindings")

    def test_refuses_missing_artifact_provenance_and_case_hash(self):
        self.fixture.artifacts["artifacts"][0].pop("digest")
        self.fixture.rewrite("artifacts", self.fixture.artifacts)
        with self.assertRaisesRegex(handoff.HandoffRefusal, "artifact digest"):
            self.fixture.build(self.root / "bad-artifact")
        self.fixture = HandoffFixture(self.root)
        self.fixture.audit["caseResultHashes"].pop("t1g01-b1")
        self.fixture.rewrite("audit", self.fixture.audit)
        with self.assertRaisesRegex(handoff.HandoffRefusal, "case hash universe"):
            self.fixture.build(self.root / "bad-case-hash")


if __name__ == "__main__":
    unittest.main()
