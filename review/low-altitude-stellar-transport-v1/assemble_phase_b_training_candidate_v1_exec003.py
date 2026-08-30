#!/usr/bin/env python3
"""Solver-free candidate assembler rebound to the admissible exec003 training identity.

This wrapper changes provenance identity only. The reviewed STATE-0001 candidate
representation, exact v3.2 5-degree seam copying, validation/refusal rules and
serialization remain the implementation in assemble_phase_b_training_candidate_v1.py.
No protected validation data are opened or evaluated here.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE_PATH = HERE / "assemble_phase_b_training_candidate_v1.py"
SPEC = importlib.util.spec_from_file_location("low_altitude_candidate_assembly_v1_frozen_base_exec003", BASE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load frozen candidate assembler")
base = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(base)

ORIGINAL_ASSEMBLY_ID = "low-altitude-stellar-phase-b-training-candidate-v1"
ORIGINAL_TRAINING_EXECUTION_ID = "low-altitude-stellar-phase-b-training-v1-exec001"
ASSEMBLY_ID = "low-altitude-stellar-phase-b-training-candidate-v1-exec003"
TRAINING_EXECUTION_ID = "low-altitude-stellar-phase-b-training-v1-exec003"
EXEC001_GOVERNANCE_INELIGIBLE = True
EXEC002_GOVERNANCE_INELIGIBLE = True
COORDINATOR_CORRECTION_ISSUE60_COMMENT_ID = 5468736357
EXEC002_CLASSIFICATION_ISSUE60_COMMENT_ID = 5468770998

if base.ASSEMBLY_ID != ORIGINAL_ASSEMBLY_ID:
    raise RuntimeError("frozen assembly identity drift")
if base.TRAINING_EXECUTION_ID != ORIGINAL_TRAINING_EXECUTION_ID:
    raise RuntimeError("frozen training identity drift")

# Identity/provenance rebinding only. All assembly science remains in base.
base.ASSEMBLY_ID = ASSEMBLY_ID
base.TRAINING_EXECUTION_ID = TRAINING_EXECUTION_ID


def main() -> int:
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
