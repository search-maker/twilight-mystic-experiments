#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import re
from pathlib import Path

BASE_EXECUTOR_REL=Path('experiments/level-b-v2-densified58-fresh-validation-v1/executor_v1.py')
BASE_EXECUTOR_GIT_BLOB_SHA='5bf0477f0d5100dcb73da8027233e8415ce9021c'
BRANCH_RE=re.compile(r'^dispatch/level-b-v3-fresh-validation-ordinal28-v1$')
STAGE_ID='LEVEL_B_V3_FRESH_PROTECTED_VALIDATION_EXECUTION_V1_ORDINAL28'

class Refusal(RuntimeError): pass

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise Refusal(f'load failure {path}')
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

def main()->int:
    root=Path(__file__).resolve().parents[2]
    base=module('frozen_v0070_executor_for_v3_o28',root/BASE_EXECUTOR_REL)
    base.BRANCH_RE=BRANCH_RE
    base.STAGE_ID=STAGE_ID
    return int(base.main())

if __name__=='__main__': raise SystemExit(main())
