from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "experiments/aerosol-vertical-profile-sensitivity-v1"
GLOBAL_ORDINAL = STAGE / "global_ordinal.py"
SURFACE = STAGE / "preauthorization_surface.py"
AUTH_WORKFLOW = ROOT / ".github/workflows/aerosol-vertical-profile-authorization-review.yml"

HEAD = "67844e1dd2523963f2682f186387280dfb930760"
AUTH = "authorization/aerosol-vertical-profile-sensitivity-v1-ordinal-40"
HISTORY = "history/aerosol-vertical-profile-sensitivity-v1-ordinal-40-auth-review-failed-1"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def payload() -> dict:
    return {
        "branches": [
            {"name": AUTH, "commit": {"sha": HEAD}},
            {"name": HISTORY, "commit": {"sha": HEAD}},
        ],
        "runs": [
            {
                "id": 33109014744,
                "head_branch": AUTH,
                "head_sha": HEAD,
                "path": ".github/workflows/aerosol-vertical-profile-authorization-review.yml",
                "event": "pull_request",
                "run_attempt": 1,
                "status": "completed",
                "conclusion": "failure",
                "name": "Aerosol vertical-profile v1 authorization review",
            }
        ],
        "artifacts": [],
        "pulls": [
            {
                "number": 561,
                "state": "closed",
                "merged_at": None,
                "head": {"ref": AUTH, "sha": HEAD},
                "title": "Review AVPS v1 ordinal 40 authorization candidate",
                "body": "failed closed before allocation; no dispatch or result opening",
            }
        ],
        "issues": [],
        "issueComments": [],
        "pullReviewComments": [],
        "commitComments": [],
        "issue60Comments": [
            {"id": 1, "body": "ORDINAL39_ASIV_V1_DISPATCH_CONSUMED"}
        ],
    }


class AerosolVerticalProfileFailedAuthorizationRecoveryV1Tests(unittest.TestCase):
    def test_failed_review_history_reuses_exact_unconsumed_ordinal_40(self) -> None:
        ordinal = load("avps_failed_recovery_ordinal", GLOBAL_ORDINAL)
        p = payload()
        history = ordinal.failed_authorization_history(p, 40)
        self.assertEqual(history["heads"], [HEAD])
        self.assertEqual(history["prNumbers"], [561])
        self.assertEqual(history["reviewRunIds"], [33109014744])
        candidate, observations = ordinal.derive_next_global_ordinal(p, 39)
        self.assertEqual(candidate, 40)
        self.assertGreaterEqual(max(int(row["ordinal"]) for row in observations), 40)

    def test_preauthorization_surface_marks_preserved_failed_head_reusable(self) -> None:
        surface = load("avps_failed_recovery_surface", SURFACE)
        out = surface.build_surface(
            payload(),
            40,
            candidate_seed_authorization_recheck_passed=True,
        )
        self.assertTrue(out["authorizationBranchExists"])
        self.assertTrue(out["authorizationBranchReusableAfterFailedReview"])
        self.assertEqual(out["positiveCandidateClaimsExcludingCurrent"], 0)
        self.assertEqual(out["candidateExecutionKeyPriorUseCount"], 0)
        self.assertEqual(out["currentConsumedMarkerCount"], 0)
        self.assertEqual(out["matchingAuthorizationMarkers"], 0)

    def test_reuse_refuses_any_allocation_dispatch_or_science_evidence(self) -> None:
        ordinal = load("avps_failed_recovery_negative", GLOBAL_ORDINAL)

        marked = payload()
        marked["issue60Comments"].append({
            "id": 2,
            "body": (
                "ORDINAL40_AVPS_V1_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED "
                f"commit={HEAD} parent={'1' * 40} pr=561"
            ),
        })
        with self.assertRaises(ordinal.GlobalOrdinalRefusal):
            ordinal.failed_authorization_history(marked, 40)

        dispatched = payload()
        dispatched["branches"].append({
            "name": "dispatch/aerosol-vertical-profile-sensitivity-v1-ordinal-40",
            "commit": {"sha": HEAD},
        })
        with self.assertRaises(ordinal.GlobalOrdinalRefusal):
            ordinal.failed_authorization_history(dispatched, 40)

        executed = payload()
        executed["runs"].append({
            "id": 999,
            "head_branch": "dispatch/aerosol-vertical-profile-sensitivity-v1-ordinal-40",
            "head_sha": HEAD,
            "path": ".github/workflows/avps-v1-science.yml",
            "event": "workflow_dispatch",
            "run_attempt": 1,
            "status": "completed",
            "conclusion": "failure",
        })
        with self.assertRaises(ordinal.GlobalOrdinalRefusal):
            ordinal.failed_authorization_history(executed, 40)

    def test_reuse_refuses_nonterminal_or_rerun_review_history(self) -> None:
        ordinal = load("avps_failed_recovery_attempt", GLOBAL_ORDINAL)
        p = payload()
        p["runs"][0]["run_attempt"] = 2
        with self.assertRaises(ordinal.GlobalOrdinalRefusal):
            ordinal.failed_authorization_history(p, 40)

    def test_authorization_review_waits_for_sibling_actions_stability_without_weakening_audit(self) -> None:
        text = AUTH_WORKFLOW.read_text()
        self.assertIn("Stabilize authorization-head Actions metadata before global scan", text)
        self.assertIn("actions/runs?head_sha={head}&per_page=100", text)
        self.assertIn("stable_polls >= 6", text)
        self.assertIn("quietWindowSeconds':30", text)
        self.assertIn("repository_global_seed_scan.py", text)
        self.assertIn("--audit-mode authorization-recheck", text)
        self.assertIn("--current-run-id \"$GITHUB_RUN_ID\"", text)
        self.assertNotIn("setup-micromamba", text)
        self.assertNotIn("rubin-libradtran", text)
        self.assertNotIn("uvspec -", text)


if __name__ == "__main__":
    unittest.main()
