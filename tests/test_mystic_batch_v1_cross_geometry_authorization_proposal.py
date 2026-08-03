from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "experiments/mystic-batch-v1/cross_geometry_authorization_proposal.py"


def load_module():
    spec = importlib.util.spec_from_file_location("cg_authorization_proposal", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load proposal generator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


module = load_module()


class AuthorizationProposalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        package = self.root / "experiments/mystic-batch-v1"
        workflows = self.root / ".github/workflows"
        package.mkdir(parents=True)
        workflows.mkdir(parents=True)
        self.paths = {
            "authorization": Path("experiments/mystic-batch-v1/authorization.json"),
            "authorizationTemplate": Path("experiments/mystic-batch-v1/authorization-template.json"),
            "proposal": Path("experiments/mystic-batch-v1/proposal.json"),
            "contract": Path("experiments/mystic-batch-v1/contract.json"),
            "proposalTemplate": Path("experiments/mystic-batch-v1/proposal-authorization-template.json"),
            "proposalAdapter": Path("experiments/mystic-batch-v1/proposal-adapter.py"),
            "proposalValidator": Path("experiments/mystic-batch-v1/proposal-validator.py"),
            "executionAdapter": Path("experiments/mystic-batch-v1/execution-adapter.py"),
            "executionWorkflow": Path(".github/workflows/execution.yml"),
            "runtimeLock": Path("experiments/mystic-batch-v1/runtime-lock.json"),
            "plan": Path("experiments/mystic-batch-v1/plan.py"),
            "analysisDriver": Path("experiments/mystic-batch-v1/analysis.py"),
            "executor": Path("experiments/mystic-batch-v1/executor.py"),
            "aggregate": Path("experiments/mystic-batch-v1/aggregate.py"),
            "audit": Path("experiments/mystic-batch-v1/audit.py"),
        }
        disabled = {
            "schemaVersion": 1,
            "stageId": "cross-geometry-pilot-v1",
            "authorized": False,
            "scientificExecution": False,
            "scientificDiagnostic": False,
            "successDoesNotAuthorizeProduction": True,
            "executionKey": None,
            "batchId": None,
            "proposalPath": None,
            "proposalRawSha256": None,
            "contractRawSha256": None,
            "proposalAdapterRawSha256": None,
            "proposalValidatorRawSha256": None,
            "executionAdapterRawSha256": None,
            "executionWorkflowRawSha256": None,
            "runtimeLockRawSha256": None,
            "planRawSha256": None,
            "analysisDriverRawSha256": None,
            "executorRawSha256": None,
            "aggregateRawSha256": None,
            "auditRawSha256": None,
            "exactAuthorizationParentCommit": None,
            "exactAuthorizationCommit": None,
            "authorizationOrdinal": 0,
            "consumed": False,
            "note": "disabled",
        }
        proposal = {
            "schemaVersion": 1,
            "stageId": "cross-geometry-pilot-v1",
            "batchId": "cross-geometry-pilot-screening-v1",
            "proposalOnly": True,
            "scientificExecution": False,
        }
        (self.root / self.paths["authorization"]).write_text(json.dumps(disabled))
        (self.root / self.paths["authorizationTemplate"]).write_text(json.dumps(disabled))
        (self.root / self.paths["proposal"]).write_text(json.dumps(proposal))
        (self.root / self.paths["contract"]).write_text("{}\n")
        (self.root / self.paths["proposalTemplate"]).write_text("{}\n")
        (self.root / self.paths["proposalAdapter"]).write_text("# adapter\n")
        (self.root / self.paths["proposalValidator"]).write_text(
            "def validate(*args):\n    return {'status': 'PROPOSAL_VALIDATED_NO_EXECUTION'}\n"
        )
        for key in ("executionAdapter", "executionWorkflow", "runtimeLock", "plan", "analysisDriver", "executor", "aggregate", "audit"):
            (self.root / self.paths[key]).write_text(f"# {key}\n")
        subprocess.run(["git", "init"], cwd=self.root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.root, check=True)
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-m", "source"], cwd=self.root, check=True, capture_output=True)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_proposal_binds_exact_files(self) -> None:
        with mock.patch.object(module, "PATHS", self.paths):
            result = module.build_proposal(self.root)
        self.assertEqual(result["status"], "PROPOSAL_ONLY_NOT_AUTHORIZATION")
        self.assertFalse(result["executionAuthorizedByProposal"])
        proposed = result["proposedAuthorization"]
        self.assertTrue(proposed["authorized"])
        self.assertTrue(proposed["scientificExecution"])
        self.assertEqual(proposed["exactAuthorizationParentCommit"], result["sourceCommit"])
        for field, path_key in {
            "proposalRawSha256": "proposal",
            "contractRawSha256": "contract",
            "proposalAdapterRawSha256": "proposalAdapter",
            "proposalValidatorRawSha256": "proposalValidator",
            "executionAdapterRawSha256": "executionAdapter",
            "executionWorkflowRawSha256": "executionWorkflow",
            "runtimeLockRawSha256": "runtimeLock",
            "planRawSha256": "plan",
            "analysisDriverRawSha256": "analysisDriver",
            "executorRawSha256": "executor",
            "aggregateRawSha256": "aggregate",
            "auditRawSha256": "audit",
        }.items():
            self.assertEqual(proposed[field], module.raw_sha256(self.root / self.paths[path_key]))

    def test_enabled_active_authorization_is_refused(self) -> None:
        template = json.loads((self.root / self.paths["authorizationTemplate"]).read_text())
        enabled = {**template, "authorized": True}
        with self.assertRaises(module.ProposalFailure):
            module.ensure_disabled(enabled, template)

    def test_proposal_does_not_itself_authorize_execution(self) -> None:
        with mock.patch.object(module, "PATHS", self.paths):
            result = module.build_proposal(self.root)
        self.assertFalse(result["executionAuthorizedByProposal"])
        self.assertIn("no syntax check", result["boundary"])
        self.assertIsNone(result["proposedAuthorization"]["exactAuthorizationCommit"])


if __name__ == "__main__":
    unittest.main()
