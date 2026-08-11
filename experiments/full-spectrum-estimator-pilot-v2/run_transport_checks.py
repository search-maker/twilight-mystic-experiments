#!/usr/bin/env python3
from __future__ import annotations
import argparse, compileall, json, os, re, ssl, subprocess, sys, urllib.error
from pathlib import Path
from unittest import mock

HERE=Path(__file__).resolve().parent
MODULES=['freshness.py','github_surface.py','package_evidence.py','authorization_guard.py','dispatch_guard.py','execution_guard.py','executor.py','run_transport_checks.py','test_transport_v6.py']
WORKFLOWS=['full-spectrum-estimator-pilot-v2-transport-review-v6.yml','full-spectrum-estimator-pilot-v2-authorization-review-v6.yml','full-spectrum-estimator-pilot-v2-ordinal14-execution-v6.yml']

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--repository-root',type=Path,required=True); a=ap.parse_args(); root=a.repository_root.resolve()
    env=os.environ.copy(); env['TRANSPORT_TEST_REPOSITORY_ROOT']=str(root)
    test=subprocess.run([sys.executable,'-m','unittest','-v',str(root/'experiments/full-spectrum-estimator-pilot-v2/test_transport_v6.py')],cwd=root,env=env,text=True,capture_output=True)
    sys.stdout.write(test.stdout); sys.stderr.write(test.stderr)
    if test.returncode: return test.returncode
    m=re.search(r'Ran (\d+) tests',test.stderr+test.stdout); count=int(m.group(1)) if m else None
    if count!=67: raise SystemExit(f'expected 67 transport tests, observed {count}')
    sys.path.insert(0,str(root/'experiments/full-spectrum-estimator-pilot-v2'))
    import freshness, github_surface
    # Reproduce the exact Python urllib failure shape observed on the hosted
    # runner: SSLCertVerificationError wrapped as URLError. The verified gh API
    # fallback must be used for this case, while ordinary URLError remains a
    # hard failure.
    wrapped_tls=urllib.error.URLError(ssl.SSLCertVerificationError(1,'certificate verify failed'))
    sentinel=[{'name':'main'}]
    with mock.patch.object(github_surface,'_api_with_urllib',side_effect=wrapped_tls), mock.patch.object(github_surface,'_api_with_gh',return_value=sentinel) as fallback:
        if github_surface._api('https://api.github.com/repos/search-maker/twilight-mystic-experiments/branches?page=1','secret') != sentinel:
            raise SystemExit('urllib-wrapped TLS verification failure did not use verified fallback')
        fallback.assert_called_once()
    with mock.patch.object(github_surface,'_api_with_urllib',side_effect=urllib.error.URLError('network')), mock.patch.object(github_surface,'_api_with_gh') as fallback:
        try:
            github_surface._api('https://api.github.com/repos/search-maker/twilight-mystic-experiments/branches?page=1','secret')
        except urllib.error.URLError:
            pass
        else:
            raise SystemExit('non-TLS URLError was incorrectly swallowed by GitHub API fallback')
        fallback.assert_not_called()
    if freshness.positive_candidate_claims('ordinal 14 allocated/reserved/consumed: **false**'):
        raise SystemExit('boolean-false ordinal-14 status was misclassified as a positive claim')
    if len(freshness.positive_candidate_claims('We allocated ordinal 14 for this run.')) != 1:
        raise SystemExit('positive ordinal-14 allocation claim was not detected')
    markdown_examples=(
      'false negative: `Although no dispatch exists, ordinal 14 is authorized.`',
      'regression fixture: `We allocated ordinal 14 for this run.`',
      '> Ordinal 14 is authorized.',
      '```text\nOrdinal 14 is authorized.\n```',
      '~~~\nWe allocated ordinal 14 for this run.\n~~~',
    )
    for example in markdown_examples:
        if freshness.positive_candidate_claims(example):
            raise SystemExit(f'Markdown quotation/example was misclassified as live ordinal-14 state: {example!r}')
    if len(freshness.positive_candidate_claims('Although no dispatch exists, ordinal 14 is authorized.')) != 1:
        raise SystemExit('plain live positive ordinal-14 state was hidden by Markdown-example filtering')
    if len(freshness.positive_candidate_claims('We allocated ordinal 14 for this run.')) != 1:
        raise SystemExit('plain live positive ordinal-14 allocation was hidden by Markdown-example filtering')
    base={'branches':[{'name':'dispatch/tier1-precision-continuation-wave3-ordinal13-v1','commit':{'sha':'1'*40}}],'pulls':[],'issues':[],'issue60Comments':[],'activeAuthorizationPathOnMainExists':False}
    pr_title='Authorize '+freshness.TITLE
    pr_checks=[
      {'id':101,'event':'pull_request','head_branch':freshness.AUTH_BRANCH,'display_title':pr_title,'name':'Full-spectrum estimator pilot v2 authorization review v6','path':'.github/workflows/full-spectrum-estimator-pilot-v2-authorization-review-v6.yml'},
      {'id':102,'event':'pull_request','head_branch':freshness.AUTH_BRANCH,'display_title':pr_title,'name':'Full-spectrum estimator pilot v2 transport review v6','path':'.github/workflows/full-spectrum-estimator-pilot-v2-transport-review-v6.yml'},
      {'id':103,'event':'pull_request','head_branch':freshness.AUTH_BRANCH,'display_title':pr_title,'name':'Corrected spectral convergence contract','path':'.github/workflows/contract.yml'},
    ]
    s=github_surface.build_surface({**base,'runs':pr_checks})
    if s['candidatePriorScientificRunCount'] != 0:
        raise SystemExit('non-scientific PR checks were misclassified as prior ordinal-14 scientific runs')
    scientific={'id':104,'event':'push','head_branch':freshness.DISPATCH_BRANCH,'display_title':freshness.TITLE,'name':freshness.TITLE+' execution v6','path':github_surface.SCIENTIFIC_WORKFLOW}
    s=github_surface.build_surface({**base,'runs':pr_checks+[scientific]},current_run_id=999)
    if s['candidatePriorScientificRunCount'] != 1:
        raise SystemExit('real push-only ordinal-14 scientific run was not detected exactly once')
    failed_head='a'*40
    failed_branch={'name':freshness.AUTH_BRANCH,'commit':{'sha':failed_head}}
    failed_pr={'number':112,'state':'closed','merged_at':None,'title':'Failed ordinal 14 authorization review','body':'Authorization for ordinal 14 was refused.','head':{'ref':freshness.AUTH_BRANCH,'sha':failed_head}}
    failed_review={'id':105,'event':'pull_request','head_branch':freshness.AUTH_BRANCH,'head_sha':failed_head,'display_title':'Failed ordinal 14 authorization review','name':'Full-spectrum estimator pilot v2 authorization review v6','path':github_surface.AUTHORIZATION_REVIEW_WORKFLOW,'run_attempt':1,'status':'completed','conclusion':'failure'}
    stale=github_surface.build_surface({**base,'branches':base['branches']+[failed_branch],'pulls':[failed_pr],'runs':[failed_review]})
    if stale['authorizationBranchReusableAfterFailedReview'] is not True:
        raise SystemExit('exact failed-review authorization ref was not recognized as reusable')
    freshness.validate_preauthorization(stale)
    success_review={**failed_review,'id':106,'conclusion':'success'}
    not_reusable=github_surface.build_surface({**base,'branches':base['branches']+[failed_branch],'pulls':[failed_pr],'runs':[failed_review,success_review]})
    if not_reusable['authorizationBranchReusableAfterFailedReview'] is not False:
        raise SystemExit('authorization ref with a successful review was incorrectly reusable')
    try:
        freshness.validate_preauthorization(not_reusable)
    except freshness.FreshnessRefusal:
        pass
    else:
        raise SystemExit('preauthorization accepted a ref with prior successful authorization review')
    for name in MODULES:
        if not compileall.compile_file(str(root/'experiments/full-spectrum-estimator-pilot-v2'/name),quiet=1,force=True): raise SystemExit(f'compile failed: {name}')
    try:
        import yaml
    except Exception as exc: raise SystemExit(f'PyYAML unavailable: {exc}')
    for name in WORKFLOWS:
        p=root/'.github/workflows'/name
        value=yaml.safe_load(p.read_text())
        if not isinstance(value,dict): raise SystemExit(f'workflow YAML did not parse to mapping: {name}')
    transport=(root/'.github/workflows'/WORKFLOWS[0]).read_text(); auth=(root/'.github/workflows'/WORKFLOWS[1]).read_text(); sci=(root/'.github/workflows'/WORKFLOWS[2]).read_text()
    for label,text in [('transport',transport),('authorization',auth)]:
        forbidden=('setup-micromamba','rubin-libradtran','command -v uvspec','--allow-execution','workflow_dispatch:','schedule:','repository_dispatch:')
        found=[x for x in forbidden if x in text]
        if found: raise SystemExit(f'{label} review execution surface violation: {found}')
    if 'workflow_dispatch:' in sci or 'schedule:' in sci or 'repository_dispatch:' in sci: raise SystemExit('scientific workflow exposes alternate trigger')
    static=subprocess.run([sys.executable,str(root/'experiments/full-spectrum-estimator-pilot-v2/package_evidence.py'),'verify-static','--repository-root',str(root)],cwd=root,text=True,capture_output=True)
    if static.returncode: sys.stderr.write(static.stderr); return static.returncode
    summary={'status':'TRANSPORT_V6_CHECKS_PASS','testsPassed':67,'pythonCompile':True,'workflowYamlParsed':3,'reviewWorkflowScientificExecutionSurface':False,'authorizationReviewScientificExecutionSurface':False,'scientificExecutionPerformed':False,'authorizationCreated':False,'dispatchCreated':False,'ordinalAllocatedReservedOrConsumed':False,'freshnessBooleanFalseRegression':True,'scientificRunClassificationRegression':True,'failedAuthorizationRefReuseRegression':True,'markdownExampleIsolationRegression':True,'wrappedTlsFallbackRegression':True}
    print(json.dumps(summary,indent=2,sort_keys=True)); return 0
if __name__=='__main__': raise SystemExit(main())
