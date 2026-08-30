#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE_PUBLISHER = ROOT / ".github/workflows/avps-v2-postconsumption-recovery2-dispatch-publisher.yml"
SOURCE_TRIGGER = ROOT / ".github/workflows/avps-v2-postconsumption-recovery2-publisher-trigger-bridge.yml"
OUT = ROOT / "generated-avps-v2-recovery2-publisher-recovery1"
PUBLISHER_NAME = "avps-v2-postconsumption-recovery2-dispatch-publisher-recovery1.yml"
TRIGGER_NAME = "avps-v2-postconsumption-recovery2-publisher-recovery1-trigger-bridge.yml"
REVIEW_NAME = "avps-v2-recovery2-ordinal43-publisher-recovery1-review.yml"
FAILED_RUN = "33290906727"
FAILED_JOB = "99202243870"


def require(text: str, token: str) -> None:
    if token not in text:
        raise SystemExit(f"required source token missing: {token!r}")


def replace_once(text: str, old: str, new: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"expected one occurrence of {old!r}, found {count}")
    return text.replace(old, new, 1)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


pub = SOURCE_PUBLISHER.read_text(encoding="utf-8")
trig = SOURCE_TRIGGER.read_text(encoding="utf-8")

for token in (
    "Fresh zero-runtime pre-dispatch fence",
    "Create exact dispatch ref and consumed marker once",
    "Explicitly dispatch exact science workflow from main",
    "GH_TOKEN: ${{ github.token }}",
    "payload=preauthorization_surface.collect(os.environ['GITHUB_REPOSITORY'],os.environ['GITHUB_TOKEN'])",
    "avps-v2-postconsumption-recovery2-science.yml",
):
    require(pub, token)
for token in (
    "AVPS v2 publisher postconsumption-recovery2-ordinal43 trigger bridge",
    "dispatch-trigger/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery2-ordinal-43-publisher",
    "dispatch-triggers/avps-v2-postconsumption-recovery2-ordinal43-publisher.txt",
    "avps-v2-postconsumption-recovery2-dispatch-publisher.yml",
):
    require(trig, token)

# Fresh publisher identity. The original failed workflow remains untouched and immutable.
pub = replace_once(pub, "name: AVPS v2 dispatch publisher", "name: AVPS v2 recovery2 ordinal43 dispatch publisher recovery1")
pub = replace_once(pub, "run-name: AVPS v2 postconsumption recovery2 ordinal 43 zero-runtime dispatch publisher", "run-name: AVPS v2 postconsumption recovery2 ordinal 43 zero-runtime dispatch publisher recovery1")
pub = replace_once(pub, "group: avps-v2-postconsumption-recovery2-ordinal-43-dispatch-publisher", "group: avps-v2-postconsumption-recovery2-ordinal-43-dispatch-publisher-recovery1")
pub = replace_once(pub, "jobs:\n  publish:", "jobs:\n  publish-recovery1:")
pub = replace_once(pub, "  HISTORICAL_SEED_LEDGER_BLOB: 491d1b6653bea0fcc5275269723a76aa1af52300\n", "  HISTORICAL_SEED_LEDGER_BLOB: 491d1b6653bea0fcc5275269723a76aa1af52300\n  FAILED_PUBLISHER_RUN: '33290906727'\n  FAILED_PUBLISHER_JOB: '99202243870'\n  RECOVERY_REVIEW_WORKFLOW: avps-v2-recovery2-ordinal43-publisher-recovery1-review.yml\n  RECOVERY_REVIEW_ARTIFACT: avps-v2-recovery2-ordinal43-publisher-recovery1-review\n")
pub = replace_once(pub, "      - name: Fresh zero-runtime pre-dispatch fence", "      - name: Fresh recovery1 zero-runtime pre-dispatch fence")
# The exact failure was GH_TOKEN/GITHUB_TOKEN propagation. Supply both verified aliases in the recovery identity.
pub = replace_once(pub, "        env:\n          GH_TOKEN: ${{ github.token }}\n        run: |\n          set -euo pipefail\n          test \"$GITHUB_EVENT_NAME\" = workflow_dispatch", "        env:\n          GH_TOKEN: ${{ github.token }}\n          GITHUB_TOKEN: ${{ github.token }}\n        run: |\n          set -euo pipefail\n          test \"$GITHUB_EVENT_NAME\" = workflow_dispatch")
pub = pub.replace("dispatch-evidence/", "dispatch-recovery1-evidence/")
pub = pub.replace("mkdir -p dispatch-evidence", "mkdir -p dispatch-recovery1-evidence")
pub = pub.replace("name: avps-v2-postconsumption-recovery2-dispatch-publisher-ordinal-43", "name: avps-v2-postconsumption-recovery2-dispatch-publisher-recovery1-ordinal-43")

