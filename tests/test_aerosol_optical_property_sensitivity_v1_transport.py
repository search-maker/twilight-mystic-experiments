from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "experiments/aerosol-optical-property-sensitivity-v1"
EXEC = STAGE / "execution-candidate"
CONTRACT = STAGE / "transport-contract.v1.json"
WORKFLOWS = ROOT / ".github/workflows"


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class AopsTransportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(CONTRACT.read_text())

    def test_transport_contract_stays_pre_authorization(self) -> None:
        c = self.contract
        self.assertEqual(c["status"], "FROZEN_TRANSPORT_REVIEW_NOT_AUTHORIZATION")
        self.assertEqual(c["reviewPackageMainSha"], "ccb6ade025f0c6291f0851c3c9b869bd0114cf2a")
        for key in (
            "scientificOrdinalAllocated", "authorizationCreated", "dispatchCreated",
            "scientificExecutionAuthorized", "solverExecutionAuthorized", "resultOpeningAuthorized",
        ):
            self.assertFalse(c[key], key)
        self.assertEqual(c["science"]["caseCount"], 360)
        self.assertEqual(c["science"]["comparisonGroupCount"], 72)
        self.assertEqual(c["science"]["analysisCellCount"], 24)
        self.assertEqual(c["science"]["maximumConcurrentCaseWorkers"], 8)
        self.assertEqual([x["caseCount"] for x in c["science"]["caseShards"]], [90,90,90,90])
        self.assertEqual([x["maxParallel"] for x in c["science"]["caseShards"]], [2,2,2,2])
        self.assertEqual(c["science"]["solverTimeoutSeconds"], 7200)
        self.assertEqual(c["science"]["githubJobCeilingMinutes"], 150)
        self.assertTrue(c["science"]["exact360ArtifactUniverseBeforeOpeningRequired"])
        self.assertTrue(c["science"]["levelBOnlyAfterExact360AggregateSuccess"])

    def test_every_transport_binding_matches_exact_bytes(self) -> None:
        bindings = self.contract["gitBlobBindings"]
        self.assertGreaterEqual(len(bindings), 16)
        for rel, expected in sorted(bindings.items()):
            path = ROOT / rel
            self.assertTrue(path.is_file(), rel)
            self.assertEqual(git_blob_sha1(path), expected, rel)

    def test_transport_authorization_wrapper_enforces_contract_bytes(self) -> None:
        mod = load("aops_transport_auth_test", EXEC / "authorization_transport_guard.py")
        auth = {
            "transportContractRawSha256": raw_sha256(CONTRACT),
            "reviewPackageMainSha": self.contract["reviewPackageMainSha"],
        }
        out = mod.validate_transport_contract(ROOT, auth)
        self.assertEqual(out["stageId"], "aerosol-optical-property-sensitivity-v1-transport-contract")

    def test_preauthorization_and_authorization_review_are_zero_runtime(self) -> None:
        pre = (WORKFLOWS / "aops-v1-preauthorization-audit.yml").read_text()
        review = (WORKFLOWS / "aops-v1-authorization-review.yml").read_text()
        self.assertIn("audit-mode authorization-recheck", pre)
        self.assertIn("derive_next_global_ordinal", pre)
        self.assertIn("identityAllocationPermitted", json.dumps(self.contract))
        self.assertNotIn("setup-micromamba", pre)
        self.assertNotIn("--allow-execution", pre)
        self.assertNotIn("setup-micromamba", review)
        self.assertNotIn("--allow-execution", review)
        self.assertIn("types: [opened]", review)
        self.assertIn("authorization.json", review)
        self.assertIn("live-seed-authorization-proof.json", review)

    def test_publisher_uploads_success_evidence_before_explicit_dispatch(self) -> None:
        text = (WORKFLOWS / "aops-v1-dispatch-publisher.yml").read_text()
        self.assertIn("git push origin", text)
        self.assertIn("ORDINAL${ORDINAL}_AOPS_V1_DISPATCH_CONSUMED", text)
        upload = text.index("Persist immutable publisher evidence before science trigger")
        dispatch = text.index("Explicitly dispatch attempt-1 science on pushed ref")
        self.assertLess(upload, dispatch)
        self.assertIn("aops-v1-execution.yml/dispatches", text)
        self.assertIn("EXPLICIT_WORKFLOW_DISPATCH_AFTER_ACTUAL_GIT_PUSH", text)

    def test_science_workflow_is_four_exact_shards_and_fail_closed_before_opening(self) -> None:
        text = (WORKFLOWS / "aops-v1-execution.yml").read_text()
        self.assertIn("workflow_dispatch:", text)
        self.assertIn("test \"$GITHUB_RUN_ATTEMPT\" = 1", text)
        for dep in (2,4,6,8):
            self.assertIn(f"cases-dep{dep}:", text)
            self.assertIn(f"matrix{dep}", text)
        self.assertEqual(text.count("max-parallel: 2"), 4)
        self.assertEqual(text.count("timeout-minutes: 150"), 4)
        self.assertIn("expected exactly 360 current-run case artifacts", text)
        self.assertIn("COMPLETE_EXACT_360_CASE_ARTIFACT_UNIVERSE", text)
        self.assertIn("COMPLETED_PREREGISTERED_AOPS_V1_ANALYSIS", text)
        self.assertIn("COMPLETED_PREREGISTERED_AOPS_V1_LEVEL_B", text)
        self.assertLess(text.index("Run frozen exact-360 acquisition and scalar/spectral analysis"), text.index("Run frozen Level-B propagation only after exact-360 aggregate"))
        self.assertIn("max-parallel: 2", text)
        self.assertIn("solverTimeoutSeconds", (STAGE / "execution-contract.review.json").read_text())

    def test_science_guard_requires_separate_authorization_and_live_seed_proofs(self) -> None:
        guard = (EXEC / "guard.py").read_text()
        self.assertIn("authorization_seed_proof", guard)
        self.assertIn("live_seed_proof", guard)
        self.assertIn("transport_guard.validate_enabled_document", guard)
        self.assertIn("live science seed recheck must be bound to exact authorization head", guard)
        self.assertIn("priorRunsOnDispatch", guard)
        self.assertIn("AOPS_V1_DISPATCH_PUBLISHER_PASS_ACTUAL_GIT_PUSH", guard)


if __name__ == "__main__":
    unittest.main()
