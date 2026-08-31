from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / 'review' / 'lunar-scattered-light-source-contract-v1' / 'lunar_finite_disk_exec002.py'
AUTH = ROOT / 'review' / 'lunar-scattered-light-source-contract-v1' / 'lunar-finite-disk-transfer-kernel-sensitivity-v1-exec002-authorization.json'


def load_runtime():
    spec = importlib.util.spec_from_file_location('lunar_fd_exec002_runtime_test', RUNTIME)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> None:
    mod = load_runtime()
    report = mod.validate_runtime_contract()
    assert report['executionId'] == 'lunar-finite-disk-transfer-kernel-sensitivity-v1-exec002'
    assert report['caseCount'] == 198
    assert report['geometryCount'] == 6
    assert report['directionsPerGeometry'] == 33
    assert report['candidateSeedCount'] == 198
    assert report['candidateSeedCanonicalSha256'] == '30350e6986b554d09bcd77e9095cb871dd634a80a4f219cca29d0fc0b8249e84'
    assert report['candidateRowsCanonicalSha256'] == '7dbb4cbe6c34ffad668eb63ad051bd7319d68e56ea1b3c4e540d70eda23b1c95'
    assert report['acceptanceThreshold'] is None
    assert report['mandatorySpectralFollowOnNm'] == [450.0, 650.0, 750.0]
    assert report['solverExecutionPerformed'] is False
    assert report['resultOpened'] is False
    assert report['finiteMoonDiskValidated'] is False
    assert report['productionAuthorized'] is False

    auth = json.loads(AUTH.read_text())
    assert auth['consumedPredecessor']['runId'] == 33303099872
    assert auth['consumedPredecessor']['rerunRetryResumeForbidden'] is True
    assert auth['sourceReview']['authorizationRecheckArtifactId'] == 9740536985
    assert auth['priorFreshnessEvidence']['artifactId'] == 9739969664
    assert auth['resultContract']['mandatorySpectralFollowOnRequiredBeforeAnyBroadbandFiniteDiskAdequacyClaim'] is True
    assert auth['resultContract']['finiteMoonDiskValidatedByThisExecution'] is False
    assert auth['authorization']['dispatchCreated'] is False

    source = RUNTIME.read_text()
    assert 'lunar-finite-disk-transfer-kernel-sensitivity-v1-exec001' in source  # consumed predecessor guard only
    assert 'candidateSeeds' in source
    assert 'seedLiteralsSerializedInManifest' in source
    assert "'seed':" not in source
    assert 'Taylor' not in source and 'Jerusalem' not in source

    print('lunar finite-disk exec002 runtime contract tests passed')


if __name__ == '__main__':
    main()
