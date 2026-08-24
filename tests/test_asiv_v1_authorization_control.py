from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "experiments/aerosol-scenario-interpolation-validation-v1"
EXECD = STAGE / "execution-candidate"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def proof(head: str = "a" * 40) -> dict:
    return {
        "schemaVersion": 1,
        "stageId": "aerosol-scenario-interpolation-validation-v1-preauthorization-freshness-proof",
        "status": "PASS_ASIV_SEED_AND_GEOMETRY_AUTHORIZATION_RECHECK_NOT_ALLOCATED",
        "auditedMainHead": head,
        "candidateSeedCount": 24,
        "candidateSeedCanonicalSha256": "cd04e0f7a206ca7fd49f3b00eae8de6d49ba8dc1427c21e5c7530adf03837040",
        "candidateRowsCanonicalSha256": "d88da58b6fe896b8324df224c5e849399b770783d4d63bb2bc4a7b01aa844e8b",
        "allCollisionCountersZero": True,
        "trackedTreeExternalCollisionCount": 0,
        "repositoryGlobalCollisionCount": 0,
        "repositoryGlobalDoubleEnumerationStable": True,
        "repositoryGlobalStableContextSha256": "1" * 64,
        "holdoutGeometryCount": 8,
        "trackedGeometryCollisionCount": 0,
        "metadataGeometryCollisionCount": 0,
        "geometryMetadataStableContextSha256": "2" * 64,
        "scientificOrdinalAllocated": False,
        "authorizationCreated": False,
        "dispatchCreated": False,
        "scientificExecutionAuthorized": False,
        "solverExecutionAuthorized": False,
        "resultOpeningAuthorized": False,
    }


class AsivV1AuthorizationControlTests(unittest.TestCase):
    def test_seeded_review_design_is_exact_24_group_120_case_crn_universe(self):
        design_mod = load("asiv_design_test", STAGE / "execution_design.py")
        transport = load("asiv_transport_test", STAGE / "execution_transport.py")
        d = design_mod.build_review_execution_design(proof(), "a" * 40)
        transport.validate_authorized_design(ROOT, d)
        self.assertEqual(d["status"], "CANDIDATE_SEEDED_DESIGN_FRESHNESS_PROVEN_REVIEW_ONLY")
        self.assertEqual((d["groupCount"], d["caseCount"], d["holdoutGeometryCount"]), (24, 120, 8))
        self.assertIs(d["candidateSeedsAllocated"], True)
        self.assertIs(d["candidateSeedFreshnessProven"], True)
        self.assertIs(d["scientificOrdinalAllocated"], False)
        self.assertIs(d["authorizationCreated"], False)
        self.assertIs(d["dispatchCreated"], False)
        seeds = {g["groupId"]: g["seed"] for g in d["groups"]}
        self.assertEqual(len(seeds), 24)
        self.assertEqual(len(set(seeds.values())), 24)
        for gid, seed in seeds.items():
            rows = [c for c in d["cases"] if c["groupId"] == gid]
            self.assertEqual(len(rows), 5)
            self.assertEqual({c["seed"] for c in rows}, {seed})
            self.assertTrue(all(c["renderable"] is False and c["executionAuthorized"] is False for c in rows))

    def test_geometry_recheck_is_mandatory_for_every_control_transition(self):
        freshness = load("asiv_freshness_test", EXECD / "freshness.py")
        with self.assertRaisesRegex(Exception, "geometry"):
            freshness._geometry({"candidateGeometryAuthorizationRecheckPassed": False})
        freshness._geometry({"candidateGeometryAuthorizationRecheckPassed": True})

    def test_authorization_builder_is_deterministic_closed_dispatch_document(self):
        builder = load("asiv_builder_test", EXECD / "build_authorization.py")
        guard = load("asiv_guard_test", EXECD / "authorization_guard.py")
        a = builder.build(ROOT, "a" * 40, 39, proof())
        b = builder.build(ROOT, "a" * 40, 39, proof())
        self.assertEqual(a, b)
        self.assertEqual(a["status"], "AUTHORIZED_PENDING_SEPARATE_DISPATCH")
        self.assertEqual(a["scientificOrdinal"], 39)
        self.assertEqual(a["authorizationBranch"], "authorization/aerosol-scenario-interpolation-validation-v1-ordinal-39")
        self.assertEqual(a["dispatchBranch"], "dispatch/aerosol-scenario-interpolation-validation-v1-ordinal-39")
        self.assertEqual((a["caseCount"], a["groupCount"], a["holdoutGeometryCount"]), (120, 24, 8))
        self.assertIs(a["scientificExecutionAuthorized"], True)
        self.assertIs(a["solverExecutionAuthorized"], True)
        for key in ("dispatchAuthorized", "resultOpeningAuthorized", "automaticDispatch", "consumed", "githubRerunAllowed", "retryAllowed", "resumeAllowed", "postHoldoutRetuningAllowed", "productionAuthorized"):
            self.assertIs(a[key], False, key)
        self.assertEqual(a["selectedModelCanonicalSha256"], "0b11a1691bfd2d9e3f073c786044bacedd3e9210bcb0660c76f21c34128a61af")
        guard.validate_enabled_document(ROOT, a, "a" * 40, proof())
        self.assertTrue({"authorizationReviewWorkflow", "dispatchPublisherWorkflow", "scientificExecutionWorkflow", "boundHumanThreshold", "runtimeOverlay"} <= set(a["byteBindings"]))

    def test_workflow_boundaries_are_separate_and_fail_closed(self):
        auth = (ROOT / ".github/workflows/asiv-v1-authorization-review.yml").read_text()
        publisher = (ROOT / ".github/workflows/asiv-v1-dispatch-publisher.yml").read_text()
        science = (ROOT / ".github/workflows/asiv-v1-execution.yml").read_text()
        self.assertIn("pull_request:", auth)
        self.assertNotIn("setup-micromamba", auth)
        self.assertNotIn("command -v uvspec", auth)
        self.assertIn("DISPATCH_PUBLISHED_ZERO_RUNTIME", publisher)
        self.assertNotIn("setup-micromamba", publisher)
        self.assertNotIn("command -v uvspec", publisher)
        self.assertIn("workflow_dispatch:", science)
        self.assertIn("max-parallel: 8", science)
        self.assertIn("asiv-v1-case-${{ matrix.caseId }}", science)
        self.assertIn("exact 120 unique current-run case artifacts", science)
        self.assertIn("bound-human-threshold.mjs", science)
        self.assertIn("production=false", science)
        self.assertIn("starsvisibility_mutation=false", science)
        self.assertNotIn(".github/dispatch-requests/asiv-v1.json", [p.relative_to(ROOT).as_posix() for p in ROOT.rglob("asiv-v1.json")])


if __name__ == "__main__":
    unittest.main()
