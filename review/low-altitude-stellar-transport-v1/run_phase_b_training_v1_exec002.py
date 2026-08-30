#!/usr/bin/env python3
"""Governance-clean exec002 launcher for the frozen LOWALT-STELLAR-STATE-0001 Phase-B training.

This is a mechanical recovery identity only. It delegates every scientific
operation to the already-reviewed Phase-B training controller and changes no
training altitude, observer-elevation knot, AOD knot, wavelength, atmosphere,
solver directive, parser rule, numerical refusal rule, or protected surface.
The predecessor exec001 is preserved as non-admissible diagnostic evidence and
is never retried/resumed/re-run.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE_PATH = HERE / "run_phase_b_training_v1.py"
SPEC = importlib.util.spec_from_file_location("low_altitude_phase_b_training_v1_frozen_base", BASE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load frozen Phase-B training controller")
base = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(base)

EXECUTION_ID = "low-altitude-stellar-phase-b-training-v1-exec002"
PREDECESSOR_EXECUTION_ID = "low-altitude-stellar-phase-b-training-v1-exec001"
PREDECESSOR_CLASSIFICATION = "LOWALT_PHASE_B_EXEC001_CONSUMED_NOT_ADMISSIBLE_FENCE_AND_DUPLICATE_TRIGGER"
GOVERNANCE_CORRECTION_ISSUE60_COMMENT_ID = 5468736357
PROTECTED_VALIDATION_REMAINS_CLOSED = True

if base.EXECUTION_ID != PREDECESSOR_EXECUTION_ID:
    raise RuntimeError("frozen predecessor execution identity drift")

# The only execution-controller mutation permitted by this recovery: bind a
# fresh execution identity. All scientific functions remain the exact base
# implementations imported above.
base.EXECUTION_ID = EXECUTION_ID
_base_review_ledger = base.review_ledger


def recovery_review_ledger():
    ledger = _base_review_ledger()
    if ledger.get("executionId") != EXECUTION_ID:
        raise RuntimeError("exec002 identity did not bind into frozen controller")
    ledger.update({
        "recoveryIdentityOnly": True,
        "recoveryFromExecutionId": PREDECESSOR_EXECUTION_ID,
        "predecessorClassification": PREDECESSOR_CLASSIFICATION,
        "governanceCorrectionIssue60CommentId": GOVERNANCE_CORRECTION_ISSUE60_COMMENT_ID,
        "predecessorNumericalOutputAdmissible": False,
        "protectedValidationRemainsClosed": True,
        "scientificDesignChangedFromFrozenPhaseB": False,
    })
    return ledger


# base.main resolves review_ledger through its own module globals, so install
# the provenance-enriched ledger while leaving execute_campaign untouched.
base.review_ledger = recovery_review_ledger


def main() -> int:
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
