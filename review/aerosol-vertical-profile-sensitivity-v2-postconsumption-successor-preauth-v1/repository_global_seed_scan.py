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

# Coordinator 5606837364 authorizes only the root parent-counter projection;
# Coordinator 5607593710 additionally authorizes the narrow path-specific
# embedded-repository identity projection below.  The installed bound scanner
# itself remains byte-bound and unchanged.  No broad recursive blacklist is
# introduced: only the four GitHub repository-summary locations named by the
# Coordinator are projected, while all meaningful pull/run row content stays
# subject to the bound scanner's fail-closed canonicalization.
_REDUNDANT_PARENT_COUNTERS = {
    "issues": frozenset({"comments"}),
    "pulls": frozenset({"comments", "review_comments"}),
}
_REPOSITORY_IDENTITY_FIELDS = ("id", "node_id", "name", "full_name")
_REPOSITORY_OWNER_IDENTITY_FIELDS = ("id", "node_id", "login")
_EMBEDDED_REPOSITORY_PATHS = {
    "pulls": (("head", "repo"), ("base", "repo")),
    "runs": (("repository",), ("head_repository",)),
}
_CUSTOM_CANONICAL_SURFACES = frozenset(
    set(_REDUNDANT_PARENT_COUNTERS) | set(_EMBEDDED_REPOSITORY_PATHS)
)
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


def _stable_repository_identity(value):
    if not isinstance(value, dict):
        return value
    projected = {
        name: value[name]
        for name in _REPOSITORY_IDENTITY_FIELDS
        if name in value
    }
    if "owner" in value:
        owner = value.get("owner")
        if isinstance(owner, dict):
            projected["owner"] = {
                name: owner[name]
                for name in _REPOSITORY_OWNER_IDENTITY_FIELDS
                if name in owner
            }
        else:
            projected["owner"] = owner
    return projected


def _project_embedded_repository_identity(row: dict, surface_key: str) -> dict:
    paths = _EMBEDDED_REPOSITORY_PATHS.get(surface_key)
    if not paths:
        return row
    projected = copy.deepcopy(row)
    for path in paths:
        if len(path) == 1:
            name = path[0]
            if name in projected:
                projected[name] = _stable_repository_identity(projected.get(name))
            continue
        parent_name, repo_name = path
        parent = projected.get(parent_name)
        if isinstance(parent, dict) and repo_name in parent:
            parent[repo_name] = _stable_repository_identity(parent.get(repo_name))
    return projected


def _canonical_surface_row(row: dict, surface_key: str):
    return _ORIGINAL_CANONICAL_COLLISION_VALUE(
        _project_embedded_repository_identity(
            _without_redundant_parent_counters(row, surface_key),
            surface_key,
        )
    )


def _dedupe_rows_by_id(rows: list[dict], surface_key: str) -> list[dict]:
    """Project only authorized root counters / nested repo summaries before stable-ID dedupe."""
    if surface_key not in _CUSTOM_CANONICAL_SURFACES:
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
    """Canonical context with only the two explicitly authorized projections applied."""
    filtered = mod._without_current_audit_self_metadata(context, current_run_id)
    out: dict[str, object] = {}
    for surface_key in mod.SURFACE_KEYS:
        rows = filtered.get(surface_key)
        if not isinstance(rows, list):
            raise ValueError(f"repository-global context requires {surface_key} array")
        if surface_key not in _CUSTOM_CANONICAL_SURFACES:
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


def _repo_summary(*, pushed_at: str = "2026-09-09T19:20:48Z", size: int = 22074, open_issues_count: int = 268, open_issues: int = 268) -> dict:
    return {
        "id": 1321052980,
        "node_id": "R_kgDOTr2rNA",
        "name": "twilight-mystic-experiments",
        "full_name": "search-maker/twilight-mystic-experiments",
        "owner": {
            "login": "search-maker",
            "id": 304153003,
            "node_id": "U_kgDOEiEBqw",
            "avatar_url": "https://avatars.githubusercontent.com/u/304153003?v=4",
        },
        "pushed_at": pushed_at,
        "size": size,
        "open_issues_count": open_issues_count,
        "open_issues": open_issues,
        "default_branch": "main",
        "visibility": "public",
    }


