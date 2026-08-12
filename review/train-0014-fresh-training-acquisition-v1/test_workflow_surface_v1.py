#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path

FORBIDDEN_TEXT = (
    'workflow_dispatch:', 'schedule:', 'uvspec', 'rubin-libradtran',
    'setup-micromamba', '--allow-execution',
)

def strip_comment(line: str) -> str:
    return line.split('#', 1)[0].rstrip()

def child_keys_under_top_level(text: str, parent: str) -> list[str]:
    start = None
    lines = text.splitlines()
    for i, raw in enumerate(lines):
        if strip_comment(raw) == parent + ':':
            if start is not None:
                raise AssertionError(f'duplicate top-level {parent}')
            start = i
    if start is None:
        raise AssertionError(f'missing top-level {parent}')
    keys: list[str] = []
    for raw in lines[start+1:]:
        line = strip_comment(raw)
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(' '))
        if indent == 0:
            break
        if indent == 2 and line.strip().endswith(':'):
            keys.append(line.strip()[:-1])
    return keys

def validate(text: str) -> None:
    triggers = child_keys_under_top_level(text, 'on')
    if triggers != ['pull_request']:
        raise AssertionError(f'workflow triggers must be exactly pull_request, got {triggers!r}')
    lower = text.lower()
    for token in FORBIDDEN_TEXT:
        if token in lower:
            raise AssertionError(f'forbidden execution surface token: {token}')
    if 'permissions:\n  contents: read\n  actions: read' not in text:
        raise AssertionError('read-only permission surface drift')

def refuse(text: str) -> None:
    try: validate(text)
    except AssertionError: return
    raise AssertionError('unsafe mutation accepted')

def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument('--workflow',type=Path,required=True); a=p.parse_args()
    text=a.workflow.read_text(); validate(text)
    mutations=[
        text.replace('  pull_request:', '  push:\n    branches: [main]\n  pull_request:', 1),
        text.replace('  pull_request:', '  workflow_dispatch:\n  pull_request:', 1),
        text.replace('  pull_request:', '  schedule:\n    - cron: "0 0 * * *"\n  pull_request:', 1),
        text + '\njobs:\n  unsafe:\n    steps:\n      - run: uvspec < input\n',
        text.replace('      - uses: actions/setup-python@v5', '      - uses: mamba-org/setup-micromamba@v2\n      - uses: actions/setup-python@v5', 1),
    ]
    for m in mutations: refuse(m)
    print('PR-only no-solver workflow surface: 1 exact pass + 5 mutation refusals: PASS')
    return 0
if __name__=='__main__': raise SystemExit(main())
