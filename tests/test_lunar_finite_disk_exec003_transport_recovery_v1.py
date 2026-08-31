#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / 'review/lunar-scattered-light-source-contract-v1/lunar_finite_disk_exec003_transport_recovery.py'
spec = importlib.util.spec_from_file_location('lunar_fd_exec003_recovery', MODULE)
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

c = mod.validate_contract()
assert c['status'] == 'FROZEN_SOLVER_FREE_RECOVERY_NOT_AUTHORIZED_NOT_DISPATCHED'
assert c['freshExecutionId'] == 'lunar-finite-disk-transfer-kernel-sensitivity-v1-exec003'
assert c['consumedPredecessor']['runId'] == 33350041283
assert c['consumedPredecessor']['preflightJobId'] == 99361464208
assert c['consumedPredecessor']['failure'] == 'TRANSIENT_GITHUB_ACTIONS_RUNS_API_HTTP_502_DURING_REPOSITORY_GLOBAL_SCAN'
assert c['consumedPredecessor']['seedUniverseConsumed'] is True
assert c['frozenScience']['totalDirectionalCases'] == 198
assert c['frozenScience']['photonHistoriesPerDirectionalCase'] == 5_000_000
assert c['frozenScience']['acceptanceThreshold'] is None
assert c['frozenScience']['mandatorySpectralFollowOnNm'] == [450.0, 650.0, 750.0]
assert c['seedPolicy']['exec002SeedsReusable'] is False
assert c['seedPolicy']['freshExec003SeedUniverseRequired'] is True
assert c['seedPolicy']['candidateSeedsAllocatedByThisContract'] is False
assert c['transportRetryPolicy']['scope'] == 'READ_ONLY_GITHUB_REPOSITORY_METADATA_ENUMERATION_ONLY'
assert c['transportRetryPolicy']['maxAttemptsPerMetadataRequest'] == 4
assert c['transportRetryPolicy']['backoffSeconds'] == [2, 5, 10]
assert c['transportRetryPolicy']['githubActionsRunRerun'] is False
assert c['transportRetryPolicy']['solverRetry'] is False
assert all(value is False for value in c['protectedBoundaries'].values())

s = mod.self_test()
assert s['status'] == 'PASS_EXEC003_TRANSPORT_RECOVERY_SELF_TEST'
assert s['maxMetadataRequestAttempts'] == 4
assert s['solverExecuted'] is False
assert s['seedAuthorized'] is False
assert s['resultOpened'] is False

print('lunar finite-disk exec003 transport recovery tests passed')
