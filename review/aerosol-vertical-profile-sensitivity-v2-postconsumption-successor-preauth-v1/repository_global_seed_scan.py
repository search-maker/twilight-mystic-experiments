from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = ROOT / "experiments/aerosol-family-challenge-v2/repository_global_seed_scan.py"
EXPECTED_BASE_BLOB = "4c6d704fa24228284780bcb1dd7c52537b4c5b0d"


def git_blob_sha1(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


if git_blob_sha1(BASE) != EXPECTED_BASE_BLOB:
    raise SystemExit("bound repository-global seed scanner byte drift")

spec = importlib.util.spec_from_file_location("avps_successor_bound_repository_global_seed_scan", BASE)
if spec is None or spec.loader is None:
    raise SystemExit("cannot import bound repository-global seed scanner")
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)
mod.REVIEW_PROOF_ARTIFACT_NAME = "vertical-profile-v2-postconsumption-successor-preauthorization-proof"

# Coordinator 5606837364 authorizes only this narrow successor-wrapper repair:
# parent summary counters that are redundant with separately enumerated child
# comment surfaces must not make an already-fenced parent row appear changed.
# Content-bearing parent/child fields and every bound-scanner seed/collision
# guard remain significant.  The installed bound scanner itself is unchanged.
_REDUNDANT_PARENT_COUNTERS = {
    "issues": frozenset({"comments"}),
    "pulls": frozenset({"comments", "review_comments"}),
}
_ORIGINAL_CANONICAL_COLLISION_VALUE = mod._canonical_collision_value
_ORIGINAL_DEDUPE_ROWS_BY_ID = mod._dedupe_rows_by_id
_UNCHANGED_FUNCTIONS = {
    name: getattr(mod, name)
    for name in (
        "seed_literals",
        "find_post_fence_seed_collisions",
        "evaluate_context",
        "collect_stable",
        "final_expected_branch_head",
    )
}


def _without_redundant_parent_counters(row: dict, surface_key: str) -> dict:
    counters = _REDUNDANT_PARENT_COUNTERS.get(surface_key)
    if not counters:
        return row
    return {name: value for name, value in row.items() if name not in counters}


def _canonical_surface_row(row: dict, surface_key: str):
    return _ORIGINAL_CANONICAL_COLLISION_VALUE(
        _without_redundant_parent_counters(row, surface_key)
    )


def _dedupe_rows_by_id(rows: list[dict], surface_key: str) -> list[dict]:
    """Use parent-counter projection only for Issue/PR stable-ID dedupe."""
    if surface_key not in _REDUNDANT_PARENT_COUNTERS:
        return _ORIGINAL_DEDUPE_ROWS_BY_ID(rows, surface_key)
    by_id: dict[int, dict] = {}
    canonical_by_id: dict[int, object] = {}
    for row in rows:
        row_id = mod._numeric_row_id(row, surface_key)
        canonical = _canonical_surface_row(row, surface_key)
        if row_id in canonical_by_id and canonical_by_id[row_id] != canonical:
            raise RuntimeError(f"{surface_key} row {row_id} changed within one complete enumeration")
        by_id[row_id] = row
        canonical_by_id[row_id] = canonical
    return [by_id[row_id] for row_id in sorted(by_id)]


def _canonical_collision_context(context: dict, current_run_id: int | None = None) -> dict:
    """Canonical context with only redundant root Issue/PR counters projected out."""
    filtered = mod._without_current_audit_self_metadata(context, current_run_id)
    out: dict[str, object] = {}
    for surface_key in mod.SURFACE_KEYS:
        rows = filtered.get(surface_key)
        if not isinstance(rows, list):
            raise ValueError(f"repository-global context requires {surface_key} array")
        if surface_key not in _REDUNDANT_PARENT_COUNTERS:
            out[surface_key] = _ORIGINAL_CANONICAL_COLLISION_VALUE(rows)
            continue
        normalized = [_canonical_surface_row(row, surface_key) for row in rows]
        out[surface_key] = sorted(
            normalized,
            key=lambda item: json.dumps(
                item,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ),
        )
    return out


