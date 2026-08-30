#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC_SCIENCE = ROOT / '.github/workflows/avps-v2-postconsumption-recovery2-science.yml'
SRC_PUBLISHER = ROOT / '.github/workflows/avps-v2-postconsumption-recovery2-dispatch-publisher.yml'
SRC_TRIGGER = ROOT / '.github/workflows/avps-v2-postconsumption-recovery2-publisher-trigger-bridge.yml'
OUT = ROOT / 'generated-avps-v2-recovery3-ordinal44-execution-package'

SCIENCE_NAME = 'avps-v2-postconsumption-recovery3-science.yml'
PUBLISHER_NAME = 'avps-v2-postconsumption-recovery3-dispatch-publisher.yml'
TRIGGER_NAME = 'avps-v2-postconsumption-recovery3-publisher-trigger-bridge.yml'

SOURCE_BLOBS = {
    'science': 'bd973b2ea039ee696f26a600104932a8619d5633',
    'publisher': 'a5349ad644f93bf45fba79c58cee2ec7b0dd6359',
    'trigger': 'c102d173aba9f0aa952b25459a9b4a30626c7936',
}

AUTH_HEAD = 'dd3a4c692af505389e9feb1e5f5480fa389110a3'
AUTH_PARENT = 'd8cd4af807e7a8f11ed39fdc579ed92adf866aab'
AUTH_PR = '718'
AUTH_REVIEW_RUN = '33319037610'
AUTH_REVIEW_ARTIFACT = '9734515864'
AUTH_REVIEW_DIGEST = 'sha256:bfef625ebb0a45f8a59e38cb46b64ded9e7d9f3fcbb895355144a3af5044eed7'
AUTH_JSON_PATH = 'review/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3-authorization-control-v1/authorization.json'
AUTH_JSON_BLOB = '927956c0c01d02d3b025b141bb1c8b72d873dfc7'
AUTH_BRANCH = 'authorization/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3-ordinal-44'
DISPATCH_BRANCH = 'dispatch/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3-ordinal-44'
EXECUTION_KEY = 'aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3:numerical:44'
ALLOCATION_MARKER = f'ORDINAL44_AVPS_V2_POSTCONSUMPTION_RECOVERY3_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED commit={AUTH_HEAD} parent={AUTH_PARENT} pr=718'
CONSUMED_MARKER = 'ORDINAL44_AVPS_V2_POSTCONSUMPTION_RECOVERY3_DISPATCH_CONSUMED'
CANDIDATE_SEED = 'd2817b1ea4f2bdc8cb1842e565b099b015e4e28c5874482629fadc450069d9bf'
CANDIDATE_ROWS = 'b6a519eadacdb99ea53c52d483c8acfeba05829643cb988de21682a53fc47896'
AUTH_SEED_LEDGER_PATH = 'review/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3-seed-freshness-v1/seed_ledger.py'
AUTH_SEED_LEDGER_BLOB = 'a4fc0b95c3627a310c0c17a1ae8b89701511b3b8'
PACKAGE_REVIEW_WORKFLOW = 'avps-v2-recovery3-ordinal44-execution-package-review.yml'
PACKAGE_REVIEW_ARTIFACT = 'avps-v2-recovery3-ordinal44-execution-package-review'


