from __future__ import annotations

import importlib.util
import json
import math
import statistics
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    'holdout_builder',
    ROOT / 'modeling/surrogate-training-v2/exploratory_holdout_dataset_exact.py',
)
assert SPEC and SPEC.loader
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


class BuilderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = self.root / 'source.json'
        self.audit = self.root / 'audit.json'
        self.a12 = self.root / 'a12.json'
        self.a13 = self.root / 'a13.json'
        self.w1 = self.root / 'w1'; self.w1.mkdir()
        self.w2 = self.root / 'w2'; self.w2.mkdir()
        self.w3 = self.root / 'w3'; self.w3.mkdir()
        self._make_fixture()

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def nodes(scale):
        return [scale * (index + 1) for index in range(15)]

    @staticmethod
    def value(nodes):
        return m._photopic(nodes)

    def source_record(self, geometry_id, role):
        index = int(geometry_id[-2:])
        nodes1 = self.nodes(1e-7 * (1 + index / 100))
        nodes2 = self.nodes(1.1e-7 * (1 + index / 100))
        values = [self.value(nodes1), self.value(nodes2)]
        return {
            'geometryId': geometry_id,
            'role': role,
            'geometry': {
                'geometryId': geometry_id,
                'sunDepressionDeg': 2.0 + index / 10,
                'targetAltitudeDeg': 5.0 + index,
                'relativeAzimuthDeg': 36.0,
                'observerElevationM': 100.0,
                'aod550': 0.1,
            },
            'caseIds': [geometry_id + '-alis-b1', geometry_id + '-alis-b2'],
            'classification': 'ADAPTIVE_CONTINUATION_REQUIRED' if geometry_id in m.WAVE1_HOLDOUT_IDS else 'PRECISION_TARGET_MET',
            'numericalStatus': 'CONTINUATION_REQUIRED' if geometry_id in m.WAVE1_HOLDOUT_IDS else 'NUMERICALLY_CONVERGED',
            'executionComplete': True,
            'scientificallyEligible': geometry_id not in m.WAVE1_HOLDOUT_IDS,
            'eligibleForProvisionalFit': False,
            'eligibleForInternalHoldout': role == 'internal-holdout',
            'statistics': {
                'blockCount': 2,
                'valuesCdM2': values,
                'meanCdM2': statistics.fmean(values),
                'sampleStdCdM2': statistics.stdev(values),
                'relativeStandardErrorOfMean': 0.05,
                'relativeStandardErrorStatus': 'COMPUTED',
                'zeroHitBlockCount': 0,
                'zeroHitBlockFraction': 0.0,
                'nonzeroBlockValuesCdM2': values,
                'nodeMeanRadiance': [(left + right) / 2 for left, right in zip(nodes1, nodes2, strict=True)],
            },
            'zeroHitCaseIds': [],
            'sourceBindings': {},
        }

    def case(self, geometry_id, block, stage):
        nodes = self.nodes((block + int(geometry_id[-2:])) * 1e-8)
        row = {
            'caseId': f'{geometry_id}-case-b{block}',
            'groupId': geometry_id,
            'block': block,
            'stageId': stage,
            'status': 'COMPLETED',
            'role': 'internal-holdout',
            'syntaxCheckCount': 1,
            'solverExecutionCount': 1,
            'retryAllowed': False,
            'resumeAllowed': False,
            'fittingSurfaceExposed': False,
            'selectedNodeRadiance': nodes,
            'selectedPhotopicContributionCdM2': self.value(nodes),
            'zeroHit': False,
        }
        row['contentSha256'] = m.canonical_sha256(row)
        return row

    def point(self, geometry_id, rows, classification='PRECISION_ACCEPTED'):
        source = next(row for row in self.records if row['geometryId'] == geometry_id)
        values = list(source['statistics']['valuesCdM2']) + [row['selectedPhotopicContributionCdM2'] for row in rows]
        sample_std = statistics.stdev(values)
        mean = statistics.fmean(values)
        return {
            'geometryId': geometry_id,
            'role': 'internal-holdout',
            'blockCount': len(values),
            'valuesCdM2': values,
            'meanCdM2': mean,
            'sampleStdCdM2': sample_std,
            'relativeStandardErrorOfMean': sample_std / math.sqrt(len(values)) / mean,
            'relativeStandardErrorStatus': 'COMPUTED',
            'zeroHitBlockCount': 0,
            'zeroHitBlockFraction': 0.0,
            'nonzeroBlockValuesCdM2': values,
            'classification': classification,
            'numericalStatus': 'NUMERICALLY_CONVERGED_ACCEPTED',
            'scientificallyEligible': classification in m.ELIGIBLE,
        }

    @staticmethod
    def write_case(root, row):
        directory = root / row['caseId']; directory.mkdir()
        (directory / 'case-result.json').write_text(m.dump(row))

    def _make_fixture(self):
        self.records = [
            self.source_record(geometry_id, 'internal-holdout' if geometry_id in m.HOLDOUT_IDS else 'surrogate-training')
            for geometry_id in m.ALL_IDS
        ]
        self.source.write_text(m.dump({
            'schemaVersion': 2,
            'stageId': m.SOURCE_STAGE,
            'status': m.SOURCE_STATUS,
            'executionComplete': True,
            'scientificallyEligible': False,
            'surrogateTrainingAutomaticallyAuthorized': False,
            'records': self.records,
        }))
        self.audit.write_text('{}\n')
        cases = {}
        for geometry_id in m.WAVE1_HOLDOUT_IDS:
            cases[geometry_id] = {}
            for block in (3, 4):
                row = self.case(geometry_id, block, m.WAVE1_STAGE)
                cases[geometry_id][block] = row; self.write_case(self.w1, row)
        for geometry_id in m.WAVE2_HOLDOUT_IDS:
            for block in (5, 6):
                row = self.case(geometry_id, block, m.WAVE2_STAGE)
                cases[geometry_id][block] = row; self.write_case(self.w2, row)
        for geometry_id in m.WAVE3_HOLDOUT_IDS:
            for block in (7, 8):
                row = self.case(geometry_id, block, m.WAVE3_STAGE)
                cases[geometry_id][block] = row; self.write_case(self.w3, row)
        points12 = []
        for geometry_id in m.ORDINAL12_IDS:
            if geometry_id in m.WAVE1_HOLDOUT_IDS:
                rows = [cases[geometry_id][block] for block in (3, 4)]
                if geometry_id in m.WAVE2_HOLDOUT_IDS:
                    rows += [cases[geometry_id][block] for block in (5, 6)]
                point = self.point(geometry_id, rows)
            else:
                point = {'geometryId': geometry_id}
            points12.append(point)
        points13 = []
        for geometry_id in m.ORDINAL13_IDS:
            if geometry_id in m.WAVE3_HOLDOUT_IDS:
                rows = [cases[geometry_id][block] for block in (3, 4, 5, 6, 7, 8)]
                point = self.point(geometry_id, rows, 'PRECISION_CONTINUATION_EXHAUSTED')
                point['numericalStatus'] = 'NUMERICAL_PRECISION_EXHAUSTED'
                point['scientificallyEligible'] = False
            else:
                point = {'geometryId': geometry_id}
            points13.append(point)
        self.a12.write_text(m.dump({'points': points12}))
        self.a13.write_text(m.dump({'points': points13}))
        m.base.SOURCE_DATASET_RAW_SHA256 = m.raw_sha256(self.source)
        m.base.SOURCE_AUDIT_RAW_SHA256 = m.raw_sha256(self.audit)
        m.base.ORDINAL12_ANALYSIS_RAW_SHA256 = m.raw_sha256(self.a12)
        m.base.ORDINAL13_ANALYSIS_RAW_SHA256 = m.raw_sha256(self.a13)

    def build(self):
        return m.build(self.source, self.audit, self.a12, self.a13, self.w1, self.w2, self.w3)

    def test_builds_exact_nine_holdout_records(self):
        value = self.build()
        self.assertEqual(value['holdoutGeometryIds'], list(m.HOLDOUT_IDS))
        self.assertEqual(len(value['records']), 9)
        self.assertEqual(value['blockCountDistribution'], {'2': 6, '4': 1, '8': 2})
        self.assertTrue(all(row['role'] == 'internal-holdout' for row in value['records']))
        payload = {key: item for key, item in value.items() if key != 'holdoutDatasetSha256'}
        self.assertEqual(value['holdoutDatasetSha256'], m.canonical_sha256(payload))

    def test_refuses_case_role_change(self):
        path = next(self.w1.rglob('case-result.json'))
        row = json.loads(path.read_text()); row['role'] = 'surrogate-training'
        row['contentSha256'] = m.canonical_sha256({key: item for key, item in row.items() if key != 'contentSha256'})
        path.write_text(m.dump(row))
        with self.assertRaisesRegex(m.Refusal, 'execution proof changed'):
            self.build()

    def test_refuses_source_role_drift(self):
        source = json.loads(self.source.read_text()); source['records'][4]['role'] = 'surrogate-training'
        self.source.write_text(m.dump(source)); m.base.SOURCE_DATASET_RAW_SHA256 = m.raw_sha256(self.source)
        with self.assertRaisesRegex(m.Refusal, 'role map changed'):
            self.build()

    def test_refuses_analysis_value_drift(self):
        analysis = json.loads(self.a12.read_text())
        point = next(row for row in analysis['points'] if row['geometryId'] == 'train-0015')
        point['valuesCdM2'][-1] *= 2
        self.a12.write_text(m.dump(analysis)); m.base.ORDINAL12_ANALYSIS_RAW_SHA256 = m.raw_sha256(self.a12)
        with self.assertRaisesRegex(m.Refusal, 'value mismatch'):
            self.build()


if __name__ == '__main__':
    unittest.main()
