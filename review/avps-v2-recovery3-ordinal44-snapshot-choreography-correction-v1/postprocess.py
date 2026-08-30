#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'generated-avps-v2-recovery3-ordinal44-execution-package'
SCIENCE = OUT / 'avps-v2-postconsumption-recovery3-science.yml'
PUBLISHER = OUT / 'avps-v2-postconsumption-recovery3-dispatch-publisher.yml'
TRIGGER = OUT / 'avps-v2-postconsumption-recovery3-publisher-trigger-bridge.yml'
MANIFEST = OUT / 'manifest.json'

AUTH_HEAD = 'dd3a4c692af505389e9feb1e5f5480fa389110a3'
DISPATCH_BRANCH = 'dispatch/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3-ordinal-44'
SCIENCE_WORKFLOW = 'avps-v2-postconsumption-recovery3-science.yml'
CORRECTION_REVIEW_WORKFLOW = 'avps-v2-recovery3-ordinal44-snapshot-choreography-correction-review.yml'
CORRECTION_REVIEW_ARTIFACT = 'avps-v2-recovery3-ordinal44-snapshot-choreography-correction-review'
CORRECTION_REVIEW_STATUS = 'PASS_AVPS_V2_RECOVERY3_ORDINAL44_SNAPSHOT_CHOREOGRAPHY_CORRECTION_REVIEW_ZERO_RUNTIME'
CORRECTION_ADMISSIBLE_PREFIX = 'AVPS_V2_RECOVERY3_ORDINAL44_EXECUTION_PACKAGE_CORRECTED_ADMISSIBLE'
NOT_ADMISSIBLE_COMMENT_ID = 5470357989


def replace_exact(text: str, old: str, new: str, count: int = 1) -> str:
    got = text.count(old)
    if got != count:
        raise SystemExit(f'expected {count} occurrences of {old!r}, found {got}')
    return text.replace(old, new, count)


def replace_env(text: str, key: str, value: str) -> str:
    pat = re.compile(rf'(?m)^  {re.escape(key)}: .*?$')
    hits = pat.findall(text)
    if len(hits) != 1:
        raise SystemExit(f'env field {key} count drift: {len(hits)}')
    return pat.sub(f'  {key}: {value}', text, count=1)


def git_blob(raw: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def identity(path: Path) -> dict[str, str]:
    raw = path.read_bytes()
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'gitBlobSha1': git_blob(raw)}


def barrier_block() -> str:
    return r'''  snapshot-fence-release:
    needs: preflight
    runs-on: ubuntu-24.04
    timeout-minutes: 15
    steps:
      - name: Verify matching recovery3 WRITE_QUIET_END before solver runtime
        shell: bash
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          set -euo pipefail
          mkdir -p snapshot-fence-release
          for attempt in $(seq 1 120); do
            gh api --paginate --slurp "repos/$GITHUB_REPOSITORY/issues/60/comments?per_page=100" > snapshot-fence-release/issue60-pages.json
            set +e
            python - <<'PY'
          import json, os, sys
          from pathlib import Path
          pages=json.load(open('snapshot-fence-release/issue60-pages.json'))
          comments=[c for page in pages for c in page]
          auth=os.environ['AUTH_HEAD']
          dispatch=os.environ['DISPATCH_BRANCH']
          run=str(os.environ['GITHUB_RUN_ID'])
          begins=[]
          for c in comments:
              body=str(c.get('body') or '').strip()
              if not body.startswith('WRITE_QUIET_BEGIN '):
                  continue
              fields={}
              for token in body.split()[1:]:
                  if '=' in token:
                      k,v=token.split('=',1); fields[k]=v
              if (fields.get('token','').startswith('AVPS_V2_RECOVERY3_ORDINAL44_SNAPSHOT_') and
                  fields.get('authorization')==auth and fields.get('dispatch')==dispatch and
                  fields.get('expected_science_workflow')=='avps-v2-postconsumption-recovery3-science.yml'):
                  begins.append((int(c['id']),fields))
          if len(begins)!=1:
              raise SystemExit(f'exactly one matching recovery3 WRITE_QUIET_BEGIN required, got {len(begins)}')
          begin_id, begin_fields=begins[0]
          ends=[]
          for c in comments:
              body=str(c.get('body') or '').strip()
              if not body.startswith('WRITE_QUIET_END '):
                  continue
              fields={}
              for token in body.split()[1:]:
                  if '=' in token:
                      k,v=token.split('=',1); fields[k]=v
              if fields.get('begin')==str(begin_id):
                  ends.append((int(c['id']),fields))
          if not ends:
              sys.exit(2)
          if len(ends)!=1:
              raise SystemExit(f'exactly one matching recovery3 WRITE_QUIET_END required, got {len(ends)}')
          end_id,end_fields=ends[0]
          required={
              'token':begin_fields['token'],
              'authorization':auth,
              'dispatch':dispatch,
              'science_run':run,
              'guard':'repository-global-candidate-seed-recheck',
              'step_conclusion':'success',
          }
          for k,v in required.items():
              if end_fields.get(k)!=v:
                  raise SystemExit(f'WRITE_QUIET_END field drift {k}: {end_fields.get(k)!r} != {v!r}')
          out={'schemaVersion':1,'status':'PASS_AVPS_V2_RECOVERY3_SNAPSHOT_FENCE_RELEASE_BEFORE_SOLVER','beginCommentId':begin_id,'endCommentId':end_id,'fenceToken':begin_fields['token'],'authorizationHead':auth,'dispatchBranch':dispatch,'scienceRunId':int(run),'guardStepConclusion':'success','solverExecutionPermittedAfterBarrier':True}
          Path('snapshot-fence-release/release-receipt.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
          PY
            rc=$?
            set -e
            if [ "$rc" -eq 0 ]; then
              break
            fi
            if [ "$rc" -ne 2 ]; then
              exit "$rc"
            fi
            if [ "$attempt" -eq 120 ]; then
              echo 'matching WRITE_QUIET_END not observed within bounded 10-minute barrier' >&2
              exit 1
            fi
            sleep 5
          done
          test -s snapshot-fence-release/release-receipt.json

      - uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7.0.1
        with:
          name: avps-v2-recovery3-ordinal44-snapshot-fence-release
          path: snapshot-fence-release/release-receipt.json
          if-no-files-found: error
          compression-level: 0

'''


