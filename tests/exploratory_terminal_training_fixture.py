from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ExploratoryTerminalTrainingFixture:
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.model = load(
            cls.root / 'modeling/surrogate-training-v2/exploratory_noisy_label_training_exact.py',
            'exploratory_dataset_model',
        )
        cls.builder = load(
            cls.root / 'modeling/surrogate-training-v2/exploratory_terminal_training_dataset.py',
            'exploratory_dataset_builder',
        )
        cls.exhausted = [
            'train-0003', 'train-0007', 'train-0011', 'train-0013', 'train-0015',
            'train-0019', 'train-0023', 'train-0027', 'train-0029', 'train-0031',
            'train-0035', 'train-0039', 'train-0041', 'train-0043', 'train-0047',
        ]

    def binding(self, analysis_path: Path):
        value = {
            'schemaVersion': 1,
            'stageId': 'surrogate-training-v2-wave3-terminal-source-binding-v1',
            'status': 'AUDITED_THREE_WAVE_SOURCE_BOUND',
            'runId': 31070968611,
            'runAttempt': 1,
            'authorizationRef': '6c22de3578b1b0dcbc640779baa66be8d1051fe1',
            'executionSourceMainSha': 'ae81798f538899b09b6c03c3d6e90ab93458427c',
            'executionManifestSha256': '822fc607d4418835074d53b5990163a46a3d7969d499dcbe5d601c9952aa0958',
            'sourceOrdinal12AnalysisRawSha256': 'c18f9ca23c910924400360ca18c4186d30594bc1aa2d3dd07a43a6031b274237',
            'sourceOrdinal12AnalysisSha256': '8e87fd440d15233dc66543a9ca011535a857b12b5602fd506f6466a900bfafc2',
            'artifactCount': 35,
            'caseArtifactCount': 30,
            'geometryCount': 15,
            'nextWaveGeometryIds': [],
            'scientificallyEligible': False,
            'exhaustedGeometryIds': self.exhausted,
            'aggregateRawSha256': '1' * 64,
            'auditRawSha256': '2' * 64,
            'analysisRawSha256': self.builder.raw_sha256(analysis_path),
            'terminalReportRawSha256': '4' * 64,
            'terminalReportSha256': '5' * 64,
            'additionalExecutionAutomaticallyAuthorized': False,
            'internalHoldoutOpened': False,
            'tier2Authorized': False,
            'productionPromotionAuthorized': False,
        }
        value['bindingSha256'] = self.model.canonical_sha256(value)
        return value

    def source_dataset(self):
        records = []
        for index, gid in enumerate(self.builder.TRAINING_IDS):
            continued = gid in self.builder.CONTINUATION_IDS
            active = gid in self.builder.WAVE3_TRAINING_IDS
            block_count = 6 if continued else 2
            values = [0.001 + index * 1e-6 + block * 1e-7 for block in range(block_count)]
            records.append({
                'geometryId': gid,
                'role': 'surrogate-training',
                'geometry': {
                    'sunDepressionDeg': 1.0 + index * 0.1,
                    'targetAltitudeDeg': 2.0 + index,
                    'relativeAzimuthDeg': 3.0 + index * 2,
                    'observerElevationM': 10.0 + index * 25,
                    'aod550': 0.05 + index * 0.001,
                },
                'caseIds': [f'{gid}-b{block}' for block in range(1, block_count + 1)],
                'classification': 'ADAPTIVE_CONTINUATION_REQUIRED' if active else 'PRECISION_TARGET_MET',
                'numericalStatus': 'NUMERICAL_PRECISION_INSUFFICIENT' if active else 'NUMERICALLY_CONVERGED',
                'executionComplete': True,
                'scientificallyEligible': not active,
                'eligibleForProvisionalFit': not active,
                'statistics': {
                    'blockCount': block_count,
                    'valuesCdM2': values,
                    'meanCdM2': sum(values) / len(values),
                    'sampleStdCdM2': 1e-7,
                    'relativeStandardErrorOfMean': 0.2 if active else 0.01,
                    'relativeStandardErrorStatus': 'COMPUTED',
                    'zeroHitBlockCount': 0,
                    'zeroHitBlockFraction': 0.0,
                    'nonzeroBlockValuesCdM2': values,
                    'nodeMeanRadiance': [1e-5 + index * 1e-8] * 15,
                },
                'zeroHitCaseIds': [],
                'sourceBindings': {},
            })
        value = {
            'schemaVersion': 1,
            'stageId': self.builder.SOURCE_STAGE,
            'status': self.builder.SOURCE_STATUS,
            'trainingGeometryIds': list(self.builder.TRAINING_IDS),
            'internalHoldoutGeometryIdsExcludedAndUnopened': list(self.builder.HOLDOUT_IDS),
            'holdoutRecordCount': 0,
            'holdoutValuesIncluded': False,
            'records': records,
        }
        value['datasetSha256'] = self.builder.canonical_sha256(value)
        return value

    def analysis(self):
        points = []
        for gid in self.builder.CONTINUATION_IDS:
            exhausted = gid in self.exhausted
            values = [0.001 + block * 1e-5 for block in range(8)]
            point = {
                'geometryId': gid,
                'role': 'surrogate-training' if gid in self.builder.TRAINING_IDS else 'internal-holdout',
                'blockCount': 8 if exhausted else 6,
                'capReached': exhausted,
                'classification': 'PRECISION_CONTINUATION_EXHAUSTED' if exhausted else 'PRECISION_ACCEPTED',
                'numericalStatus': 'NUMERICAL_PRECISION_EXHAUSTED' if exhausted else 'NUMERICALLY_ACCEPTED',
                'scientificallyEligible': not exhausted,
                'valuesCdM2': values if exhausted else values[:6],
                'nonzeroBlockValuesCdM2': values if exhausted else values[:6],
                'relativeStandardErrorOfMean': 0.25 if exhausted else 0.05,
                'relativeStandardErrorStatus': 'COMPUTED',
                'zeroHitBlockCount': 0,
                'zeroHitBlockFraction': 0.0,
            }
            if gid in self.builder.HOLDOUT_IDS:
                point['secretHoldoutTargetMustNotReachOutput'] = 987654321.0
            points.append(point)
        return {
            'schemaVersion': 1,
            'stageId': 'tier1-precision-continuation-wave3-analysis-v1',
            'analysis': {
                'status': 'CONTINUATION_ANALYZED',
                'points': points,
                'nextWaveGeometryIds': [],
                'exhaustedGeometryIds': self.exhausted,
                'scientificallyEligible': False,
            },
        }

    def write_results(self, root: Path, analysis: dict):
        point_map = {point['geometryId']: point for point in analysis['analysis']['points']}
        for gid in self.builder.WAVE3_TRAINING_IDS:
            point = point_map[gid]
            for block, offset in ((7, 6), (8, 7)):
                value = float(point['valuesCdM2'][offset])
                base = value / (683.002 * 10.0 * sum(weight / 1000.0 for weight in self.builder.CIE))
                nodes = [base] * 15
                row = {
                    'stageId': self.builder.RESULT_STAGE,
                    'status': 'COMPLETED',
                    'caseId': f'{gid}-precision-continuation-wave3-v1-b{block}',
                    'groupId': gid,
                    'block': block,
                    'role': 'surrogate-training',
                    'selectedNodeRadiance': nodes,
                    'selectedPhotopicContributionCdM2': self.builder._photopic(nodes),
                    'zeroHit': False,
                    'syntaxCheckCount': 1,
                    'solverExecutionCount': 1,
                    'retryAllowed': False,
                    'resumeAllowed': False,
                    'fittingSurfaceExposed': False,
                }
                row['contentSha256'] = self.builder.canonical_sha256(row)
                path = root / gid / f'b{block}' / 'case-result.json'
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(row, sort_keys=True) + '\n')

    def fixture(self, root: Path):
        analysis = self.analysis()
        analysis_path = root / 'analysis.json'
        analysis_path.write_text(json.dumps(analysis, indent=2, sort_keys=True) + '\n')
        binding = self.binding(analysis_path)
        binding_path = root / 'binding.json'
        binding_path.write_text(json.dumps(binding, indent=2, sort_keys=True) + '\n')
        source = self.source_dataset()
        source_path = root / 'source-training.json'
        source_path.write_text(json.dumps(source, indent=2, sort_keys=True) + '\n')
        results = root / 'results'
        self.write_results(results, analysis)
        return source_path, binding_path, analysis_path, results
