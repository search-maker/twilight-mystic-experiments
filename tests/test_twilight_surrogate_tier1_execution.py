from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPOSITORY_ROOT = HERE.parent if (HERE.parent / 'experiments').is_dir() else HERE
MODULE_ROOT = (
    REPOSITORY_ROOT / 'experiments/mystic-batch-v1'
    if (REPOSITORY_ROOT / 'experiments/mystic-batch-v1').is_dir()
    else HERE
)


def load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, MODULE_ROOT / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


package = load_module("tier1_package", "twilight_surrogate_tier1_execution_package.py")
adapter = load_module("tier1_adapter", "twilight_surrogate_tier1_execution_adapter.py")
plan = load_module("tier1_plan", "twilight_surrogate_tier1_execution_plan.py")
analysis = load_module("tier1_analysis", "twilight_surrogate_tier1_analysis.py")
source_audit = load_module("tier1_source_audit", "twilight_surrogate_tier1_source_audit.py")
auth_proposal = load_module(
    "tier1_auth_proposal", "twilight_surrogate_tier1_authorization_proposal.py"
)


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n")


def tier1_proposal() -> dict:
    geometries = []
    cases = []
    training = []
    holdout = []
    ordinal = 0
    photon_total = 0
    for index in range(1, 49):
        photons = (
            20_000_000
            if index <= 19
            else 50_000_000
            if index <= 31
            else 100_000_000
            if index <= 40
            else 200_000_000
        )
        geometry_id = f"train-{index:04d}"
        role = "internal-holdout" if index % 5 == 0 else "surrogate-training"
        (holdout if role == "internal-holdout" else training).append(geometry_id)
        importance = [500.0, 550.0, 600.0][index % 3]
        geometries.append(
            {
                "geometryId": geometry_id,
                "executionTierId": "tier-1-provisional",
                "sunDepressionDeg": 2.0 + index / 3,
                "targetAltitudeDeg": 5.0 + index,
                "relativeAzimuthDeg": float((index * 11) % 180),
                "observerElevationM": float(index * 20),
                "aod550": 0.05 + index / 500,
                "alisSpectralImportanceSamplingNm": importance,
                "photonHistoriesPerBlock": photons,
            }
        )
        for block in (1, 2):
            ordinal += 1
            photon_total += photons
            cases.append(
                {
                    "ordinal": ordinal,
                    "caseId": f"{geometry_id}-alis-b{block}",
                    "groupId": geometry_id,
                    "method": "alis",
                    "block": block,
                    "seed": 910_000 + ordinal,
                    "photonHistories": photons,
                    "alisSpectralImportanceSamplingNm": importance,
                    "role": role,
                    "executionTierId": "tier-1-provisional",
                }
            )
    assert photon_total == 6_960_000_000
    return {
        "schemaVersion": 1,
        "stageId": "twilight-surrogate-tier-1-proposal-v1",
        "batchId": "twilight-surrogate-space-filling-v1-tier-1",
        "status": "PROPOSAL_ONLY_NOT_AUTHORIZATION",
        "mode": "scientific-proposal",
        "proposalOnly": True,
        "scientificExecution": False,
        "successDoesNotAuthorizeProduction": True,
        "observationValidationRequired": True,
        "authorizationRequired": True,
        "executionTierId": "tier-1-provisional",
        "geometryCount": 48,
        "caseCount": 96,
        "configuredMcPhotonsSum": photon_total,
        "method": "alis",
        "blocksPerGeometry": 2,
        "source": {"runId": 777},
        "bindings": {"sourceAnalysisRawSha256": "a" * 64},
        "externalValidationAnchorIds": [f"g{i:02d}" for i in range(1, 7)],
        "trainingGeometryIds": training,
        "internalHoldoutGeometryIds": holdout,
        "geometries": geometries,
        "cases": cases,
        "adaptiveContinuation": {"automaticScientificExecution": False},
        "surrogateTrainingAutomaticallyAuthorized": False,
        "productionModelReady": False,
    }


def pilot_manifest() -> dict:
    runtime = {
        key: "a" * 64
        for key in (
            "uvspecSha256",
            "uvspecHelpSha256",
            "libRadtranDataTreeSha256",
            "atmosphereSha256",
            "runtimeLockRawSha256",
        )
    }
    return {
        "stageId": "cross-geometry-pilot-v1",
        "adapterId": "mystic-cross-geometry-v1",
        "runtime": runtime,
        "frozenInputs": {
            "wavelengthDomainNm": [380, 780],
            "diagnosticNodesNm": [
                470, 480, 490, 500, 510, 520, 530, 540, 560, 580, 590, 600, 610, 640, 660
            ],
            "molecularAbsorption": "crs",
            "mcSpherical": "1D",
            "alisSpectralImportanceSamplingNm": 405.0,
            "albedo": 0.15,
            "dataPaths": {
                "solarFlux": {"root": "libRadtranData", "path": "solar"},
                "wavelengthGrid": {"root": "repository", "path": "grid.dat"},
                "atmosphere": {"root": "libRadtranData", "path": "atmosphere.dat"},
            },
        },
    }


class ExecutionCoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.proposal_path = self.root / "proposal.json"
        self.pilot_path = self.root / "pilot.json"
        write(self.proposal_path, tier1_proposal())
        write(self.pilot_path, pilot_manifest())

    def tearDown(self):
        self.temp.cleanup()

    def test_package_and_plan_are_exact(self):
        manifest = package.build(self.proposal_path, self.pilot_path)
        self.assertEqual(len(manifest["geometries"]), 48)
        self.assertEqual(len(manifest["cases"]), 96)
        self.assertEqual(manifest["limits"]["maximumParallel"], 8)
        self.assertEqual(manifest["frozenInputs"]["alisSpectralImportanceSamplingNm"], 550.0)
        manifest_path = self.root / "manifest.json"
        guard_path = self.root / "guard.json"
        adapter_path = self.root / "adapter.py"
        lock_path = self.root / "lock.json"
        workflow_path = self.root / "workflow.yml"
        write(manifest_path, manifest)
        write(
            guard_path,
            {
                "status": "AUTHORIZED",
                "caseCount": 96,
                "configuredMcPhotonsSum": 6_960_000_000,
                "authorizationRef": "b" * 40,
                "authorizationOrdinal": 1,
                "executionKey": "twilight-surrogate-tier-1-v1:numerical:1",
            },
        )
        adapter_path.write_text("# adapter\n")
        lock_path.write_text("{}\n")
        workflow_path.write_text("name: fixture\n")
        result = plan.build(manifest_path, guard_path, adapter_path, lock_path, workflow_path)
        self.assertEqual(result["caseCount"], 96)
        self.assertEqual(result["configuredMcPhotonsSum"], 6_960_000_000)
        self.assertEqual(result["maximumParallel"], 8)
        self.assertEqual(len(result["matrix"]), 96)
        timeout_by_photons = {row["photon_histories"]: row["timeout_seconds"] for row in result["matrix"]}
        self.assertEqual(timeout_by_photons, {20_000_000: 900, 50_000_000: 1200, 100_000_000: 1800, 200_000_000: 2400})

    def test_adapter_uses_case_specific_importance_reference(self):
        manifest = package.build(self.proposal_path, self.pilot_path)
        manifest_path = self.root / "manifest.json"
        write(manifest_path, manifest)
        runtime_path = self.root / "runtime.json"
        write(runtime_path, {"schemaVersion": 1, "stageId": "mystic-batch-v1", "scientificSolverExecuted": False, "syntaxCheckExecuted": False, **manifest["runtime"]})
        stub = self.root / "cross_geometry_adapter.py"
        stub.write_text("""
def resolve_case(manifest, case_id):
    case = [item for item in manifest['cases'] if item['caseId'] == case_id][0]
    geometry = [item for item in manifest['geometries'] if item['geometryId'] == case['groupId']][0]
    return case, geometry

def normalized_inputs(manifest, case, geometry):
    return {'alisSpectralImportanceSamplingNm': manifest['frozenInputs']['alisSpectralImportanceSamplingNm']}

def render_input(inputs, data_dir, repository_root, case_dir):
    return f"mc_spectral_is {inputs['alisSpectralImportanceSamplingNm']}\\n"
""")
        old_base = adapter.BASE
        adapter.BASE = stub
        try:
            selected = manifest["cases"][0]
            result = adapter.prepare_case(manifest_path, runtime_path, selected["caseId"], self.root, self.root, self.root / "case-output")
        finally:
            adapter.BASE = old_base
        self.assertEqual(result["alisSpectralImportanceSamplingNm"], selected["alisSpectralImportanceSamplingNm"])
        self.assertIn(str(selected["alisSpectralImportanceSamplingNm"]), Path(result["inputPath"]).read_text())

    def test_analysis_groups_two_blocks_and_never_trains(self):
        proposal = tier1_proposal()
        manifest = package.build(self.proposal_path, self.pilot_path)
        manifest_path = self.root / "manifest.json"
        write(manifest_path, manifest)
        cases_root = self.root / "cases"
        for case in proposal["cases"]:
            case_dir = cases_root / case["caseId"]
            value = 1.0 + (0.01 if case["block"] == 2 else 0.0)
            write(case_dir / "case-result.json", {"caseId": case["caseId"], "status": "COMPLETED", "solver": {"exitCode": 0, "timedOut": False}, "seed": case["seed"], "photonHistories": case["photonHistories"], "selectedPhotopicContributionCdM2": value, "selectedNodeRadiance": [0.1] * 15})
        summary_path = self.root / "summary.json"
        audit_path = self.root / "audit.json"
        write(summary_path, {"classification": "BATCH_NUMERICALLY_COMPLETE", "caseCountCompleted": 96, "configuredMcPhotonsSum": 6_960_000_000})
        write(audit_path, {"status": "PASSED", "caseResultCount": 96})
        result, dataset = analysis.analyze(manifest_path, cases_root, summary_path, audit_path)
        self.assertEqual(result["precisionAcceptedGeometryCount"], 48)
        self.assertEqual(dataset["trainingRecordCount"], 39)
        self.assertEqual(dataset["internalHoldoutRecordCount"], 9)
        self.assertFalse(result["surrogateTrainingAutomaticallyAuthorized"])


class SourceAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.proposal = self.root / "proposal.json"
        self.anchors = self.root / "anchors.json"
        self.readiness = self.root / "readiness.json"
        self.run = self.root / "run.json"
        self.artifacts = self.root / "artifacts.json"
        write(self.proposal, tier1_proposal())
        write(self.anchors, {"schemaVersion": 1, "stageId": "twilight-model-readiness-v1", "status": "REFERENCE_ANCHORS_VALIDATED", "anchorCount": 6, "anchors": [{"groupId": f"g{i:02d}", "eligibleForTraining": False} for i in range(1, 7)], "trainingAutomaticallyAuthorized": False, "productionModelReady": False, "observationValidationRequired": True})
        write(self.readiness, {"schemaVersion": 1, "stageId": "twilight-surrogate-tier-1-proposal-v1", "status": "TIER_1_PROPOSAL_READY_PENDING_SEPARATE_AUTHORIZATION", "referenceAnchorCount": 6, "geometryCount": 48, "caseCount": 96, "configuredMcPhotonsSum": 6_960_000_000, "scientificExecution": False, "executionAuthorized": False, "surrogateTrainingAuthorized": False, "productionModelReady": False, "observationValidationRequired": True})
        write(self.run, {"id": 333, "status": "completed", "conclusion": "success", "event": "workflow_run", "run_attempt": 1, "head_branch": "main", "head_sha": "c" * 40, "name": source_audit.WORKFLOW_NAME, "path": source_audit.WORKFLOW_PATH})
        write(self.artifacts, {"artifacts": [{"id": 444, "name": source_audit.ARTIFACT_NAME, "expired": False, "digest": "sha256:" + "d" * 64, "workflow_run": {"id": 333}}]})

    def tearDown(self):
        self.temp.cleanup()

    def test_audit_accepts_exact_first_attempt_proposal(self):
        result = source_audit.audit(self.proposal, self.anchors, self.readiness, self.run, self.artifacts)
        self.assertEqual(result["status"], "TIER_1_SOURCE_PROPOSAL_AUDITED")
        self.assertEqual(result["caseCount"], 96)
        self.assertFalse(result["executionAuthorized"])

    def test_audit_refuses_retry(self):
        value = json.loads(self.run.read_text())
        value["run_attempt"] = 2
        write(self.run, value)
        with self.assertRaises(source_audit.SourceAuditError):
            source_audit.audit(self.proposal, self.anchors, self.readiness, self.run, self.artifacts)


class AuthorizationProposalTests(unittest.TestCase):
    def test_generator_binds_disabled_tree_without_authorizing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            subprocess.run(["git", "init", "-q", root], check=True)
            subprocess.run(["git", "-C", root, "config", "user.email", "test@example.com"], check=True)
            subprocess.run(["git", "-C", root, "config", "user.name", "Test"], check=True)
            template = json.loads((MODULE_ROOT / "authorization.twilight-surrogate-tier-1-template.json").read_text())
            write(root / auth_proposal.TEMPLATE_PATH, template)
            write(root / auth_proposal.AUTHORIZATION_PATH, template)
            for relative in auth_proposal.paths().values():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(f"fixture {relative.as_posix()}\n")
            source = root / "source-audit.json"
            write(source, {"schemaVersion": 1, "stageId": "twilight-surrogate-tier-1-source-audit-v1", "status": "TIER_1_SOURCE_PROPOSAL_AUDITED", "sourceProposalRunId": 333, "sourceProposalArtifactId": 444, "sourceProposalArtifactDigest": "sha256:" + "d" * 64, "tier1ProposalRawSha256": "e" * 64, "geometryCount": 48, "caseCount": 96, "configuredMcPhotonsSum": 6_960_000_000, "referenceAnchorCount": 6, "scientificExecution": False, "executionAuthorized": False, "surrogateTrainingAuthorized": False, "productionModelReady": False, "observationValidationRequired": True})
            subprocess.run(["git", "-C", root, "add", "."], check=True)
            subprocess.run(["git", "-C", root, "commit", "-qm", "base"], check=True)
            result = auth_proposal.build(root, source)
            self.assertEqual(result["status"], "PROPOSAL_ONLY_NOT_AUTHORIZATION")
            self.assertFalse(result["executionAuthorizedByProposal"])
            self.assertEqual(result["authorizationOrdinal"], 1)
            self.assertEqual(result["authorization"]["authorized"], True)
            self.assertEqual(result["authorization"]["exactAuthorizationParentCommit"], subprocess.check_output(["git", "-C", root, "rev-parse", "HEAD"], text=True).strip())


if __name__ == "__main__":
    unittest.main()
