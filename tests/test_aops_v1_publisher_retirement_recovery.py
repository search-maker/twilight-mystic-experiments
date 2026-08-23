from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GO_PATH = ROOT / "experiments/aerosol-optical-property-sensitivity-v1/execution-candidate/global_ordinal.py"
spec = importlib.util.spec_from_file_location("aops_publisher_retirement_global_ordinal", GO_PATH)
assert spec is not None and spec.loader is not None
go = importlib.util.module_from_spec(spec)
spec.loader.exec_module(go)

FAILED = "aec35f62bf4971d871b5ae2a50bff6cdfb107ac4"
HEAD36 = "e1b7fa0860bd9e252f47dd8ddfa9b35e930d7654"
HEAD37 = "1111111111111111111111111111111111111111"
PARENT = "f7d3efc39486d205286afcb31b920ff78dd46698"
PUB36 = "6d0644708dd773ad8b65e8fe80fb2dc61c043cb7"
PUB37 = "2222222222222222222222222222222222222222"
AUTH36 = "authorization/aerosol-optical-property-sensitivity-v1-ordinal-36"
HIST36 = "history/aerosol-optical-property-sensitivity-v1-ordinal-36-auth-review-failed-1"
PUBLISH36 = "status/aops-v1-dispatch-publisher-ordinal-36"


def allocation(ordinal: int, head: str, parent: str, pr: int) -> str:
    return f"ORDINAL{ordinal}_AOPS_V1_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED commit={head} parent={parent} pr={pr}"


def retired(ordinal: int) -> str:
    return f"ORDINAL{ordinal}_AOPS_V1_AUTHORIZATION_RETIRED_UNDISPATCHED"


def payload36(*, with_retirement: bool = True):
    comments = [
        {"id": 1, "body": "ORDINAL35_AEROSOL_FAMILY_V2_R8_TIMEOUT_RECOVERY_V1_DISPATCH_CONSUMED"},
        {"id": 2, "body": allocation(36, HEAD36, PARENT, 304)},
    ]
    if with_retirement:
        comments.append({"id": 3, "body": retired(36)})
    return {
        "branches": [
            {"name": AUTH36, "commit": {"sha": HEAD36}},
            {"name": HIST36, "commit": {"sha": FAILED}},
            {"name": PUBLISH36, "commit": {"sha": PUB36}},
        ],
        "runs": [
            {"id": 32612380809, "head_branch": AUTH36, "head_sha": FAILED, "path": go.AUTH_REVIEW_WORKFLOW, "event": "pull_request", "run_attempt": 1, "status": "completed", "conclusion": "failure"},
            {"id": 32620394579, "head_branch": AUTH36, "head_sha": HEAD36, "path": go.AUTH_REVIEW_WORKFLOW, "event": "pull_request", "run_attempt": 1, "status": "completed", "conclusion": "success"},
            {"id": 32620794412, "head_branch": PUBLISH36, "head_sha": PUB36, "path": go.PUBLISHER_WORKFLOW, "event": "push", "run_attempt": 1, "status": "completed", "conclusion": "failure"},
        ],
        "artifacts": [],
        "pulls": [
            {"number": 299, "state": "closed", "merged_at": None, "head": {"ref": AUTH36, "sha": FAILED}, "base": {"sha": "7297a579112b6089acc5b5d45292e8169039c022"}, "title": "failed review", "body": ""},
            {"number": 304, "state": "closed", "merged_at": None, "head": {"ref": AUTH36, "sha": HEAD36}, "base": {"sha": PARENT}, "title": "reviewed allocation", "body": ""},
        ],
        "issues": [],
        "issueComments": [],
        "pullReviewComments": [],
        "commitComments": [],
        "issue60Comments": comments,
    }