mod._dedupe_rows_by_id = _dedupe_rows_by_id
mod.canonical_collision_context = _canonical_collision_context


def _empty_context() -> dict:
    return {key: [] for key in mod.SURFACE_KEYS}


def _fixture_context() -> dict:
    """GitHub-shaped parent/child rows matching the live false-instability class."""
    main_sha = "a" * 40
    review_sha = "b" * 40
    context = _empty_context()
    context["branches"] = [
        {"name": "main", "commit": {"sha": main_sha}},
        {"name": "review/avps-fixture", "commit": {"sha": review_sha}},
    ]
    context["pulls"] = [
        {
            "id": 301,
            "number": 1020,
            "url": "https://api.github.com/repos/search-maker/twilight-mystic-experiments/pulls/1020",
            "title": "AVPS fixture proposal",
            "body": "stable pull body",
            "state": "open",
            "comments": 4,
            "review_comments": 2,
            "head": {"ref": "review/avps-fixture", "sha": review_sha},
            "base": {"ref": "main", "sha": main_sha},
        }
    ]
    context["issues"] = [
        {
            "id": 401,
            "number": 60,
            "url": "https://api.github.com/repos/search-maker/twilight-mystic-experiments/issues/60",
            "title": "MYSTIC control",
            "body": "stable issue body",
            "state": "open",
            "comments": 10,
        }
    ]
    context["issueComments"] = [
        {
            "id": 501,
            "issue_url": "https://api.github.com/repos/search-maker/twilight-mystic-experiments/issues/60",
            "body": "stable issue comment",
        },
        {
            "id": 502,
            "issue_url": "https://api.github.com/repos/search-maker/twilight-mystic-experiments/issues/1020",
            "body": "stable PR conversation comment",
        },
    ]
    context["pullReviewComments"] = [
        {
            "id": 601,
            "pull_request_url": "https://api.github.com/repos/search-maker/twilight-mystic-experiments/pulls/1020",
            "body": "stable review comment",
            "commit_id": review_sha,
            "path": "fixture.py",
            "line": 1,
        }
    ]
    context["issue60Comments"] = [copy.deepcopy(context["issueComments"][0])]
    return context


def _expect_runtime_error(label: str, fn) -> None:
    try:
        fn()
    except RuntimeError:
        return
    raise SystemExit(f"snapshot-counter fixture did not fail closed: {label}")


