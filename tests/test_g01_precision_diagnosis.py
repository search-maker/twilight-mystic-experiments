from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "experiments/mystic-batch-v1/g01_precision_diagnosis.py"
spec = importlib.util.spec_from_file_location("g01_diag", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n")


class G01DiagnosisTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.analysis = self.root / "analysis.json"
        self.readiness = self.root / "readiness.json"
        self.dataset = self.root / "dataset.json"
        self.preflight = self.root / "preflight"
        self.run = self.root / "run.json"
        self.artifacts = self.root / "artifacts.json"
        held_values = [0.004506067717766593, 0.003010531920610223, 0.0032999632406862296, 0.0038986015089986065]
        held_summary = module.method_summary(held_values)
        vroom_values = [0.0030667663372535036, 0.0043350386845514175, 0.0025989544753383742, 0.0033054814482914954, 0.003914309208951925, 0.003980629762365087]
        vroom_summary = module.method_summary(vroom_values)
        vroom_summary["nodeMeanRadiance"] = [0.0001] * 15
        held_summary["nodeMeanRadiance"] = [0.00011] * 15
        write(self.analysis, {
            "schemaVersion": 1,
            "stageId": module.SOURCE_STAGE_ID,
            "status": "TIMEOUT_CONTINUATION_ANALYZED",
            "computationalReferenceScreeningComplete": False,
            "noAutomaticAdditionalBlocks": True,
            "screeningOnly": True,
            "successDoesNotAuthorizeProduction": True,
            "sourceFailedRunId": 30871800549,
            "preservedG01CaseResultCount": 4,
            "newCaseResultCount": 8,
            "newConfiguredMcPhotonsSum": 1_600_000_000,
            "geometryResults": [
                {
                    "groupId": module.GROUP_ID,
                    "classification": "HELD_OUT_CONFIRMATION_INCONCLUSIVE_PRECISION_CAP_REACHED",
                    "nextAction": "TECHNICAL_DIAGNOSIS_REQUIRED_NO_AUTOMATIC_MORE_BLOCKS",
                    "meanRatioAlisToVroom": 1.0411093471572315,
                    "vroomPhotopicWeightFractionNodeRatioInsideInterval": 0.9650038923996925,
                    "methodStatistics": {"alis": held_summary, "reference-vroom": vroom_summary},
                },
                {"groupId": "g06-late-opposite-high-aerosol", "classification": "HELD_OUT_CONFIRMATION_PASSED"},
            ],
        })
        write(self.readiness, {
            "schemaVersion": 1,
            "status": "COMPUTATIONAL_REFERENCE_SCREENING_REQUIRES_DIAGNOSIS",
            "computationalReferenceScreeningComplete": False,
            "acceptedReferenceGeometryCount": 5,
            "heldOutConfirmationFailureCount": 1,
            "technicalDiagnosisRequiredGeometryIds": [module.GROUP_ID],
            "noAutomaticAdditionalBlocks": True,
            "productionModelReady": False,
            "observationValidationRequired": True,
            "surrogateTrainingAutomaticallyAuthorized": False,
        })
        write(self.dataset, {"status": "INCOMPLETE_COMPUTATIONAL_REFERENCE_DATASET", "records": [{"groupId": group} for group in ("g02", "g03", "g04", "g05", "g06")]})
        write(self.run, {
            "id": module.SOURCE_RUN_ID,
            "status": "completed",
            "conclusion": "success",
            "event": "workflow_dispatch",
            "run_attempt": 1,
            "head_branch": "main",
            "head_sha": "a" * 40,
            "name": module.SOURCE_WORKFLOW_NAME,
            "path": module.SOURCE_WORKFLOW_PATH,
        })
        write(self.artifacts, {"artifacts": [
            {"id": 1, "name": module.ANALYSIS_ARTIFACT, "expired": False, "digest": "sha256:" + "b" * 64, "workflow_run": {"id": module.SOURCE_RUN_ID}},
            {"id": 2, "name": module.PREFLIGHT_ARTIFACT, "expired": False, "digest": "sha256:" + "c" * 64, "workflow_run": {"id": module.SOURCE_RUN_ID}},
        ]})
        write(self.preflight / "source-package/final-convergence-analysis.json", {
            "geometryResults": [{
                "groupId": module.GROUP_ID,
                "selectedAlisReferenceNm": 600.0,
                "candidateAlisReferences": [
                    {"referenceNm": 500.0, "alisStatistics": {**module.method_summary([0.0018, 0.0025, 0.0037]), "nodeMeanRadiance": [0.1] * 15}},
                    {"referenceNm": 550.0, "alisStatistics": {**module.method_summary([0.0035, 0.0017, 0.0029]), "nodeMeanRadiance": [0.1] * 15}},
                    {"referenceNm": 600.0, "alisStatistics": {**module.method_summary([0.004570805238636181, 0.0027757607275786054, 0.004252291237305099]), "nodeMeanRadiance": [0.1] * 15}},
                ],
            }]
        })
        nodes = [470,480,490,500,510,520,530,540,560,580,590,600,610,640,660]
        for index, value in enumerate(held_values, start=1):
            write(self.preflight / f"source-g01/cgc-g01-alis-r{index}/case-result.json", {
                "caseId": f"cgc-g01-alis-r{index}",
                "status": "COMPLETED",
                "scientificDiagnostic": True,
                "successDoesNotAuthorizeProduction": True,
                "seed": 80600 + index,
                "photonHistories": module.PHOTONS_PER_BLOCK,
                "syntaxCheckCount": 1,
                "solverExecutionCount": 1,
                "syntax": {"exitCode": 0, "timedOut": False},
                "solver": {"exitCode": 0, "timedOut": False, "elapsedSeconds": 370.0 + index},
                "selectedPhotopicContributionCdM2": value,
                "diagnosticNodesNm": nodes,
                "selectedNodeRadiance": [value * (0.02 + j * 0.001) for j in range(15)],
            })

    def tearDown(self):
        self.temp.cleanup()

    def call(self):
        return module.build(self.analysis, self.readiness, self.dataset, self.preflight, self.run, self.artifacts)

    def test_diagnoses_precision_only_and_freezes_four_cases(self):
        diagnosis, proposal, readiness = self.call()
        self.assertEqual(diagnosis["failureMode"], "MONTE_CARLO_PRECISION_ONLY")
        self.assertTrue(diagnosis["methodCompatibilityPassed"])
        self.assertFalse(diagnosis["singleBlockDeletionAuthorized"])
        self.assertEqual(diagnosis["recommendedAdditionalBlocks"], 4)
        self.assertEqual(proposal["limits"]["maximumConfiguredMcPhotonsSum"], 200_000_000)
        self.assertEqual([case["seed"] for case in proposal["cases"]], module.NEW_SEEDS)
        self.assertEqual([case["block"] for case in proposal["cases"]], module.NEW_BLOCKS)
        self.assertFalse(proposal["executionAuthorizedByProposal"])
        self.assertEqual(readiness["status"], "G01_FIXED_PRECISION_DIAGNOSIS_PROPOSED_PENDING_SEPARATE_AUTHORIZATION")

    def test_refuses_method_discrepancy_masquerading_as_precision(self):
        value = json.loads(self.analysis.read_text())
        value["geometryResults"][0]["meanRatioAlisToVroom"] = 2.1
        write(self.analysis, value)
        with self.assertRaises(module.DiagnosisError):
            self.call()

    def test_refuses_changed_preserved_seed(self):
        path = self.preflight / "source-g01/cgc-g01-alis-r1/case-result.json"
        value = json.loads(path.read_text())
        value["seed"] = 99999
        write(path, value)
        with self.assertRaises(module.DiagnosisError):
            self.call()


if __name__ == "__main__":
    unittest.main()
