#!/usr/bin/env python3
from __future__ import annotations
import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("replay", ROOT / "replay_existing_real_artifacts_v1.py")
mod = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(mod)
BASE = json.loads((ROOT / "artifact-pipeline-replay-protocol-v1.json").read_text())
mod.validate_protocol(BASE)

def rehash(d):
    d["protocolSha256"] = None
    d["protocolSha256"] = mod.self_hash_null(d, "protocolSha256")

def mutate(path, value):
    d = copy.deepcopy(BASE); cur = d
    for key in path[:-1]: cur = cur[key]
    cur[path[-1]] = value; rehash(d); return d

mutations = [
    (["decisionSemantics", "newScientificExecutionAuthorized"], True),
    (["decisionSemantics", "campaignAuthorizationIssued"], True),
    (["decisionSemantics", "scientificOrdinalAllocated"], True),
    (["decisionSemantics", "nextScientificOrdinal"], 19),
    (["decisionSemantics", "solverInvocationAllowed"], True),
    (["decisionSemantics", "existingRealArtifactsOnly"], False),
    (["sourceBindings", "liveMainAtFreeze"], "0" * 40),
    (["sourceBindings", "tier2CoreCampaignContractSha256"], "0" * 64),
    (["sourceBindings", "historicalBuilderGitBlobSha"], "0" * 40),
    (["sourceRuns", 0, "runId"], 1),
    (["sourceRuns", 0, "runAttempt"], 2),
    (["sourceRuns", 1, "conclusion"], "success"),
    (["sourceRuns", 2, "headSha"], "0" * 40),
    (["sourceRuns", 3, "expectedTrainingCaseArtifacts"], 27),
    (["trainingReplayUniverse", "trainingCaseArtifactCount"], 165),
    (["trainingReplayUniverse", "internalHoldoutGeometryCountExcluded"], 0),
    (["trainingReplayUniverse", "holdoutValuesMayBeRead"], True),
    (["mustExercise"], mod.MUST_EXERCISE[:-1]),
    (["outputContract", "candidateDoesNotSatisfyReplayGateByItself"], False),
    (["outputContract", "separateVersionedResultBindingPRRequired"], False),
    (["nextBoundary", "scientificExecutionAllowedAfterCandidate"], True),
    (["nextBoundary", "ordinal19AllocationAllowedAfterCandidate"], True),
]
for path, value in mutations:
    bad = mutate(path, value)
    try: mod.validate_protocol(bad)
    except mod.Refusal: pass
    else: raise SystemExit(f"mutation accepted: {path}")
bad = copy.deepcopy(BASE); bad["protocolSha256"] = "0" * 64
try: mod.validate_protocol(bad)
except mod.Refusal: pass
else: raise SystemExit("self-hash tamper accepted")
print(f"PASS: {len(mutations) + 1} fail-closed protocol mutations refused")
