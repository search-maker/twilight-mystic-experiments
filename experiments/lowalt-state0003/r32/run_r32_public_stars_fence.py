#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNNER = HERE / "run_r32.py"

spec = importlib.util.spec_from_file_location("lowalt_r32_core", RUNNER)
if spec is None or spec.loader is None:
    raise RuntimeError("cannot-load-r32-runner")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

BOUND_STARS_MAIN = os.environ.get("R32_EXTERNAL_STARS_MAIN_SHA", "")
if BOUND_STARS_MAIN != mod.STARS_MAIN_SHA:
    raise RuntimeError(("external-stars-main-binding-drift", BOUND_STARS_MAIN, mod.STARS_MAIN_SHA))


def _fresh_control_fence(evidence: Path) -> dict:
    gh = os.environ["GH_TOKEN"]
    repo = os.environ["GITHUB_REPOSITORY"]
    runid = int(os.environ["GITHUB_RUN_ID"])
    issue = mod.api_get(f"https://api.github.com/repos/{repo}/issues/60", gh)
    count = int(issue["comments"])
    page = (count - 1) // 100 + 1
    tail = mod.api_get(f"https://api.github.com/repos/{repo}/issues/60/comments?per_page=100&page={page}", gh)
    lowalt = [
        r for r in tail
        if int(r["id"]) >= mod.AUTHORITY_COMMENT
        and ("LOWALT" in r.get("body", "").upper() or "LOW-ALTITUDE" in r.get("body", "").upper())
    ]
    forbidden_new = []
    for row in lowalt:
        cid = int(row["id"])
        if cid in (mod.AUTHORITY_COMMENT, mod.OWNER_CLASSIFICATION_COMMENT):
            continue
        first = (row.get("body") or "").splitlines()[0].upper()
        if first.startswith("COORDINATOR::LOWALT") or "WRITE_QUIET_BEGIN" in first:
            forbidden_new.append({"id": cid, "first": first})

    main = mod.api_get(f"https://api.github.com/repos/{repo}/branches/main", gh)["commit"]["sha"]
    other = {}
    for status in ("in_progress", "queued"):
        runs = mod.api_get(
            f"https://api.github.com/repos/{repo}/actions/runs?status={status}&per_page=100", gh
        )["workflow_runs"]
        other[status] = [
            {
                "id": int(r["id"]),
                "name": r.get("name"),
                "head_branch": r.get("head_branch"),
                "head_sha": r.get("head_sha"),
            }
            for r in runs
            if int(r["id"]) != runid
        ]

    out = {
        "schemaVersion": 1,
        "issue60CommentCount": count,
        "latestIssue60CommentId": int(tail[-1]["id"]) if tail else None,
        "newerLowAltCoordinatorRestrictions": forbidden_new,
        "twilightMain": main,
        "starsMain": BOUND_STARS_MAIN,
        "starsMainReadMode": "FRESH_EXTERNAL_CONNECTOR_PRETRIGGER_BINDING_PRIVATE_REPOSITORY",
        "starsMainRuntimeCrossRepoRequestPerformed": False,
        "starsMainBindingExpectedByFrozenRunner": mod.STARS_MAIN_SHA,
        "otherMutableActions": other,
        "activeActionAloneIsNotBlocker": True,
        "productionBelow5Deg": "FAIL_CLOSED_UNCHANGED",
    }
    mod.write_json(evidence / "fresh-pre-development-fence.json", out)
    if forbidden_new:
        raise RuntimeError(("newer-lowalt-authority", forbidden_new))
    if BOUND_STARS_MAIN != mod.STARS_MAIN_SHA:
        raise RuntimeError(("stars-main-drift", BOUND_STARS_MAIN, mod.STARS_MAIN_SHA))
    return out


mod.fresh_control_fence = _fresh_control_fence

pre = Path(os.environ.get("R32_PRE_DIR", "/tmp"))
pre.mkdir(parents=True, exist_ok=True)
mod.write_json(
    pre / "private-stars-fence-adapter.json",
    {
        "schemaVersion": 1,
        "classification": "LOWALT_R32_MECHANICAL_PRIVATE_STARSVISIBILITY_PRETRIGGER_BINDING_ADAPTER",
        "starsRepositoryVisibility": "private",
        "boundStarsMainSha": BOUND_STARS_MAIN,
        "runtimeCrossRepoGithubTokenUsed": False,
        "sameRepoGithubApiRemainsAuthenticated": True,
        "scientificMatrixModified": False,
        "scientificContractModified": False,
        "scientificIdentityModified": False,
        "developmentResultOpenedByAdapter": False,
        "auditOpenedByAdapter": False,
        "productionBelow5Deg": "FAIL_CLOSED_UNCHANGED",
    },
)

if __name__ == "__main__":
    try:
        rc = mod.main()
    except Exception as exc:
        evidence = Path(os.environ.get("R32_EVIDENCE_DIR", "/tmp/r32-evidence"))
        evidence.mkdir(parents=True, exist_ok=True)
        mod.write_json(
            evidence / "fatal-barrier.json",
            {
                "classification": "LOWALT_R32_MECHANICAL_OR_GOVERNANCE_BARRIER",
                "errorType": type(exc).__name__,
                "error": str(exc),
                "auditOpened": False,
                "retuningPerformed": False,
                "productionBelow5Deg": "FAIL_CLOSED_UNCHANGED",
            },
        )
        mod.manifest(evidence)
        raise
    raise SystemExit(rc)