failed_proof = r'''          # Bind the failed publisher as immutable pre-consumption evidence. Never rerun it.
          gh api "repos/$GITHUB_REPOSITORY/actions/runs/$FAILED_PUBLISHER_RUN" > dispatch-recovery1-evidence/failed-publisher-run.json
          gh api "repos/$GITHUB_REPOSITORY/actions/runs/$FAILED_PUBLISHER_RUN/jobs" > dispatch-recovery1-evidence/failed-publisher-jobs.json
          python - <<'PY'
          import json,os
          r=json.load(open('dispatch-recovery1-evidence/failed-publisher-run.json'))
          jobs=json.load(open('dispatch-recovery1-evidence/failed-publisher-jobs.json')).get('jobs',[])
          if r.get('id')!=int(os.environ['FAILED_PUBLISHER_RUN']) or r.get('run_attempt')!=1 or r.get('event')!='workflow_dispatch' or r.get('conclusion')!='failure': raise SystemExit('failed publisher identity drift')
          hit=[j for j in jobs if j.get('id')==int(os.environ['FAILED_PUBLISHER_JOB'])]
          if len(hit)!=1 or hit[0].get('conclusion')!='failure': raise SystemExit('failed publisher job drift')
          steps={s.get('name'):s.get('conclusion') for s in hit[0].get('steps',[])}
          if steps.get('Fresh zero-runtime pre-dispatch fence')!='failure': raise SystemExit('prior publisher failure-step drift')
          for n in ('Create exact dispatch ref and consumed marker once','Upload zero-runtime publisher evidence before science dispatch','Explicitly dispatch exact science workflow from main'):
              if steps.get(n)!='skipped': raise SystemExit(f'prior publisher crossed pre-consumption boundary: {n}={steps.get(n)!r}')
          PY
'''
needle = "          mkdir -p dispatch-recovery1-evidence\n"
pub = replace_once(pub, needle, needle + failed_proof)

