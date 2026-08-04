from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "experiments/model-readiness-v1"
MYSTIC = ROOT / "experiments/mystic-batch-v1"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


contract = load_module("soft_reference_contract", MODEL / "reference_dataset_contract.py")
proposal_module = load_module("soft_tier1_proposal", MODEL / "tier1_proposal.py")
source_audit = load_module("soft_tier1_source_audit", MYSTIC / "twilight_surrogate_tier1_source_audit.py")

GROUPS = sorted(contract.EXPECTED_GROUPS)
G01 = contract.SOFT_DIAGNOSTIC_GROUP
HARD_GROUPS = [group for group in GROUPS if group != G01]


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n")


def method(mean: float, rsem: float = 0.05, blocks: int = 4) -> dict:
    return {
        "blockCount": blocks,
        "meanCdM2": mean,
        "relativeStandardErrorOfMean": rsem,
        "nodeMeanRadiance": [mean] * 15,
    }


def geometry(group: str, index: int) -> dict:
    return {
        "geometryId": group,
        "sunDepressionDeg": 4.0 + index,
        "targetAltitudeDeg": 10.0 + index,
        "relativeAzimuthDeg": 30.0 + index,
        "observerElevationM": 100.0 * index,
        "aod550": 0.15,
    }


def hard_record(group: str, index: int) -> dict:
    return {
        "groupId": group,
        "geometry": geometry(group, index),
        "methodStatistics": {
            "reference-vroom": method(1.0),
            "alis": method(0.95),
        },
        "methodOrigins": {
            "reference-vroom": "frozen-reference",
            "alis": "held-out-confirmation",
        },
        "meanRatioAlisToVroom": 0.95,
        "nodeAgreementFraction": 1.0,
    }


def partial_source() -> tuple[dict, dict, dict, dict]:
    dataset = {
        "schemaVersion": 1,
        "status": "INCOMPLETE_COMPUTATIONAL_REFERENCE_DATASET",
        "sourceStageId": "g01-fixed-precision-diagnosis-execution-v1",
        "screeningOnly": True,
        "observationValidationRequired": True,
        "records": [hard_record(group, index + 1) for index, group in enumerate(HARD_GROUPS)],
    }
    readiness = {
        "schemaVersion": 1,
        "status": "COMPUTATIONAL_REFERENCE_SCREENING_REQUIRES_DIAGNOSIS",
        "computationalReferenceScreeningComplete": False,
        "acceptedReferenceGeometryCount": 5,
        "heldOutConfirmationFailureCount": 1,
        "technicalDiagnosisRequiredGeometryIds": [G01],
        "productionModelReady": False,
        "observationValidationRequired": True,
        "surrogateTrainingAutomaticallyAuthorized": False,
        "noAutomaticAdditionalBlocks": True,
    }
    analysis = {
        "schemaVersion": 1,
        "stageId": "g01-fixed-precision-diagnosis-execution-v1",
        "status": "G01_FIXED_PRECISION_EXECUTION_ANALYZED",
        "classification": "G01_PERSISTENT_HIGH_VARIANCE",
        "computationalReferenceScreeningComplete": False,
        "noAutomaticAdditionalBlocks": True,
        "screeningOnly": True,
        "successDoesNotAuthorizeProduction": True,
        "g01Result": {
            "classification": "G01_PERSISTENT_HIGH_VARIANCE",
            "methodStatistics": {
                "reference-vroom": method(0.003533, 0.0754, 6),
                "alis": method(0.003787, 0.095729, 8),
            },
            "meanRatioAlisToVroom": 1.0717,
            "vroomPhotopicWeightFractionNodeRatioInsideInterval": 0.965,
        },
    }
    pilot = {
        "stageId": "cross-geometry-pilot-v1",
        "geometries": [geometry(group, index + 1) for index, group in enumerate(GROUPS)],
    }
    return dataset, readiness, analysis, pilot


def fake_design_source(groups: list[str]) -> str:
    return """
import json

def load(path):
    return json.loads(path.read_text())

def build(spec, policy):
    geometries=[]; cases=[]; training=[]; holdout=[]
    for i in range(1,97):
        gid=f'train-{i:04d}'; tier='tier-1-provisional' if i<=48 else 'tier-2-completion'
        geometries.append({'geometryId':gid,'executionTierId':tier})
        (holdout if i%%5==0 else training).append(gid)
        for block in (1,2):
            ordinal=(i-1)*2+block
            role='internal-holdout' if i%%5==0 else 'surrogate-training'
            cases.append({'ordinal':ordinal,'caseId':f'{gid}-alis-b{block}','groupId':gid,'executionTierId':tier,'seed':920000+ordinal,'photonHistories':72500000 if i<=48 else 1,'method':'alis','role':role,'alisSpectralImportanceSamplingNm':[500.0,550.0,600.0][i%%3]})
    first=[g['geometryId'] for g in geometries[:48]]
    first_cases=[c['caseId'] for c in cases[:96]]
    return {
      'executionTiers':[{'tierId':'tier-1-provisional','geometryIds':first,'caseIds':first_cases,'configuredMcPhotonsSum':6960000000,'purpose':'early-surrogate-and-holdout-error-map'}],
      'geometries':geometries,'cases':cases,'trainingGeometryIds':training,'internalHoldoutGeometryIds':holdout,
      'externalValidationAnchorIds':sorted(%r),'blocksPerGeometry':2,'sampling':{},'importanceSamplingPolicy':{},'parameterRanges':{},'photonSchedule':[],
      'adaptiveContinuation':{'automaticScientificExecution':False}
    }
""" % groups


