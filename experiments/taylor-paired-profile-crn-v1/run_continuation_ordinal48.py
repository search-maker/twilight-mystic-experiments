#!/usr/bin/env python3
from __future__ import annotations
import argparse
import importlib.util
import json
import sys
from pathlib import Path

EXECUTION_KEY = 'taylor-paired-profile-crn-v1:scientific:48-continuation1'
PAIR_BASES = [1531000000, 1532000000, 1533000000, 1534000000]
PAIR_LABELS = [7, 8, 9, 10]
ROW = 26


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location('taylor_ordinal47_frozen_base', path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'cannot import frozen ordinal47 base runner {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def option_value(args, name):
    if name not in args:
        raise RuntimeError(f'missing required forwarded option {name}')
    i = args.index(name)
    if i + 1 >= len(args):
        raise RuntimeError(f'missing value for {name}')
    return args[i + 1]


def main():
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument('--continuation-pair', type=int, required=True, choices=PAIR_LABELS)
    p.add_argument('--base-runner', type=Path, required=True)
    known, rest = p.parse_known_args()
    if '--pair' in rest:
        raise RuntimeError('caller must not pass base-local --pair')
    if int(option_value(rest, '--row')) != ROW:
        raise RuntimeError('continuation is frozen to row26 only')

    local_pair = PAIR_LABELS.index(known.continuation_pair) + 1
    module = load_module(known.base_runner)
    module.EXECUTION_KEY = EXECUTION_KEY
    module.ROWS = [ROW]
    module.PAIR_BASES = PAIR_BASES

    old_argv = sys.argv[:]
    try:
        sys.argv = [old_argv[0], *rest, '--pair', str(local_pair)]
        module.main()
    finally:
        sys.argv = old_argv

    output_dir = Path(option_value(rest, '--output-dir')).resolve()
    result_path = output_dir / 'pair-result.json'
    data = json.loads(result_path.read_text())
    if data.get('executionKey') != EXECUTION_KEY or int(data.get('row')) != ROW or int(data.get('pair')) != local_pair:
        raise RuntimeError('base result identity mismatch before continuation relabel')
    if int(data.get('pairSeedBase')) != PAIR_BASES[local_pair - 1]:
        raise RuntimeError('continuation seed base mismatch')
    data['pair'] = known.continuation_pair
    data['continuationPairLabel'] = known.continuation_pair
    data['continuationLocalPairIndex'] = local_pair
    data['continuationOfExecutionKey'] = 'taylor-paired-profile-crn-v1:scientific:47'
    data['continuationOfScienceRunId'] = 33543818095
    data['selectionReason'] = 'row26 alone failed preregistered paired-delta SE threshold in immutable ordinal47 analysis'
    result_path.write_text(json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + '\n')
    print(json.dumps({'status':'COMPLETED','executionKey':EXECUTION_KEY,'row':ROW,'pair':known.continuation_pair,'pairSeedBase':data['pairSeedBase']}, sort_keys=True))


if __name__ == '__main__':
    main()