# Bind the fresh recovery publisher/trigger bytes to their own attempt-1 solver-free PR review.
recovery_review = r'''          gh api --paginate --slurp "repos/$GITHUB_REPOSITORY/actions/workflows/$RECOVERY_REVIEW_WORKFLOW/runs?event=pull_request&per_page=100" > dispatch-recovery1-evidence/recovery-review-pages.json
          python - <<'PY'
          import json
          pages=json.load(open('dispatch-recovery1-evidence/recovery-review-pages.json')); runs=[r for p in pages for r in p.get('workflow_runs',[])]
          good=[r for r in runs if int(r.get('run_attempt') or 0)==1 and r.get('status')=='completed' and r.get('conclusion')=='success']
          if not good: raise SystemExit('no successful attempt-1 publisher recovery1 review')
          json.dump(good,open('dispatch-recovery1-evidence/recovery-review-candidates.json','w'),indent=2)
          PY
          RECOVERY_REVIEW_RUN=''
          for RID in $(python -c "import json; print(' '.join(str(x['id']) for x in json.load(open('dispatch-recovery1-evidence/recovery-review-candidates.json'))))"); do
            rm -rf dispatch-recovery1-evidence/recovery-review-artifact; mkdir dispatch-recovery1-evidence/recovery-review-artifact
            if gh run download "$RID" -n "$RECOVERY_REVIEW_ARTIFACT" -D dispatch-recovery1-evidence/recovery-review-artifact >/dev/null 2>&1; then
              if python - <<'PY'
          import json,subprocess
          from pathlib import Path
          hits=list(Path('dispatch-recovery1-evidence/recovery-review-artifact').rglob('review-receipt.json'))
          if len(hits)!=1: raise SystemExit(1)
          r=json.load(open(hits[0]))
          pub_blob=subprocess.check_output(['git','hash-object','.github/workflows/avps-v2-postconsumption-recovery2-dispatch-publisher-recovery1.yml'],text=True).strip()
          trig_blob=subprocess.check_output(['git','hash-object','.github/workflows/avps-v2-postconsumption-recovery2-publisher-recovery1-trigger-bridge.yml'],text=True).strip()
          if r.get('status')!='PASS_AVPS_V2_RECOVERY2_ORDINAL43_PUBLISHER_RECOVERY1_SOLVER_FREE': raise SystemExit(1)
          if r.get('publisherBlob')!=pub_blob or r.get('triggerBlob')!=trig_blob: raise SystemExit(1)
          if not r.get('failedPublisherPreConsumption'): raise SystemExit(1)
          PY
              then RECOVERY_REVIEW_RUN="$RID"; break; fi
            fi
          done
          test -n "$RECOVERY_REVIEW_RUN"
'''
needle = "          test -n \"$MATCHED\"\n          export MATCHED\n          echo \"review_run=$MATCHED\" >> \"$GITHUB_OUTPUT\"\n"
pub = replace_once(pub, needle, needle + "\n" + recovery_review)

pub = pub.replace("'status':'PRE_DISPATCH_FENCE_PASS_ZERO_RUNTIME'", "'status':'RECOVERY1_PRE_DISPATCH_FENCE_PASS_ZERO_RUNTIME'")
pub = pub.replace("'dispatchCreated':False}", "'dispatchCreated':False,'failedPublisherRun':int(os.environ['FAILED_PUBLISHER_RUN']),'failedPublisherPreConsumption':True,'recoveryReviewRun':int(os.environ['RECOVERY_REVIEW_RUN'])}")
pub = pub.replace("'status':'DISPATCH_PUBLISHED_ZERO_RUNTIME'", "'status':'RECOVERY1_DISPATCH_PUBLISHED_ZERO_RUNTIME'")

