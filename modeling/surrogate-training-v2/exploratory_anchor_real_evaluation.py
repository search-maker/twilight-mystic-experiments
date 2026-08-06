#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

CLAIM_NAME = 'surrogate-training-v2-exploratory-external-anchor-opening-claim-v2'
MODEL_SPEC = {
    'artifactId': 8969169714,
    'name': 'surrogate-training-v2-exploratory-noisy-label-v2-contract',
    'runId': 31105103370,
    'headSha': 'ca6da420cd7acfbcfad77c4f55eecc78b4e1bdfe',
    'zipSha256': 'b5d64aab87066eea029ef57dcfcfb1e50753a54a848c73641adc2a308ad18a3e',
    'member': 'exploratory-training-only-model-v2.json',
    'memberRawSha256': '2497c0b78f552a03564565e44d2b633828428eda0bc967954f646cfdf1dd0cb5',
}
ANCHOR_SPEC = {
    'artifactId': 8890906227,
    'name': 'twilight-surrogate-tier-1-proposal-v1',
    'runId': 30905632743,
    'headSha': '9ab74efabfd34799aeeb5c9220a84639861f739d',
    'zipSha256': '899507d315ae25db88babb3f610587fca24238e7a7000038eed009c7a14af9a0',
    'member': 'validated-reference-anchors.json',
}
PROTOCOL_SHA256 = '7ddeb3d0c4e29a8e419513339e50925d09a340d8fe86c651ea7f0e7b277b8a77'
MODEL_HASH = 'c75971120e778e9ca85ffec81cdd8aa362fd46be364b436c54ef6cdf2a82bcac'


class Refusal(RuntimeError):
    pass


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected is not None and urllib.parse.urlparse(req.full_url).netloc != urllib.parse.urlparse(newurl).netloc:
            redirected.remove_header('Authorization')
        return redirected


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n'


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    ).hexdigest()


def client(repository: str, token: str):
    root = f'https://api.github.com/repos/{repository}'
    headers = {
        'Accept': 'application/vnd.github+json',
        'Authorization': f'Bearer {token}',
        'X-GitHub-Api-Version': '2022-11-28',
        'User-Agent': 'surrogate-training-v2-anchor-once',
    }
    opener = urllib.request.build_opener(SafeRedirect())

    def request(url: str) -> bytes:
        with opener.open(urllib.request.Request(url, headers=headers), timeout=90) as response:
            return response.read()

    def api_json(url: str) -> dict[str, Any]:
        value = json.loads(request(url))
        if not isinstance(value, dict):
            raise Refusal(f'expected GitHub object: {url}')
        return value

    return root, request, api_json


def assert_no_prior_claim(repository: str, token: str) -> None:
    root, _, api_json = client(repository, token)
    encoded = urllib.parse.quote(CLAIM_NAME, safe='')
    value = api_json(f'{root}/actions/artifacts?name={encoded}&per_page=100')
    rows = [row for row in value.get('artifacts', []) if isinstance(row, dict) and not row.get('expired')]
    if rows:
        raise Refusal(
            'external anchor opening already claimed: '
            + repr([(row.get('id'), row.get('workflow_run', {}).get('id')) for row in rows])
        )


def download_exact(root, request, api_json, spec: dict[str, Any]) -> tuple[bytes, dict[str, Any]]:
    metadata = api_json(f"{root}/actions/artifacts/{spec['artifactId']}")
    workflow = metadata.get('workflow_run', {})
    if (
        metadata.get('name') != spec['name']
        or workflow.get('id') != spec['runId']
        or workflow.get('head_sha') != spec['headSha']
    ):
        raise Refusal(f"artifact identity changed: {spec['artifactId']}")
    data = request(metadata['archive_download_url'])
    digest = hashlib.sha256(data).hexdigest()
    if digest != spec['zipSha256'] or metadata.get('digest', '').removeprefix('sha256:') != spec['zipSha256']:
        raise Refusal(f"artifact ZIP digest changed: {spec['artifactId']}")
    return data, metadata


def exact_member(data: bytes, member: str, label: str) -> bytes:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = archive.namelist()
        matches = [name for name in names if name == member or name.endswith('/' + member)]
        if len(matches) != 1:
            raise Refusal(f'{label} member universe changed: {matches}')
        return archive.read(matches[0])


