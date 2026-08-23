from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path.cwd()
STAGE = ROOT / "experiments/aerosol-optical-property-sensitivity-v1"
EXECD = STAGE / "execution-candidate"
GLOBAL = EXECD / "global_ordinal.py"
CONTROL = EXECD / "control_surface.py"
FREEZE = ROOT / "evidence/aerosol-optical-property-sensitivity-v1/review-freeze.json"
CONTRACT = STAGE / "transport-contract.v1.json"
TEST = ROOT / "tests/test_aops_v1_publisher_retirement_recovery.py"


def git_blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one anchor, got {count}")
    return text.replace(old, new, 1)


text = GLOBAL.read_text()
old = '''AUTH_REVIEW_WORKFLOW = ".github/workflows/aops-v1-authorization-review.yml"\nEXECUTION_WORKFLOW = ".github/workflows/aops-v1-execution.yml"\nAOPS_ALLOCATION_MARKER = re.compile(\n    r"^ORDINAL([0-9]+)_AOPS_V1_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED(?:\\s|$)", re.I\n)\n'''
new = '''AUTH_REVIEW_WORKFLOW = ".github/workflows/aops-v1-authorization-review.yml"\nEXECUTION_WORKFLOW = ".github/workflows/aops-v1-execution.yml"\nPUBLISHER_WORKFLOW = ".github/workflows/aops-v1-dispatch-publisher.yml"\nAOPS_ALLOCATION_MARKER = re.compile(\n    r"^ORDINAL([0-9]+)_AOPS_V1_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED "\n    r"commit=([0-9a-f]{40}) parent=([0-9a-f]{40}) pr=([1-9][0-9]*)$",\n    re.I,\n)\nAOPS_RETIRED_MARKER = re.compile(\n    r"^ORDINAL([0-9]+)_AOPS_V1_AUTHORIZATION_RETIRED_UNDISPATCHED$", re.I\n)\n\n\ndef retired_authorization_marker(ordinal: int) -> str:\n    return f"ORDINAL{ordinal}_AOPS_V1_AUTHORIZATION_RETIRED_UNDISPATCHED"\n'''
text = replace_once(text, old, new, "global marker definitions")

old = '''        for row in payload.get("issue60Comments", []):\n            body = str(row.get("body") or "").strip()\n            m = AOPS_ALLOCATION_MARKER.match(body)\n            if m and int(m.group(1)) == ordinal:\n                raise GlobalOrdinalRefusal(f"ordinal {ordinal} failed head already has allocation marker")\n            if body.lower() == f"ORDINAL{ordinal}_AOPS_V1_DISPATCH_CONSUMED".lower():\n                raise GlobalOrdinalRefusal(f"ordinal {ordinal} failed head already has consumed marker")\n'''
new = '''        for row in payload.get("issue60Comments", []):\n            body = str(row.get("body") or "").strip()\n            m = AOPS_ALLOCATION_MARKER.fullmatch(body)\n            if (\n                m\n                and int(m.group(1)) == ordinal\n                and m.group(2).lower() == head\n                and int(m.group(4)) == pr_number\n            ):\n                raise GlobalOrdinalRefusal(f"ordinal {ordinal} failed head already has allocation marker")\n            if body.lower() == f"ORDINAL{ordinal}_AOPS_V1_DISPATCH_CONSUMED".lower():\n                raise GlobalOrdinalRefusal(f"ordinal {ordinal} failed head already has consumed marker")\n'''
text = replace_once(text, old, new, "failed-history allocation binding")