# Fresh trigger identity targets only the fresh recovery publisher and refuses duplicate recovery runs.
trig = trig.replace("name: AVPS v2 publisher postconsumption-recovery2-ordinal43 trigger bridge", "name: AVPS v2 recovery2 ordinal43 publisher recovery1 trigger bridge")
trig = trig.replace("run-name: AVPS v2 postconsumption recovery2 ordinal 43 publisher postconsumption-recovery2-ordinal43 trigger bridge", "run-name: AVPS v2 postconsumption recovery2 ordinal 43 publisher recovery1 trigger bridge")
trig = trig.replace("dispatch-trigger/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery2-ordinal-43-publisher", "dispatch-trigger/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery2-ordinal-43-publisher-recovery1")
trig = trig.replace("dispatch-triggers/avps-v2-postconsumption-recovery2-ordinal43-publisher.txt", "dispatch-triggers/avps-v2-postconsumption-recovery2-ordinal43-publisher-recovery1.txt")
trig = trig.replace("avps-v2-postconsumption-recovery2-dispatch-publisher.yml", PUBLISHER_NAME)
trig = trig.replace("postconsumption-recovery2-ordinal-43-publisher-trigger-bridge", "postconsumption-recovery2-ordinal-43-publisher-recovery1-trigger-bridge")
trig = trig.replace("trigger-postconsumption-recovery2-ordinal43", "trigger-postconsumption-recovery2-ordinal43-recovery1")
trig = trig.replace("AVPS_V2_POSTCONSUMPTION_RECOVERY2_ORDINAL43_PUBLISHER_TRIGGER_V1", "AVPS_V2_POSTCONSUMPTION_RECOVERY2_ORDINAL43_PUBLISHER_RECOVERY1_TRIGGER_V1")
trig = trig.replace("publisher postconsumption-recovery2-ordinal43", "publisher recovery1 postconsumption-recovery2-ordinal43")
trig = trig.replace("postconsumption-recovery2-ordinal43-publisher-run-ids.txt", "postconsumption-recovery2-ordinal43-publisher-recovery1-run-ids.txt")
trig = trig.replace("trigger-postconsumption-recovery2-ordinal43-evidence", "trigger-postconsumption-recovery2-ordinal43-recovery1-evidence")
trig = trig.replace("POSTCONSUMPTION_RECOVERY2_ORDINAL43_PRE_TRIGGER_BRIDGE_PASS_ZERO_RUNTIME", "POSTCONSUMPTION_RECOVERY2_ORDINAL43_PUBLISHER_RECOVERY1_PRE_TRIGGER_BRIDGE_PASS_ZERO_RUNTIME")
trig = trig.replace("POSTCONSUMPTION_RECOVERY2_ORDINAL43_PUBLISHER_WORKFLOW_DISPATCH_REQUESTED_BY_ZERO_RUNTIME_BRIDGE", "POSTCONSUMPTION_RECOVERY2_ORDINAL43_PUBLISHER_RECOVERY1_WORKFLOW_DISPATCH_REQUESTED_BY_ZERO_RUNTIME_BRIDGE")
trig = trig.replace("avps-v2-publisher-postconsumption-recovery2-ordinal43-trigger-bridge-pre", "avps-v2-publisher-recovery1-postconsumption-recovery2-ordinal43-trigger-bridge-pre")
trig = trig.replace("avps-v2-publisher-postconsumption-recovery2-ordinal43-trigger-bridge-post", "avps-v2-publisher-recovery1-postconsumption-recovery2-ordinal43-trigger-bridge-post")

# The recovery trigger must bind the failed original publisher and require it to remain pre-consumption.
trig = replace_once(trig, "  SCIENTIFIC_ORDINAL: '43'\n", "  SCIENTIFIC_ORDINAL: '43'\n  FAILED_PUBLISHER_RUN: '33290906727'\n  FAILED_PUBLISHER_JOB: '99202243870'\n")
proof = r'''          gh api "repos/$GITHUB_REPOSITORY/actions/runs/$FAILED_PUBLISHER_RUN" > failed-original-publisher.json
          gh api "repos/$GITHUB_REPOSITORY/actions/runs/$FAILED_PUBLISHER_RUN/jobs" > failed-original-publisher-jobs.json
          python - <<'PY'
          import json,os
          r=json.load(open('failed-original-publisher.json')); jobs=json.load(open('failed-original-publisher-jobs.json')).get('jobs',[])
          if r.get('id')!=int(os.environ['FAILED_PUBLISHER_RUN']) or r.get('run_attempt')!=1 or r.get('conclusion')!='failure': raise SystemExit('failed publisher drift')
          hit=[j for j in jobs if j.get('id')==int(os.environ['FAILED_PUBLISHER_JOB'])]
          if len(hit)!=1: raise SystemExit('failed publisher job missing')
          steps={s.get('name'):s.get('conclusion') for s in hit[0].get('steps',[])}
          if steps.get('Fresh zero-runtime pre-dispatch fence')!='failure': raise SystemExit('failed publisher step drift')
          for n in ('Create exact dispatch ref and consumed marker once','Upload zero-runtime publisher evidence before science dispatch','Explicitly dispatch exact science workflow from main'):
              if steps.get(n)!='skipped': raise SystemExit('failed publisher crossed consumption boundary')
          PY
'''
needle = "          test \"$(git show origin/main:.github/workflows/$PUBLISHER_WORKFLOW | git hash-object --stdin)\" = \"$PUBLISHER_BLOB\"\n"
trig = replace_once(trig, needle, needle + proof)

