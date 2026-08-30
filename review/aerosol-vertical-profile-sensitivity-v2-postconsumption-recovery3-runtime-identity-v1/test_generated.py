from __future__ import annotations
import importlib.util, json, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
GEN=ROOT/"generated-avps-v2-recovery3-ordinal44-runtime-identity"

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise SystemExit(f"cannot load {path}")
    m=importlib.util.module_from_spec(spec); sys.modules[name]=m; spec.loader.exec_module(m); return m

def expect_refusal(fn,label):
    try: fn()
    except Exception: return True
    raise SystemExit(f"expected refusal did not occur: {label}")

def main(auth_path: Path):
    adapter=load("recovery3_test_adapter",GEN/"runtime_adapter.py")
    executor=load("recovery3_test_executor",GEN/"executor.py")
    aggregator=load("recovery3_test_aggregator",GEN/"aggregator.py")
    auth=json.loads(auth_path.read_text()); adapter.validate_authorization(auth)
    cases=adapter.authorized_case_universe(auth)
    if len(cases)!=360 or len({r["groupId"] for r in cases})!=72: raise SystemExit("case/group cardinality drift")
    groups={}
    for r in cases: groups.setdefault(r["groupId"],[]).append(r)
    if any(len(v)!=5 or len({x["stateId"] for x in v})!=5 or len({x["seed"] for x in v})!=1 for v in groups.values()): raise SystemExit("CRN five-state structure drift")
    seed=adapter.seed_receipt()
    if seed!={"seedCount":72,"seedCanonicalSha256":"d2817b1ea4f2bdc8cb1842e565b099b015e4e28c5874482629fadc450069d9bf","rowsCanonicalSha256":"b6a519eadacdb99ea53c52d483c8acfeba05829643cb988de21682a53fc47896"}: raise SystemExit("seed receipt drift")
    guard={"status":"EXACT_ONE_USE_AVPS_V2_POSTCONSUMPTION_RECOVERY3_DISPATCH_AUTHORIZED","scientificOrdinal":44,"executionKey":"aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3:numerical:44","authorizationHead":"dd3a4c692af505389e9feb1e5f5480fa389110a3","authorizationPr":718,"dispatchBranch":"dispatch/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3-ordinal-44","dispatchBranchHeadSha":"dd3a4c692af505389e9feb1e5f5480fa389110a3","workflowRunId":123456789,"workflowRunAttempt":1,"allocationMarkerCount":1,"consumedMarkerCount":1,"candidateSeedCanonicalSha256":"d2817b1ea4f2bdc8cb1842e565b099b015e4e28c5874482629fadc450069d9bf","preSolverRepositoryGlobalSeedRecheckPassed":True,"fourAliasDataTreeSha256":"5e1814dd36cf861fd85477a97607299248f8272268df7bf428d31bbb6aa4354a","solverExecutionPermittedNow":True,"githubRerun":False,"retryAllowed":False,"resumeAllowed":False}
    executor.validate_guard(guard)
    old=dict(guard); old.update({"status":"EXACT_ONE_USE_AVPS_V2_DISPATCH_AUTHORIZED","scientificOrdinal":41,"executionKey":"aerosol-vertical-profile-sensitivity-v2:numerical:41","authorizationHead":"d5f5e4d9d19d7ede573fecae68565a92baabbec3","authorizationPr":604,"dispatchBranch":"dispatch/aerosol-vertical-profile-sensitivity-v2-ordinal-41","dispatchBranchHeadSha":"d5f5e4d9d19d7ede573fecae68565a92baabbec3","candidateSeedCanonicalSha256":"02f624d582e9b2caba6b920d65a5e8a8bc8fc1a2693623bc2f73abf5d3f706d2"})
    expect_refusal(lambda:executor.validate_guard(old),"old ordinal41 guard")
    bad=dict(auth); bad.update({"stageId":"aerosol-vertical-profile-sensitivity-v2","status":"AUTHORIZED_PENDING_SEPARATE_DISPATCH","scientificOrdinal":41,"executionKey":"aerosol-vertical-profile-sensitivity-v2:numerical:41"})
    expect_refusal(lambda:adapter.validate_authorization(bad),"old ordinal41 authorization")
    expect_refusal(lambda:executor.execute_case(Path('.'),Path('none'),Path('none'),Path('none'),Path('none'),'none',Path('none'),Path('none'),Path('none'),allow_execution=False),"review-mode solver refusal")
    closed=aggregator.structural_closed_aggregate_fixture(ROOT,auth_path)
    receipt={"schemaVersion":1,"status":"PASS_AVPS_V2_RECOVERY3_ORDINAL44_RUNTIME_IDENTITY_ZERO_RUNTIME_REVIEW","authorizationAccepted":True,"recovery3GuardAccepted":True,"oldOrdinal41GuardAccepted":False,"oldOrdinal41AuthorizationAccepted":False,"caseCount":360,"groupCount":72,"statesPerGroup":5,"seedReceipt":seed,"closedAggregate":closed,"scientificRuntime":False,"solverExecution":False,"resultsOpened":False,"levelB":False,"holdout":False,"taylorOrJerusalemUsed":False,"newMappingAuthorized":False}
    Path("runtime-identity-review-receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print(json.dumps(receipt,sort_keys=True))

if __name__=="__main__":
    if len(sys.argv)!=2: raise SystemExit("usage: test_generated.py <authorization.json>")
    main(Path(sys.argv[1]))
