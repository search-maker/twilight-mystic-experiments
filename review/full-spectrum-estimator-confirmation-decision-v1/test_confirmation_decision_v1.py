#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
VALIDATOR = HERE / 'validate_confirmation_decision_v1.py'
DECISION = HERE / 'full-spectrum-estimator-confirmation-decision-v1.json'
ANALYSIS_FIXTURE = HERE / 'test-fixtures/confirmation-analysis-v1.json'


def run(analysis: dict, decision: dict) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as temp_dir:
        analysis_path = Path(temp_dir) / 'analysis.json'
        decision_path = Path(temp_dir) / 'decision.json'
        analysis_path.write_text(json.dumps(analysis, indent=2, sort_keys=True) + '\n')
        decision_path.write_text(json.dumps(decision, indent=2, sort_keys=True) + '\n')
        return subprocess.run(
            [
                'python3', str(VALIDATOR),
                '--analysis', str(analysis_path),
                '--decision', str(decision_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )


def rehash(value: dict, field: str) -> None:
    copy_value = dict(value)
    copy_value[field] = None
    value[field] = hashlib.sha256(
        json.dumps(copy_value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    ).hexdigest()


analysis = json.loads(ANALYSIS_FIXTURE.read_text())
decision = json.loads(DECISION.read_text())
assert run(analysis, decision).returncode == 0

analysis_mutations = []
mutated = copy.deepcopy(analysis); mutated['sourceRunId'] = 1; rehash(mutated, 'analysisSha256'); analysis_mutations.append(mutated)
mutated = copy.deepcopy(analysis); mutated['candidateReports'][0]['classification'] = 'CONFIRMATION_PRECISION_NOT_ESTABLISHED'; rehash(mutated, 'analysisSha256'); analysis_mutations.append(mutated)
mutated = copy.deepcopy(analysis); mutated['holdoutValuesRead'] = True; rehash(mutated, 'analysisSha256'); analysis_mutations.append(mutated)
mutated = copy.deepcopy(analysis); mutated['candidateReports'][-1]['statisticsByPrimaryChannel']['photopicLuminanceCdM2']['anyExactZero'] = False; rehash(mutated, 'analysisSha256'); analysis_mutations.append(mutated)
for mutated in analysis_mutations:
    assert run(mutated, decision).returncode == 2

decision_mutations = []
mutated = copy.deepcopy(decision); mutated['sourceConfirmation']['aggregateJobId'] = 1; rehash(mutated, 'decisionSha256'); decision_mutations.append(mutated)
mutated = copy.deepcopy(decision); mutated['sourceConfirmation']['acquisitionManifestSha256'] = '0' * 64; rehash(mutated, 'decisionSha256'); decision_mutations.append(mutated)
mutated = copy.deepcopy(decision); mutated['decisionSemantics']['globalEstimatorSelected'] = True; rehash(mutated, 'decisionSha256'); decision_mutations.append(mutated)
mutated = copy.deepcopy(decision); mutated['decisionSemantics']['decisionType'] = 'GLOBAL'; rehash(mutated, 'decisionSha256'); decision_mutations.append(mutated)
mutated = copy.deepcopy(decision); mutated['frozenInterpretation']['historicalMaximumAcceptedRsem'] = 0.09; rehash(mutated, 'decisionSha256'); decision_mutations.append(mutated)
mutated = copy.deepcopy(decision); mutated['frozenInterpretation']['candidateDecisions'][0]['confirmationValuesAdmittedAsTrainingLabels'] = True; rehash(mutated, 'decisionSha256'); decision_mutations.append(mutated)
mutated = copy.deepcopy(decision); mutated['frozenInterpretation']['candidateDecisions'][0]['configurationScope'] = 'GLOBAL'; rehash(mutated, 'decisionSha256'); decision_mutations.append(mutated)
mutated = copy.deepcopy(decision); mutated['frozenInterpretation']['candidateDecisions'][0]['currentTrainingTreatment'] = 'ADMIT'; rehash(mutated, 'decisionSha256'); decision_mutations.append(mutated)
mutated = copy.deepcopy(decision); mutated['frozenInterpretation']['candidateDecisions'][1]['futureResolutionOptions'] = []; rehash(mutated, 'decisionSha256'); decision_mutations.append(mutated)
mutated = copy.deepcopy(decision); mutated['frozenInterpretation']['candidateDecisions'] = mutated['frozenInterpretation']['candidateDecisions'][:-1]; rehash(mutated, 'decisionSha256'); decision_mutations.append(mutated)
mutated = copy.deepcopy(decision); mutated['decisionSha256'] = '0' * 64; decision_mutations.append(mutated)
for mutated in decision_mutations:
    assert run(analysis, mutated).returncode == 2

print(f'{len(analysis_mutations) + len(decision_mutations)} mutation refusals + 1 exact pass: PASS')