# PUBLISHER_BLOB is filled after publisher generation so the trigger binds exact reviewed bytes.
publisher_blob_placeholder = "__RECOVERY_PUBLISHER_BLOB__"
trig = replace_once(trig, "  PUBLISHER_BLOB: a5349ad644f93bf45fba79c58cee2ec7b0dd6359", f"  PUBLISHER_BLOB: {publisher_blob_placeholder}")

review = f'''name: AVPS v2 recovery2 ordinal43 publisher recovery1 review

on:
  pull_request:
    branches: [main]
    paths:
      - '.github/workflows/{PUBLISHER_NAME}'
      - '.github/workflows/{TRIGGER_NAME}'
      - '.github/workflows/{REVIEW_NAME}'

permissions:
  actions: read
  contents: read
  issues: read
  pull-requests: read

jobs:
  review:
    runs-on: ubuntu-24.04
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          ref: ${{{{ github.event.pull_request.head.sha }}}}
          fetch-depth: 0
          persist-credentials: false
      - name: Verify exact recovery-only scope and failed pre-consumption identity
        shell: bash
        env:
          GH_TOKEN: ${{{{ github.token }}}}
          PR_BASE: ${{{{ github.event.pull_request.base.sha }}}}
          PR_HEAD: ${{{{ github.event.pull_request.head.sha }}}}
          FAILED_PUBLISHER_RUN: '{FAILED_RUN}'
          FAILED_PUBLISHER_JOB: '{FAILED_JOB}'
        run: |
          set -euo pipefail
          test "$GITHUB_EVENT_NAME" = pull_request
          test "$GITHUB_RUN_ATTEMPT" = 1
          test "$(git rev-parse HEAD)" = "$PR_HEAD"
          git diff --name-only "$PR_BASE"..."$PR_HEAD" | sort > changed.txt
          cat > expected.txt <<'EOF'
          .github/workflows/{PUBLISHER_NAME}
          .github/workflows/{REVIEW_NAME}
          .github/workflows/{TRIGGER_NAME}
          EOF
          sort -o expected.txt expected.txt
          diff -u expected.txt changed.txt
          test "$(git diff --name-only "$PR_BASE"..."$PR_HEAD" | grep -Ec '^experiments/|^scientific-tools/' || true)" = 0
          gh api "repos/$GITHUB_REPOSITORY/actions/runs/$FAILED_PUBLISHER_RUN" > failed-run.json
          gh api "repos/$GITHUB_REPOSITORY/actions/runs/$FAILED_PUBLISHER_RUN/jobs" > failed-jobs.json
          python - <<'PY'
          import json,os,subprocess
          from pathlib import Path
          r=json.load(open('failed-run.json')); jobs=json.load(open('failed-jobs.json')).get('jobs',[])
          if r.get('id')!=int(os.environ['FAILED_PUBLISHER_RUN']) or r.get('run_attempt')!=1 or r.get('event')!='workflow_dispatch' or r.get('conclusion')!='failure': raise SystemExit('failed publisher identity drift')
          hit=[j for j in jobs if j.get('id')==int(os.environ['FAILED_PUBLISHER_JOB'])]
          if len(hit)!=1 or hit[0].get('conclusion')!='failure': raise SystemExit('failed publisher job drift')
          steps={{s.get('name'):s.get('conclusion') for s in hit[0].get('steps',[])}}
          if steps.get('Fresh zero-runtime pre-dispatch fence')!='failure': raise SystemExit('failed publisher failure-step drift')
          for n in ('Create exact dispatch ref and consumed marker once','Upload zero-runtime publisher evidence before science dispatch','Explicitly dispatch exact science workflow from main'):
              if steps.get(n)!='skipped': raise SystemExit(f'prior publisher crossed boundary: {{n}}')
          pub=Path('.github/workflows/{PUBLISHER_NAME}').read_text()
          trig=Path('.github/workflows/{TRIGGER_NAME}').read_text()
          for token in ('GITHUB_TOKEN: ${{{{ github.token }}}}','FAILED_PUBLISHER_RUN','Fresh recovery1 zero-runtime pre-dispatch fence','avps-v2-postconsumption-recovery2-science.yml'):
              if token not in pub: raise SystemExit(f'missing recovery publisher invariant: {{token}}')
          for token in ('FAILED_PUBLISHER_RUN','publisher-recovery1','{PUBLISHER_NAME}'):
              if token not in trig: raise SystemExit(f'missing recovery trigger invariant: {{token}}')
          for text in (pub,trig):
              for forbidden in ('uvspec ','mc_photons','Taylor','Jerusalem'):
                  if forbidden in text: raise SystemExit(f'forbidden new science/result token: {{forbidden}}')
          out={{'schemaVersion':1,'status':'PASS_AVPS_V2_RECOVERY2_ORDINAL43_PUBLISHER_RECOVERY1_SOLVER_FREE','headSha':os.environ['PR_HEAD'],'baseSha':os.environ['PR_BASE'],'publisherBlob':subprocess.check_output(['git','hash-object','.github/workflows/{PUBLISHER_NAME}'],text=True).strip(),'triggerBlob':subprocess.check_output(['git','hash-object','.github/workflows/{TRIGGER_NAME}'],text=True).strip(),'failedPublisherRun':int(os.environ['FAILED_PUBLISHER_RUN']),'failedPublisherPreConsumption':True,'scientificOrdinal':43,'dispatchPresent':False,'scientificRuntime':False,'solver':False,'results':False,'levelB':False,'holdout':False,'production':False}}
          Path('review-receipt.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\\n')
          PY
      - uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7.0.1
        with:
          name: avps-v2-recovery2-ordinal43-publisher-recovery1-review
          path: |
            changed.txt
            review-receipt.json
          if-no-files-found: error
          compression-level: 0
'''

