from __future__ import annotations

import importlib.util
import os
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "arm_e0_successor_case_binding_audit_v1" / "preflight_query_authorization_live_v2.py"
SPEC = importlib.util.spec_from_file_location("arm_query_only_successor_live_preflight_v2", MODULE_PATH)
assert SPEC and SPEC.loader
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)

BASELINE = M.V1.S.BASELINE_COORDINATOR_COMMENT
PREP = BASELINE + 100
AUTH = BASELINE + 200
MAIN_SHA = "a35365a433d08b5d65ed2134187c814f476e5aad"
AUTH_TITLE = "COORDINATOR::ARM_QUERY_ONLY_SUCCESSOR_AUTHORIZED__ONE_SHOT_ATTEMPT1"
UPDATED_AT = "2026-09-09T14:38:35Z"


def baseline_body() -> str:
    return "\n".join([
        "COORDINATOR::ARM_FENCE_CLEAR_BASELINE",
        "ARM may resume only its already-authorized post-V5R1 fence-clear safe/query-only fresh-successor preparation",
        "PR1001 remains governance-NONADMISSIBLE and must not merge",
        "authenticated invocation remains separately unauthorized",
        "GLOBAL WRITE_QUIET remains binding",
    ])


def auth_body(*, main_sha: str = MAIN_SHA) -> str:
    return "\n".join([
        AUTH_TITLE,
        "Exact replacement query-only governance binding:",
        f"workflow: `{M.V1.WORKFLOW_PATH}`",
        "event: `workflow_dispatch`",
        f"exact main={main_sha}",
        "one-shot only",
        "attempt 1 only",
        "No native download, no protected SWS/SASZE opening, no E0/Stage-B/MYSTIC/production authority is granted here.",
    ])


def comments(*, main_sha: str = MAIN_SHA) -> list[dict]:
    return [
        {"id": BASELINE, "body": baseline_body()},
        {"id": PREP, "body": "ARM_OWNER::QUERY_ONLY_SUCCESSOR_READY_FOR_REVIEW\nresult-blind prep"},
        {"id": AUTH, "body": auth_body(main_sha=main_sha)},
    ]


def fake_control_plane(rows: list[dict], *, main_before: str = MAIN_SHA, main_after: str = MAIN_SHA,
                       issue_count_before: int | None = None, issue_count_after: int | None = None,
                       issue_updated_before: str = UPDATED_AT, issue_updated_after: str = UPDATED_AT,
                       default_branch_before: str = "main", default_branch_after: str = "main"):
    counts = {
        "repo": 0,
        "main": 0,
        "issue": 0,
    }
    before_count = len(rows) if issue_count_before is None else issue_count_before
    after_count = len(rows) if issue_count_after is None else issue_count_after

    def fake_json(url: str, token: str):
        if token != "test-token":
            raise AssertionError("unexpected token")
        if url == M.REPO_URL:
            counts["repo"] += 1
            branch = default_branch_before if counts["repo"] == 1 else default_branch_after
            return {"default_branch": branch}
        if url == M.MAIN_REF_URL:
            counts["main"] += 1
            sha = main_before if counts["main"] == 1 else main_after
            return {"object": {"sha": sha}}
        if url == M.ISSUE_URL:
            counts["issue"] += 1
            if counts["issue"] == 1:
                return {"comments": before_count, "updated_at": issue_updated_before}
            return {"comments": after_count, "updated_at": issue_updated_after}
        raise AssertionError(f"unexpected URL: {url}")

    return fake_json


