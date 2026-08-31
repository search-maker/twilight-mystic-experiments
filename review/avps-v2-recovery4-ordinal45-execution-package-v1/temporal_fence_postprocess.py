#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKFLOW_NAME = 'avps-v2-postconsumption-recovery4-science.yml'
FENCE_PREFIX = 'AVPS_V2_RECOVERY4_ORDINAL45_SNAPSHOT_'
AUTH_HEAD = '6e095b4b1603c90dcee0943295909b30cd1b374d'
DISPATCH_BRANCH = 'dispatch/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery4-ordinal-45'
EXECUTION_KEY = 'aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery4:numerical:45'


def _fields(body: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for token in body.replace('|', ' ').split():
        if '=' in token:
            k, v = token.split('=', 1)
            out[k] = v
    return out


def _first(body: str) -> str:
    return body.strip().splitlines()[0] if body.strip() else ''


def bind_pre_scan_begin(comments: list[dict[str, Any]], *, run_id: int, observed_at: str) -> dict[str, Any]:
    closed: set[int] = set()
    begins: list[tuple[int, dict[str, str], str]] = []
    for c in comments:
        body = str(c.get('body') or '')
        first = _first(body)
        fields = _fields(first)
        if first.startswith('WRITE_QUIET_END') and fields.get('begin', '').isdigit():
            closed.add(int(fields['begin']))
        if first.startswith('WRITE_QUIET_BEGIN'):
            begins.append((int(c['id']), fields, str(c.get('created_at') or '')))
    unmatched = [b for b in begins if b[0] not in closed]
    matching = [b for b in unmatched if (
        b[1].get('token', '').startswith(FENCE_PREFIX)
        and b[1].get('authorization') == AUTH_HEAD
        and b[1].get('dispatch') == DISPATCH_BRANCH
        and b[1].get('expected_science_workflow') == WORKFLOW_NAME
        and b[1].get('science_run') == str(run_id)
        and b[1].get('execution_key') == EXECUTION_KEY
    )]
    if len(matching) != 1:
        raise ValueError(f'exactly one matching unmatched pre-scan BEGIN required, got {len(matching)}')
    if [x[0] for x in unmatched] != [matching[0][0]]:
        raise ValueError(f'unrelated unmatched WRITE_QUIET_BEGIN present: {[x[0] for x in unmatched]}')
    begin_id, fields, created_at = matching[0]
    if not created_at:
        raise ValueError('BEGIN created_at missing')
    begin_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
    observed_dt = datetime.fromisoformat(observed_at.replace('Z', '+00:00'))
    if begin_dt > observed_dt:
        raise ValueError('BEGIN timestamp is after pre-scan observation')
    return {
        'schemaVersion': 1,
        'status': 'BOUND_AVPS_V2_RECOVERY4_ORDINAL45_WRITE_QUIET_BEGIN_BEFORE_GLOBAL_SCAN',
        'beginCommentId': begin_id,
        'fenceToken': fields['token'],
        'authorizationHead': AUTH_HEAD,
        'dispatchBranch': DISPATCH_BRANCH,
        'scienceWorkflow': WORKFLOW_NAME,
        'scienceRunId': int(run_id),
        'executionKey': EXECUTION_KEY,
        'beginCreatedAt': created_at,
        'bindingObservedAtUtc': observed_at,
        'beginWasUnmatchedAtBinding': True,
        'globalUnmatchedBeginCountAtBinding': 1,
    }


def release_from_bound_guard(comments: list[dict[str, Any]], guard: dict[str, Any], *, run_id: int) -> dict[str, Any]:
    begin_id = int(guard['writeQuietBeginCommentId'])
    token = str(guard['writeQuietFenceToken'])
    ends: list[tuple[int, dict[str, str], str]] = []
    for c in comments:
        body = str(c.get('body') or '')
        first = _first(body)
        if not first.startswith('WRITE_QUIET_END'):
            continue
        fields = _fields(first)
        if fields.get('begin') == str(begin_id):
            ends.append((int(c['id']), fields, str(c.get('created_at') or '')))
    if not ends:
        raise LookupError('matching bound WRITE_QUIET_END not yet observed')
    if len(ends) != 1:
        raise ValueError(f'exactly one END for bound BEGIN required, got {len(ends)}')
    end_id, fields, created_at = ends[0]
    required = {
        'token': token,
        'authorization': AUTH_HEAD,
        'dispatch': DISPATCH_BRANCH,
        'science_run': str(run_id),
        'guard': 'repository-global-candidate-seed-recheck',
        'step_conclusion': 'success',
    }
    for k, v in required.items():
        if fields.get(k) != v:
            raise ValueError(f'WRITE_QUIET_END field drift {k}: {fields.get(k)!r} != {v!r}')
    end_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
    scan_done = datetime.fromisoformat(str(guard['repositoryGlobalSeedScanCompletedAtUtc']).replace('Z', '+00:00'))
    if end_dt < scan_done:
        raise ValueError('WRITE_QUIET_END predates completed bound repository-global scan')
    return {
        'schemaVersion': 1,
        'status': 'PASS_AVPS_V2_RECOVERY4_SNAPSHOT_FENCE_RELEASE_BEFORE_SOLVER',
        'beginCommentId': begin_id,
        'endCommentId': end_id,
        'fenceToken': token,
        'authorizationHead': AUTH_HEAD,
        'dispatchBranch': DISPATCH_BRANCH,
        'scienceRunId': int(run_id),
        'guardStepConclusion': 'success',
        'releaseUsesPreflightBoundBeginOnly': True,
        'solverExecutionPermittedAfterBarrier': True,
    }


PRE_SCAN_BINDING = r'''          gh api --paginate --slurp "repos/$GITHUB_REPOSITORY/issues/60/comments?per_page=100" > execution-preflight/pre-scan-issue60-pages.json
          python - <<'PY'
          import json, os
          from datetime import datetime, timezone
          from pathlib import Path
          FENCE_PREFIX='AVPS_V2_RECOVERY4_ORDINAL45_SNAPSHOT_'
          WORKFLOW='avps-v2-postconsumption-recovery4-science.yml'
          EXECUTION_KEY='aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery4:numerical:45'
          def fields(first):
              out={}
              for token in first.replace('|',' ').split():
                  if '=' in token:
                      k,v=token.split('=',1); out[k]=v
              return out
          pages=json.load(open('execution-preflight/pre-scan-issue60-pages.json'))
          comments=[c for page in pages for c in page]
          closed=set(); begins=[]
          for c in comments:
              body=str(c.get('body') or '').strip(); first=body.splitlines()[0] if body else ''
              f=fields(first)
              if first.startswith('WRITE_QUIET_END') and f.get('begin','').isdigit(): closed.add(int(f['begin']))
              if first.startswith('WRITE_QUIET_BEGIN'): begins.append((int(c['id']),f,str(c.get('created_at') or '')))
          unmatched=[b for b in begins if b[0] not in closed]
          matching=[b for b in unmatched if (
              b[1].get('token','').startswith(FENCE_PREFIX)
              and b[1].get('authorization')==os.environ['AUTH_HEAD']
              and b[1].get('dispatch')==os.environ['DISPATCH_BRANCH']
              and b[1].get('expected_science_workflow')==WORKFLOW
              and b[1].get('science_run')==str(os.environ['GITHUB_RUN_ID'])
              and b[1].get('execution_key')==EXECUTION_KEY)]
          if len(matching)!=1: raise SystemExit(f'exactly one matching unmatched pre-scan WRITE_QUIET_BEGIN required, got {len(matching)}')
          if [x[0] for x in unmatched] != [matching[0][0]]: raise SystemExit(f'unrelated unmatched WRITE_QUIET_BEGIN present: {[x[0] for x in unmatched]}')
          begin_id,f,created=matching[0]
          observed=datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
          if not created: raise SystemExit('matching BEGIN created_at missing')
          begin_dt=datetime.fromisoformat(created.replace('Z','+00:00')); observed_dt=datetime.fromisoformat(observed.replace('Z','+00:00'))
          if begin_dt>observed_dt: raise SystemExit('matching BEGIN timestamp is after pre-scan observation')
          binding={'schemaVersion':1,'status':'BOUND_AVPS_V2_RECOVERY4_ORDINAL45_WRITE_QUIET_BEGIN_BEFORE_GLOBAL_SCAN','beginCommentId':begin_id,'fenceToken':f['token'],'authorizationHead':os.environ['AUTH_HEAD'],'dispatchBranch':os.environ['DISPATCH_BRANCH'],'scienceWorkflow':WORKFLOW,'scienceRunId':int(os.environ['GITHUB_RUN_ID']),'executionKey':EXECUTION_KEY,'beginCreatedAt':created,'bindingObservedAtUtc':observed,'beginWasUnmatchedAtBinding':True,'globalUnmatchedBeginCountAtBinding':1}
          Path('execution-preflight/pre-scan-fence-binding.json').write_text(json.dumps(binding,indent=2,sort_keys=True)+'\n')
          Path('execution-preflight/repository-global-seed-scan-started-at.txt').write_text(datetime.now(timezone.utc).isoformat().replace('+00:00','Z')+'\n')
          PY
'''

NEW_SNAPSHOT_JOB = r'''  snapshot-fence-release:
    needs: preflight
    runs-on: ubuntu-24.04
    timeout-minutes: 15
    steps:
      - name: Download exact current-run preflight guard and bound pre-scan fence evidence
        shell: bash
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          set -euo pipefail
          mkdir -p snapshot-fence-release/preflight
          gh run download "$GITHUB_RUN_ID" -n avps-v2-postconsumption-recovery4-preflight-ordinal-45 -D snapshot-fence-release/preflight
          test -s snapshot-fence-release/preflight/execution-guard.json
          test -s snapshot-fence-release/preflight/pre-scan-fence-binding.json
          python - <<'PY'
          import json, os
          g=json.load(open('snapshot-fence-release/preflight/execution-guard.json'))
          b=json.load(open('snapshot-fence-release/preflight/pre-scan-fence-binding.json'))
          required={'status':'EXACT_ONE_USE_AVPS_V2_POSTCONSUMPTION_RECOVERY4_DISPATCH_AUTHORIZED','scientificOrdinal':45,'workflowRunId':int(os.environ['GITHUB_RUN_ID']),'workflowRunAttempt':1,'authorizationHead':os.environ['AUTH_HEAD'],'dispatchBranch':os.environ['DISPATCH_BRANCH'],'preSolverRepositoryGlobalSeedRecheckPassed':True,'preSolverWriteQuietBoundBeforeGlobalScan':True,'releaseMustUsePreflightBoundBeginOnly':True}
          for k,v in required.items():
              if g.get(k)!=v: raise SystemExit(f'preflight execution guard drift {k}: {g.get(k)!r} != {v!r}')
          if g.get('writeQuietBeginCommentId')!=b.get('beginCommentId') or g.get('writeQuietFenceToken')!=b.get('fenceToken'): raise SystemExit('preflight guard/binding fence identity drift')
          if b.get('scienceRunId')!=int(os.environ['GITHUB_RUN_ID']): raise SystemExit('pre-scan fence binding run drift')
          PY

      - name: Verify only matching END for the exact pre-scan bound BEGIN
        shell: bash
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          set -euo pipefail
          cat > snapshot-fence-release/verify-bound-end.py <<'PY'
          import json, os, sys
          from datetime import datetime
          from pathlib import Path
          guard=json.load(open('snapshot-fence-release/preflight/execution-guard.json'))
          pages=json.load(open('snapshot-fence-release/issue60-pages.json'))
          comments=[c for page in pages for c in page]
          begin_id=int(guard['writeQuietBeginCommentId']); token=str(guard['writeQuietFenceToken'])
          ends=[]
          for c in comments:
              body=str(c.get('body') or '').strip(); first=body.splitlines()[0] if body else ''
              if not first.startswith('WRITE_QUIET_END'): continue
              fields={}
              for item in first.replace('|',' ').split():
                  if '=' in item:
                      k,v=item.split('=',1); fields[k]=v
              if fields.get('begin')==str(begin_id): ends.append((int(c['id']),fields,str(c.get('created_at') or '')))
          if not ends: sys.exit(2)
          if len(ends)!=1: raise SystemExit(f'exactly one matching END for pre-scan bound BEGIN required, got {len(ends)}')
          end_id,end_fields,created=ends[0]
          required={'token':token,'authorization':os.environ['AUTH_HEAD'],'dispatch':os.environ['DISPATCH_BRANCH'],'science_run':str(os.environ['GITHUB_RUN_ID']),'guard':'repository-global-candidate-seed-recheck','step_conclusion':'success'}
          for k,v in required.items():
              if end_fields.get(k)!=v: raise SystemExit(f'WRITE_QUIET_END field drift {k}: {end_fields.get(k)!r} != {v!r}')
          if not created: raise SystemExit('matching END created_at missing')
          end_dt=datetime.fromisoformat(created.replace('Z','+00:00'))
          scan_done=datetime.fromisoformat(str(guard['repositoryGlobalSeedScanCompletedAtUtc']).replace('Z','+00:00'))
          if end_dt<scan_done: raise SystemExit('matching END predates completed pre-scan-bound repository-global guard')
          out={'schemaVersion':1,'status':'PASS_AVPS_V2_RECOVERY4_SNAPSHOT_FENCE_RELEASE_BEFORE_SOLVER','beginCommentId':begin_id,'endCommentId':end_id,'fenceToken':token,'authorizationHead':os.environ['AUTH_HEAD'],'dispatchBranch':os.environ['DISPATCH_BRANCH'],'scienceRunId':int(os.environ['GITHUB_RUN_ID']),'guardStepConclusion':'success','releaseUsesPreflightBoundBeginOnly':True,'solverExecutionPermittedAfterBarrier':True}
          Path('snapshot-fence-release/release-receipt.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
          PY
          for attempt in $(seq 1 120); do
            gh api --paginate --slurp "repos/$GITHUB_REPOSITORY/issues/60/comments?per_page=100" > snapshot-fence-release/issue60-pages.json
            set +e
            python snapshot-fence-release/verify-bound-end.py
            rc=$?
            set -e
            if [ "$rc" -eq 0 ]; then break; fi
            if [ "$rc" -ne 2 ]; then exit "$rc"; fi
            if [ "$attempt" -eq 120 ]; then
              echo 'matching WRITE_QUIET_END for the pre-scan bound BEGIN not observed within bounded 10-minute barrier' >&2
              exit 1
            fi
            sleep 5
          done
          test -s snapshot-fence-release/release-receipt.json

      - uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7.0.1
        with:
          name: avps-v2-recovery4-ordinal45-snapshot-fence-release
          path: snapshot-fence-release/release-receipt.json
          if-no-files-found: error
          compression-level: 0

'''


def sha_meta(data: bytes) -> dict[str, Any]:
    return {
        'sha256': hashlib.sha256(data).hexdigest(),
        'gitBlobSha1': hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest(),
        'size': len(data),
    }


def patch_workflow(text: str) -> str:
    env_old = '        env:\n          GITHUB_TOKEN: ${{ github.token }}\n        run: |\n          set -euo pipefail\n          git ls-files -z > execution-preflight/tracked-files.nul\n'
    env_new = '        env:\n          GITHUB_TOKEN: ${{ github.token }}\n          GH_TOKEN: ${{ github.token }}\n        run: |\n          set -euo pipefail\n          git ls-files -z > execution-preflight/tracked-files.nul\n'
    if text.count(env_old) != 1:
        raise ValueError('fresh-seed step env anchor drift')
    text = text.replace(env_old, env_new, 1)
    scan_anchor = '          python review/aerosol-vertical-profile-sensitivity-v2-seed-freshness/repository_global_seed_scan.py \\\n'
    if text.count(scan_anchor) != 1:
        raise ValueError('repository-global scan invocation anchor drift')
    text = text.replace(scan_anchor, PRE_SCAN_BINDING + scan_anchor, 1)
    guard_start = "          guard={\n            'schemaVersion':1,'status':'EXACT_ONE_USE_AVPS_V2_POSTCONSUMPTION_RECOVERY4_DISPATCH_AUTHORIZED','scientificOrdinal':45,\n"
    if text.count(guard_start) != 1:
        raise ValueError('guard construction anchor drift')
    guard_prelude = "          binding=json.load(open('execution-preflight/pre-scan-fence-binding.json'))\n          scan_started=Path('execution-preflight/repository-global-seed-scan-started-at.txt').read_text().strip()\n          from datetime import datetime, timezone\n          begin_dt=datetime.fromisoformat(binding['beginCreatedAt'].replace('Z','+00:00')); scan_start_dt=datetime.fromisoformat(scan_started.replace('Z','+00:00'))\n          if scan_start_dt<begin_dt: raise SystemExit('repository-global scan start predates bound BEGIN')\n          scan_done=datetime.now(timezone.utc).isoformat().replace('+00:00','Z')\n          scan_bytes=Path('execution-preflight/repository-global-seed-scan.json').read_bytes()\n          scan_sha=__import__('hashlib').sha256(scan_bytes).hexdigest()\n"
    text = text.replace(guard_start, guard_prelude + guard_start, 1)
    old_tail = "            'preSolverRepositoryGlobalSeedRecheckPassed':True,'fourAliasDataTreeSha256':os.environ['FOUR_ALIAS_SHA256'],\n            'solverExecutionPermittedNow':True,'githubRerun':False,'retryAllowed':False,'resumeAllowed':False,\n"
    new_tail = "            'preSolverRepositoryGlobalSeedRecheckPassed':True,'fourAliasDataTreeSha256':os.environ['FOUR_ALIAS_SHA256'],\n            'writeQuietBeginCommentId':binding['beginCommentId'],'writeQuietFenceToken':binding['fenceToken'],\n            'writeQuietBeginCreatedAt':binding['beginCreatedAt'],'writeQuietBindingObservedAtUtc':binding['bindingObservedAtUtc'],\n            'repositoryGlobalSeedScanStartedAtUtc':scan_started,'repositoryGlobalSeedScanCompletedAtUtc':scan_done,\n            'repositoryGlobalSeedScanSha256':scan_sha,'preSolverWriteQuietBoundBeforeGlobalScan':True,\n            'releaseMustUsePreflightBoundBeginOnly':True,\n            'solverExecutionPermittedNow':True,'githubRerun':False,'retryAllowed':False,'resumeAllowed':False,\n"
    if text.count(old_tail) != 1:
        raise ValueError('guard tail anchor drift')
    text = text.replace(old_tail, new_tail, 1)
    start = text.find('  snapshot-fence-release:\n')
    end = text.find('  cases-dep2:\n', start)
    if start < 0 or end < 0:
        raise ValueError('snapshot fence job anchors drift')
    old_snapshot = text[start:end]
    if 'WRITE_QUIET_BEGIN' not in old_snapshot:
        raise ValueError('expected old independent BEGIN lookup missing')
    text = text[:start] + NEW_SNAPSHOT_JOB + text[end:]
    return text


def run_fixtures(path: Path) -> dict[str, Any]:
    fx = json.loads(path.read_text())
    results=[]
    for case in fx['cases']:
        name=case['name']; expected=case['expected']; stage=case['stage']
        try:
            if stage=='bind':
                bind_pre_scan_begin(case['comments'], run_id=case['runId'], observed_at=case['observedAtUtc'])
            elif stage=='release':
                release_from_bound_guard(case['comments'], case['guard'], run_id=case['runId'])
            else:
                raise ValueError('unknown fixture stage')
            outcome='PASS'
        except (ValueError, LookupError, KeyError) as exc:
            outcome='REFUSED'; reason=str(exc)
        else:
            reason='accepted by frozen temporal-fence contract'
        if outcome != expected:
            raise SystemExit(f'fixture {name}: {outcome} != expected {expected}: {reason}')
        results.append({'name':name,'expected':expected,'outcome':outcome,'reason':reason})
    return {'schemaVersion':1,'status':'PASS_RECOVERY4_TEMPORAL_FENCE_ZERO_RUNTIME_REGRESSIONS','caseCount':len(results),'cases':results}


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--package', type=Path, required=True)
    ap.add_argument('--fixtures', type=Path, required=True)
    ap.add_argument('--regression-output', type=Path, required=True)
    args=ap.parse_args()
    regression=run_fixtures(args.fixtures)
    args.regression_output.write_text(json.dumps(regression,indent=2,sort_keys=True)+'\n')
    wf=args.package/WORKFLOW_NAME
    before=wf.read_text()
    after=patch_workflow(before)
    if after==before: raise SystemExit('temporal fence postprocessor made no change')
    wf.write_text(after)
    manifest_path=args.package/'manifest.json'
    m=json.loads(manifest_path.read_text())
    m['outputs'][WORKFLOW_NAME]=sha_meta(wf.read_bytes())
    m['temporalFencePreScanBindingCorrected']=True
    m['preScanFenceBindingRequired']=True
    m['snapshotReleaseUsesPreflightBoundBeginOnly']=True
    m['independentLateBeginSearchRemoved']=True
    m['frozenScienceChanged']=False
    manifest_path.write_text(json.dumps(m,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'status':'CORRECTED_RECOVERY4_TEMPORAL_FENCE_ZERO_RUNTIME','workflow':m['outputs'][WORKFLOW_NAME],'regressions':regression['status']},sort_keys=True))
    return 0

if __name__=='__main__':
    raise SystemExit(main())
