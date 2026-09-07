from __future__ import annotations
import importlib.util, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
WORKFLOW=ROOT/'review/lunar-scattered-light-source-contract-v1/lunar-finite-disk-exec004-science-workflow-v1.yml'
RUNTIME=ROOT/'review/lunar-scattered-light-source-contract-v1/lunar_finite_disk_exec004.py'
ADAPTER=ROOT/'review/lunar-scattered-light-source-contract-v1/lunar_mystic_input_exec004_reptran_adapter.py'

def require(text: str, token: str): assert token in text, token

def load_runtime():
    spec=importlib.util.spec_from_file_location('lunar_exec004_review',RUNTIME); assert spec and spec.loader
    mod=importlib.util.module_from_spec(spec); sys.modules[spec.name]=mod; spec.loader.exec_module(mod); return mod

def main():
    text=WORKFLOW.read_text(); runtime_text=RUNTIME.read_text(); adapter_text=ADAPTER.read_text(); runtime=load_runtime(); c=runtime.review_contract()
    assert c['status']=='FROZEN_EXEC004_REPTRAN_SCIENCE_RUNTIME_REVIEW_ONLY_NOT_AUTHORIZED'
    assert c['executionId']=='lunar-finite-disk-transfer-kernel-sensitivity-v1-exec004'
    assert c['control']['run']==34059309664 and c['control']['artifact']==9997398593 and c['control']['candidateSeedCount']==198
    assert c['control']['seedCanonicalSha256']=='9a29092f1708b3c8c46542967b29471689b9de3b293adadbc16c25410091e585'
    assert c['control']['rowsCanonicalSha256']=='9f6aa730fa7720fd985cfbda55ac49023f90be7de8d5f5bc931ab52aca77aa56'
    assert c['authorizationTimeRecheck']['head']=='74f70d2d5db29926c5d1833326d3469993cbbdb2'
    assert c['authorizationTimeRecheck']['run']==34065544069 and c['authorizationTimeRecheck']['artifact']==9999276308
    assert c['authorizationTimeRecheck']['proofSha256']=='0310413267de648fda91c1f0f683651d54ef55786a2e5244de67664260f5750b'
    assert c['reptranPrerequisites']['molecularAbsorption']=='reptran' and c['reptranPrerequisites']['historicalCrsFallbackAllowed'] is False
    s=c['frozenScience']; assert (s['wavelengthNm'],s['geometryCount'],s['directionsPerGeometry'],s['totalDirectionalCases'])==(550.0,6,33,198)
    assert s['photonHistoriesPerDirectionalCase']==5_000_000 and s['totalPhotonHistories']==990_000_000 and s['mandatorySpectralFollowOnNm']==[450.0,650.0,750.0]
    assert all(v is False for v in c['protectedBoundaries'].values())
    assert not runtime.AUTH_PATH.exists()
    try: runtime.load_authorization()
    except runtime.Exec004Error as exc: assert 'authorization file absent' in str(exc)
    else: raise AssertionError('review branch self-authorized')
    require(text,'execution/lunar-finite-disk-transfer-kernel-sensitivity-v1-exec004')
    require(text,"CONTROL_RUN_ID: '34059309664'"); require(text,"RECHECK_RUN_ID: '34065544069'")
    require(text,'FENCE_STAGE: LUNAR_FINITE_DISK_EXEC004_FINAL_PREFLIGHT_GLOBAL_SCAN_V1')
    require(text,'shard: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17]')
    require(text,'test "$(wc -l < work/shard-case-paths.txt)" -eq 11')
    require(text,'rubin-libradtran=2.0.6=py312pl5321he9373c2_1')
    require(text,'lunar_finite_disk_exec004.py prepare-shard'); require(text,'lunar_finite_disk_exec004.py evaluate')
    require(text,'merge-multiple: true'); require(text,'WRITE_QUIET_END'); require(text,'len(matches)==1')
    require(text,"'executionIdentityAndCandidateSeedsConsumedByThisAttempt':True")
    require(text,'mandatorySpectralFollowOnNm'); require(text,"p['molecularAbsorption']=='reptran'")
    pre=text.index('Fresh tracked-tree and repository-global collision recheck before solver'); solver=text.index('uses: mamba-org/setup-micromamba@v2'); assert pre<solver
    require(adapter_text, "line.startswith('mol_abs_param crs')")
    require(adapter_text,"lines().count('mol_abs_param reptran')") if False else None
    require(adapter_text,"text.splitlines().count('mol_abs_param reptran') != 1")
    require(adapter_text,"customSourceReptranConsumptionCapabilityVerified")
    require(runtime_text,"'molAbsParam': 'reptran'"); require(runtime_text,"'historicalCrsFallbackAllowed': False")
    require(runtime_text, "'taylorOrJerusalemUsed': False")
    print('lunar finite-disk exec004 REPTRAN science workflow contract tests passed')

if __name__=='__main__': main()
