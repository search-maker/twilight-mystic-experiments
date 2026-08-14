#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,re
from pathlib import Path
BASE_EXECUTOR_REL=Path('experiments/level-b-v2-densified58-fresh-validation-v1/executor_v1.py')
BASE_EXECUTOR_GIT_BLOB_SHA='5bf0477f0d5100dcb73da8027233e8415ce9021c'
BRANCH_RE=re.compile(r'^dispatch/level-b-v2-densified58-fresh-validation-ordinal27-v1$')
STAGE_ID='LEVEL_B_V2_DENSIFIED58_FRESH_PROTECTED_VALIDATION_EXECUTION_V4_ORDINAL27_RECOVERY'
class Refusal(RuntimeError):pass
def module(n,p):
    s=importlib.util.spec_from_file_location(n,p)
    if s is None or s.loader is None:raise Refusal(f'load failure {p}')
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def main()->int:
    root=Path(__file__).resolve().parents[2];b=module('fv1_executor_for_o27',root/BASE_EXECUTOR_REL);b.BRANCH_RE=BRANCH_RE;b.STAGE_ID=STAGE_ID;return int(b.main())
if __name__=='__main__':raise SystemExit(main())
