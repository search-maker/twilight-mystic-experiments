#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE / 'run_pair.py'

spec = importlib.util.spec_from_file_location('taylor_paired_profile_crn_v1_base', BASE)
if spec is None or spec.loader is None:
    raise RuntimeError(f'cannot import frozen base runner {BASE}')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

# Solver-free ordinal46 failed before any profile/runtime materialization because its
# repository seed scan matched digits inside an unrelated decimal.  The science is
# unchanged, but one-shot governance requires a fresh execution identity and seeds.
module.EXECUTION_KEY = 'taylor-paired-profile-crn-v1:scientific:47'
module.PAIR_BASES = [1521000000, 1522000000, 1523000000, 1524000000, 1525000000, 1526000000]

if __name__ == '__main__':
    try:
        module.main()
    except Exception as exc:
        import json
        import sys
        print(json.dumps({'status': 'FAILED', 'stageId': module.STAGE, 'executionKey': module.EXECUTION_KEY, 'error': str(exc)}), file=sys.stderr)
        raise