def git_blob(raw: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def require_blob(path: Path, expected: str) -> str:
    raw = path.read_bytes()
    got = git_blob(raw)
    if got != expected:
        raise SystemExit(f'source blob drift for {path}: {got} != {expected}')
    return raw.decode('utf-8')


def replace_once(text: str, old: str, new: str) -> str:
    n = text.count(old)
    if n != 1:
        raise SystemExit(f'expected one occurrence of {old!r}, found {n}')
    return text.replace(old, new, 1)


def replace_all_present(text: str, old: str, new: str, *, min_count: int = 1) -> str:
    n = text.count(old)
    if n < min_count:
        raise SystemExit(f'expected at least {min_count} occurrences of {old!r}, found {n}')
    return text.replace(old, new)


def replace_env(text: str, key: str, value: str) -> str:
    pat = re.compile(rf'(?m)^  {re.escape(key)}: .*?$')
    hits = pat.findall(text)
    if len(hits) != 1:
        raise SystemExit(f'env field {key} count drift: {len(hits)}')
    return pat.sub(f'  {key}: {value}', text, count=1)


def transform_common_env(text: str) -> str:
    vals = {
        'AUTH_BRANCH': AUTH_BRANCH,
        'AUTH_HEAD': AUTH_HEAD,
        'AUTH_PARENT': AUTH_PARENT,
        'AUTH_PR': f"'{AUTH_PR}'",
        'AUTH_REVIEW_RUN': f"'{AUTH_REVIEW_RUN}'",
        'AUTH_REVIEW_ARTIFACT': f"'{AUTH_REVIEW_ARTIFACT}'",
        'AUTH_REVIEW_DIGEST': AUTH_REVIEW_DIGEST,
        'DISPATCH_BRANCH': DISPATCH_BRANCH,
        'EXECUTION_KEY': EXECUTION_KEY,
        'ALLOCATION_MARKER': ALLOCATION_MARKER,
        'CONSUMED_MARKER': CONSUMED_MARKER,
        'CANDIDATE_SEED_SHA256': CANDIDATE_SEED,
        'CANDIDATE_ROWS_SHA256': CANDIDATE_ROWS,
        'AUTH_SEED_LEDGER_PATH': AUTH_SEED_LEDGER_PATH,
        'AUTH_SEED_LEDGER_BLOB': AUTH_SEED_LEDGER_BLOB,
    }
    for k, v in vals.items():
        text = replace_env(text, k, v)
    return text


def transform_science(src: str) -> str:
    t = transform_common_env(src)
    t = replace_once(t, 'run-name: AVPS v2 postconsumption recovery2 ordinal 43 | ${{ inputs.dispatch_ref }}',
                     'run-name: AVPS v2 postconsumption recovery3 ordinal 44 | ${{ inputs.dispatch_ref }}')
    t = replace_once(t, 'group: avps-v2-postconsumption-recovery2-ordinal-43-science',
                     'group: avps-v2-postconsumption-recovery3-ordinal-44-science')
    t = replace_all_present(t,
        'review/avps-v2-recovery2-posttransport-authorization-control-recovery-v1/authorization.json',
        AUTH_JSON_PATH, min_count=2)
    t = replace_all_present(t, '9db4602cd2877161b9c4d6d5ffad27409c52dd3f', AUTH_JSON_BLOB, min_count=2)
    t = replace_all_present(t, "p['number']!=647", "p['number']!=718", min_count=1)
    t = replace_all_present(t, "'authorizationPr':647", "'authorizationPr':718", min_count=1)
    t = replace_all_present(t, "'scientificOrdinal':43", "'scientificOrdinal':44", min_count=1)
    t = replace_all_present(t, "'scientificOrdinal': 43", "'scientificOrdinal': 44", min_count=1) if "'scientificOrdinal': 43" in t else t
    t = replace_all_present(t,
        'actions/workflows/avps-v2-postconsumption-recovery2-science.yml/runs?event=workflow_dispatch',
        'actions/workflows/avps-v2-postconsumption-recovery3-science.yml/runs?event=workflow_dispatch', min_count=1)
    t = t.replace('AVPS_V2_POSTCONSUMPTION_RECOVERY2_', 'AVPS_V2_POSTCONSUMPTION_RECOVERY3_')
    t = t.replace('postconsumption-recovery2-ordinal43', 'postconsumption-recovery3-ordinal44')
    t = t.replace('postconsumption-recovery2-ordinal-43', 'postconsumption-recovery3-ordinal-44')
    if 'review/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery2-science-transport-v1/native_authorization_seed_transport.py' not in t:
        raise SystemExit('reviewed native seed transport dependency was lost')
    for forbidden in ('5fd0c82cb14a02ace38a5a7be30b8b075ccae298',
                      '33277629404', '9722104370',
                      'ORDINAL43_AVPS_V2_POSTCONSUMPTION_RECOVERY2_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED'):
        if forbidden in t:
            raise SystemExit(f'stale recovery2 authorization token in science output: {forbidden}')
    return t


def package_review_block() -> str:
    return r'''          gh api --paginate --slurp "repos/$GITHUB_REPOSITORY/actions/workflows/$PACKAGE_REVIEW_WORKFLOW/runs?event=pull_request&per_page=100" > dispatch-evidence/package-review-pages.json
          python - <<'PY'
          import json
          pages=json.load(open('dispatch-evidence/package-review-pages.json')); runs=[r for p in pages for r in p.get('workflow_runs',[])]
          good=[r for r in runs if int(r.get('run_attempt') or 0)==1 and r.get('status')=='completed' and r.get('conclusion')=='success']
          if not good: raise SystemExit('no successful attempt-1 recovery3 ordinal44 execution-package review')
          json.dump(good,open('dispatch-evidence/package-review-candidates.json','w'),indent=2)
          PY
          MATCHED=''
          for RID in $(python -c "import json; print(' '.join(str(x['id']) for x in json.load(open('dispatch-evidence/package-review-candidates.json'))))"); do
            rm -rf dispatch-evidence/package-review-artifact; mkdir dispatch-evidence/package-review-artifact
            if gh run download "$RID" -n "$PACKAGE_REVIEW_ARTIFACT" -D dispatch-evidence/package-review-artifact >/dev/null 2>&1; then
              if python - <<'PY'
          import json,subprocess
          from pathlib import Path
          hits=list(Path('dispatch-evidence/package-review-artifact').rglob('review-receipt.json'))
          if len(hits)!=1: raise SystemExit(1)
          r=json.load(open(hits[0]))
          science_blob=subprocess.check_output(['git','hash-object','.github/workflows/avps-v2-postconsumption-recovery3-science.yml'],text=True).strip()
          publisher_blob=subprocess.check_output(['git','hash-object','.github/workflows/avps-v2-postconsumption-recovery3-dispatch-publisher.yml'],text=True).strip()
          trigger_blob=subprocess.check_output(['git','hash-object','.github/workflows/avps-v2-postconsumption-recovery3-publisher-trigger-bridge.yml'],text=True).strip()
          if r.get('status')!='PASS_AVPS_V2_RECOVERY3_ORDINAL44_EXECUTION_PACKAGE_REVIEW_ZERO_RUNTIME': raise SystemExit(1)
          if r.get('scienceBlob')!=science_blob or r.get('publisherBlob')!=publisher_blob or r.get('triggerBlob')!=trigger_blob: raise SystemExit(1)
          if r.get('scientificOrdinal')!=44 or r.get('solverExecutionPerformed') is not False or r.get('dispatchCreated') is not False: raise SystemExit(1)
          PY
              then MATCHED="$RID"; break; fi
            fi
          done
          test -n "$MATCHED"
          export MATCHED
          echo "review_run=$MATCHED" >> "$GITHUB_OUTPUT"
'''


def transform_publisher(src: str) -> str:
    t = transform_common_env(src)
    t = replace_once(t, 'name: AVPS v2 dispatch publisher', 'name: AVPS v2 recovery3 ordinal44 dispatch publisher')
    t = replace_once(t, 'run-name: AVPS v2 postconsumption recovery2 ordinal 43 zero-runtime dispatch publisher',
                     'run-name: AVPS v2 postconsumption recovery3 ordinal 44 zero-runtime dispatch publisher')
    t = replace_once(t, 'group: avps-v2-postconsumption-recovery2-ordinal-43-dispatch-publisher',
                     'group: avps-v2-postconsumption-recovery3-ordinal-44-dispatch-publisher')
    t = replace_once(t,
        '        env:\n          GH_TOKEN: ${{ github.token }}\n        run: |\n          set -euo pipefail\n          test "$GITHUB_EVENT_NAME" = workflow_dispatch',
        '        env:\n          GH_TOKEN: ${{ github.token }}\n          GITHUB_TOKEN: ${{ github.token }}\n        run: |\n          set -euo pipefail\n          test "$GITHUB_EVENT_NAME" = workflow_dispatch')
    t = replace_all_present(t,
        'review/avps-v2-recovery2-posttransport-authorization-control-recovery-v1/authorization.json',
        AUTH_JSON_PATH, min_count=0) if 'review/avps-v2-recovery2-posttransport-authorization-control-recovery-v1/authorization.json' in t else t
    t = replace_all_present(t, "p['number']!=647", "p['number']!=718", min_count=1)
    t = replace_all_present(t, "'authorizationPr':647", "'authorizationPr':718", min_count=1)
    t = replace_all_present(t, "'scientificOrdinal':43", "'scientificOrdinal':44", min_count=1)
    t = replace_all_present(t,
        'actions/workflows/avps-v2-postconsumption-recovery2-science.yml/runs?event=workflow_dispatch',
        'actions/workflows/avps-v2-postconsumption-recovery3-science.yml/runs?event=workflow_dispatch', min_count=1)
    t = replace_once(t, 'test -s .github/workflows/avps-v2-postconsumption-recovery2-science.yml',
                     'test -s .github/workflows/avps-v2-postconsumption-recovery3-science.yml')
    t = replace_once(t, 'test -s .github/workflows/avps-v2-postconsumption-recovery2-dispatch-publisher.yml',
                     'test -s .github/workflows/avps-v2-postconsumption-recovery3-dispatch-publisher.yml')
    t = replace_once(t, "sha('.github/workflows/avps-v2-postconsumption-recovery2-science.yml'),'publisherWorkflowSha256':sha('.github/workflows/avps-v2-postconsumption-recovery2-dispatch-publisher.yml')",
                     "sha('.github/workflows/avps-v2-postconsumption-recovery3-science.yml'),'publisherWorkflowSha256':sha('.github/workflows/avps-v2-postconsumption-recovery3-dispatch-publisher.yml')")
    pat = re.compile(r'''          gh api --paginate --slurp "repos/\$GITHUB_REPOSITORY/actions/workflows/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery2-implementation-generator-v1-review\.yml/runs\?event=pull_request&per_page=100".*?          echo "review_run=\$MATCHED" >> "\$GITHUB_OUTPUT"\n''', re.S)
    if len(pat.findall(t)) != 1:
        raise SystemExit('could not isolate legacy recovery2 implementation-review block')
    t = pat.sub(package_review_block(), t, count=1)
    anchor = "  HISTORICAL_SEED_LEDGER_BLOB: 491d1b6653bea0fcc5275269723a76aa1af52300\n"
    t = replace_once(t, anchor, anchor + f"  PACKAGE_REVIEW_WORKFLOW: {PACKAGE_REVIEW_WORKFLOW}\n  PACKAGE_REVIEW_ARTIFACT: {PACKAGE_REVIEW_ARTIFACT}\n")
    t = replace_all_present(t, 'if latest!=42:', 'if latest!=43:', min_count=1)
    t = replace_all_present(t, 'max(ordinals)!=43', 'max(ordinals)!=44', min_count=1)
    t = t.replace('ordinal43 allocation marker', 'ordinal44 allocation marker')
    t = t.replace('ordinal43 consumed marker', 'ordinal44 consumed marker')
    t = t.replace('PASS_GLOBAL_ORDINAL43_ALLOCATED_NOT_CONSUMED_PRE_DISPATCH', 'PASS_GLOBAL_ORDINAL44_ALLOCATED_NOT_CONSUMED_PRE_DISPATCH')
    t = t.replace("'candidateScientificOrdinal':43", "'candidateScientificOrdinal':44")
    t = t.replace('AVPS_V2_POSTCONSUMPTION_RECOVERY2_', 'AVPS_V2_POSTCONSUMPTION_RECOVERY3_')
    t = t.replace('postconsumption-recovery2-ordinal43', 'postconsumption-recovery3-ordinal44')
    t = t.replace('postconsumption-recovery2-ordinal-43', 'postconsumption-recovery3-ordinal-44')
    t = replace_all_present(t,
        'avps-v2-postconsumption-recovery2-dispatch-publisher-ordinal-43',
        'avps-v2-postconsumption-recovery3-dispatch-publisher-ordinal-44', min_count=1)
    t = replace_once(t,
        "PAYLOAD='{\"ref\":\"main\",\"inputs\":{\"dispatch_ref\":\"dispatch/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery2-ordinal-43\"}}'",
        "PAYLOAD='{\"ref\":\"main\",\"inputs\":{\"dispatch_ref\":\"dispatch/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3-ordinal-44\"}}'")
    t = replace_once(t,
        'repos/$GITHUB_REPOSITORY/actions/workflows/avps-v2-postconsumption-recovery2-science.yml/dispatches',
        'repos/$GITHUB_REPOSITORY/actions/workflows/avps-v2-postconsumption-recovery3-science.yml/dispatches')
    if 'aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery2-implementation-generator-v1-review.yml' in t:
        raise SystemExit('legacy implementation review block survived')
    for forbidden in ('5fd0c82cb14a02ace38a5a7be30b8b075ccae298', '33277629404', '9722104370'):
        if forbidden in t:
            raise SystemExit(f'stale recovery2 authorization token in publisher output: {forbidden}')
    return t


def transform_trigger(src: str, publisher_blob: str) -> str:
    t = src
    t = replace_once(t, 'name: AVPS v2 publisher postconsumption-recovery2-ordinal43 trigger bridge',
                     'name: AVPS v2 publisher postconsumption-recovery3-ordinal44 trigger bridge')
    t = t.replace('postconsumption recovery2 ordinal 43', 'postconsumption recovery3 ordinal 44')
    t = t.replace('postconsumption-recovery2-ordinal43', 'postconsumption-recovery3-ordinal44')
    t = t.replace('postconsumption-recovery2-ordinal-43', 'postconsumption-recovery3-ordinal-44')
    t = t.replace('POSTCONSUMPTION_RECOVERY2_ORDINAL43', 'POSTCONSUMPTION_RECOVERY3_ORDINAL44')
    t = t.replace('AVPS_V2_POSTCONSUMPTION_RECOVERY2_ORDINAL43', 'AVPS_V2_POSTCONSUMPTION_RECOVERY3_ORDINAL44')
    t = replace_env(t, 'ACTIVATION_BRANCH', 'dispatch-trigger/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3-ordinal-44-publisher')
    t = replace_env(t, 'ACTIVATION_MARKER', 'dispatch-triggers/avps-v2-postconsumption-recovery3-ordinal44-publisher.txt')
    t = replace_env(t, 'PUBLISHER_WORKFLOW', PUBLISHER_NAME)
    t = replace_env(t, 'PUBLISHER_BLOB', publisher_blob)
    t = replace_env(t, 'SCIENTIFIC_ORDINAL', "'44'")
    t = t.replace("'scientificOrdinal':43", "'scientificOrdinal':44")
    return t


def main() -> int:
    science_src = require_blob(SRC_SCIENCE, SOURCE_BLOBS['science'])
    publisher_src = require_blob(SRC_PUBLISHER, SOURCE_BLOBS['publisher'])
    trigger_src = require_blob(SRC_TRIGGER, SOURCE_BLOBS['trigger'])

    science = transform_science(science_src)
    publisher = transform_publisher(publisher_src)
    publisher_blob = git_blob(publisher.encode())
    trigger = transform_trigger(trigger_src, publisher_blob)

    OUT.mkdir(parents=True, exist_ok=True)
    outputs = {SCIENCE_NAME: science, PUBLISHER_NAME: publisher, TRIGGER_NAME: trigger}
    for name, text in outputs.items():
        (OUT / name).write_text(text, encoding='utf-8')

    manifest = {
        'schemaVersion': 1,
        'status': 'GENERATED_AVPS_V2_RECOVERY3_ORDINAL44_EXECUTION_PACKAGE_ZERO_RUNTIME_NOT_PUBLISHED_NOT_DISPATCHED',
        'sourceBlobs': SOURCE_BLOBS,
        'authorizationHead': AUTH_HEAD,
        'authorizationParent': AUTH_PARENT,
        'authorizationPr': 718,
        'authorizationReviewRun': int(AUTH_REVIEW_RUN),
        'authorizationReviewArtifact': int(AUTH_REVIEW_ARTIFACT),
        'authorizationReviewDigest': AUTH_REVIEW_DIGEST,
        'scientificOrdinal': 44,
        'executionKey': EXECUTION_KEY,
        'candidateSeedCanonicalSha256': CANDIDATE_SEED,
        'candidateRowsCanonicalSha256': CANDIDATE_ROWS,
        'frozenScienceDesignChanged': False,
        'caseCount': 360,
        'commonRandomNumberGroupCount': 72,
        'statesPerGroup': 5,
        'photonHistoriesPerCase': 20_000_000,
        'outputs': {name: {'sha256': sha256(text.encode()), 'gitBlobSha1': git_blob(text.encode())} for name, text in outputs.items()},
        'dispatchCreated': False,
        'scientificRuntime': False,
        'solverExecution': False,
        'resultOpening': False,
        'levelBOpening': False,
        'protectedHoldoutOpening': False,
        'taylorOrJerusalemUsed': False,
        'invalidatedLowAltitudeEvidenceUsed': False,
        'productionAuthorized': False,
    }
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    print(json.dumps(manifest, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