def transform_science(text: str) -> str:
    if 'snapshot-fence-release:' in text:
        raise SystemExit('snapshot-fence-release already present before correction')
    jobs=('cases-dep2','cases-dep4','cases-dep6','cases-dep8')
    for job in jobs:
        old=f'\n  {job}:\n    needs: preflight\n'
        new=f'\n  {job}:\n    needs: [preflight, snapshot-fence-release]\n'
        text=replace_exact(text,old,new,1)
    anchor='\n  cases-dep2:\n    needs: [preflight, snapshot-fence-release]\n'
    text=replace_exact(text,anchor,'\n'+barrier_block()+anchor.lstrip('\n'),1)
    for job in jobs:
        section=text.split(f'\n  {job}:\n',1)[1].split('\n  ',1)[0]
        if 'needs: [preflight, snapshot-fence-release]' not in section:
            raise SystemExit(f'{job} is not barrier-gated')
    return text


def publisher_tail() -> str:
    return r'''
      - name: Acquire snapshot fence, bootstrap once, dispatch science, observe exact guard step, and release
        shell: bash
        env:
          GH_TOKEN: ${{ github.token }}
          GITHUB_TOKEN: ${{ github.token }}
        run: |
          set -euo pipefail
          mkdir -p dispatch-evidence
          FENCE_BEGIN=0
          FENCE_CLOSED=0
          SCIENCE_RUN=0
          PREFLIGHT_JOB=0
          STEP_CONCLUSION=not_observed
          FENCE_TOKEN="AVPS_V2_RECOVERY3_ORDINAL44_SNAPSHOT_${GITHUB_RUN_ID}"

          close_fence() {
            if [ "$FENCE_BEGIN" = 0 ] || [ "$FENCE_CLOSED" = 1 ]; then return 0; fi
            local observed_at body
            observed_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)
            body="WRITE_QUIET_END begin=$FENCE_BEGIN token=$FENCE_TOKEN authorization=$AUTH_HEAD dispatch=$DISPATCH_BRANCH science_run=$SCIENCE_RUN preflight_job=$PREFLIGHT_JOB guard=repository-global-candidate-seed-recheck step_conclusion=$STEP_CONCLUSION observed_at=$observed_at"
            gh api --method POST "repos/$GITHUB_REPOSITORY/issues/60/comments" -f body="$body" > dispatch-evidence/write-quiet-end.json
            FENCE_CLOSED=1
          }
          trap 'rc=$?; trap - EXIT; if [ "$FENCE_BEGIN" != 0 ] && [ "$FENCE_CLOSED" != 1 ]; then STEP_CONCLUSION="publisher_exit_${rc}"; close_fence || true; fi; exit "$rc"' EXIT

          # Last live-ledger/main check before acquiring the short-lived fence.
          test "$(gh api "repos/$GITHUB_REPOSITORY/branches/main" --jq .commit.sha)" = "$GITHUB_SHA"
          if git ls-remote --exit-code --heads origin "$DISPATCH_BRANCH" >/dev/null 2>&1; then
            echo 'dispatch branch appeared after pre-dispatch review' >&2
            exit 1
          fi
          gh api --paginate --slurp "repos/$GITHUB_REPOSITORY/issues/60/comments?per_page=100" > dispatch-evidence/pre-begin-comments.json
          python - <<'PY'
          import json, os, re
          pages=json.load(open('dispatch-evidence/pre-begin-comments.json'))
          comments=[c for page in pages for c in page]
          not_admissible=5470357989
          prefix='AVPS_V2_RECOVERY3_ORDINAL44_EXECUTION_PACKAGE_CORRECTED_ADMISSIBLE'
          corrected=[c for c in comments if int(c.get('id') or 0)>not_admissible and str(c.get('body') or '').strip().startswith(prefix)]
          if len(corrected)!=1: raise SystemExit(f'exactly one post-invalidation corrected-admissible marker required, got {len(corrected)}')
          corrected_id=int(corrected[0]['id'])
          open_begins={}
          for c in comments:
              cid=int(c.get('id') or 0)
              if cid<=corrected_id: continue
              body=str(c.get('body') or '').strip()
              if body.startswith('WRITE_QUIET_BEGIN '):
                  open_begins[cid]=body
              elif body.startswith('WRITE_QUIET_END '):
                  m=re.search(r'\bbegin=(\d+)\b',body)
                  if not m: raise SystemExit(f'new WRITE_QUIET_END lacks begin binding: {cid}')
                  open_begins.pop(int(m.group(1)),None)
          if open_begins: raise SystemExit(f'unmatched WRITE_QUIET_BEGIN after corrected-admissible marker: {sorted(open_begins)}')
          blockers=('NOT_ADMISSIBLE','DO NOT USE','FAIL-CLOSED','CLOSED')
          for c in comments:
              cid=int(c.get('id') or 0)
              if cid<=corrected_id: continue
              upper=str(c.get('body') or '').upper()
              relevant=('AVPS' in upper or 'ORDINAL44' in upper or 'ORDINAL 44' in upper or 'RECOVERY3' in upper)
              superseding=('SUPERSED' in upper or ('COORDINATOR' in upper and 'RECOVERY' in upper))
              if relevant and (any(x in upper for x in blockers) or superseding):
                  raise SystemExit(f'newer relevant fail-closed/closure/recovery directive: {cid}')
          PY

          BEGIN_BODY="WRITE_QUIET_BEGIN token=$FENCE_TOKEN authorization=$AUTH_HEAD dispatch=$DISPATCH_BRANCH expected_science_workflow=avps-v2-postconsumption-recovery3-science.yml publisher_run=$GITHUB_RUN_ID"
          gh api --method POST "repos/$GITHUB_REPOSITORY/issues/60/comments" -f body="$BEGIN_BODY" > dispatch-evidence/write-quiet-begin.json
          FENCE_BEGIN=$(python -c "import json; print(json.load(open('dispatch-evidence/write-quiet-begin.json'))['id'])")
          test "$FENCE_BEGIN" -gt 0

          # Bootstrap writes are the only intentional repository mutations while the fence is held.
          gh api --method POST "repos/$GITHUB_REPOSITORY/git/refs" -f ref="refs/heads/$DISPATCH_BRANCH" -f sha="$AUTH_HEAD" > dispatch-evidence/ref-create.json
          test "$(gh api "repos/$GITHUB_REPOSITORY/git/ref/heads/$DISPATCH_BRANCH" --jq .object.sha)" = "$AUTH_HEAD"
          gh api --method POST "repos/$GITHUB_REPOSITORY/issues/60/comments" -f body="$CONSUMED_MARKER" > dispatch-evidence/consumed-comment.json
          gh api --paginate --slurp "repos/$GITHUB_REPOSITORY/issues/60/comments?per_page=100" > dispatch-evidence/post-bootstrap-comments.json
          python - <<'PY'
          import json,os
          pages=json.load(open('dispatch-evidence/post-bootstrap-comments.json')); bodies=[str(c.get('body') or '').strip() for p in pages for c in p]
          if sum(b==os.environ['ALLOCATION_MARKER'] for b in bodies)!=1: raise SystemExit('post-bootstrap allocation cardinality drift')
          if sum(b.startswith(os.environ['CONSUMED_MARKER']) for b in bodies)!=1: raise SystemExit('post-bootstrap consumed cardinality drift')
          PY

          PAYLOAD='{"ref":"main","inputs":{"dispatch_ref":"dispatch/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3-ordinal-44"}}'
          gh api --method POST "repos/$GITHUB_REPOSITORY/actions/workflows/avps-v2-postconsumption-recovery3-science.yml/dispatches" --input - <<< "$PAYLOAD"

          # Resolve exactly one attempt-1 science run on the publisher's exact main head.
          for attempt in $(seq 1 120); do
            gh api "repos/$GITHUB_REPOSITORY/actions/workflows/avps-v2-postconsumption-recovery3-science.yml/runs?event=workflow_dispatch&branch=main&per_page=20" > dispatch-evidence/science-runs.json
            set +e
            SCIENCE_RUN=$(python - <<'PY'
          import json,os,sys
          rows=json.load(open('dispatch-evidence/science-runs.json')).get('workflow_runs',[])
          good=[r for r in rows if r.get('head_sha')==os.environ['GITHUB_SHA'] and int(r.get('run_attempt') or 0)==1 and os.environ['DISPATCH_BRANCH'] in str(r.get('display_title') or '')]
          if len(good)>1: raise SystemExit(f'multiple matching science runs: {[r.get("id") for r in good]}')
          if not good: sys.exit(2)
          print(good[0]['id'])
          PY
            )
            rc=$?
            set -e
            if [ "$rc" -eq 0 ]; then break; fi
            if [ "$rc" -ne 2 ]; then exit "$rc"; fi
            if [ "$attempt" -eq 120 ]; then echo 'science run not created within bounded 10-minute wait' >&2; exit 1; fi
            sleep 5
          done
          test "$SCIENCE_RUN" -gt 0

          # Remain read-only until the exact repository-global guard step is terminal.
          for attempt in $(seq 1 360); do
            gh api "repos/$GITHUB_REPOSITORY/actions/runs/$SCIENCE_RUN/jobs?per_page=100" > dispatch-evidence/science-jobs.json
            set +e
            STATE=$(python - <<'PY'
          import json,sys
          jobs=json.load(open('dispatch-evidence/science-jobs.json')).get('jobs',[])
          pre=[j for j in jobs if j.get('name')=='preflight']
          if len(pre)>1: raise SystemExit('multiple preflight jobs')
          if not pre:
              print('WAIT'); sys.exit(2)
          job=pre[0]
          hits=[s for s in (job.get('steps') or []) if s.get('name')=='Fresh repository-global candidate-seed recheck and one-use guard']
          if len(hits)>1: raise SystemExit('multiple repository-global guard steps')
          if hits and hits[0].get('status')=='completed':
              print(f"TERMINAL {job['id']} {hits[0].get('conclusion') or 'unknown'}"); sys.exit(0)
          if job.get('status')=='completed':
              print(f"TERMINAL {job['id']} guard_step_missing"); sys.exit(0)
          print('WAIT'); sys.exit(2)
          PY
            )
            rc=$?
            set -e
            if [ "$rc" -eq 0 ]; then
              read -r tag PREFLIGHT_JOB STEP_CONCLUSION <<< "$STATE"
              test "$tag" = TERMINAL
              break
            fi
            if [ "$rc" -ne 2 ]; then exit "$rc"; fi
            if [ "$attempt" -eq 360 ]; then echo 'guard step not terminal within bounded 30-minute wait' >&2; exit 1; fi
            sleep 5
          done

          close_fence
          trap - EXIT

          # Durable readback: exactly one END must bind this BEGIN and exact science run.
          gh api --paginate --slurp "repos/$GITHUB_REPOSITORY/issues/60/comments?per_page=100" > dispatch-evidence/post-end-comments.json
          python - <<'PY'
          import json,os
          begin=json.load(open('dispatch-evidence/write-quiet-begin.json'))
          end=json.load(open('dispatch-evidence/write-quiet-end.json'))
          pages=json.load(open('dispatch-evidence/post-end-comments.json')); comments=[c for p in pages for c in p]
          bid=str(begin['id']); eid=int(end['id'])
          hits=[]
          for c in comments:
              body=str(c.get('body') or '').strip()
              if body.startswith('WRITE_QUIET_END ') and f'begin={bid}' in body:
                  hits.append(c)
          if len(hits)!=1 or int(hits[0]['id'])!=eid: raise SystemExit('matching END cardinality/identity drift')
          PY

          python - <<'PY'
          import json,os
          from pathlib import Path
          begin=json.load(open('dispatch-evidence/write-quiet-begin.json'))
          end=json.load(open('dispatch-evidence/write-quiet-end.json'))
          out={'schemaVersion':2,'status':'DISPATCH_PUBLISHED_AND_SNAPSHOT_FENCE_RELEASED','scientificOrdinal':44,'executionKey':os.environ['EXECUTION_KEY'],'authorizationHead':os.environ['AUTH_HEAD'],'authorizationParent':os.environ['AUTH_PARENT'],'authorizationPr':718,'dispatchBranch':os.environ['DISPATCH_BRANCH'],'dispatchBranchHeadSha':os.environ['AUTH_HEAD'],'workflowRunAttempt':1,'writeQuietBeginCommentId':int(begin['id']),'writeQuietEndCommentId':int(end['id']),'scienceRunId':int(os.environ.get('SCIENCE_RUN_FOR_RECEIPT','0')) if os.environ.get('SCIENCE_RUN_FOR_RECEIPT') else None,'scientificRuntimeSetupPerformed':False,'solverExecutionPerformedByPublisher':False,'consumedMarkerPosted':True,'scienceDispatchRequested':True,'snapshotGuardStepObservedTerminal':True}
          Path('dispatch-evidence/dispatch-publisher.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
          PY

          if [ "$STEP_CONCLUSION" != success ]; then
            echo "repository-global guard step terminal conclusion: $STEP_CONCLUSION" >&2
            exit 1
          fi

      - name: Upload zero-runtime publisher and fence evidence after release
        uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7.0.1
        with:
          name: avps-v2-postconsumption-recovery3-dispatch-publisher-ordinal-44
          path: dispatch-evidence/
          if-no-files-found: error
          compression-level: 0
'''


