from __future__ import annotations
import argparse, io, json, os, re, urllib.request, zipfile
from pathlib import Path
from typing import Any

TOKEN_RE = re.compile(rb'(?<![0-9_])[0-9_]{7,20}(?![0-9_])')


def req(url: str, token: str):
    request = urllib.request.Request(
        url,
        headers={
            'Authorization': f'Bearer {token}',
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28',
        },
    )
    return urllib.request.urlopen(request, timeout=90)


def pages(url: str, token: str, key: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    page = 1
    while True:
        sep = '&' if '?' in url else '?'
        data = json.load(req(f'{url}{sep}per_page=100&page={page}', token))
        rows = data.get(key, [])
        if not isinstance(rows, list):
            raise RuntimeError(f'GitHub response missing list: {key}')
        out.extend(rows)
        if len(rows) < 100:
            return out
        page += 1


def scan_bytes(data: bytes, candidates: set[int], location: dict[str, Any]) -> list[dict[str, Any]]:
    hits = []
    for m in TOKEN_RE.finditer(data):
        text = m.group(0).decode().replace('_', '')
        if text.isdigit() and int(text) in candidates:
            hits.append({**location, 'seed': int(text), 'byteOffset': m.start()})
    return hits


def scan_zip(blob: bytes, candidates: set[int], location: dict[str, Any], depth: int = 0) -> list[dict[str, Any]]:
    if depth > 2:
        return []
    hits: list[dict[str, Any]] = []
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        for name in z.namelist():
            if name.endswith('/'):
                continue
            data = z.read(name)
            member_location = {**location, 'member': name}
            hits.extend(scan_bytes(data, candidates, member_location))
            if data[:4] == b'PK\x03\x04':
                try:
                    hits.extend(scan_zip(data, candidates, {**member_location, 'nestedZip': True}, depth + 1))
                except zipfile.BadZipFile:
                    pass
    return hits


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--repository', required=True)
    ap.add_argument('--candidate-seed-ledger', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--exclude-current-run-id', type=int)
    a = ap.parse_args()
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        raise SystemExit('GITHUB_TOKEN required')

    base = f'https://api.github.com/repos/{a.repository}'
    ledger = json.loads(a.candidate_seed_ledger.read_text())
    seeds = ledger.get('candidateSeeds') if isinstance(ledger, dict) else None
    if not isinstance(seeds, list) or len(seeds) != 72 or len(set(seeds)) != 72:
        raise SystemExit('candidate seed ledger must contain exactly 72 unique seeds')
    candidates = set(seeds)
    all_runs = pages(base + '/actions/runs', token, 'workflow_runs')
    excluded = [r for r in all_runs if a.exclude_current_run_id is not None and int(r.get('id') or 0) == a.exclude_current_run_id]
    runs = [r for r in all_runs if r not in excluded]
    if a.exclude_current_run_id is not None and len(excluded) != 1:
        raise SystemExit('exact current audit run was not uniquely present in Actions run inventory')
    hits: list[dict[str, Any]] = []
    unavailable: list[dict[str, Any]] = []
    artifact_count = 0
    artifact_scanned = 0
    run_log_scanned = 0

    # Scan run metadata itself so seed-like values in names/refs are not silently omitted.
    for run in runs:
        meta = json.dumps({
            'id': run.get('id'),
            'name': run.get('name'),
            'display_title': run.get('display_title'),
            'head_branch': run.get('head_branch'),
            'head_sha': run.get('head_sha'),
            'event': run.get('event'),
        }, sort_keys=True).encode()
        hits.extend(scan_bytes(meta, candidates, {'surface': 'workflow-run-metadata', 'runId': run.get('id')}))

        # Complete run-history proof includes archived job logs, not only uploaded artifacts.
        try:
            log_blob = req(base + f"/actions/runs/{run['id']}/logs", token).read()
            hits.extend(scan_zip(log_blob, candidates, {'surface': 'workflow-run-logs', 'runId': run['id']}))
            run_log_scanned += 1
        except Exception as exc:
            unavailable.append({'runId': run.get('id'), 'surface': 'workflow-run-logs', 'reason': type(exc).__name__})

        try:
            arts = pages(base + f"/actions/runs/{run['id']}/artifacts", token, 'artifacts')
        except Exception as exc:
            unavailable.append({'runId': run.get('id'), 'surface': 'artifact-list', 'reason': type(exc).__name__})
            continue
        for art in arts:
            artifact_count += 1
            if art.get('expired'):
                unavailable.append({'runId': run['id'], 'artifactId': art.get('id'), 'name': art.get('name'), 'surface': 'artifact', 'reason': 'expired'})
                continue
            try:
                blob = req(base + f"/actions/artifacts/{art['id']}/zip", token).read()
                hits.extend(scan_zip(blob, candidates, {'surface': 'artifact', 'runId': run['id'], 'artifactId': art['id'], 'artifactName': art.get('name')}))
                artifact_scanned += 1
            except Exception as exc:
                unavailable.append({'runId': run['id'], 'artifactId': art.get('id'), 'name': art.get('name'), 'surface': 'artifact', 'reason': type(exc).__name__})

    complete = not unavailable and run_log_scanned == len(runs) and artifact_scanned == artifact_count
    out = {
        'workflowRunCountEnumerated': len(all_runs),
        'workflowRunCountScanned': len(runs),
        'excludedCurrentAuditRunId': a.exclude_current_run_id,
        'excludedCurrentAuditRunCount': len(excluded),
        'workflowRunLogCountScanned': run_log_scanned,
        'artifactCountEnumerated': artifact_count,
        'artifactCountScanned': artifact_scanned,
        'expiredOrUnavailableSurfaceCount': len(unavailable),
        'unavailableSurfaces': unavailable,
        'runHistoryCollisionCount': len(hits),
        'hits': hits,
        'completeRunHistoryArtifactAndLogScanPassed': complete and not hits,
    }
    a.output.write_text(json.dumps(out, indent=2, sort_keys=True) + '\n')
    return 0 if out['completeRunHistoryArtifactAndLogScanPassed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
