from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "arm_e0_successor_case_binding_audit_v1" / "preflight_query_authorization_v1.py"
SPEC = importlib.util.spec_from_file_location("arm_query_only_successor_preflight_v1", MODULE_PATH)
assert SPEC and SPEC.loader
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)

BASELINE = M.S.BASELINE_COORDINATOR_COMMENT
PREP = BASELINE + 100
AUTH = BASELINE + 200
MAIN_SHA = "a35365a433d08b5d65ed2134187c814f476e5aad"
AUTH_TITLE = "COORDINATOR::ARM_QUERY_ONLY_SUCCESSOR_AUTHORIZED__ONE_SHOT_ATTEMPT1"


def baseline_body() -> str:
    return "\n".join([
        "COORDINATOR::ARM_FENCE_CLEAR_BASELINE",
        "ARM may resume only its already-authorized post-V5R1 fence-clear safe/query-only fresh-successor preparation",
        "PR1001 remains governance-NONADMISSIBLE and must not merge",
        "authenticated invocation remains separately unauthorized",
        "GLOBAL WRITE_QUIET remains binding",
    ])


def auth_body(*, title: str = AUTH_TITLE, main_sha: str = MAIN_SHA, include_path: bool = True,
              include_event: bool = True, include_attempt: bool = True, include_one_shot: bool = True,
              include_main_binding: bool = True) -> str:
    lines = [title, "Exact replacement query-only governance binding:"]
    if include_path:
        lines.append(f"workflow: `{M.WORKFLOW_PATH}`")
    if include_event:
        lines.append("event: `workflow_dispatch`")
    if include_main_binding:
        lines.append(f"exact main={main_sha}")
    else:
        lines.append(f"candidate sha: {main_sha}")
        lines.append("query authority remains granted")
    if include_one_shot:
        lines.append("one-shot only")
    if include_attempt:
        lines.append("attempt 1 only")
    lines.append("No native download, no protected SWS/SASZE opening, no E0/Stage-B/MYSTIC/production authority is granted here.")
    return "\n".join(lines)


def comments(*, title: str = AUTH_TITLE, body_main_sha: str = MAIN_SHA, later_arm: bool = False,
             include_path: bool = True, include_event: bool = True,
             include_attempt: bool = True, include_one_shot: bool = True,
             include_main_binding: bool = True) -> list[dict]:
    rows = [
        {"id": BASELINE, "body": baseline_body()},
        {"id": PREP, "body": "ARM_OWNER::QUERY_ONLY_SUCCESSOR_READY_FOR_REVIEW\nresult-blind prep"},
        {"id": AUTH, "body": auth_body(
            title=title,
            main_sha=body_main_sha,
            include_path=include_path,
            include_event=include_event,
            include_attempt=include_attempt,
            include_one_shot=include_one_shot,
            include_main_binding=include_main_binding,
        )},
    ]
    if later_arm:
        rows.append({"id": AUTH + 1, "body": "ARM_OWNER::LATER_READY_FOR_REVIEW\npost-authorization ARM control"})
    return rows


def invoke(rows: list[dict], *, authorization_comment: int = AUTH,
           authorization_title: str = AUTH_TITLE, exact_main_sha: str = MAIN_SHA,
           expected_current_main_sha: str = MAIN_SHA,
           expected_count: int | None = None, expected_latest: int | None = None):
    return M.preflight(
        rows,
        authorization_comment=authorization_comment,
        authorization_title=authorization_title,
        exact_main_sha=exact_main_sha,
        expected_current_main_sha=expected_current_main_sha,
        expected_issue60_comment_count=len(rows) if expected_count is None else expected_count,
        expected_issue60_latest_comment_id=rows[-1]["id"] if expected_latest is None else expected_latest,
    )


