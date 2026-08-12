#!/usr/bin/env python3
from __future__ import annotations
import argparse
import tempfile
from pathlib import Path

FORBIDDEN_TEXT = (
    'workflow_dispatch:', 'schedule:', 'uvspec', 'rubin-libradtran',
    'setup-micromamba', '--allow-execution',
)

def strip_comment(line: str) -> str:
    # The reviewed workflow contains no quoted # characters. This deliberately
    # narrow parser is a structural guard for this exact review surface.
    return line.split('#', 1)[0].rstrip()

def child_keys_under_top_level(text: str, parent: str) -> list[str]:
    lines = text.splitlines()
    start = None
    for i, raw in enumerate(lines):
        line = strip_comment(raw)
        if line == parent + ':':
            if start is not None:
                raise AssertionError(f'duplicate top-level {parent!r}')
            start = i
    if start is None:
        raise AssertionError(f'missing top-level {parent!r}')
    out: list[str] = []
    for raw in lines[start + 1:]:
        line = strip_comment(raw)
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(' '))
        if indent == 0:
            break
        if indent == 2 and line.strip().endswith(':'):
            out.append(line.strip()[:-1])
    return out

def validate(text: str) -> None:
    triggers = child_keys_under_top_level(text, 'on')
    if triggers != ['pull_request']:
        raise AssertionError(f'workflow triggers must be exactly pull_request, got {triggers!r}')
    lowered = text.lower()
    for token in FORBIDDEN_TEXT:
        if token in lowered:
            raise AssertionError(f'forbidden execution surface token: {token}')
    if 'permissions:\n  contents: read\n  actions: read' not in text:
        raise AssertionError('read-only permissions drift')

def expect_refusal(text: str) -> None:
    try:
        validate(text)
    except AssertionError:
        return
    raise AssertionError('unsafe workflow mutation unexpectedly accepted')

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--workflow', type=Path, required=True)
    a = p.parse_args()
    text = a.workflow.read_text()
    validate(text)
    mutations = [
        text.replace('  pull_request:', '  push:\n    branches: [main]\n  pull_request:', 1),
        text.replace('  pull_request:', '  workflow_dispatch:\n  pull_request:', 1),
        text.replace('  pull_request:', '  schedule:\n    - cron: "0 0 * * *"\n  pull_request:', 1),
        text + '\n# mutation\njobs:\n  unsafe:\n    steps:\n      - run: uvspec < input\n',
        text.replace('      - uses: actions/setup-python@v5', '      - uses: mamba-org/setup-micromamba@v2\n      - uses: actions/setup-python@v5', 1),
    ]
    for m in mutations:
        expect_refusal(m)
    print('PR-only zero-runtime workflow surface: 1 exact pass + 5 mutation refusals: PASS')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
