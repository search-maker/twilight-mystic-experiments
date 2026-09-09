from __future__ import annotations

import hashlib
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "arm_e0_successor_case_binding_audit_v1" / "build_rebind_plan_guarded_v2.py"
MANIFEST_PATH = ROOT / "tools" / "arm_ena_sws_query_only_availability_v1" / "ordered_25_cases.json"
SPEC = importlib.util.spec_from_file_location("arm_e0_successor_rebind_guarded_v2", MODULE_PATH)
assert SPEC and SPEC.loader
G = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(G)
P = G.P

DISPATCH_SHA = "a" * 40
DISPATCH_REF = "refs/heads/main"
BASELINE = 5000000000
PREP_COMMENT = 5000000001
AUTH_COMMENT = 6000000001
AUTH_TITLE = "COORDINATOR::ARM_QUERY_ONLY_SUCCESSOR_AUTHORIZED__ONE_SHOT_ATTEMPT1"


def ordered_cases() -> list[str]:
    _manifest, cases = P.load_manifest(MANIFEST_PATH)
    return cases


def make_query(*, ordinal: int = 3) -> dict:
    cases = ordered_cases()
    checked = []
    for i in range(1, ordinal + 1):
        case = cases[i - 1]
        checked.append({
            "ordinal": i,
            "case_id": case,
            "date": case[:10],
            "match_count": 1 if i == ordinal else 0,
        })
    selected = cases[ordinal - 1]
    ymd = selected[:10].replace("-", "")
    return {
        "schema": 1,
        "purpose": P.QUERY_PURPOSE,
        "status": "FIRST_NATIVE_FILENAME_RESOLVED",
        "datastream": P.DATASTREAM,
        "ordered_case_manifest_sha256": P.EXPECTED_MANIFEST_SHA256,
        "ordered_case_count": P.EXPECTED_CASE_COUNT,
        "checked_case_count": ordinal,
        "checked_cases": checked,
        "first_match": {
            "ordinal": ordinal,
            "case_id": selected,
            "date": selected[:10],
            "filenames": [f"enaswsC1.b1.{ymd}.000000.nc"],
        },
        "query_error": None,
        "credentials_persisted": False,
        "native_file_download_performed": False,
        "native_file_open_performed": False,
        "protected_sws_sasze_values_read": False,
        "stage_b_authorized": False,
        "mystic_science_authorized": False,
        "production_authorized": False,
    }


def auth_body(*, title: str = AUTH_TITLE, main_sha: str = DISPATCH_SHA,
              include_workflow: bool = True, include_event: bool = True,
              include_main: bool = True, include_attempt: bool = True,
              include_one_shot: bool = True) -> str:
    lines = [title, "Exact replacement query-only governance binding:"]
    if include_workflow:
        lines.append(f"workflow: `{G.WORKFLOW_PATH}`")
    if include_event:
        lines.append("event: `workflow_dispatch`")
    if include_main:
        lines.append(f"exact main={main_sha}")
    if include_one_shot:
        lines.append("one-shot only")
    if include_attempt:
        lines.append("attempt 1 only")
    return "\n".join(lines)


def make_comments(*, auth_title: str = AUTH_TITLE, extra_after: bool = False,
                  body_main_sha: str = DISPATCH_SHA, include_workflow: bool = True,
                  include_event: bool = True, include_main: bool = True,
                  include_attempt: bool = True, include_one_shot: bool = True) -> list[dict]:
    rows = [
        {"id": BASELINE, "body": "COORDINATOR::BASELINE\nsynthetic baseline"},
        {"id": PREP_COMMENT, "body": "ARM_OWNER::SAFE_PREP_READY_FOR_REVIEW\nsynthetic prep"},
        {"id": AUTH_COMMENT, "body": auth_body(
            title=auth_title,
            main_sha=body_main_sha,
            include_workflow=include_workflow,
            include_event=include_event,
            include_main=include_main,
            include_attempt=include_attempt,
            include_one_shot=include_one_shot,
        )},
    ]
    if extra_after:
        rows.append({"id": AUTH_COMMENT + 1, "body": "ARM_OWNER::LATER_READY_FOR_REVIEW\nsynthetic later ARM control"})
    return rows


