from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / 'review' / 'lunar-scattered-light-source-contract-v1' / 'lunar-finite-disk-exec002-science-workflow-v1.yml'
RUNTIME = ROOT / 'review' / 'lunar-scattered-light-source-contract-v1' / 'lunar_finite_disk_exec002.py'


def require(text: str, token: str) -> None:
    assert token in text, token


def main() -> None:
    text = WORKFLOW.read_text()
    runtime = RUNTIME.read_text()

    require(text, 'execution/lunar-finite-disk-transfer-kernel-sensitivity-v1-exec002')
    require(text, 'AUTHORIZATION_REVIEW_HEAD: 16efed6164670263bb18d960d76cfb8a42e4a36b')
    require(text, "AUTHORIZATION_REVIEW_RUN_ID: '33342878656'")
    require(text, "AUTHORIZATION_REVIEW_ARTIFACT_ID: '9741082547'")
    require(text, 'sha256:3ae40fa83dd12bd74ad022344dd470f94e75dcfa8e3406bc890b1e5a51a731e9')
    require(text, "AUTHORIZATION_RECHECK_ARTIFACT_ID: '9740536985'")
    require(text, "CONTROL_ARTIFACT_ID: '9739969664'")
    require(text, '30350e6986b554d09bcd77e9095cb871dd634a80a4f219cca29d0fc0b8249e84')
    require(text, '7dbb4cbe6c34ffad668eb63ad051bd7319d68e56ea1b3c4e540d70eda23b1c95')
    require(text, 'FENCE_STAGE: LUNAR_FINITE_DISK_EXEC002_FINAL_PREFLIGHT_GLOBAL_SCAN_V1')

    # Exact scientific size and runtime remain unchanged from the frozen contract.
    require(text, 'matrix:\n        shard: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17]')
    require(text, 'test "$(wc -l < work/shard-case-paths.txt)" -eq 11')
    require(text, 'rubin-libradtran=2.0.6=py312pl5321he9373c2_1')
    require(text, 'lunar_finite_disk_exec002.py prepare-shard')
    require(text, 'lunar_finite_disk_exec002.py evaluate')

    # Historical artifact IDs are bound exactly, and archive retrieval is by immutable ID.
    require(text, 'artifact-ids: ${{ env.AUTHORIZATION_REVIEW_ARTIFACT_ID }}')
    require(text, 'artifact-ids: ${{ env.CONTROL_ARTIFACT_ID }}')
    assert '9741235986' not in text
    assert 'sha256:7f30472329828f90193297129d567c45e8b6dfadcbe83f804c49630c11a530da' not in text

    # The historical page-one release bug must not recur.
    require(text, 'gh api --paginate --slurp "repos/$GITHUB_REPOSITORY/issues/60/comments?per_page=100"')
    require(text, 'require matching paginated WRITE_QUIET_END before solver')

    # Fence BEGIN must bind the actual execution parent, not the older authorization-review head.
    require(text, 'git rev-parse HEAD^ > final-preflight-evidence/execution-parent.txt')
    require(text, 'assert f"parent={parent}" in body(begin)')
    require(text, 'assert f"authorizationReviewHead={os.environ[\'AUTHORIZATION_REVIEW_HEAD\']}" in body(begin)')
    assert 'parent={os.environ[\'AUTHORIZATION_REVIEW_HEAD\']}' not in text

    # Final collision proof precedes solver installation and binds the exact current head.
    preflight = text.index('Fresh final repository-global collision recheck before any solver')
    solver = text.index('uses: mamba-org/setup-micromamba@v2')
    assert preflight < solver
    require(text, '--expected-repo-head "$GITHUB_SHA"')
    require(text, "'executionIdentityAndCandidateSeedsConsumedByThisAttempt':True")

    # The 550-nm execution remains descriptive only and cannot close finite-disk validation.
    require(text, "p['finiteMoonDiskValidated'] is False")
    require(text, "p['mandatorySpectralFollowOnWavelengthsNm']==[450.0,650.0,750.0]")
    require(text, '450/650/750-nm follow-on remains mandatory before broadband finite-disk adequacy.')
    assert 'acceptanceThreshold=' not in text
    assert 'Taylor' in text and 'Jerusalem' in text  # only explicit no-use claim text

    # Runtime must take the seed ledger only as an externally bound artifact; no literal seed list is committed.
    require(runtime, 'load_candidate_ledger')
    require(runtime, 'candidateSeedCanonicalSha256')
    require(runtime, 'seedLiteralsSerializedInManifest')
    require(runtime, 'EXPECTED_AUTH_REVIEW_ARTIFACT_ID = 9741082547')
    assert '9741235986' not in runtime
    assert '32_910_001' not in runtime

    print('lunar finite-disk exec002 science workflow contract tests passed')


if __name__ == '__main__':
    main()
