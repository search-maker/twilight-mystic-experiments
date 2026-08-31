from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / 'review' / 'lunar-scattered-light-source-contract-v1' / 'lunar-finite-disk-exec003-science-workflow-v1.yml'
RUNTIME = ROOT / 'review' / 'lunar-scattered-light-source-contract-v1' / 'lunar_finite_disk_exec003.py'


def require(text: str, token: str) -> None:
    assert token in text, token


def load_runtime():
    spec = importlib.util.spec_from_file_location('lunar_fd_exec003_science_review', RUNTIME)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def require_flat_artifact_downloads(text: str) -> None:
    lines = text.splitlines()
    ids = [i for i, line in enumerate(lines) if line.strip().startswith('artifact-ids:')]
    assert len(ids) == 4, ids
    for i in ids:
        block = '\n'.join(lines[i:i + 9])
        assert 'merge-multiple: true' in block, block


def main() -> None:
    text = WORKFLOW.read_text(encoding='utf-8')
    runtime_text = RUNTIME.read_text(encoding='utf-8')
    runtime = load_runtime()
    c = runtime.review_contract()

    assert c['status'] == 'FROZEN_EXEC003_SCIENCE_RUNTIME_REVIEW_ONLY_NOT_AUTHORIZED'
    assert c['executionId'] == 'lunar-finite-disk-transfer-kernel-sensitivity-v1-exec003'
    assert c['control']['run'] == 33362571300
    assert c['control']['artifact'] == 9747665530
    assert c['control']['candidateSeedCount'] == 198
    assert c['control']['seedCanonicalSha256'] == 'e27ba17758a6111da3b791535fff2a46d4e06a04fb163b546c871d455370ab44'
    assert c['control']['rowsCanonicalSha256'] == 'ad13f6645d6db0621af78c2434c3a0c9f82b09850def79d051175d4a6cb814d5'
    assert c['authorizationTimeRecheck']['head'] == 'f0131389c2195d61bd55b91cf03748dfd4c0da97'
    assert c['authorizationTimeRecheck']['run'] == 33380238826
    assert c['authorizationTimeRecheck']['artifact'] == 9754092951
    assert c['authorizationTimeRecheck']['proofSha256'] == '0c5d40e6fc2431cdce24419b87631da21048ce6ab9a2e0e3859a4e38c2c84bb9'
    science = c['frozenScience']
    assert (science['wavelengthNm'], science['geometryCount'], science['directionsPerGeometry'], science['totalDirectionalCases']) == (550.0, 6, 33, 198)
    assert science['photonHistoriesPerDirectionalCase'] == 5_000_000
    assert science['totalPhotonHistories'] == 990_000_000
    assert science['acceptanceThreshold'] is None
    assert science['mandatorySpectralFollowOnNm'] == [450.0, 650.0, 750.0]
    assert all(value is False for value in c['protectedBoundaries'].values())

    # Review branch cannot self-authorize merely because runtime/workflow bytes exist.
    assert not runtime.AUTH_PATH.exists()
    try:
        runtime.load_authorization()
    except runtime.Exec003Error as exc:
        assert 'authorization file absent' in str(exc)
    else:
        raise AssertionError('missing exec003 authorization must fail closed')

    require(text, 'execution/lunar-finite-disk-transfer-kernel-sensitivity-v1-exec003')
    require(text, "CONTROL_RUN_ID: '33362571300'")
    require(text, "CONTROL_ARTIFACT_ID: '9747665530'")
    require(text, 'e27ba17758a6111da3b791535fff2a46d4e06a04fb163b546c871d455370ab44')
    require(text, 'ad13f6645d6db0621af78c2434c3a0c9f82b09850def79d051175d4a6cb814d5')
    require(text, 'V5_HEAD: f0131389c2195d61bd55b91cf03748dfd4c0da97')
    require(text, "V5_RUN_ID: '33380238826'")
    require(text, "V5_ARTIFACT_ID: '9754092951'")
    require(text, 'FENCE_STAGE: LUNAR_FINITE_DISK_EXEC003_FINAL_PREFLIGHT_GLOBAL_SCAN_V1')
    require(text, 'matrix:\n        shard: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17]')
    require(text, 'test "$(wc -l < work/shard-case-paths.txt)" -eq 11')
    require(text, 'rubin-libradtran=2.0.6=py312pl5321he9373c2_1')
    require(text, 'lunar_finite_disk_exec003.py prepare-shard')
    require(text, 'lunar_finite_disk_exec003.py evaluate')
    require(text, 'merge-multiple: true')
    require_flat_artifact_downloads(text)

    preflight = text.index('Fresh final repository-global collision recheck before any solver')
    solver = text.index('uses: mamba-org/setup-micromamba@v2')
    assert preflight < solver
    require(text, 'snapshot-fence-release:')
    require(text, 'WRITE_QUIET_END')
    require(text, "'executionIdentityAndCandidateSeedsConsumedByThisAttempt':True")
    require(text, 'repository_global_seed_scan_hardening.py')
    require(text, 'request_with_bounded_transport_retry')
    require(text, "p['finiteMoonDiskValidated'] is False")
    require(text, "p['empiricalAtmosphericMoonlightValidated'] is False")
    require(text, "p['totalSkyValidated'] is False")
    require(text, "p['productionAuthorized'] is False")
    assert 'acceptanceThreshold=' not in text
    assert 'Taylor' in text and 'Jerusalem' in text

    require(runtime_text, "status': 'FROZEN_EXEC003_SCIENCE_RUNTIME_REVIEW_ONLY_NOT_AUTHORIZED'")
    require(runtime_text, 'AUTHORIZED_ONE_SHOT_ATTEMPT1_ONLY_AFTER_V6_SOLVER_FREE_REVIEW')
    require(runtime_text, 'PASS_LUNAR_FINITE_DISK_EXEC003_SCIENCE_WORKFLOW_V6_SOLVER_FREE')
    require(runtime_text, "report['authorizationTimeRecheckArtifactId'] = V5_ARTIFACT")
    require(runtime_text, "report['scienceWorkflowReviewArtifactId']")
    assert '30350e6986b554d09bcd77e9095cb871dd634a80a4f219cca29d0fc0b8249e84' not in runtime_text
    assert '32910001' not in runtime_text

    print('lunar finite-disk exec003 science workflow contract tests passed')


if __name__ == '__main__':
    main()
