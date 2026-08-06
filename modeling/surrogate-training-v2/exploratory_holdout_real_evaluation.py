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

CLAIM_NAME = 'surrogate-training-v2-exploratory-holdout-opening-claim-v1'
MODEL_HASH = '381323604143498619cec494d221747d0d32f37a7e7cbb811b0154b6b4f68848'
PROTOCOL_SHA256 = 'f8fe9d486679ef1c9179ed08c790da987bc838cd952effcdebb33862f57d8f69'
ANALYSES = (
    {'label':'ordinal12-analysis','artifactId':8954776553,'name':'tier1-wave2-ordinal12-analysis','runId':31065046524,'headSha':'18a5746778441d57b722c740a17c94af9b56e9c9','zipSha256':'bd60e2ff433aa104ab84a4497310737d0b0d4695c8d454ad125d91f94efabe37','output':'ordinal12-analysis.json'},
    {'label':'ordinal13-analysis','artifactId':8956922604,'name':'tier1-wave3-ordinal13-analysis','runId':31070968611,'headSha':'6c22de3578b1b0dcbc640779baa66be8d1051fe1','zipSha256':'00fe0cecf2cef26d7438786fc9ddb249b4f804f02b8eade48dc1f2744b45dc07','output':'ordinal13-analysis.json'},
)
CASES = (
    (8949754216,'tier1-wave1-ordinal11-case-train-0015-precision-continuation-v5-b3',31052639692,'5b28ea31649f2c37e8b56ddae893a57608c2e148','37862d942348dc05927219d17371b6c3290de06afb077de75af4ddc3bd7cc297','wave1'),
    (8949758979,'tier1-wave1-ordinal11-case-train-0015-precision-continuation-v5-b4',31052639692,'5b28ea31649f2c37e8b56ddae893a57608c2e148','69208c55c48670e0a913dc5cb5d8342da9381a998fdb6fc57e2168a8782a5ebb','wave1'),
    (8950110684,'tier1-wave1-ordinal11-case-train-0035-precision-continuation-v5-b3',31052639692,'5b28ea31649f2c37e8b56ddae893a57608c2e148','7990911b7937f716f2520b5d4627fe5142a5524121fc708f10ccf95e48220952','wave1'),
    (8950120351,'tier1-wave1-ordinal11-case-train-0035-precision-continuation-v5-b4',31052639692,'5b28ea31649f2c37e8b56ddae893a57608c2e148','6cd770031e04aee027c10cf167cf433bef1c6818d4e976275e0ec82bd1183a43','wave1'),
    (8950441522,'tier1-wave1-ordinal11-case-train-0045-precision-continuation-v5-b3',31052639692,'5b28ea31649f2c37e8b56ddae893a57608c2e148','b6548c7bf211469d2de64871de826400ecf7b7bfb3ebd54f9b8da54b193cdffe','wave1'),
    (8950470337,'tier1-wave1-ordinal11-case-train-0045-precision-continuation-v5-b4',31052639692,'5b28ea31649f2c37e8b56ddae893a57608c2e148','8e334c30a06e0ea6ec4e544c346192ad5c96d800b70dfe543d26062978995e05','wave1'),
    (8954045616,'tier1-wave2-ordinal12-case-train-0015-precision-continuation-wave2-v1-b5',31065046524,'18a5746778441d57b722c740a17c94af9b56e9c9','da6180e714e3c0385d94c75f974ec2a16bf393ab6bf7bc2dcfc78888398a5183','wave2'),
    (8953942670,'tier1-wave2-ordinal12-case-train-0015-precision-continuation-wave2-v1-b6',31065046524,'18a5746778441d57b722c740a17c94af9b56e9c9','92ba9a491ca831b5cf505e94be922117304cb910b10a2e1c283f5dce0e9e51e7','wave2'),
    (8954198983,'tier1-wave2-ordinal12-case-train-0035-precision-continuation-wave2-v1-b5',31065046524,'18a5746778441d57b722c740a17c94af9b56e9c9','42ab324674852a988519ab223c159ba69177f0212b3c8dab3791b82bbb9bb76c','wave2'),
    (8954244409,'tier1-wave2-ordinal12-case-train-0035-precision-continuation-wave2-v1-b6',31065046524,'18a5746778441d57b722c740a17c94af9b56e9c9','80f6290e0b56affeec93cd6548f4c849e1318f8b53feb9c6390e111a56413725','wave2'),
    (8956033959,'tier1-wave3-ordinal13-case-train-0015-precision-continuation-wave3-v1-b7',31070968611,'6c22de3578b1b0dcbc640779baa66be8d1051fe1','a0c90dfcfa9a7fa65b66ff46dee7e6e5964471df9742d346ace04284fe11c5b6','wave3'),
    (8955959835,'tier1-wave3-ordinal13-case-train-0015-precision-continuation-wave3-v1-b8',31070968611,'6c22de3578b1b0dcbc640779baa66be8d1051fe1','dc8e681930c617d70f83500036f8e2af1b378c0f59ba1b84f736682e1295ae51','wave3'),
    (8956281656,'tier1-wave3-ordinal13-case-train-0035-precision-continuation-wave3-v1-b7',31070968611,'6c22de3578b1b0dcbc640779baa66be8d1051fe1','e5a03f2f040549d5b32bcd773c02953a99e6aa1a34078db19cb5497a4b8d0883','wave3'),
    (8956253169,'tier1-wave3-ordinal13-case-train-0035-precision-continuation-wave3-v1-b8',31070968611,'6c22de3578b1b0dcbc640779baa66be8d1051fe1','c94575c465ebc29c1b8d906029804a2ab7ddc140a6708f53c2e16b3be3ae1217','wave3'),
)