def append_retired37(p):
    auth = "authorization/aerosol-optical-property-sensitivity-v1-ordinal-37"
    pub = "status/aops-v1-dispatch-publisher-ordinal-37"
    p["branches"].extend([
        {"name": auth, "commit": {"sha": HEAD37}},
        {"name": pub, "commit": {"sha": PUB37}},
    ])
    p["runs"].extend([
        {"id": 3701, "head_branch": auth, "head_sha": HEAD37, "path": go.AUTH_REVIEW_WORKFLOW, "event": "pull_request", "run_attempt": 1, "status": "completed", "conclusion": "success"},
        {"id": 3702, "head_branch": pub, "head_sha": PUB37, "path": go.PUBLISHER_WORKFLOW, "event": "push", "run_attempt": 1, "status": "completed", "conclusion": "failure"},
    ])
    p["pulls"].append({"number": 305, "state": "closed", "merged_at": None, "head": {"ref": auth, "sha": HEAD37}, "base": {"sha": PARENT}, "title": "reviewed allocation 37", "body": ""})
    p["issue60Comments"].extend([
        {"id": 4, "body": allocation(37, HEAD37, PARENT, 305)},
        {"id": 5, "body": retired(37)},
    ])
    return p


class PublisherRetirementRecovery(unittest.TestCase):
    def test_new_head_allocation_marker_does_not_poison_failed_head_history(self):
        p = payload36(with_retirement=False)
        history = go.failed_authorization_history(p, 36)
        self.assertEqual(history["heads"], [FAILED])
        self.assertEqual(history["prNumbers"], [299])

    def test_failed_head_exact_allocation_marker_is_still_refused(self):
        p = payload36(with_retirement=False)
        p["issue60Comments"][1]["body"] = allocation(36, FAILED, "7297a579112b6089acc5b5d45292e8169039c022", 299)
        with self.assertRaises(go.GlobalOrdinalRefusal):
            go.failed_authorization_history(p, 36)

    def test_exact_retired_undispatched_allocation_advances_to_37(self):
        p = payload36()
        go._retired_undispatched_proof(p, 36)
        candidate, observations = go.derive_next_global_ordinal(p, 35)
        self.assertEqual(candidate, 37)
        self.assertEqual(max(int(row["ordinal"]) for row in observations), 36)

    def test_retirement_marker_is_required_before_advancement(self):
        with self.assertRaises(go.GlobalOrdinalRefusal):
            go.derive_next_global_ordinal(payload36(with_retirement=False), 35)

    def test_retirement_fails_closed_on_dispatch_consumption_or_bad_publisher_history(self):
        cases = []
        p = payload36(); p["branches"].append({"name": "dispatch/aerosol-optical-property-sensitivity-v1-ordinal-36", "commit": {"sha": HEAD36}}); cases.append(p)
        p = payload36(); p["issue60Comments"].append({"id": 9, "body": "ORDINAL36_AOPS_V1_DISPATCH_CONSUMED"}); cases.append(p)
        p = payload36(); p["pulls"][1]["state"] = "open"; cases.append(p)
        p = payload36(); p["runs"][2]["run_attempt"] = 2; cases.append(p)
        p = payload36(); p["runs"][2]["conclusion"] = "success"; cases.append(p)
        p = payload36(); p["runs"].append({"id": 99, "head_branch": "dispatch/aerosol-optical-property-sensitivity-v1-ordinal-36", "head_sha": HEAD36, "path": go.EXECUTION_WORKFLOW, "event": "workflow_dispatch", "run_attempt": 1, "status": "completed", "conclusion": "failure"}); cases.append(p)
        for p in cases:
            with self.subTest(case=cases.index(p)):
                with self.assertRaises(go.GlobalOrdinalRefusal):
                    go._retired_undispatched_proof(p, 36)

    def test_consecutive_aops_retirements_are_monotonic(self):
        p = append_retired37(payload36())
        candidate, observations = go.derive_next_global_ordinal(p, 35)
        self.assertEqual(candidate, 38)
        self.assertEqual(max(int(row["ordinal"]) for row in observations), 37)


if __name__ == "__main__":
    unittest.main()
