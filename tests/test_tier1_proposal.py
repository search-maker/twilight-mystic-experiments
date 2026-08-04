from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "experiments/model-readiness-v1/tier1_proposal.py"
spec = importlib.util.spec_from_file_location("tier1_proposal", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)

GROUPS = [
    "g01-reference-bridge", "g02-early-near-low", "g03-early-perpendicular-high",
    "g04-mid-perpendicular", "g05-mid-opposite-low", "g06-late-opposite-high-aerosol",
]


def write(path: Path, value):
    path.write_text(json.dumps(value, sort_keys=True) + "\n")


class Tier1ProposalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.dataset = self.root / "dataset.json"
        self.readiness = self.root / "readiness.json"
        self.analysis = self.root / "analysis.json"
        self.run = self.root / "run.json"
        self.artifacts = self.root / "artifacts.json"
        self.contract = self.root / "contract.py"
        self.design = self.root / "design.py"
        self.spec = self.root / "spec.json"
        self.policy = self.root / "policy.py"
        write(self.dataset, {"records": [{"groupId": group} for group in GROUPS]})
        write(self.readiness, {"ok": True})
        write(self.analysis, {
            "schemaVersion": 1,
            "stageId": module.SOURCE_STAGE_ID,
            "status": "TIMEOUT_CONTINUATION_ANALYZED",
            "computationalReferenceScreeningComplete": True,
            "noAutomaticAdditionalBlocks": True,
            "screeningOnly": True,
            "successDoesNotAuthorizeProduction": True,
        })
        write(self.run, {
            "id": 123,
            "status": "completed",
            "conclusion": "success",
            "event": "workflow_dispatch",
            "run_attempt": 1,
            "head_branch": "main",
            "name": "MYSTIC held-out timeout continuation v1 scientific execution",
            "path": ".github/workflows/mystic-batch-v1-cross-geometry-confirmation-timeout-continuation.yml",
            "head_sha": "a" * 40,
        })
        write(self.artifacts, {"artifacts": [{
            "id": 456,
            "name": module.SOURCE_ARTIFACT,
            "expired": False,
            "digest": "sha256:" + "b" * 64,
            "workflow_run": {"id": 123},
        }]})
        self.contract.write_text("""
def validate(dataset, readiness):
    return {
        'status': 'REFERENCE_ANCHORS_VALIDATED',
        'anchorCount': 6,
        'anchors': [{'groupId': row['groupId']} for row in dataset['records']],
        'trainingAutomaticallyAuthorized': False,
    }
""")
        self.design.write_text("""
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
            cases.append({'ordinal':ordinal,'caseId':f'{gid}-alis-b{block}','groupId':gid,'executionTierId':tier,'seed':910000+ordinal,'photonHistories':72500000 if i<=48 else 1})
    first=[g['geometryId'] for g in geometries[:48]]
    first_cases=[c['caseId'] for c in cases[:96]]
    return {
      'executionTiers':[{'tierId':'tier-1-provisional','geometryIds':first,'caseIds':first_cases,'configuredMcPhotonsSum':6960000000,'purpose':'early-surrogate-and-holdout-error-map'}],
      'geometries':geometries,'cases':cases,'trainingGeometryIds':training,'internalHoldoutGeometryIds':holdout,
      'externalValidationAnchorIds':sorted(%r),'blocksPerGeometry':2,'sampling':{},'importanceSamplingPolicy':{},'parameterRanges':{},'photonSchedule':[],
      'adaptiveContinuation':{'automaticScientificExecution':False}
    }
""" % GROUPS)
        write(self.spec, {"dummy": True})
        self.policy.write_text("# variance reduction only\n")

    def tearDown(self):
        self.temp.cleanup()

    def call(self):
        return module.build(self.dataset, self.readiness, self.analysis, self.run, self.artifacts, self.contract, self.design, self.spec, self.policy)

    def test_builds_exact_tier_one_proposal(self):
        anchors, proposal, readiness = self.call()
        self.assertEqual(anchors["anchorCount"], 6)
        self.assertEqual(proposal["geometryCount"], 48)
        self.assertEqual(proposal["caseCount"], 96)
        self.assertEqual(proposal["configuredMcPhotonsSum"], 6_960_000_000)
        self.assertFalse(proposal["scientificExecution"])
        self.assertTrue(proposal["authorizationRequired"])
        self.assertEqual(readiness["status"], "TIER_1_PROPOSAL_READY_PENDING_SEPARATE_AUTHORIZATION")

    def test_refuses_incomplete_source_analysis(self):
        value = json.loads(self.analysis.read_text())
        value["computationalReferenceScreeningComplete"] = False
        write(self.analysis, value)
        with self.assertRaises(module.ProposalError):
            self.call()

    def test_refuses_non_first_attempt_source(self):
        value = json.loads(self.run.read_text())
        value["run_attempt"] = 2
        write(self.run, value)
        with self.assertRaises(module.ProposalError):
            self.call()

    def test_real_repository_modules_produce_frozen_tier(self):
        contract = ROOT / "experiments/model-readiness-v1/reference_dataset_contract.py"
        design = ROOT / "experiments/model-readiness-v1/training_design.py"
        spec_path = ROOT / "experiments/model-readiness-v1/training-design.proposal.json"
        policy = ROOT / "experiments/model-readiness-v1/importance_policy.py"
        if not contract.exists() or not design.exists():
            self.skipTest("real repository modules not present in local fixture")
        geometries = {
            group: {
                "geometryId": group,
                "sunDepressionDeg": 6.0 + index,
                "targetAltitudeDeg": 10.0 + index,
                "relativeAzimuthDeg": 30.0 + index,
                "observerElevationM": 100.0 * index,
                "aod550": 0.1 + 0.01 * index,
            }
            for index, group in enumerate(GROUPS)
        }
        method = {
            "blockCount": 2,
            "meanCdM2": 1.0,
            "relativeStandardErrorOfMean": 0.05,
            "nodeMeanRadiance": [0.1] * 15,
        }
        write(self.dataset, {
            "schemaVersion": 1,
            "status": "AUDITED_COMPUTATIONAL_REFERENCE_DATASET",
            "sourceStageId": module.SOURCE_STAGE_ID,
            "screeningOnly": True,
            "observationValidationRequired": True,
            "records": [
                {
                    "groupId": group,
                    "geometry": geometries[group],
                    "methodStatistics": {"reference-vroom": method, "alis": method},
                    "methodOrigins": {"reference-vroom": "fixture", "alis": "fixture"},
                    "meanRatioAlisToVroom": 1.0,
                    "nodeAgreementFraction": 0.9,
                }
                for group in GROUPS
            ],
        })
        write(self.readiness, {
            "schemaVersion": 1,
            "status": "COMPUTATIONAL_REFERENCE_SCREENING_COMPLETE",
            "computationalReferenceScreeningComplete": True,
            "acceptedReferenceGeometryCount": 6,
            "heldOutConfirmationFailureCount": 0,
            "technicalDiagnosisRequiredGeometryIds": [],
            "productionModelReady": False,
            "observationValidationRequired": True,
            "surrogateTrainingAutomaticallyAuthorized": False,
        })
        anchors, proposal, readiness = module.build(
            self.dataset, self.readiness, self.analysis, self.run, self.artifacts,
            contract, design, spec_path, policy,
        )
        self.assertEqual(anchors["anchorCount"], 6)
        self.assertEqual(proposal["geometryCount"], 48)
        self.assertEqual(proposal["caseCount"], 96)
        self.assertEqual(proposal["configuredMcPhotonsSum"], 6_960_000_000)
        self.assertEqual(len(proposal["internalHoldoutGeometryIds"]), 9)
        self.assertFalse(readiness["executionAuthorized"])


if __name__ == "__main__":
    unittest.main()