# Bind exact recovery publisher blob into the trigger after final publisher text is known.
pub_blob = hashlib.sha1((f"blob {len(pub.encode('utf-8'))}\0".encode() + pub.encode('utf-8'))).hexdigest()
trig = trig.replace(publisher_blob_placeholder, pub_blob)

OUT.mkdir(parents=True, exist_ok=True)
(OUT / PUBLISHER_NAME).write_text(pub, encoding="utf-8")
(OUT / TRIGGER_NAME).write_text(trig, encoding="utf-8")
(OUT / REVIEW_NAME).write_text(review, encoding="utf-8")
manifest = {
    "schemaVersion": 1,
    "status": "GENERATED_AVPS_V2_RECOVERY2_ORDINAL43_PUBLISHER_RECOVERY1_ZERO_RUNTIME",
    "sourcePublisher": str(SOURCE_PUBLISHER.relative_to(ROOT)),
    "sourceTrigger": str(SOURCE_TRIGGER.relative_to(ROOT)),
    "failedPublisherRun": int(FAILED_RUN),
    "failedPublisherJob": int(FAILED_JOB),
    "outputs": {
        PUBLISHER_NAME: {"sha256": sha256_text(pub)},
        TRIGGER_NAME: {"sha256": sha256_text(trig)},
        REVIEW_NAME: {"sha256": sha256_text(review)},
    },
    "scientificOrdinal": 43,
    "scienceChanged": False,
    "authorizationChanged": False,
    "seedIdentityChanged": False,
    "dispatchCreated": False,
    "scientificRuntime": False,
}
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(manifest, indent=2, sort_keys=True))