class QueryOnlySuccessorLivePredispatchTests(unittest.TestCase):
    def invoke(self, rows: list[dict], *, second_rows: list[dict] | None = None, **fake_kwargs):
        fake_json = fake_control_plane(rows, **fake_kwargs)
        snapshots = [rows, rows if second_rows is None else second_rows]
        with mock.patch.object(M, "_github_json", side_effect=fake_json), \
             mock.patch.object(M, "_complete_issue_comments", side_effect=snapshots), \
             mock.patch.dict(os.environ, {}, clear=True):
            return M.live_preflight(
                authorization_comment=AUTH,
                authorization_title=AUTH_TITLE,
                token="test-token",
            )

    def invoke_auto(self, rows: list[dict], *, second_rows: list[dict] | None = None, **fake_kwargs):
        fake_json = fake_control_plane(rows, **fake_kwargs)
        snapshots = [rows, rows if second_rows is None else second_rows]
        with mock.patch.object(M, "_github_json", side_effect=fake_json), \
             mock.patch.object(M, "_complete_issue_comments", side_effect=snapshots), \
             mock.patch.dict(os.environ, {}, clear=True):
            return M.live_preflight(token="test-token")

    def test_passes_stable_double_read_and_bound_v1(self):
        rows = comments()
        out = self.invoke(rows)
        self.assertEqual(out["schema"], 2)
        self.assertEqual(out["status"], M.STATUS)
        self.assertEqual(out["fresh_current_main_sha"], MAIN_SHA)
        self.assertEqual(out["issue60_updated_at"], UPDATED_AT)
        self.assertTrue(out["github_control_plane_read_performed"])
        self.assertTrue(out["live_main_double_read_stable"])
        self.assertTrue(out["live_issue_metadata_double_read_stable"])
        self.assertTrue(out["live_issue_ledger_double_read_stable"])
        self.assertEqual(out["live_issue_ledger_sha256"], out["issue60_ledger_sha256"])
        self.assertFalse(out["authorization_identity_derived_from_stable_live_ledger"])
        self.assertFalse(out["arm_network_access_performed"])
        self.assertFalse(out["arm_credentials_read"])
        self.assertFalse(out["e0_execution_authorized_by_this_receipt"])

    def test_auto_derives_latest_arm_authorization_from_same_stable_ledger(self):
        out = self.invoke_auto(comments())
        self.assertEqual(out["authorization_comment"], AUTH)
        self.assertEqual(out["authorization_title"], AUTH_TITLE)
        self.assertTrue(out["authorization_identity_derived_from_stable_live_ledger"])
        self.assertEqual(out["latest_arm_relevant_comment_id"], AUTH)

    def test_auto_refuses_later_generic_coordinator_arm_false_note(self):
        rows = comments()
        rows.append({
            "id": AUTH + 100,
            "body": "\n".join([
                "COORDINATOR::AVPS_PHASE_B_STILL_PENDING",
                "ARM: replacement authenticated-query authority remains FALSE until Phase-B is installed/postmerge-stable.",
            ]),
        })
        with self.assertRaises(M.LivePreflightRefusal):
            self.invoke_auto(rows)

    def test_auto_refuses_later_cross_lane_markdown_arm_false_note(self):
        rows = comments()
        later = AUTH + 101
        rows.append({
            "id": later,
            "body": "\n".join([
                "COORDINATOR::CLOSURE_SPRINT_OTHER_LANES__SCIENCE_FALSE",
                "",
                "## Cross-lane critical path / serialization",
                "Other exact-base work may proceed in its frozen order.",
                "ARM PR1016/main movement remains deferred through that boundary; Authenticated ARM query authority stays FALSE.",
            ]),
        })
        with self.assertRaises(M.LivePreflightRefusal):
            self.invoke_auto(rows)

    def test_markdown_arm_headings_are_freshness_relevant(self):
        bodies = (
            "COORDINATOR::OTHER_LANE\n\n## ARM / ORDERING\nAuthenticated query authority remains FALSE.",
            "COORDINATOR::OTHER_LANE\n\n## C. ARM — exact-base ordering\nAuthenticated query authority remains FALSE.",
        )
        for offset, body in enumerate(bodies, start=1):
            with self.subTest(body=body):
                cid = BASELINE + 1000 + offset
                out = M.V1.S.audit_arm_governance([
                    {"id": BASELINE, "body": baseline_body()},
                    {"id": cid, "body": body},
                ])
                self.assertEqual(out["arm_relevant_comment_ids_after_baseline"], [cid])

    def test_unrelated_non_arm_coordinator_failure_is_not_freshness_relevant(self):
        cid = BASELINE + 2000
        out = M.V1.S.audit_arm_governance([
            {"id": BASELINE, "body": baseline_body()},
            {
                "id": cid,
                "body": "COORDINATOR::TOTAL_SKY_REJECTED\n\n## Total-Sky\nREJECTED / FAIL_CLOSED / DO NOT MERGE.",
            },
        ])
        self.assertEqual(out["arm_relevant_comment_ids_after_baseline"], [])

    def test_refuses_half_explicit_authorization_identity(self):
        rows = comments()
        fake_json = fake_control_plane(rows)
        with mock.patch.object(M, "_github_json", side_effect=fake_json), \
             mock.patch.object(M, "_complete_issue_comments", side_effect=[rows, rows]), \
             mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(M.LivePreflightRefusal):
                M.live_preflight(authorization_comment=AUTH, token="test-token")

    def test_refuses_main_move_during_live_readback(self):
        with self.assertRaises(M.LivePreflightRefusal):
            self.invoke(comments(), main_after="b" * 40)

    def test_refuses_issue_update_during_live_readback(self):
        with self.assertRaises(M.LivePreflightRefusal):
            self.invoke(comments(), issue_updated_after="2026-09-09T14:39:00Z")

    def test_refuses_issue_count_change_during_live_readback(self):
        rows = comments()
        with self.assertRaises(M.LivePreflightRefusal):
            self.invoke(rows, issue_count_after=len(rows) + 1)

    def test_refuses_stable_metadata_that_disagrees_with_snapshot_count(self):
        rows = comments()
        with self.assertRaises(M.LivePreflightRefusal):
            self.invoke(rows, issue_count_before=len(rows) + 1, issue_count_after=len(rows) + 1)

    def test_refuses_comment_body_edit_between_complete_snapshots_even_if_metadata_stable(self):
        first = comments()
        second = [dict(row) for row in first]
        second[1]["body"] = "ARM_OWNER::QUERY_ONLY_SUCCESSOR_READY_FOR_REVIEW\nedited control body"
        with self.assertRaises(M.LivePreflightRefusal):
            self.invoke(first, second_rows=second)

    def test_refuses_comment_identity_change_between_complete_snapshots_even_if_count_stable(self):
        first = comments()
        second = [dict(row) for row in first]
        second[-1]["id"] = AUTH + 1
        with self.assertRaises(M.LivePreflightRefusal):
            self.invoke(first, second_rows=second)

    def test_refuses_default_branch_drift(self):
        with self.assertRaises(M.LivePreflightRefusal):
            self.invoke(comments(), default_branch_after="other")

    def test_refuses_authorization_body_bound_to_old_main(self):
        rows = comments(main_sha="b" * 40)
        with self.assertRaises(M.LivePreflightRefusal):
            self.invoke(rows)

    def test_refuses_arm_credentials_in_environment(self):
        rows = comments()
        fake_json = fake_control_plane(rows)
        with mock.patch.object(M, "_github_json", side_effect=fake_json), \
             mock.patch.object(M, "_complete_issue_comments", side_effect=[rows, rows]), \
             mock.patch.dict(os.environ, {"ARM_USER_ID": "present"}, clear=True):
            with self.assertRaises(M.LivePreflightRefusal):
                M.live_preflight(
                    authorization_comment=AUTH,
                    authorization_title=AUTH_TITLE,
                    token="test-token",
                )

    def test_refuses_missing_github_token(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(M.LivePreflightRefusal):
                M.live_preflight(
                    authorization_comment=AUTH,
                    authorization_title=AUTH_TITLE,
                    token="",
                )


if __name__ == "__main__":
    unittest.main()