def load_evaluator(repository_root: Path):
    path = repository_root / 'modeling/surrogate-training-v2/exploratory_anchor_evaluation.py'
    spec = importlib.util.spec_from_file_location('external_anchor_evaluator_v2', path)
    if spec is None or spec.loader is None:
        raise Refusal(f'evaluator unavailable: {path}')
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def evaluate_once(
    *,
    repository: str,
    token: str,
    repository_root: Path,
    output_root: Path,
    head_sha: str,
    base_sha: str,
    run_id: int,
    run_attempt: int,
) -> dict[str, Any]:
    if run_attempt != 1:
        raise Refusal('GitHub Re-run is forbidden')
    output_root.mkdir(parents=True, exist_ok=True)
    root, request, api_json = client(repository, token)
    model_zip, _ = download_exact(root, request, api_json, MODEL_SPEC)
    anchor_zip, _ = download_exact(root, request, api_json, ANCHOR_SPEC)
    model_raw = exact_member(model_zip, MODEL_SPEC['member'], 'model')
    if hashlib.sha256(model_raw).hexdigest() != MODEL_SPEC['memberRawSha256']:
        raise Refusal('model member raw hash changed')
    anchors_raw = exact_member(anchor_zip, ANCHOR_SPEC['member'], 'anchors')
    model_path = output_root / 'exploratory-training-only-model-v2.json'
    anchors_path = output_root / 'validated-reference-anchors.json'
    model_path.write_bytes(model_raw)
    anchors_path.write_bytes(anchors_raw)
    evaluator = load_evaluator(repository_root)
    protocol_path = repository_root / 'modeling/surrogate-training-v2/exploratory_anchor_protocol.json'
    result = evaluator.evaluate(model_path, protocol_path, anchors_path)
    result_path = output_root / 'external-anchor-result-v2.json'
    result_path.write_text(evaluator.dump(result), encoding='utf-8', newline='\n')
    report: dict[str, Any] = {
        'schemaVersion': 1,
        'stageId': 'surrogate-training-v2-exploratory-external-anchor-run-v2',
        'status': result['status'],
        'repository': repository,
        'headSha': head_sha,
        'baseSha': base_sha,
        'runId': run_id,
        'runAttempt': run_attempt,
        'claimName': CLAIM_NAME,
        'protocolSha256': PROTOCOL_SHA256,
        'modelHash': MODEL_HASH,
        'modelArtifactId': MODEL_SPEC['artifactId'],
        'modelArtifactZipSha256': MODEL_SPEC['zipSha256'],
        'anchorArtifactId': ANCHOR_SPEC['artifactId'],
        'anchorArtifactZipSha256': ANCHOR_SPEC['zipSha256'],
        'anchorsRawSha256': hashlib.sha256(anchors_raw).hexdigest(),
        'resultSha256': result['resultSha256'],
        'computationallyValidated': result['computationallyValidated'],
        'generalizationValidated': result['generalizationValidated'],
        'selectionFromAnchorsForbidden': True,
        'thresholdTuningFromAnchorsForbidden': True,
        'observationallyValidated': False,
        'tier2Authorized': False,
        'productionModelReady': False,
        'productionPromotionAuthorized': False,
    }
    report['reportSha256'] = canonical_sha256(report)
    (output_root / 'external-anchor-run-report-v2.json').write_text(
        dump(report), encoding='utf-8', newline='\n'
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)
    check = sub.add_parser('claim-check')
    check.add_argument('--repository', required=True)
    check.add_argument('--token', required=True)
    run = sub.add_parser('evaluate')
    run.add_argument('--repository', required=True)
    run.add_argument('--token', required=True)
    run.add_argument('--repository-root', type=Path, required=True)
    run.add_argument('--output-root', type=Path, required=True)
    run.add_argument('--head-sha', required=True)
    run.add_argument('--base-sha', required=True)
    run.add_argument('--run-id', type=int, required=True)
    run.add_argument('--run-attempt', type=int, required=True)
    args = parser.parse_args()
    try:
        if args.command == 'claim-check':
            assert_no_prior_claim(args.repository, args.token)
            return 0
        report = evaluate_once(
            repository=args.repository,
            token=args.token,
            repository_root=args.repository_root,
            output_root=args.output_root,
            head_sha=args.head_sha,
            base_sha=args.base_sha,
            run_id=args.run_id,
            run_attempt=args.run_attempt,
        )
        return 0 if report['computationallyValidated'] else 3
    except Exception as exc:
        print(dump({'status': 'REFUSED', 'reason': str(exc)}), end='')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
