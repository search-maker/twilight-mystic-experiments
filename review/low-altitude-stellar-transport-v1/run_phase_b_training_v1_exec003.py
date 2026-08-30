#!/usr/bin/env python3
"""Governance-clean exec003 launcher for frozen LOWALT-STELLAR-STATE-0001 Phase-B training.

Exec001 and exec002 are preserved as non-admissible provenance. This launcher
changes no scientific design: it imports the original reviewed Phase-B training
controller, binds a fresh execution identity, and adds recovery provenance only.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE_PATH = HERE / "run_phase_b_training_v1.py"
SPEC = importlib.util.spec_from_file_location("low_altitude_phase_b_training_v1_frozen_base_exec003", BASE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load frozen Phase-B training controller")
base = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(base)

EXECUTION_ID = "low-altitude-stellar-phase-b-training-v1-exec003"
ORIGINAL_EXECUTION_ID = "low-altitude-stellar-phase-b-training-v1-exec001"
EXEC002_ID = "low-altitude-stellar-phase-b-training-v1-exec002"
COORDINATOR_CORRECTION_ISSUE60_COMMENT_ID = 5468736357
EXEC002_CLASSIFICATION_ISSUE60_COMMENT_ID = 5468770998
EXEC001_CLASSIFICATION = "LOWALT_PHASE_B_EXEC001_CONSUMED_NOT_ADMISSIBLE_FENCE_AND_DUPLICATE_TRIGGER"
EXEC002_CLASSIFICATION = "LOWALT_PHASE_B_EXEC002_CONSUMED_NOT_ADMISSIBLE_DUPLICATE_TRIGGER"

if base.EXECUTION_ID != ORIGINAL_EXECUTION_ID:
    raise RuntimeError("frozen predecessor execution identity drift")

base.EXECUTION_ID = EXECUTION_ID
_base_review_ledger = base.review_ledger


def recovery_review_ledger():
    ledger = _base_review_ledger()
    if ledger.get("executionId") != EXECUTION_ID:
        raise RuntimeError("exec003 identity did not bind into frozen controller")
    ledger.update({
        "recoveryIdentityOnly": True,
        "recoveryFromExecutionIds": [ORIGINAL_EXECUTION_ID, EXEC002_ID],
        "predecessorClassifications": [EXEC001_CLASSIFICATION, EXEC002_CLASSIFICATION],
        "coordinatorCorrectionIssue60CommentId": COORDINATOR_CORRECTION_ISSUE60_COMMENT_ID,
        "exec002ClassificationIssue60CommentId": EXEC002_CLASSIFICATION_ISSUE60_COMMENT_ID,
        "predecessorNumericalOutputAdmissible": False,
        "protectedValidationRemainsClosed": True,
        "scientificDesignChangedFromFrozenPhaseB": False,
        "dispatchTransportChangedOnly": True,
    })
    return ledger


base.review_ledger = recovery_review_ledger


def main() -> int:
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
