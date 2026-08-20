from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from core import (
    BASE_CORE_GIT_BLOB_SHA1,
    BASE_DESIGN_GIT_BLOB_SHA1,
    Refusal,
    canonical_sha256,
    git_blob_sha1,
    raw_sha256,
    validate_design,
    validate_seed_audit_for_freeze,
    write_manifest,
)

STAGE_ID='aerosol-family-challenge-v2-r7-freeze'
EXACT_BLOBS={
    'analysis-contract.v3.json':'d2411cd7636d3d34a0b9132a48fbcea4ccf35d76',
    'analysis.py':'50b64b5c8a7a9d28a1c7174c1a1fda8d7380799d',
    'derived_channels.py':'ccfd04d4c21188966351f4257e92893d7ce340c7',
    'adapter.py':'108af0a95274ee88fccf9d51d32f88ef0186bfaf',
    'wavelength-grid-1nm.dat':'3bb3db96580d555ef758f57cabd6cac55b61cebb',
}

def _verify_science_bytes(package: Path, analysis_contract: Path) -> dict:
    if analysis_contract.resolve() != (package/'analysis-contract.v3.json').resolve():
        raise Refusal('R7 analysis contract must be the bound local copy')
    for name,expected in EXACT_BLOBS.items():
        path=package/name
        if not path.is_file() or git_blob_sha1(path)!=expected:
            raise Refusal(f'R7 bound scientific byte drift: {name}')
    contract=json.loads(analysis_contract.read_text())
    exact={'schemaVersion':3,'stageId':'aerosol-family-challenge-v2-analysis','status':'FROZEN_BEFORE_RESULTS','resultsOpened':False,'scientificExecutionAuthorized':False}
    for key,value in exact.items():
        if contract.get(key)!=value:
            raise Refusal(f'R7 analysis contract boundary drift: {key}')
    return contract

def freeze(design_path: Path, analysis_contract: Path, seed_audit_path: Path, manifest_out: Path, freeze_out: Path) -> dict:
    design=json.loads(design_path.read_text())
    audit=json.loads(seed_audit_path.read_text())
    validate_design(design)
    validate_seed_audit_for_freeze(audit,design_path,design)
    package=design_path.parent
    contract=_verify_science_bytes(package,analysis_contract)
    manifest=write_manifest(design_path,manifest_out)
    manifest['status']='FROZEN_MANIFEST_SEED_FRESHNESS_PROVEN_REVIEW_ONLY'
    manifest['seedFreshnessStatus']=audit['status']
    manifest['seedAuditRawSha256']=raw_sha256(seed_audit_path)
    manifest['seedAuditRepositoryHead']=audit['repositoryHead']
    manifest_out.write_text(json.dumps(manifest,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8',newline='\n')
    record={
      'schemaVersion':4,
      'stageId':STAGE_ID,
      'status':'FROZEN_REVIEW_PACKAGE_NOT_AUTHORIZATION',
      'scientificExecutionAuthorized':False,
      'solverExecutionAuthorized':False,
      'resultsOpened':False,
      'continuationReason':design['continuationReason'],
      'scientificScopeChange':'NONE_SEEDS_AND_GOVERNANCE_IDENTITY_ONLY',
      'boundR6DesignGitBlobSha':BASE_DESIGN_GIT_BLOB_SHA1,
      'boundR6CoreGitBlobSha':BASE_CORE_GIT_BLOB_SHA1,
      'sourceBaseMainSha':audit['sourceBaseMainSha'],
      'seedAuditExactHead':audit['repositoryHead'],
      'authorizationTimeSeedRecheckStillRequired':True,
      'designRawSha256':raw_sha256(design_path),
      'analysisContractRawSha256':raw_sha256(analysis_contract),
      'analysisContractCanonicalSha256':canonical_sha256(contract),
      'analysisImplementationRawSha256':raw_sha256(package/'analysis.py'),
      'derivedChannelsRawSha256':raw_sha256(package/'derived_channels.py'),
      'seedAuditRawSha256':raw_sha256(seed_audit_path),
      'wavelengthGridRawSha256':raw_sha256(package/'wavelength-grid-1nm.dat'),
      'wavelengthGridGitBlobSha':git_blob_sha1(package/'wavelength-grid-1nm.dat'),
      'manifestRawSha256':raw_sha256(manifest_out),
      'manifestCanonicalSha256':canonical_sha256(manifest),
    }
    freeze_out.write_text(json.dumps(record,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8',newline='\n')
    return record

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--design',type=Path,required=True)
    ap.add_argument('--analysis-contract',type=Path,required=True)
    ap.add_argument('--seed-audit',type=Path,required=True)
    ap.add_argument('--manifest-out',type=Path,required=True)
    ap.add_argument('--freeze-out',type=Path,required=True)
    args=ap.parse_args()
    try:
        print(json.dumps(freeze(args.design,args.analysis_contract,args.seed_audit,args.manifest_out,args.freeze_out),indent=2,sort_keys=True)+'\n',end='')
        return 0
    except Exception as exc:
        print(json.dumps({'stageId':STAGE_ID,'status':'REFUSED','reason':str(exc)},indent=2,sort_keys=True)+'\n',end='',file=sys.stderr)
        return 2

if __name__=='__main__':
    raise SystemExit(main())