class Refusal(RuntimeError):
    pass

class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected is not None and urllib.parse.urlparse(req.full_url).netloc != urllib.parse.urlparse(newurl).netloc:
            redirected.remove_header('Authorization')
        return redirected

def canonical(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()

def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n'

def module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise Refusal(f'module unavailable: {path}')
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value

def client(repository: str, token: str):
    api_root = f'https://api.github.com/repos/{repository}'
    headers = {'Accept':'application/vnd.github+json','Authorization':f'Bearer {token}','X-GitHub-Api-Version':'2022-11-28','User-Agent':'surrogate-training-v2-holdout-once'}
    opener = urllib.request.build_opener(SafeRedirect())
    def request(url: str) -> bytes:
        with opener.open(urllib.request.Request(url, headers=headers), timeout=90) as response:
            return response.read()
    def api_json(url: str) -> dict[str, Any]:
        value = json.loads(request(url))
        if not isinstance(value, dict):
            raise Refusal(f'expected GitHub object: {url}')
        return value
    return api_root, request, api_json

def assert_no_prior_claim(repository: str, token: str) -> None:
    api_root, _, api_json = client(repository, token)
    encoded = urllib.parse.quote(CLAIM_NAME, safe='')
    value = api_json(f'{api_root}/actions/artifacts?name={encoded}&per_page=100')
    artifacts = [row for row in value.get('artifacts', []) if isinstance(row, dict) and not row.get('expired')]
    if artifacts:
        identities = [(row.get('id'), row.get('workflow_run', {}).get('id')) for row in artifacts]
        raise Refusal(f'internal holdout opening already claimed: {identities}')

def download_exact(api_root, request, api_json, spec: dict[str, Any]) -> bytes:
    metadata = api_json(f"{api_root}/actions/artifacts/{spec['artifactId']}")
    workflow = metadata.get('workflow_run', {})
    if metadata.get('name') != spec['name'] or workflow.get('id') != spec['runId'] or workflow.get('head_sha') != spec['headSha']:
        raise Refusal(f"artifact identity changed: {spec['artifactId']}")
    data = request(metadata['archive_download_url'])
    digest = hashlib.sha256(data).hexdigest()
    if digest != spec['zipSha256'] or metadata.get('digest', '').removeprefix('sha256:') != spec['zipSha256']:
        raise Refusal(f"artifact ZIP digest changed: {spec['artifactId']}")
    return data

def one_member(data: bytes, suffix: str, label: str) -> bytes:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        members = [name for name in archive.namelist() if name.endswith(suffix)]
        if len(members) != 1:
            raise Refusal(f'{label} member universe changed: {members}')
        return archive.read(members[0])

def evaluate_once(repository: str, token: str, repository_root: Path, work_root: Path, output_root: Path, head_sha: str, base_sha: str, run_id: int, run_attempt: int) -> dict[str, Any]:
    if run_attempt != 1:
        raise Refusal('GitHub Re-run is forbidden')
    api_root, request, api_json = client(repository, token)
    work_root.mkdir(parents=True, exist_ok=False)
    output_root.mkdir(parents=True, exist_ok=True)
    inventory: dict[str, str] = {}
    analysis_paths: dict[str, Path] = {}
    for spec in ANALYSES:
        data = download_exact(api_root, request, api_json, spec)
        inventory[spec['name']] = spec['zipSha256']
        path = work_root / spec['output']
        path.write_bytes(one_member(data, 'analysis.json', spec['label']))
        analysis_paths[spec['label']] = path
    roots = {name: work_root / name for name in ('wave1','wave2','wave3')}
    for root in roots.values():
        root.mkdir()
    for artifact_id, name, source_run_id, source_head, zip_sha, wave in CASES:
        spec = {'artifactId':artifact_id,'name':name,'runId':source_run_id,'headSha':source_head,'zipSha256':zip_sha}
        data = download_exact(api_root, request, api_json, spec)
        inventory[name] = zip_sha
        member = one_member(data, 'case-result.json', name)
        case_dir = roots[wave] / name
        case_dir.mkdir()
        (case_dir / 'case-result.json').write_bytes(member)
    builder = module(repository_root / 'modeling/surrogate-training-v2/exploratory_holdout_dataset.py', 'holdout_dataset_builder')
    evaluator = module(repository_root / 'modeling/surrogate-training-v2/exploratory_holdout_evaluation.py', 'holdout_evaluator')
    dataset = builder.build(
        repository_root / 'evidence/ordinal2-corrected-v2/tier1-numerical-dataset.json',
        repository_root / 'evidence/ordinal2-corrected-v2/audit-report.json',
        analysis_paths['ordinal12-analysis'], analysis_paths['ordinal13-analysis'],
        roots['wave1'], roots['wave2'], roots['wave3'],
    )
    dataset_path = output_root / 'internal-holdout-dataset.json'
    dataset_path.write_text(builder.dump(dataset), encoding='utf-8', newline='\n')
    result = evaluator.evaluate(
        model_path=repository_root / 'modeling/surrogate-training-v2/evidence/exploratory-training-only-model.json',
        protocol_path=repository_root / 'modeling/surrogate-training-v2/exploratory_holdout_protocol.json',
        holdout_dataset_path=dataset_path,
    )
    (output_root / 'internal-holdout-result.json').write_text(evaluator.dump(result), encoding='utf-8', newline='\n')
    report = {
        'schemaVersion':1,'stageId':'surrogate-training-v2-exploratory-internal-holdout-run-v1','status':result['status'],
        'repository':repository,'headSha':head_sha,'baseSha':base_sha,'runId':run_id,'runAttempt':run_attempt,
        'claimName':CLAIM_NAME,'protocolSha256':PROTOCOL_SHA256,'modelHash':MODEL_HASH,
        'holdoutDatasetSha256':dataset['holdoutDatasetSha256'],'holdoutResultSha256':result['resultSha256'],
        'artifactZipSha256ByName':inventory,'generalizationValidated':result['generalizationValidated'],
        'selectionFromHoldoutForbidden':True,'thresholdTuningFromHoldoutForbidden':True,
        'hardAnchorsOpened':False,'softDiagnosticsOpened':False,'tier2Authorized':False,
        'productionModelReady':False,'productionPromotionAuthorized':False,
    }
    report['reportSha256'] = canonical(report)
    (output_root / 'internal-holdout-run-report.json').write_text(dump(report), encoding='utf-8', newline='\n')
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
    run.add_argument('--work-root', type=Path, required=True)
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
        report = evaluate_once(args.repository,args.token,args.repository_root,args.work_root,args.output_root,args.head_sha,args.base_sha,args.run_id,args.run_attempt)
        return 0 if report['generalizationValidated'] else 3
    except Exception as exc:
        print(dump({'status':'REFUSED','reason':str(exc)}), end='')
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