class SoftAnchorContractTests(unittest.TestCase):
    def test_five_hard_plus_one_soft_is_explicit_and_non_gating(self):
        dataset, readiness, analysis, pilot = partial_source()
        result = contract.validate(dataset, readiness, analysis, pilot)
        self.assertEqual(result["anchorCount"], 6)
        self.assertEqual(result["hardValidationAnchorCount"], 5)
        self.assertEqual(result["softDiagnosticAnchorCount"], 1)
        soft = [row for row in result["anchors"] if row["anchorStrength"] == "soft-diagnostic"]
        self.assertEqual([row["groupId"] for row in soft], [G01])
        self.assertFalse(soft[0]["eligibleForTraining"])
        self.assertFalse(soft[0]["eligibleForModelAcceptance"])
        self.assertEqual(soft[0]["failedAcceptanceGate"], "alis-relative-standard-error-of-mean<=0.08")

    def test_soft_anchor_requires_exact_bounded_near_miss(self):
        dataset, readiness, analysis, pilot = partial_source()
        analysis["g01Result"]["methodStatistics"]["alis"]["relativeStandardErrorOfMean"] = 0.079
        with self.assertRaises(contract.ContractError):
            contract.validate(dataset, readiness, analysis, pilot)


class SoftAnchorProposalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        dataset, readiness, analysis, pilot = partial_source()
        self.dataset = self.root / "dataset.json"; write(self.dataset, dataset)
        self.readiness = self.root / "readiness.json"; write(self.readiness, readiness)
        self.analysis = self.root / "analysis.json"; write(self.analysis, analysis)
        self.pilot = self.root / "pilot.json"; write(self.pilot, pilot)
        self.run = self.root / "run.json"; write(self.run, {
            "id": 9001,
            "status": "completed",
            "conclusion": "success",
            "event": "push",
            "run_attempt": 1,
            "head_branch": "main",
            "head_sha": "a" * 40,
            "name": "G01 precision artifact-only recovery",
            "path": ".github/workflows/mystic-batch-v1-cross-geometry-g01-precision-recovery.yml",
        })
        self.artifacts = self.root / "artifacts.json"; write(self.artifacts, {"artifacts": [{
            "id": 9002,
            "name": "cross-geometry-g01-precision-continuation-v1-recovery-analysis",
            "expired": False,
            "digest": "sha256:" + "b" * 64,
            "workflow_run": {"id": 9001},
        }]})
        self.design = self.root / "design.py"; self.design.write_text(fake_design_source(GROUPS))
        self.spec = self.root / "spec.json"; write(self.spec, {"dummy": True})
        self.policy = self.root / "policy.py"; self.policy.write_text("# variance reduction only\n")

    def tearDown(self):
        self.temp.cleanup()

    def test_recovery_source_generates_tier_one_without_promoting_soft_anchor(self):
        anchors, proposal, readiness = proposal_module.build(
            self.dataset,
            self.readiness,
            self.analysis,
            self.run,
            self.artifacts,
            MODEL / "reference_dataset_contract.py",
            self.design,
            self.spec,
            self.policy,
            self.pilot,
        )
        self.assertEqual(anchors["hardValidationAnchorCount"], 5)
        self.assertEqual(anchors["softDiagnosticAnchorIds"], [G01])
        self.assertEqual(proposal["caseCount"], 96)
        self.assertEqual(proposal["configuredMcPhotonsSum"], 6_960_000_000)
        self.assertEqual(proposal["softDiagnosticAnchorIds"], [G01])
        self.assertTrue(proposal["referenceAnchorPolicy"]["softDiagnosticsAreReportOnly"])
        self.assertEqual(readiness["hardValidationAnchorCount"], 5)
        self.assertEqual(readiness["softDiagnosticAnchorCount"], 1)

        proposal_path = self.root / "tier-1-scientific-proposal.json"; write(proposal_path, proposal)
        anchors_path = self.root / "validated-reference-anchors.json"; write(anchors_path, anchors)
        readiness_path = self.root / "tier-1-readiness.json"; write(readiness_path, readiness)
        proposal_run = self.root / "proposal-run.json"; write(proposal_run, {
            "id": 9101,
            "status": "completed",
            "conclusion": "success",
            "event": "push",
            "run_attempt": 1,
            "head_branch": "main",
            "head_sha": "c" * 40,
            "name": source_audit.WORKFLOW_NAME,
            "path": source_audit.WORKFLOW_PATH,
        })
        proposal_artifacts = self.root / "proposal-artifacts.json"; write(proposal_artifacts, {"artifacts": [{
            "id": 9102,
            "name": source_audit.ARTIFACT_NAME,
            "expired": False,
            "digest": "sha256:" + "d" * 64,
            "workflow_run": {"id": 9101},
        }]})
        audited = source_audit.audit(
            proposal_path, anchors_path, readiness_path, proposal_run, proposal_artifacts
        )
        self.assertEqual(audited["hardValidationAnchorCount"], 5)
        self.assertEqual(audited["softDiagnosticAnchorCount"], 1)

        broken = json.loads(anchors_path.read_text())
        next(row for row in broken["anchors"] if row["groupId"] == G01)["eligibleForModelAcceptance"] = True
        write(anchors_path, broken)
        with self.assertRaises(source_audit.SourceAuditError):
            source_audit.audit(
                proposal_path, anchors_path, readiness_path, proposal_run, proposal_artifacts
            )


if __name__ == "__main__":
    unittest.main()