def ledger_sha(comments: list[dict]) -> str:
    canonical = json.dumps(
        [{"id": int(r.get("id", 0)), "body": str(r.get("body", ""))} for r in comments],
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def make_stress(*, comments: list[dict] | None = None, arm_ids: list[int] | None = None) -> dict:
    comments = make_comments() if comments is None else comments
    arm_ids = [PREP_COMMENT, AUTH_COMMENT] if arm_ids is None else arm_ids
    return {
        "schema": 1,
        "status": "EXACT_EXECUTABLE_STRESS_PASS",
        "purpose": P.QUERY_PURPOSE,
        "workflow_sha256": "b" * 64,
        "executable_sha256": "c" * 64,
        "ordered_case_manifest_sha256": P.EXPECTED_MANIFEST_SHA256,
        "event_name": "workflow_dispatch",
        "github_ref": DISPATCH_REF,
        "github_sha": DISPATCH_SHA,
        "default_branch": "main",
        "issue60_comment_count": len(comments),
        "issue60_latest_comment_id": comments[-1]["id"],
        "issue60_ledger_sha256": ledger_sha(comments),
        "baseline_coordinator_comment": BASELINE,
        "arm_relevant_comment_ids_after_baseline": arm_ids,
        "write_quiet_begin_ids_after_baseline": [],
        "write_quiet_end_ids_after_baseline": [],
        "arm_network_access_performed": False,
        "arm_credentials_read": False,
        "native_file_download_performed": False,
        "native_file_open_performed": False,
        "protected_sws_sasze_values_read": False,
        "stage_b_authorized": False,
        "mystic_science_authorized": False,
        "production_authorized": False,
    }


def build(**overrides):
    comments = overrides.pop("issue60_comments_snapshot", make_comments())
    stress = overrides.pop("stress_receipt", make_stress(comments=comments))
    kwargs = {
        "issue60_comments_snapshot": comments,
        "query_receipt": make_query(),
        "query_receipt_sha256": "e" * 64,
        "stress_receipt": stress,
        "stress_receipt_sha256": "f" * 64,
        "ordered_cases": ordered_cases(),
        "query_authorization_comment": AUTH_COMMENT,
        "query_authorization_title": AUTH_TITLE,
        "query_dispatch_ref": DISPATCH_REF,
        "query_dispatch_sha": DISPATCH_SHA,
        "query_workflow_run_id": 7000000001,
        "query_run_attempt": 1,
        "query_artifact_id": 8000000001,
        "query_artifact_digest": "sha256:" + "1" * 64,
        "stress_artifact_id": 8000000002,
        "stress_artifact_digest": "sha256:" + "2" * 64,
    }
    kwargs.update(overrides)
    return G.build_guarded_plan(**kwargs)


class GuardedRebindPlanV2Tests(unittest.TestCase):
    def test_builds_guarded_result_blind_plan(self):
        out = build()
        self.assertEqual(out["schema"], 2)
        self.assertEqual(out["status"], G.STATUS)
        self.assertTrue(out["query_authorization_bound_to_stress_ledger"])
        self.assertTrue(out["query_authorization_title_exactly_bound"])
        self.assertTrue(out["query_authorization_current_stress_classifier_compatible"])
        self.assertTrue(out["query_authorization_is_latest_arm_governance"])
        self.assertTrue(out["query_authorization_body_bound_to_dispatch_identity"])
        proof = out["query_authority_binding"]
        self.assertEqual(proof["query_authorization_comment"], AUTH_COMMENT)
        self.assertEqual(proof["query_authorization_title"], AUTH_TITLE)
        self.assertTrue(proof["query_authorization_current_stress_classifier_compatible"])
        self.assertTrue(proof["query_authorization_body_bound_to_dispatch_identity"])
        self.assertEqual(proof["query_authorization_bound_main_sha"], DISPATCH_SHA)
        self.assertEqual(proof["query_authorization_bound_workflow_path"], G.WORKFLOW_PATH)
        self.assertFalse(proof["legacy_authority_reused"])
        self.assertFalse(out["plan_is_authorization"])
        self.assertFalse(out["protected_sws_sasze_values_read"])
        self.assertFalse(out["stage_b_authorized"])
        self.assertFalse(out["mystic_science_authorized"])
        self.assertFalse(out["production_authorized"])

    def test_exact_proposed_authority_title_is_current_stress_compatible(self):
        self.assertEqual(G.S._direct_arm_control_disposition(AUTH_TITLE), "allowed")

    def test_refuses_authorization_body_main_not_matching_dispatch_sha(self):
        comments = make_comments(body_main_sha="b" * 40)
        stress = make_stress(comments=comments)
        with self.assertRaises(G.GuardedPlanRefusal):
            build(issue60_comments_snapshot=comments, stress_receipt=stress)

    def test_refuses_missing_authorization_dispatch_bindings(self):
        for kwargs in (
            {"include_workflow": False},
            {"include_event": False},
            {"include_main": False},
            {"include_attempt": False},
            {"include_one_shot": False},
        ):
            comments = make_comments(**kwargs)
            stress = make_stress(comments=comments)
            with self.subTest(kwargs=kwargs), self.assertRaises(G.GuardedPlanRefusal):
                build(issue60_comments_snapshot=comments, stress_receipt=stress)

    def test_refuses_title_positive_here_but_ambiguous_to_current_stress(self):
        title = "COORDINATOR::ARM_REPLACEMENT_QUERY_ONLY_ONE_SHOT_AUTHORIZED"
        comments = make_comments(auth_title=title)
        stress = make_stress(comments=comments)
        with self.assertRaises(G.GuardedPlanRefusal):
            build(issue60_comments_snapshot=comments, stress_receipt=stress, query_authorization_title=title)

    def test_refuses_supplied_title_not_matching_exact_comment(self):
        with self.assertRaises(G.GuardedPlanRefusal):
            build(query_authorization_title="COORDINATOR::ARM_QUERY_ONLY_SUCCESSOR_AUTHORIZED__DIFFERENT")

    def test_refuses_tampered_issue60_snapshot_hash(self):
        comments = make_comments()
        stress = make_stress(comments=comments)
        tampered = [dict(row) for row in comments]
        tampered[-1]["body"] += "\ntamper"
        with self.assertRaises(G.GuardedPlanRefusal):
            build(issue60_comments_snapshot=tampered, stress_receipt=stress)

    def test_refuses_incomplete_issue60_snapshot(self):
        comments = make_comments()
        stress = make_stress(comments=comments)
        with self.assertRaises(G.GuardedPlanRefusal):
            build(issue60_comments_snapshot=comments[:-1], stress_receipt=stress)

    def test_refuses_authority_absent_from_stress_arm_ledger(self):
        comments = make_comments()
        stress = make_stress(comments=comments, arm_ids=[PREP_COMMENT])
        with self.assertRaises(G.GuardedPlanRefusal):
            build(issue60_comments_snapshot=comments, stress_receipt=stress)

    def test_refuses_authority_that_is_not_latest_arm_governance(self):
        comments = make_comments(extra_after=True)
        stress = make_stress(comments=comments, arm_ids=[PREP_COMMENT, AUTH_COMMENT, AUTH_COMMENT + 1])
        with self.assertRaises(G.GuardedPlanRefusal):
            build(issue60_comments_snapshot=comments, stress_receipt=stress)

    def test_refuses_non_arm_coordinator_title(self):
        comments = make_comments(auth_title="COORDINATOR::AVPS_QUERY_ONLY_SUCCESSOR_AUTHORIZED")
        stress = make_stress(comments=comments)
        with self.assertRaises(G.GuardedPlanRefusal):
            build(
                issue60_comments_snapshot=comments,
                stress_receipt=stress,
                query_authorization_title="COORDINATOR::AVPS_QUERY_ONLY_SUCCESSOR_AUTHORIZED",
            )

    def test_refuses_false_authority_title(self):
        title = "COORDINATOR::ARM_QUERY_ONLY_AUTHORITY_REMAINS_FALSE"
        comments = make_comments(auth_title=title)
        stress = make_stress(comments=comments)
        with self.assertRaises(G.GuardedPlanRefusal):
            build(issue60_comments_snapshot=comments, stress_receipt=stress, query_authorization_title=title)

    def test_refuses_not_authorized_title(self):
        title = "COORDINATOR::ARM_QUERY_ONLY_NOT_AUTHORIZED"
        comments = make_comments(auth_title=title)
        stress = make_stress(comments=comments)
        with self.assertRaises(G.GuardedPlanRefusal):
            build(issue60_comments_snapshot=comments, stress_receipt=stress, query_authorization_title=title)

    def test_refuses_authorization_request_title(self):
        title = "COORDINATOR::ARM_QUERY_ONLY_AUTHORIZATION_REQUEST"
        comments = make_comments(auth_title=title)
        stress = make_stress(comments=comments)
        with self.assertRaises(G.GuardedPlanRefusal):
            build(issue60_comments_snapshot=comments, stress_receipt=stress, query_authorization_title=title)

    def test_refuses_unordered_or_duplicate_arm_governance_ids(self):
        comments = make_comments()
        stress = make_stress(comments=comments, arm_ids=[AUTH_COMMENT, PREP_COMMENT])
        with self.assertRaises(G.GuardedPlanRefusal):
            build(issue60_comments_snapshot=comments, stress_receipt=stress)
        stress = make_stress(comments=comments, arm_ids=[PREP_COMMENT, AUTH_COMMENT, AUTH_COMMENT])
        with self.assertRaises(G.GuardedPlanRefusal):
            build(issue60_comments_snapshot=comments, stress_receipt=stress)

    def test_refuses_arm_governance_id_beyond_ledger_latest(self):
        comments = make_comments()
        stress = make_stress(comments=comments, arm_ids=[PREP_COMMENT, AUTH_COMMENT, AUTH_COMMENT + 1])
        with self.assertRaises(G.GuardedPlanRefusal):
            build(issue60_comments_snapshot=comments, stress_receipt=stress)

    def test_refuses_consumed_legacy_authority_identity(self):
        comments = [
            {"id": 1, "body": "COORDINATOR::BASELINE"},
            {"id": P.LEGACY_AUTHORITY, "body": auth_body()},
        ]
        stress = make_stress(comments=comments, arm_ids=[P.LEGACY_AUTHORITY])
        stress["baseline_coordinator_comment"] = 1
        with self.assertRaises(G.GuardedPlanRefusal):
            build(
                issue60_comments_snapshot=comments,
                stress_receipt=stress,
                query_authorization_comment=P.LEGACY_AUTHORITY,
                query_authorization_title=AUTH_TITLE,
            )

    def test_v1_refusals_still_apply_after_authority_binding(self):
        with self.assertRaises(G.GuardedPlanRefusal):
            build(query_run_attempt=2)
        with self.assertRaises(G.GuardedPlanRefusal):
            build(query_dispatch_ref="refs/heads/review/arm-ena-sws-v1-stage0")


if __name__ == "__main__":
    unittest.main()