def _fixture_context() -> dict:
    """GitHub-shaped rows matching both live false-instability classes."""
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
            "draft": True,
            "locked": False,
            "comments": 4,
            "review_comments": 2,
            "head": {
                "ref": "review/avps-fixture",
                "sha": review_sha,
                "repo": _repo_summary(),
            },
            "base": {
                "ref": "main",
                "sha": main_sha,
                "repo": _repo_summary(),
            },
        }
    ]
    context["runs"] = [
        {
            "id": 701,
            "name": "contract",
            "event": "pull_request",
            "path": ".github/workflows/contract.yml",
            "workflow_id": 801,
            "head_branch": "review/avps-fixture",
            "head_sha": review_sha,
            "repository": _repo_summary(),
            "head_repository": _repo_summary(),
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


def _mutate_embedded_repository_noise(context: dict) -> None:
    replacements = {
        "pushed_at": "2026-09-09T19:25:46Z",
        "size": 22123,
        "open_issues_count": 271,
        "open_issues": 271,
    }
    for side in ("head", "base"):
        context["pulls"][0][side]["repo"].update(replacements)
    for name in ("repository", "head_repository"):
        context["runs"][0][name].update(replacements)


def _expect_runtime_error(label: str, fn, expected: str | None = None) -> None:
    try:
        fn()
    except RuntimeError as exc:
        if expected is not None and expected not in str(exc):
            raise SystemExit(
                f"snapshot fixture failed without naming expected row for {label}: {exc}"
            ) from exc
        return
    raise SystemExit(f"snapshot fixture did not fail closed: {label}")


def _run_snapshot_projection_fixtures() -> dict:
    first = _fixture_context()
    fence = mod.build_snapshot_fence(first)
    first_fenced = mod.apply_snapshot_fence(first, fence)

    # Root Issue/PR counters advance with separately enumerated appended child
    # comments.  The child rows are post-fence while the already-fenced parent
    # rows must remain stable after the narrow counter projection.
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
    counter_stable_sha = mod.require_two_pass_stability(first_fenced, second_fenced)

    # GitHub repeats full repository summaries inside historical PR/run rows.
    # Only the transport/summary members named by the Coordinator may drift;
    # stable repository identity remains significant.
    repo_noise = copy.deepcopy(first)
    _mutate_embedded_repository_noise(repo_noise)
    repo_noise_fenced = mod.apply_snapshot_fence(repo_noise, fence)
    repository_projection_stable_sha = mod.require_two_pass_stability(
        first_fenced,
        repo_noise_fenced,
    )

    # Stable-ID pagination duplicates differing only in projected summary noise
    # must collapse regardless of which duplicate is observed first.
    summary_duplicates = copy.deepcopy(first)
    pull_noise_copy = copy.deepcopy(summary_duplicates["pulls"][0])
    run_noise_copy = copy.deepcopy(summary_duplicates["runs"][0])
    duplicate_noise_context = _fixture_context()
    _mutate_embedded_repository_noise(duplicate_noise_context)
    pull_noise_copy = duplicate_noise_context["pulls"][0]
    run_noise_copy = duplicate_noise_context["runs"][0]
    summary_duplicates["pulls"].append(pull_noise_copy)
    summary_duplicates["runs"].append(run_noise_copy)
    mod.build_snapshot_fence(summary_duplicates)

    reverse_summary_duplicates = copy.deepcopy(summary_duplicates)
    reverse_summary_duplicates["pulls"] = list(reversed(reverse_summary_duplicates["pulls"]))
    reverse_summary_duplicates["runs"] = list(reversed(reverse_summary_duplicates["runs"]))
    mod.build_snapshot_fence(reverse_summary_duplicates)

    # Existing root-counter duplicates continue to collapse.
    counter_duplicate = copy.deepcopy(first)
    issue_counter_copy = copy.deepcopy(counter_duplicate["issues"][0])
    issue_counter_copy["comments"] += 9
    counter_duplicate["issues"].append(issue_counter_copy)
    pull_counter_copy = copy.deepcopy(counter_duplicate["pulls"][0])
    pull_counter_copy["comments"] += 7
    pull_counter_copy["review_comments"] += 3
    counter_duplicate["pulls"].append(pull_counter_copy)
    mod.build_snapshot_fence(counter_duplicate)

    # Embedded repository identity changes remain fatal and name the stable row.
    pull_repo_identity_conflict = copy.deepcopy(first)
    conflicting_pull_repo = copy.deepcopy(pull_repo_identity_conflict["pulls"][0])
    conflicting_pull_repo["head"]["repo"]["id"] += 1
    conflicting_pull_repo["head"]["repo"]["full_name"] = "search-maker/other-repository"
    pull_repo_identity_conflict["pulls"].append(conflicting_pull_repo)
    _expect_runtime_error(
        "embedded pull repository identity conflict",
        lambda: mod.build_snapshot_fence(pull_repo_identity_conflict),
        "pulls row 301",
    )

    run_repo_identity_conflict = copy.deepcopy(first)
    conflicting_run_repo = copy.deepcopy(run_repo_identity_conflict["runs"][0])
    conflicting_run_repo["repository"]["id"] += 1
    conflicting_run_repo["repository"]["full_name"] = "search-maker/other-repository"
    run_repo_identity_conflict["runs"].append(conflicting_run_repo)
    _expect_runtime_error(
        "embedded run repository identity conflict",
        lambda: mod.build_snapshot_fence(run_repo_identity_conflict),
        "runs row 701",
    )

    # Meaningful same-ID pull/run content remains fail-closed and names the row.
    pull_head_conflict = copy.deepcopy(first)
    conflicting_pull_head = copy.deepcopy(pull_head_conflict["pulls"][0])
    conflicting_pull_head["head"]["sha"] = "c" * 40
    pull_head_conflict["pulls"].append(conflicting_pull_head)
    _expect_runtime_error(
        "same-ID pull head SHA conflict",
        lambda: mod.build_snapshot_fence(pull_head_conflict),
        "pulls row 301",
    )

    pull_root_lifecycle_conflict = copy.deepcopy(first)
    conflicting_pull_lifecycle = copy.deepcopy(pull_root_lifecycle_conflict["pulls"][0])
    conflicting_pull_lifecycle["draft"] = False
    pull_root_lifecycle_conflict["pulls"].append(conflicting_pull_lifecycle)
    _expect_runtime_error(
        "same-ID pull root lifecycle conflict",
        lambda: mod.build_snapshot_fence(pull_root_lifecycle_conflict),
        "pulls row 301",
    )

    run_path_conflict = copy.deepcopy(first)
    conflicting_run_path = copy.deepcopy(run_path_conflict["runs"][0])
    conflicting_run_path["path"] = ".github/workflows/other.yml"
    run_path_conflict["runs"].append(conflicting_run_path)
    _expect_runtime_error(
        "same-ID run workflow path conflict",
        lambda: mod.build_snapshot_fence(run_path_conflict),
        "runs row 701",
    )

    run_event_conflict = copy.deepcopy(first)
    conflicting_run_event = copy.deepcopy(run_event_conflict["runs"][0])
    conflicting_run_event["event"] = "workflow_dispatch"
    run_event_conflict["runs"].append(conflicting_run_event)
    _expect_runtime_error(
        "same-ID run event conflict",
        lambda: mod.build_snapshot_fence(run_event_conflict),
        "runs row 701",
    )

    true_duplicate_conflict = copy.deepcopy(first)
    conflicting_issue = copy.deepcopy(true_duplicate_conflict["issues"][0])
    conflicting_issue["body"] = "different body for same stable id"
    true_duplicate_conflict["issues"].append(conflicting_issue)
    _expect_runtime_error(
        "true same-ID issue conflict",
        lambda: mod.build_snapshot_fence(true_duplicate_conflict),
        "issues row 401",
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
        "fenced run path edit",
        lambda value: value["runs"][0].__setitem__("path", ".github/workflows/other.yml"),
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
        raise SystemExit("snapshot fixture lost post-fence candidate-seed refusal")

    for name, original in _UNCHANGED_FUNCTIONS.items():
        if getattr(mod, name) is not original:
            raise SystemExit(f"unauthorized bound-scanner function replacement: {name}")

    return {
        "schemaVersion": 2,
        "status": "PASS_NARROW_COUNTER_AND_EMBEDDED_REPOSITORY_IDENTITY_PROJECTION_FIXTURES",
        "normalizedRootCounters": {
            "issues": ["comments"],
            "pulls": ["comments", "review_comments"],
        },
        "projectedEmbeddedRepositoryPaths": {
            "pulls": ["head.repo", "base.repo"],
            "runs": ["repository", "head_repository"],
        },
        "stableRepositoryIdentityFields": list(_REPOSITORY_IDENTITY_FIELDS),
        "stableRepositoryOwnerIdentityFields": list(_REPOSITORY_OWNER_IDENTITY_FIELDS),
        "appendOnlyIssueParentCounterStable": True,
        "appendOnlyPrConversationParentCounterStable": True,
        "appendOnlyPrReviewParentCounterStable": True,
        "embeddedRepositorySummaryNoiseStableBetweenPasses": True,
        "embeddedRepositorySummaryOnlySameIdDuplicatesCollapse": True,
        "embeddedRepositorySummaryDuplicateOrderIndependent": True,
        "embeddedRepositoryIdentityConflictFailsClosedAndNamesRow": True,
        "meaningfulPullRunSameIdConflictFailsClosedAndNamesRow": True,
        "postFenceCandidateSeedRefusalPreserved": True,
        "fencedBodyTitleHeadContentEditsFailClosed": True,
        "branchHeadMovementFailsClosed": True,
        "trueSameIdConflictFailsClosed": True,
        "counterOnlySameIdPaginationDuplicateCollapses": True,
        "patchedFunctions": ["_dedupe_rows_by_id", "canonical_collision_context"],
        "seedOrdinalAuthorizationSemanticsChanged": False,
        "counterStableFixtureContextSha256": counter_stable_sha,
        "repositoryProjectionStableFixtureContextSha256": repository_projection_stable_sha,
    }


NORMALIZATION_FIXTURE_REPORT = _run_snapshot_projection_fixtures()
print(
    "AVPS_SUCCESSOR_SNAPSHOT_PROJECTION_FIXTURE "
    + json.dumps(NORMALIZATION_FIXTURE_REPORT, sort_keys=True, separators=(",", ":"))
)

if __name__ == "__main__":
    mod.main()