def transform_publisher(text: str) -> str:
    text=replace_env(text,'PACKAGE_REVIEW_WORKFLOW',CORRECTION_REVIEW_WORKFLOW)
    text=replace_env(text,'PACKAGE_REVIEW_ARTIFACT',CORRECTION_REVIEW_ARTIFACT)
    text=replace_exact(text,'PASS_AVPS_V2_RECOVERY3_ORDINAL44_EXECUTION_PACKAGE_REVIEW_ZERO_RUNTIME',CORRECTION_REVIEW_STATUS,1)
    text=replace_exact(text,'    timeout-minutes: 45\n','    timeout-minutes: 90\n',1)
    pattern=re.compile(r'\n      - name: Create exact dispatch ref and consumed marker once\n.*\Z',re.S)
    if len(pattern.findall(text))!=1:
        raise SystemExit('could not isolate publisher bootstrap/dispatch tail')
    text=pattern.sub(publisher_tail(),text,count=1)
    return text


def transform_trigger(text: str, publisher_blob: str) -> str:
    pat=re.compile(r'(?m)^  PUBLISHER_BLOB: [0-9a-f]{40}$')
    if len(pat.findall(text))!=1:
        raise SystemExit('trigger PUBLISHER_BLOB cardinality drift')
    return pat.sub(f'  PUBLISHER_BLOB: {publisher_blob}',text,count=1)