def _run_snapshot_counter_fixtures() -> dict:
    first = _fixture_context()
    fence = mod.build_snapshot_fence(first)
    first_fenced = mod.apply_snapshot_fence(first, fence)

    # Exercise the real GitHub parent/child behavior: the newly appended child
    # rows are post-fence while GitHub simultaneously increments counters on the
    # already-fenced Issue/PR parent rows.
    second = copy.deepcopy(first)
    second["issues"][0]["comments"] += 1
    issue_append = {
        "id": 503,
        "issue_url": "https://api.github.com/repos/search-maker/twilight-mystic-experiments/issues/60",
        "body": "new post-fence issue comment",
    }
    second["issueComments"].append(copy.deepcopy(issue_append))
    second["issue60Comments"].append(copy.deepcopy(issue_append))

    second["pulls"][0]["comments"] += 1
    second["issueComments"].append(
        {
            "id": 504,
            "issue_url": "https://api.github.com/repos/search-maker/twilight-mystic-experiments/issues/1020",
            "body": "new post-fence PR conversation comment",
        }
    )

    second["pulls"][0]["review_comments"] += 1
    second["pullReviewComments"].append(
        {
            "id": 602,
            "pull_request_url": "https://api.github.com/repos/search-maker/twilight-mystic-experiments/pulls/1020",
            "body": "new post-fence review comment",
            "commit_id": "b" * 40,
            "path": "fixture.py",
            "line": 2,
        }
    )
    second_fenced = mod.apply_snapshot_fence(second, fence)
    stable_sha = mod.require_two_pass_stability(first_fenced, second_fenced)

    # Counter-only repeated parent rows collapse, but any real same-ID content
    # disagreement remains fatal.
    counter_duplicate = copy.deepcopy(first)
    issue_counter_copy = copy.deepcopy(counter_duplicate["issues"][0])
    issue_counter_copy["comments"] += 9
    counter_duplicate["issues"].append(issue_counter_copy)
    pull_counter_copy = copy.deepcopy(counter_duplicate["pulls"][0])
    pull_counter_copy["comments"] += 7
    pull_counter_copy["review_comments"] += 3
    counter_duplicate["pulls"].append(pull_counter_copy)
    mod.build_snapshot_fence(counter_duplicate)

    true_duplicate_conflict = copy.deepcopy(first)
    conflicting_issue = copy.deepcopy(true_duplicate_conflict["issues"][0])
    conflicting_issue["body"] = "different body for same stable id"
    true_duplicate_conflict["issues"].append(conflicting_issue)
    _expect_runtime_error(
        "true same-ID issue conflict",
        lambda: mod.build_snapshot_fence(true_duplicate_conflict),
    )

    def expect_existing_change(label: str, mutator) -> None:
        changed = copy.deepcopy(first)
        mutator(changed)
        changed_fenced = mod.apply_snapshot_fence(changed, fence)
        _expect_runtime_error(
            label,
            lambda: mod.require_two_pass_stability(first_fenced, changed_fenced),
        )

    expect_existing_change(
        "fenced issue body edit",
        lambda value: value["issues"][0].__setitem__("body", "edited body"),
    )
    expect_existing_change(
        "fenced issue title edit",
        lambda value: value["issues"][0].__setitem__("title", "edited title"),
    )
    expect_existing_change(
        "fenced PR head edit",
        lambda value: value["pulls"][0]["head"].__setitem__("sha", "c" * 40),
    )
    expect_existing_change(
        "fenced child content edit",
        lambda value: value["pullReviewComments"][0].__setitem__("body", "edited review content"),
    )
    expect_existing_change(
        "branch-head movement",
        lambda value: value["branches"][0]["commit"].__setitem__("sha", "d" * 40),
    )

    candidate_seed = 87_654_321
    post_fence_seed = copy.deepcopy(second)
    post_fence_seed["issueComments"].append(
        {
            "id": 505,
            "issue_url": "https://api.github.com/repos/search-maker/twilight-mystic-experiments/issues/60",
            "body": f"new post-fence candidate seed {candidate_seed}",
        }
    )
    collisions = mod.find_post_fence_seed_collisions(
        post_fence_seed,
        fence,
        {candidate_seed},
    )
    if not any(candidate_seed in row.get("seeds", []) for row in collisions):
        raise SystemExit("snapshot-counter fixture lost post-fence candidate-seed refusal")

    for name, original in _UNCHANGED_FUNCTIONS.items():
        if getattr(mod, name) is not original:
            raise SystemExit(f"unauthorized bound-scanner function replacement: {name}")

    return {
        "schemaVersion": 1,
        "status": "PASS_NARROW_REDUNDANT_PARENT_COUNTER_NORMALIZATION_FIXTURES",
        "normalizedRootCounters": {
            "issues": ["comments"],
            "pulls": ["comments", "review_comments"],
        },
        "appendOnlyIssueParentCounterStable": True,
        "appendOnlyPrConversationParentCounterStable": True,
        "appendOnlyPrReviewParentCounterStable": True,
        "postFenceCandidateSeedRefusalPreserved": True,
        "fencedBodyTitleHeadContentEditsFailClosed": True,
        "branchHeadMovementFailsClosed": True,
        "trueSameIdConflictFailsClosed": True,
        "counterOnlySameIdPaginationDuplicateCollapses": True,
        "patchedFunctions": ["_dedupe_rows_by_id", "canonical_collision_context"],
        "seedOrdinalAuthorizationSemanticsChanged": False,
        "stableFixtureContextSha256": stable_sha,
    }


NORMALIZATION_FIXTURE_REPORT = _run_snapshot_counter_fixtures()
print(
    "AVPS_SUCCESSOR_SNAPSHOT_COUNTER_FIXTURE "
    + json.dumps(NORMALIZATION_FIXTURE_REPORT, sort_keys=True, separators=(",", ":"))
)

if __name__ == "__main__":
    mod.main()
