from __future__ import annotations

import math
from typing import Any

RIDGES = (1e-6, 1e-5, 1e-4, 1e-3, 1e-2, 1e-1, 1.0, 10.0)
SELECTION_RULE = '2*azLowMale+meanFoldMale+0.25*worstFoldMale+0.1*worstPointError'
SELECTED_BASIS = 'poly2-cos'
SELECTED_RIDGE = 0.001


def folds(records: list[dict[str, Any]], core) -> list[tuple[str, list[int], list[int]]]:
    identities = [int(str(record['geometryId']).split('-')[1]) for record in records]
    raw = [core.feature(record) for record in records]
    result: list[tuple[str, list[int], list[int]]] = []
    for residue in (1, 2, 3, 4):
        validation = [position for position, identity in enumerate(identities)
                      if identity % 5 == residue]
        result.append((f'mod5-{residue}',
                       [position for position in range(len(records))
                        if position not in validation], validation))
    for residue in range(5):
        validation = [position for position, identity in enumerate(identities)
                      if identity % 7 == residue]
        if len(validation) >= 4:
            result.append((f'mod7-{residue}',
                           [position for position in range(len(records))
                            if position not in validation], validation))
    boundaries = (
        ('az-low', lambda row: row[2] <= 60.0),
        ('az-high', lambda row: row[2] >= 150.0),
        ('sun-late', lambda row: row[0] >= 14.0),
        ('sun-early', lambda row: row[0] <= 5.0),
    )
    for name, predicate in boundaries:
        validation = [position for position, row in enumerate(raw) if predicate(row)]
        fitting = [position for position in range(len(records))
                   if position not in validation]
        if not validation or not fitting:
            raise core.Refusal(f'boundary fold empty: {name}')
        result.append((name, fitting, validation))
    expected = ['mod5-1', 'mod5-2', 'mod5-3', 'mod5-4',
                'mod7-0', 'mod7-1', 'mod7-2', 'mod7-3', 'mod7-4',
                'az-low', 'az-high', 'sun-late', 'sun-early']
    if [name for name, _, _ in result] != expected:
        raise core.Refusal('training-only fold universe changed')
    return result


def evaluate_candidate(records: list[dict[str, Any]], basis_name: str,
                       ridge: float, core) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for name, fitting_indices, validation_indices in folds(records, core):
        fitting = [records[index] for index in fitting_indices]
        validation = [records[index] for index in validation_indices]
        model = core.fit(fitting, basis_name, ridge)
        errors = [abs(core.predict_log(model, record) - core.target(record))
                  for record in validation]
        rows.append({
            'fold': name, 'count': len(validation),
            'meanAbsoluteLogError': sum(errors) / len(errors),
            'maximumAbsoluteLogError': max(errors),
            'withinFactorTwoCount': sum(error <= math.log(2.0) for error in errors),
        })
    low = next(row for row in rows if row['fold'] == 'az-low')
    mean_fold = sum(row['meanAbsoluteLogError'] for row in rows) / len(rows)
    worst_fold = max(row['meanAbsoluteLogError'] for row in rows)
    worst_point = max(row['maximumAbsoluteLogError'] for row in rows)
    score = 2.0 * low['meanAbsoluteLogError'] + mean_fold + 0.25 * worst_fold + 0.1 * worst_point
    return {
        'basis': basis_name, 'ridge': ridge,
        'columnCount': len(core.BASIS_FUNCTIONS[basis_name](core.feature(records[0]))),
        'selectionScore': score,
        'meanFoldMeanAbsoluteLogError': mean_fold,
        'worstFoldMeanAbsoluteLogError': worst_fold,
        'worstPointAbsoluteLogError': worst_point,
        'azimuthLowFold': low, 'folds': rows,
    }


def select(records: list[dict[str, Any]], core) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    candidates = [evaluate_candidate(records, basis_name, ridge, core)
                  for basis_name in core.BASIS_FUNCTIONS for ridge in RIDGES]
    candidates.sort(key=lambda row: (row['selectionScore'], row['columnCount'],
                                     row['ridge'], row['basis']))
    selected = candidates[0]
    if selected['basis'] != SELECTED_BASIS or selected['ridge'] != SELECTED_RIDGE:
        raise core.Refusal(
            f"training-only selection changed: {selected['basis']} {selected['ridge']}"
        )
    return selected, candidates