def main() -> int:
    science=transform_science(SCIENCE.read_text())
    publisher=transform_publisher(PUBLISHER.read_text())
    SCIENCE.write_text(science)
    PUBLISHER.write_text(publisher)
    trigger=transform_trigger(TRIGGER.read_text(),git_blob(PUBLISHER.read_bytes()))
    TRIGGER.write_text(trigger)

    manifest=json.loads(MANIFEST.read_text())
    manifest['snapshotFenceChoreographyCorrectionApplied']=True
    manifest['writeQuietBeginBeforeBootstrapRequired']=True
    manifest['guardStepTerminalEndRequired']=True
    manifest['snapshotFenceReleaseBarrierRequired']=True
    manifest['allSolverCaseJobsDependOnSnapshotFenceRelease']=True
    manifest['publisherReviewWorkflowExistsAfterCorrection']=True
    manifest['supersedesNotAdmissibleCommentId']=NOT_ADMISSIBLE_COMMENT_ID
    manifest['correctedAdmissibleMarkerRequiredBeforeDispatch']=CORRECTION_ADMISSIBLE_PREFIX
    manifest['correctionReviewWorkflow']=CORRECTION_REVIEW_WORKFLOW
    manifest['correctionReviewArtifact']=CORRECTION_REVIEW_ARTIFACT
    manifest['frozenScienceDesignChanged']=False
    manifest['outputs']={SCIENCE.name:identity(SCIENCE),PUBLISHER.name:identity(PUBLISHER),TRIGGER.name:identity(TRIGGER)}
    MANIFEST.write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
