#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path


def block_keys(lines: list[str], header: str, indent: int) -> list[str]:
    marker = (' ' * indent) + header + ':'
    try:
        start = lines.index(marker)
    except ValueError as exc:
        raise AssertionError(f'missing {marker!r}') from exc

    child_indent = indent + 2
    keys: list[str] = []
    for line in lines[start + 1 :]:
        if line and len(line) - len(line.lstrip(' ')) <= indent:
            break
        match = re.match(
            r'^' + (' ' * child_indent) + r'([A-Za-z0-9_-]+):(?:\s*.*)?$',
            line,
        )
        if match:
            keys.append(match.group(1))
    return keys


def scalar_block(lines: list[str], header: str, indent: int) -> dict[str, str]:
    marker = (' ' * indent) + header + ':'
    try:
        start = lines.index(marker)
    except ValueError as exc:
        raise AssertionError(f'missing {marker!r}') from exc

    child_indent = indent + 2
    values: dict[str, str] = {}
    for line in lines[start + 1 :]:
        if line and len(line) - len(line.lstrip(' ')) <= indent:
            break
        match = re.match(
            r'^' + (' ' * child_indent) + r'([A-Za-z0-9_-]+):\s*(\S+)\s*$',
            line,
        )
        if match:
            values[match.group(1)] = match.group(2).strip('"\'')
    return values


def validate_workflow_text(text: str) -> None:
    lines = text.splitlines()

    triggers = block_keys(lines, 'on', 0)
    assert triggers == ['pull_request'], f'expected exact PR-only trigger, got {triggers!r}'

    permissions = scalar_block(lines, 'permissions', 0)
    assert permissions == {'contents': 'read', 'actions': 'read'}, permissions

    jobs = block_keys(lines, 'jobs', 0)
    assert jobs == ['review'], jobs

    forbidden_execution_surface = (
        'workflow_dispatch:',
        'pull_request_target:',
        '\n  push:',
        '\n  schedule:',
        'setup-micromamba',
        'uvspec',
        '--allow-execution',
        'executor_confirmation',
        'run_mystic',
        'train_mystic',
    )
    for token in forbidden_execution_surface:
        assert token not in text, f'forbidden workflow surface: {token}'


def expect_refusal(text: str) -> None:
    try:
        validate_workflow_text(text)
    except AssertionError:
        return
    raise AssertionError('mutated unsafe workflow was unexpectedly accepted')


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--workflow', type=Path, required=True)
    args = parser.parse_args()

    text = args.workflow.read_text()
    validate_workflow_text(text)

    mutations = [
        text.replace('  pull_request:', '  workflow_dispatch:', 1),
        text.replace('on:\n', 'on:\n  push:\n', 1),
        text.replace('  pull_request:', '  pull_request_target:', 1),
        text.replace('  contents: read', '  contents: write', 1),
        text.replace('      - uses: actions/setup-python@v5', '      - uses: mamba-org/setup-micromamba@v2', 1),
    ]
    for mutation in mutations:
        expect_refusal(mutation)

    print('workflow surface: 1 exact pass + 5 unsafe mutation refusals: PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