start = text.index("\ndef derive_next_global_ordinal(")
text = text[:start] + r'''


def _aops_retired_ordinals(payload: dict[str, Any]) -> set[int]:
    return {
        int(match.group(1))
        for row in payload.get("issue60Comments", [])
        if (match := AOPS_RETIRED_MARKER.fullmatch(str(row.get("body") or "").strip()))
    }


def _retired_undispatched_proof(payload: dict[str, Any], ordinal: int) -> None:
    """Prove one reviewed AOPS allocation failed terminally before any dispatch transition."""
    comments = [str(row.get("body") or "").strip() for row in payload.get("issue60Comments", [])]
    retired = retired_authorization_marker(ordinal)
    if sum(1 for body in comments if body.lower() == retired.lower()) != 1:
        raise GlobalOrdinalRefusal(f"ordinal {ordinal} lacks exactly one AOPS retired-undispatched marker")

    allocations = []
    for body in comments:
        match = AOPS_ALLOCATION_MARKER.fullmatch(body)
        if match and int(match.group(1)) == ordinal:
            allocations.append(match)
    if len(allocations) != 1:
        raise GlobalOrdinalRefusal(f"ordinal {ordinal} lacks exactly one AOPS allocation marker")
    allocation = allocations[0]
    auth_head = allocation.group(2).lower()
    auth_parent = allocation.group(3).lower()
    pr_number = int(allocation.group(4))
    if not re.fullmatch(r"[0-9a-f]{40}", auth_parent):
        raise GlobalOrdinalRefusal(f"ordinal {ordinal} allocation parent is malformed")

    auth_branch = f"authorization/{STAGE}-ordinal-{ordinal}"
    dispatch_branch = f"dispatch/{STAGE}-ordinal-{ordinal}"
    publisher_branch = f"status/aops-v1-dispatch-publisher-ordinal-{ordinal}"

    auth_rows = [row for row in payload.get("branches", []) if str(row.get("name") or "") == auth_branch]
    if len(auth_rows) != 1 or str(((auth_rows[0].get("commit") or {}).get("sha") or "")).lower() != auth_head:
        raise GlobalOrdinalRefusal(f"ordinal {ordinal} retired authorization branch/head evidence drift")
    if any(str(row.get("name") or "") == dispatch_branch for row in payload.get("branches", [])):
        raise GlobalOrdinalRefusal(f"ordinal {ordinal} has a dispatch branch and cannot be retired undispatched")

    matching_prs = []
    for pr in payload.get("pulls", []):
        head = pr.get("head") or {}
        base = pr.get("base") or {}
        if (
            int(pr.get("number") or 0) == pr_number
            and head.get("ref") == auth_branch
            and str(head.get("sha") or "").lower() == auth_head
            and str(base.get("sha") or auth_parent).lower() == auth_parent
        ):
            matching_prs.append(pr)
    if len(matching_prs) != 1:
        raise GlobalOrdinalRefusal(f"ordinal {ordinal} retired allocation PR evidence missing/drifted")
    pr = matching_prs[0]
    if pr.get("state") != "closed" or pr.get("merged_at") is not None:
        raise GlobalOrdinalRefusal(f"ordinal {ordinal} retired allocation PR must be closed and unmerged")

    auth_review_runs = [
        row for row in payload.get("runs", [])
        if str(row.get("head_branch") or "") == auth_branch
        and str(row.get("head_sha") or "").lower() == auth_head
        and str(row.get("path") or "") == AUTH_REVIEW_WORKFLOW
        and str(row.get("event") or "") == "pull_request"
    ]
    if len(auth_review_runs) != 1:
        raise GlobalOrdinalRefusal(f"ordinal {ordinal} must have exactly one authorization-review run on allocated head")
    auth_review = auth_review_runs[0]
    if (
        int(auth_review.get("run_attempt") or 0) != 1
        or auth_review.get("status") != "completed"
        or auth_review.get("conclusion") != "success"
    ):
        raise GlobalOrdinalRefusal(f"ordinal {ordinal} authorization review is not successful attempt-1 evidence")

    publisher_branches = [
        row for row in payload.get("branches", [])
        if str(row.get("name") or "") == publisher_branch
    ]
    if len(publisher_branches) != 1:
        raise GlobalOrdinalRefusal(f"ordinal {ordinal} must preserve exactly one publisher request branch")
    publisher_head = str(((publisher_branches[0].get("commit") or {}).get("sha") or "")).lower()
    if not re.fullmatch(r"[0-9a-f]{40}", publisher_head):
        raise GlobalOrdinalRefusal(f"ordinal {ordinal} publisher request branch head is invalid")

    publisher_runs = [
        row for row in payload.get("runs", [])
        if str(row.get("head_branch") or "") == publisher_branch
        and str(row.get("path") or "") == PUBLISHER_WORKFLOW
        and str(row.get("event") or "") == "push"
    ]
    if len(publisher_runs) != 1:
        raise GlobalOrdinalRefusal(f"ordinal {ordinal} must have exactly one publisher attempt to justify retirement")
    publisher = publisher_runs[0]
    if str(publisher.get("head_sha") or "").lower() != publisher_head:
        raise GlobalOrdinalRefusal(f"ordinal {ordinal} publisher run head differs from preserved request branch head")
    if (
        int(publisher.get("run_attempt") or 0) != 1
        or publisher.get("status") != "completed"
        or publisher.get("conclusion") != "failure"
    ):
        raise GlobalOrdinalRefusal(f"ordinal {ordinal} publisher history is not terminal attempt-1 failure only")

    if any(str(row.get("head_branch") or "") == dispatch_branch for row in payload.get("runs", [])):
        raise GlobalOrdinalRefusal(f"ordinal {ordinal} has a scientific dispatch-branch run and cannot be retired undispatched")
    consumed = f"ORDINAL{ordinal}_AOPS_V1_DISPATCH_CONSUMED"
    if any(body.lower() == consumed.lower() for body in comments):
        raise GlobalOrdinalRefusal(f"ordinal {ordinal} has a dispatch-consumed marker and cannot be retired undispatched")


def _prove_retired_gap(payload: dict[str, Any], ordinal: int, r8_module: Any, aops_retired: set[int]) -> None:
    if ordinal in aops_retired:
        _retired_undispatched_proof(payload, ordinal)
        return
    r8_module._retired_undispatched_proof(payload, ordinal)


def derive_next_global_ordinal(
    payload: dict[str, Any], latest_consumed: int, *, current_run_id: int | None = None
):
    _, mod = _bound_r8_modules()
    observations = mod.authoritative_global_ordinal_observations(payload, current_run_id=current_run_id)
    if not observations:
        raise GlobalOrdinalRefusal("no authoritative global scientific ordinal observations")

    aops_retired = _aops_retired_ordinals(payload)
    for ordinal in sorted(aops_retired):
        _retired_undispatched_proof(payload, ordinal)

    observed_max = max(int(row["ordinal"]) for row in observations)
    if observed_max < latest_consumed:
        raise GlobalOrdinalRefusal(
            f"global identity surface is behind latest consumed ordinal: consumed={latest_consumed} observed={observed_max}"
        )

    for ordinal in range(latest_consumed + 1, observed_max):
        _prove_retired_gap(payload, ordinal, mod, aops_retired)

    if observed_max == latest_consumed:
        return latest_consumed + 1, observations

    auth_branch = f"authorization/{STAGE}-ordinal-{observed_max}"
    auth_rows = [row for row in payload.get("branches", []) if str(row.get("name") or "") == auth_branch]
    if len(auth_rows) > 1:
        raise GlobalOrdinalRefusal(f"ordinal {observed_max} has duplicate AOPS authorization branch observations")
    current_head = None if not auth_rows else str(((auth_rows[0].get("commit") or {}).get("sha") or "")).lower()
    failed = failed_authorization_history(payload, observed_max)
    if failed["heads"] and current_head in set(failed["heads"]):
        return observed_max, observations

    has_aops_allocation = any(
        (match := AOPS_ALLOCATION_MARKER.fullmatch(str(row.get("body") or "").strip()))
        and int(match.group(1)) == observed_max
        for row in payload.get("issue60Comments", [])
    )
    if current_head is not None or has_aops_allocation or observed_max in aops_retired or failed["heads"]:
        _retired_undispatched_proof(payload, observed_max)
        return observed_max + 1, observations

    if any(ordinal in aops_retired for ordinal in range(latest_consumed + 1, observed_max)):
        raise GlobalOrdinalRefusal("non-AOPS observed maximum above AOPS retired gap requires a stage-aware wrapper")
    return mod.derive_next_global_ordinal(payload, latest_consumed, current_run_id=current_run_id)
'''
GLOBAL.write_text(text)