class QueryOnlySuccessorPredispatchPreflightTests(unittest.TestCase):
    def test_passes_exact_bound_authorization(self):
        rows = comments()
        out = invoke(rows)
        self.assertEqual(out["status"], M.STATUS)
        self.assertEqual(out["stress_classifier_disposition"], "allowed")
        self.assertEqual(out["exact_main_sha"], MAIN_SHA)
        self.assertEqual(out["fresh_current_main_sha"], MAIN_SHA)
        self.assertTrue(out["planned_main_matches_fresh_current_main"])
        self.assertEqual(out["workflow_path"], M.WORKFLOW_PATH)
        self.assertEqual(out["event_name"], "workflow_dispatch")
        self.assertEqual(out["run_attempt"], 1)
        self.assertTrue(out["one_shot"])
        self.assertEqual(out["issue60_comment_count"], len(rows))
        self.assertEqual(out["issue60_latest_comment_id"], rows[-1]["id"])
        self.assertFalse(out["arm_network_access_performed"])
        self.assertFalse(out["native_file_download_performed"])
        self.assertFalse(out["protected_sws_sasze_values_read"])
        self.assertFalse(out["e0_execution_authorized_by_this_receipt"])

    def test_refuses_stale_planned_main_against_fresh_current_main(self):
        rows = comments()
        with self.assertRaises(M.PreflightRefusal):
            invoke(rows, expected_current_main_sha="b" * 40)

    def test_refuses_truncated_snapshot_against_fresh_full_metadata(self):
        full = comments(later_arm=True)
        truncated = full[:-1]
        with self.assertRaises(M.PreflightRefusal):
            invoke(truncated, expected_count=len(full), expected_latest=full[-1]["id"])

    def test_refuses_comment_count_metadata_drift(self):
        rows = comments()
        with self.assertRaises(M.PreflightRefusal):
            invoke(rows, expected_count=len(rows) + 1)

    def test_refuses_latest_comment_metadata_drift(self):
        rows = comments()
        with self.assertRaises(M.PreflightRefusal):
            invoke(rows, expected_latest=rows[-1]["id"] + 1)

    def test_refuses_wrong_exact_main_binding(self):
        rows = comments()
        with self.assertRaises(M.PreflightRefusal):
            invoke(rows, exact_main_sha="b" * 40)

    def test_refuses_sha_plus_remains_without_dedicated_main_binding(self):
        rows = comments(include_main_binding=False)
        with self.assertRaises(M.PreflightRefusal):
            invoke(rows)

    def test_refuses_missing_workflow_path(self):
        rows = comments(include_path=False)
        with self.assertRaises(M.PreflightRefusal):
            invoke(rows)

    def test_refuses_missing_workflow_dispatch(self):
        rows = comments(include_event=False)
        with self.assertRaises(M.PreflightRefusal):
            invoke(rows)

    def test_refuses_missing_attempt1_or_one_shot(self):
        rows = comments(include_attempt=False)
        with self.assertRaises(M.PreflightRefusal):
            invoke(rows)
        rows = comments(include_one_shot=False)
        with self.assertRaises(M.PreflightRefusal):
            invoke(rows)

    def test_refuses_title_mismatch(self):
        rows = comments()
        with self.assertRaises(M.PreflightRefusal):
            invoke(rows, authorization_title=AUTH_TITLE + "__DRIFT")

    def test_refuses_positive_looking_but_stress_ambiguous_title(self):
        title = "COORDINATOR::ARM_REPLACEMENT_QUERY_ONLY_ONE_SHOT_ATTEMPT1_AUTHORIZED"
        rows = comments(title=title)
        with self.assertRaises(M.PreflightRefusal):
            invoke(rows, authorization_title=title)

    def test_refuses_nonlatest_arm_authorization(self):
        rows = comments(later_arm=True)
        with self.assertRaises(M.PreflightRefusal):
            invoke(rows)

    def test_refuses_unmatched_write_quiet(self):
        rows = comments()
        rows.append({"id": AUTH + 1, "body": "WRITE_QUIET_BEGIN stage=synthetic"})
        with self.assertRaises(M.PreflightRefusal):
            invoke(rows)

    def test_refuses_malformed_main_sha(self):
        rows = comments()
        with self.assertRaises(M.PreflightRefusal):
            invoke(rows, exact_main_sha="not-a-sha")
        with self.assertRaises(M.PreflightRefusal):
            invoke(rows, expected_current_main_sha="not-a-sha")

    def test_refuses_invalid_expected_issue_metadata(self):
        rows = comments()
        with self.assertRaises(M.PreflightRefusal):
            invoke(rows, expected_count=0)
        with self.assertRaises(M.PreflightRefusal):
            invoke(rows, expected_latest=0)


if __name__ == "__main__":
    unittest.main()
