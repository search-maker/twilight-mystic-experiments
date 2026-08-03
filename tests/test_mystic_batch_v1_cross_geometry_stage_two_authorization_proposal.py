from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "experiments" / "mystic-batch-v1" / "cross_geometry_stage_two_authorization_proposal.py"


def load_module():
    spec = importlib.util.spec_from_file_location("stage_two_authorization_proposal", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


proposal = load_module()


class StageTwoAuthorizationProposalTests(unittest.TestCase):
    def test_exact_fresh_ordinal_and_key(self) -> None:
        self.assertEqual(proposal.AUTHORIZATION_ORDINAL, 3)
        self.assertEqual(proposal.EXECUTION_KEY, "cross-geometry-stage-two-v1:screening:3")

    def test_builds_exact_proposal_without_authorizing_execution(self) -> None:
        result = proposal.build_proposal(ROOT)
        self.assertEqual(result["status"], "PROPOSAL_ONLY_NOT_AUTHORIZATION")
        self.assertIs(result["executionAuthorizedByProposal"], False)
        self.assertEqual(result["caseCount"], 16)
        self.assertEqual(result["configuredMcPhotonsSum"], 320_000_000)
        self.assertEqual(result["sourceScientificRunId"], 30856116586)
        self.assertEqual(result["sourcePostprocessRunId"], 30858046820)
        auth = result["proposedAuthorization"]
        self.assertIs(auth["authorized"], True)
        self.assertIs(auth["scientificExecution"], True)
        self.assertEqual(auth["authorizationOrdinal"], 3)
        self.assertEqual(auth["executionKey"], "cross-geometry-stage-two-v1:screening:3")
        self.assertEqual(auth["exactAuthorizationParentCommit"], result["sourceCommit"])
        self.assertIsNone(auth["exactAuthorizationCommit"])
        active = json.loads((ROOT / proposal.PATHS["authorization"]).read_text())
        template = json.loads((ROOT / proposal.PATHS["authorizationTemplate"]).read_text())
        self.assertEqual(active, template)
        self.assertIs(active["authorized"], False)


if __name__ == "__main__":
    unittest.main()