global_blob = git_blob(GLOBAL)
control = CONTROL.read_text()
control = replace_once(
    control,
    '"b935b29e8be83efeed508c8177a5c596b663143b",',
    f'"{global_blob}",',
    "control_surface global_ordinal binding",
)
CONTROL.write_text(control)
control_blob = git_blob(CONTROL)

freeze = json.loads(FREEZE.read_text())
freeze["globalOrdinalWrapperGitBlobSha1"] = global_blob
FREEZE.write_text(json.dumps(freeze, indent=2, sort_keys=True) + "\n")

contract = json.loads(CONTRACT.read_text())
contract["gitBlobBindings"]["experiments/aerosol-optical-property-sensitivity-v1/execution-candidate/global_ordinal.py"] = global_blob
contract["gitBlobBindings"]["experiments/aerosol-optical-property-sensitivity-v1/execution-candidate/control_surface.py"] = control_blob
CONTRACT.write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n")

TEST.write_text(r'''from __future__ import annotations

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
''')

print(json.dumps({
    "globalOrdinalGitBlobSha1": global_blob,
    "controlSurfaceGitBlobSha1": control_blob,
    "changed": [
        str(GLOBAL.relative_to(ROOT)),
        str(CONTROL.relative_to(ROOT)),
        str(FREEZE.relative_to(ROOT)),
        str(CONTRACT.relative_to(ROOT)),
        str(TEST.relative_to(ROOT)),
    ],
}, indent=2, sort_keys=True))
