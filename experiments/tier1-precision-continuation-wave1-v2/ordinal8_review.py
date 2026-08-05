#!/usr/bin/env python3
"""Generate a deterministic candidate-ordinal-8 review packet; never allocate or dispatch."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

MAIN = "82cec0ed538c5ef182797e1f33224f80c8443c03"
WAVE1_HEAD = "3b6fc114ba7d4a71def7e602f6e94d7913883e30"
PREREG_SHA = "bcbb2376e6d7b9a3e3cefc52cd071857a98496dc5d0a8aebce2f512ac6ddf38a"
TEMPLATE_SHA = "8db81c9b4ed13076f7510300cc3b54e7d1e952ef036846aa219a0709d7504b00"
DIMS = {
    "authorizationOrdinal",
    "executionKey",
    "authorizationRef",
    "runTitle",
    "branchPath",
    "authorizationFilePath",
    "seed",
    "actionsRun",
    "pullRequest",
    "issueComment",
}
CANDIDATE = {
    "authorizationOrdinal": 8,
    "executionKey": "twilight-surrogate-tier-1-v1:numerical:8",
    "runTitle": "Tier-1 precision continuation wave 1 ordinal 8",
    "futureAuthorizationBranch": "authorization/tier1-precision-continuation-wave1-ordinal8-v2",
    "futureAuthorizationFile": "experiments/tier1-precision-continuation-wave1-v2/authorization.ordinal8.json",
    "status": "UNALLOCATED_REVIEW_ONLY",
}
CONSUMED_IDENTITIES = [
    {
        "authorizationOrdinal": 1,
        "authorizationRef": "81bbdbe17f7dcf024f49378debfd08d1317137a2",
        "executionKey": "twilight-surrogate-tier-1-v1:numerical:1",
        "pullRequest": 44,
        "runId": 30906913329,
        "state": "consumed",
    },
    {
        "authorizationOrdinal": 2,
        "authorizationRef": "9f3ef4b2afd93d5ae15a45ac70c9f27e32636f88",
        "executionKey": "twilight-surrogate-tier-1-v1:numerical:2",
        "pullRequest": 58,
        "runId": 30952457327,
        "state": "consumed",
    },
    {
        "authorizationOrdinal": 3,
        "authorizationRef": "5f7a5a7f2afd93d5ae15a45ac70c9f27e32636f88",
        "executionKey": "cross-geometry-stage-two-v1:screening:3",
        "pullRequest": 26,
        "runId": 30863907633,
        "state": "consumed",
    },
    {
        "authorizationOrdinal": 4,
        "authorizationRef": "7e630b8f46259ddf6a0cfdf5e381872c0182d0ba",
        "executionKey": "cross-geometry-final-convergence-v1:screening:4",
        "pullRequest": 28,
        "runId": 30869495039,
        "state": "consumed",
    },
    {
        "authorizationOrdinal": 5,
        "authorizationRef": "81b46da6e535e11a5e56b45572979288728805b3",
        "executionKey": "cross-geometry-selected-reference-confirmation-v1:screening:5",
        "pullRequest": 31,
        "runId": 30871800549,
        "state": "consumed",
    },
    {
        "authorizationOrdinal": 6,
        "authorizationRef": "7a348428327f1dfbac3d0606e7661ecd766d5b92",
        "executionKey": "cross-geometry-held-out-confirmation-timeout-continuation-v1:screening:6",
        "pullRequest": 34,
        "runId": 30875148389,
        "state": "consumed",
    },
    {
        "authorizationOrdinal": 7,
        "authorizationRef": "a59b885d28636f6b83aceef30b1029c785b2433d",
        "executionKey": "g01-fixed-precision-diagnosis-execution-v1:screening:7",
        "pullRequest": 40,
        "runId": 30878704003,
        "state": "consumed",
    },
]


class Refusal(ValueError):
    pass


def must(ok: bool, message: str) -> None:
    if not ok:
        raise Refusal(message)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def load(path: Path) -> tuple[dict, bytes]:
    raw = path.read_bytes()
    value = json.loads(raw)
    must(isinstance(value, dict), f"{path} must be a JSON object")
    return value, raw


def build(
    prereg_path: Path,
    template_path: Path,
    snapshot_path: Path,
    prereg_sha: str = PREREG_SHA,
    template_sha: str = TEMPLATE_SHA,
) -> dict:
    prereg, prereg_raw = load(prereg_path)
    template, template_raw = load(template_path)
    snapshot, snapshot_raw = load(snapshot_path)

    must(sha(prereg_raw) == prereg_sha, "preregistration raw SHA-256 drift")
    must(sha(template_raw) == template_sha, "template raw SHA-256 drift")

    for key in ("authorizationOrdinal", "authorizationRef", "executionKey"):
        must(prereg.get(key) is None, f"preregistration {key} must remain null")
    must(
        prereg.get("authorizationEnabled") is False
        and prereg.get("dispatchEnabled") is False
        and prereg.get("workflowDispatchEnabled") is False,
        "preregistration authorization/dispatch must remain disabled",
    )
    must(
        prereg.get("scientificExecution") is False and prereg.get("proposalOnly") is True,
        "preregistration must remain proposal-only",
    )
    must(
        prereg.get("blocks") == [3, 4]
        and prereg.get("caseCount") == 40
        and prereg.get("geometryCount") == 20,
        "wave-1 scope changed",
    )
    must(
        prereg.get("maximumConfiguredPhotonHistories") == 5_100_000_000,
        "photon budget changed",
    )
    must(
        prereg.get("roleCounts")
        == {
            "internalHoldoutCases": 6,
            "internalHoldoutGeometries": 3,
            "surrogateTrainingCases": 34,
            "surrogateTrainingGeometries": 17,
        },
        "role counts changed",
    )
    must(
        all(
            prereg.get("preservation", {}).get(key) is True
            for key in (
                "evidenceBindingsUnchanged",
                "geometryInputsUnchanged",
                "historicalArtifactsImmutable",
                "originalBlocksB1B2Preserved",
                "photonScheduleUnchanged",
                "rolesUnchanged",
                "thresholdsUnchanged",
                "zeroHitHandlingUnchanged",
            )
        ),
        "preservation proof changed",
    )
    proof = prereg.get("seedProof", {})
    must(
        proof.get("allWave1SeedsUnique") is True
        and proof.get("historicalOverlap") == []
        and proof.get("historicalSeedCount") == 196
        and proof.get("wave1SeedCount") == 40,
        "seed proof changed",
    )

    cases = prereg.get("cases")
    must(isinstance(cases, list) and len(cases) == 40, "exact 40-case universe required")
    seeds: list[int] = []
    groups: dict[str, set[int]] = {}
    photons = 0
    roles = {"surrogate-training": 0, "internal-holdout": 0}
    wave = []
    for case in cases:
        must(
            case.get("proposalOnly") is True and case.get("block") in (3, 4),
            "case boundary changed",
        )
        must(
            case.get("role") in roles
            and isinstance(case.get("seed"), int)
            and isinstance(case.get("photonHistories"), int),
            "case fields invalid",
        )
        seeds.append(case["seed"])
        photons += case["photonHistories"]
        roles[case["role"]] += 1
        groups.setdefault(case["groupId"], set()).add(case["block"])
        wave.append(
            {
                "caseId": case["caseId"],
                "block": case["block"],
                "role": case["role"],
                "seed": case["seed"],
            }
        )
    must(
        len(set(seeds)) == 40
        and len(groups) == 20
        and all(value == {3, 4} for value in groups.values()),
        "case/seed universe changed",
    )
    must(
        photons == 5_100_000_000
        and roles == {"surrogate-training": 34, "internal-holdout": 6},
        "budget/role split changed",
    )

    must(
        template.get("enabled") is False
        and template.get("dispatch") is False
        and template.get("automaticDispatch") is False
        and template.get("workflowDispatchEnabled") is False
        and template.get("solverExecutionAuthorized") is False
        and template.get("githubRerunAllowed") is False,
        "template boundary opened",
    )
    for key in ("authorizationOrdinal", "authorizationRef", "authorizationCommit", "executionKey"):
        must(template.get(key) is None, f"template {key} must remain null")

    must(snapshot.get("status") == "REVIEW_ONLY_SNAPSHOT", "snapshot status changed")
    must(snapshot.get("ordinalScope") == "REPOSITORY_GLOBAL_SINGLE_USE", "ordinal scope changed")
    must(snapshot.get("candidateIdentity") == CANDIDATE, "snapshot candidate identity changed")
    must(set(snapshot.get("checkedDimensions", [])) == DIMS, "duplicate-search coverage incomplete")
    must(snapshot.get("candidateSearchComplete") is True, "candidate search not complete")
    must(snapshot.get("consumedIdentityInventory") == CONSUMED_IDENTITIES, "consumed identity inventory changed")

    findings = snapshot.get("findings", {})
    must(findings.get("candidateOrdinalCollisions") == [], "candidate ordinal collision found")
    for key in (
        "candidateExecutionKeyCollisions",
        "authorizationRefCollisions",
        "runTitleCollisions",
        "branchPathCollisions",
        "authorizationFilePathCollisions",
        "wave1SeedCollisions",
    ):
        must(findings.get(key) == [], f"unexpected {key}")
    must(
        [item["authorizationOrdinal"] for item in CONSUMED_IDENTITIES] == list(range(1, 8)),
        "repository-global consumed ordinal inventory incomplete",
    )
    must(
        CANDIDATE["authorizationOrdinal"]
        not in {item["authorizationOrdinal"] for item in CONSUMED_IDENTITIES},
        "candidate ordinal already consumed",
    )

    return {
        "schemaVersion": 1,
        "status": "CANDIDATE_NO_COLLISION_FOUND_REVIEW_ONLY",
        "source": {
            "repository": "search-maker/twilight-mystic-experiments",
            "mainSha": MAIN,
            "mergedWave1HeadSha": WAVE1_HEAD,
            "preregistrationRawSha256": sha(prereg_raw),
            "disabledTemplateRawSha256": sha(template_raw),
            "duplicateSnapshotRawSha256": sha(snapshot_raw),
        },
        "scope": {
            "geometryCount": 20,
            "blocks": [3, 4],
            "caseCount": 40,
            "maximumConfiguredPhotonHistories": 5_100_000_000,
            "roleCounts": prereg["roleCounts"],
            "preservation": prereg["preservation"],
        },
        "wave1Seeds": wave,
        "seedProof": proof,
        "governance": {
            "ordinalScope": "REPOSITORY_GLOBAL_SINGLE_USE",
            "decisionState": "MYSTIC-STATE-0018",
            "decisionCommentId": 5194734813,
        },
        "consumedIdentityInventory": CONSUMED_IDENTITIES,
        "candidateIdentity": CANDIDATE,
        "candidateDecision": {
            "allocated": False,
            "reserved": False,
            "authorizationRefCreated": False,
            "dispatchEnabled": False,
            "candidateOrdinalCollisions": [],
            "reason": "no collision was found for candidate ordinal 8 in the accessible repository-wide review; this is not an allocation, reservation, or authorization",
        },
        "authoritativeIdentity": {
            "authorizationOrdinal": None,
            "executionKey": None,
            "authorizationRef": None,
            "authorizationCommit": None,
            "runTitle": None,
            "enabled": False,
            "dispatch": False,
            "workflowDispatchEnabled": False,
            "solverExecutionAuthorized": False,
        },
        "duplicateSearch": {
            "checkedDimensions": sorted(DIMS),
            "sources": snapshot.get("sources", []),
            "findings": findings,
        },
        "boundary": "candidate-only review; no allocation, authorization ref, dispatch, solver execution, retry, training, holdout opening, Tier-2, or production action",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--authorization-template", type=Path, required=True)
    parser.add_argument("--duplicate-snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            build(args.preregistration, args.authorization_template, args.duplicate_snapshot),
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
