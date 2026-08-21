from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import shutil
from pathlib import Path
from typing import Any

STAGE = "aerosol-family-challenge-v2-r8-timeout-recovery-v1-combined-analysis"
SOURCE_RUN_ID = 32447101887
SOURCE_ATTEMPT = 1
SOURCE_HEAD = "cca5194a5b81ea28ca9cc8417b5887936afa1fd6"
SOURCE_MANIFEST_SHA256 = "c031d6daf6a0e37240b93786394036d12bebecbba7894b6aebbad62b45a2016f"
RECOVERY_MANIFEST_SHA256 = "7bb4597784ed3dfd4f6fd062f652dc3d8c7fddb3a339c56e0ca893ce97cbcabb"
AFFECTED_GROUP = "afc2-d04-g06-late-opposite-high-aerosol-aod10-r2"
MISSING_SOURCE_CASE = AFFECTED_GROUP + "-rural-fall-winter"
SOURCE_PREFIX = "aerosol-family-v2-r8-case-"
RECOVERY_PREFIX = "afc2-r8-timeout-recovery-v1-case-"
SOURCE_AGGREGATE_BLOB = "6444a2170d19c09539a924c3028d75c78e521be2"
SOURCE_ANALYSIS_BLOB = "50b64b5c8a7a9d28a1c7174c1a1fda8d7380799d"
SOURCE_DERIVED_BLOB = "ccfd04d4c21188966351f4257e92893d7ce340c7"
SOURCE_ANALYSIS_CONTRACT_BLOB = "d2411cd7636d3d34a0b9132a48fbcea4ccf35d76"

class CombinedRefusal(RuntimeError):
    pass


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_blob_sha1(path: Path) -> str:
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()


def load(name: str, path: Path):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:
        raise CombinedRefusal(f"cannot import {path}")
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod


def rows_from_metadata(path: Path) -> list[dict[str, Any]]:
    value=json.loads(path.read_text())
    if isinstance(value, dict):
        rows=value.get("artifacts", [])
    elif isinstance(value, list) and all(isinstance(page, dict) and isinstance(page.get("artifacts"), list) for page in value):
        rows=[row for page in value for row in page["artifacts"]]
    elif isinstance(value, list):
        rows=value
    else:
        rows=[]
    if not isinstance(rows,list):
        raise CombinedRefusal(f"artifact metadata is not a list: {path}")
    return rows


def build_effective_manifest(source: dict[str, Any], recovery: dict[str, Any]) -> dict[str, Any]:
    source_cases=source.get("cases")
    recovery_cases=recovery.get("cases")
    if not isinstance(source_cases,list) or len(source_cases)!=576:
        raise CombinedRefusal("source manifest must contain exactly 576 cases")
    if not isinstance(recovery_cases,list) or len(recovery_cases)!=8:
        raise CombinedRefusal("recovery manifest must contain exactly eight cases")
    by_id={str(r["caseId"]):copy.deepcopy(r) for r in source_cases}
    if len(by_id)!=576:
        raise CombinedRefusal("source case IDs not unique")
    affected={case_id for case_id,row in by_id.items() if row.get("groupId")==AFFECTED_GROUP}
    if len(affected)!=8 or MISSING_SOURCE_CASE not in affected:
        raise CombinedRefusal("source affected group identity/cardinality drift")
    replacement={str(r["caseId"]):r for r in recovery_cases}
    if set(replacement)!=affected:
        raise CombinedRefusal("recovery case IDs do not exactly replace affected group")
    seeds={r.get("seed") for r in recovery_cases}
    if len(seeds)!=1:
        raise CombinedRefusal("recovery replacement group does not have one shared CRN seed")
    for case_id,row in replacement.items():
        src=by_id[case_id]
        for key in (
            "caseId","groupId","analysisCellId","replicate","photonHistories","aerosolFamily","aerosolSeason",
            "sunDepressionDeg","targetAltitudeDeg","relativeAzimuthDeg","observerElevationM","aod550","albedo",
            "aerosolHazeCode","aerosolSeasonCode","aerosolVulcanCode","numericalMethod","geometryId","geometryTag",
        ):
            if row.get(key)!=src.get(key):
                raise CombinedRefusal(f"replacement changes frozen physical/design field {case_id}: {key}")
        src["seed"]=row["seed"]
        src["combinedRecoverySourceRunId"]=SOURCE_RUN_ID
        src["combinedRecoveryOriginalSeed"]=row.get("sourceOrdinal34Seed")
        src["combinedRecoveryReplacementStageId"]=recovery.get("stageId")
    effective=copy.deepcopy(source)
    effective["stageId"]=STAGE+"-effective-manifest"
    effective["status"]="FROZEN_EFFECTIVE_568_SOURCE_PLUS_8_REPLACEMENT_CASE_UNIVERSE"
    effective["sourceStageId"]=source.get("stageId")
    effective["sourceRunId"]=SOURCE_RUN_ID
    effective["recoveryStageId"]=recovery.get("stageId")
    effective["affectedGroupId"]=AFFECTED_GROUP
    effective["retainedSourceCaseCount"]=568
    effective["freshReplacementCaseCount"]=8
    effective["caseCount"]=576
    effective["cases"]=[by_id[str(r["caseId"])] for r in source_cases]
    groups=effective.get("groups")
    if isinstance(groups,list):
        for group in groups:
            if group.get("groupId")==AFFECTED_GROUP:
                group["seed"]=next(iter(seeds))
                group["combinedRecoveryReplacement"]=True
    return effective


def validate_source_code(root: Path) -> None:
    base=root/"experiments/aerosol-family-challenge-v2-r8"
    checks={
        base/"execution-candidate/aggregate_results.py":SOURCE_AGGREGATE_BLOB,
        base/"analysis.py":SOURCE_ANALYSIS_BLOB,
        base/"derived_channels.py":SOURCE_DERIVED_BLOB,
        base/"analysis-contract.v3.json":SOURCE_ANALYSIS_CONTRACT_BLOB,
    }
    for path,want in checks.items():
        got=git_blob_sha1(path)
        if got!=want:
            raise CombinedRefusal(f"source R8 analysis byte binding drift: {path} expected={want} observed={got}")


def validate_run_bindings(source_run: dict[str,Any], recovery_run: dict[str,Any]) -> None:
    if int(source_run.get("id") or 0)!=SOURCE_RUN_ID or int(source_run.get("run_attempt") or 0)!=1:
        raise CombinedRefusal("source run identity/attempt drift")
    if source_run.get("head_sha")!=SOURCE_HEAD:
        raise CombinedRefusal("source run head drift")
    if int(recovery_run.get("run_attempt") or 0)!=1 or recovery_run.get("conclusion")!="success":
        raise CombinedRefusal("fresh recovery run must be terminal successful attempt 1")
    if not str(recovery_run.get("head_branch") or "").startswith("dispatch/aerosol-family-challenge-v2-r8-timeout-recovery-v1-ordinal-"):
        raise CombinedRefusal("fresh recovery run branch identity drift")


def stage_artifacts(
    source_manifest: dict[str,Any], recovery_manifest: dict[str,Any],
    source_metadata: list[dict[str,Any]], recovery_metadata: list[dict[str,Any]],
    source_downloads: Path, recovery_downloads: Path, stage_root: Path,
) -> list[dict[str,Any]]:
    expected_source={str(r["caseId"]):r for r in source_manifest["cases"]}
    affected={case_id for case_id,row in expected_source.items() if row.get("groupId")==AFFECTED_GROUP}
    retain=set(expected_source)-affected
    src_case=[r for r in source_metadata if str(r.get("name") or "").startswith(SOURCE_PREFIX)]
    if len(src_case)!=575 or len({r.get("name") for r in src_case})!=575:
        raise CombinedRefusal(f"source run must expose exactly 575 unique case artifacts, got {len(src_case)}")
    src_ids={str(r["name"])[len(SOURCE_PREFIX):] for r in src_case}
    if set(expected_source)-src_ids != {MISSING_SOURCE_CASE}:
        raise CombinedRefusal("source case artifact universe differs from exactly one preregistered missing case")
    selected_src=[r for r in src_case if str(r["name"])[len(SOURCE_PREFIX):] in retain]
    if len(selected_src)!=568:
        raise CombinedRefusal("retained source artifact count must be 568")

    rec_expected={str(r["caseId"]):r for r in recovery_manifest["cases"]}
    rec_case=[r for r in recovery_metadata if str(r.get("name") or "").startswith(RECOVERY_PREFIX)]
    if len(rec_case)!=8 or len({r.get("name") for r in rec_case})!=8:
        raise CombinedRefusal("recovery run must expose exactly eight unique case artifacts")
    rec_ids={str(r["name"])[len(RECOVERY_PREFIX):] for r in rec_case}
    if rec_ids!=set(rec_expected) or rec_ids!=affected:
        raise CombinedRefusal("recovery artifact universe does not exactly replace affected group")

    stage_root.mkdir(parents=True,exist_ok=False)
    synthetic=[]
    for meta in selected_src:
        name=str(meta["name"]); src=source_downloads/name
        if not src.is_dir(): raise CombinedRefusal(f"missing downloaded source artifact: {name}")
        dest=stage_root/name
        shutil.copytree(src,dest)
        synthetic.append(dict(meta))
    for meta in rec_case:
        rname=str(meta["name"]); case_id=rname[len(RECOVERY_PREFIX):]
        src=recovery_downloads/rname
        if not src.is_dir(): raise CombinedRefusal(f"missing downloaded recovery artifact: {rname}")
        synthetic_name=SOURCE_PREFIX+case_id
        dest=stage_root/synthetic_name
        shutil.copytree(src,dest)
        row=dict(meta); row["sourceArtifactName"]=rname; row["name"]=synthetic_name
        synthetic.append(row)
    if len(synthetic)!=576 or len({r["name"] for r in synthetic})!=576:
        raise CombinedRefusal("synthetic effective artifact universe must be exactly 576 unique names")
    return synthetic


def combined(
    repository_root: Path, source_run_path: Path, recovery_run_path: Path, recovery_acquisition_path: Path,
    source_metadata_path: Path, recovery_metadata_path: Path,
    source_downloads: Path, recovery_downloads: Path, output_dir: Path,
) -> None:
    validate_source_code(repository_root)
    source_manifest_path=repository_root/"evidence/aerosol-family-challenge-v2-r8/manifest.frozen.json"
    recovery_manifest_path=repository_root/"evidence/aerosol-family-challenge-v2-r8-timeout-recovery-v1/manifest.frozen.json"
    if sha(source_manifest_path)!=SOURCE_MANIFEST_SHA256: raise CombinedRefusal("source manifest bytes drift")
    if sha(recovery_manifest_path)!=RECOVERY_MANIFEST_SHA256: raise CombinedRefusal("recovery manifest bytes drift")
    source_manifest=json.loads(source_manifest_path.read_text()); recovery_manifest=json.loads(recovery_manifest_path.read_text())
    source_run=json.loads(source_run_path.read_text()); recovery_run=json.loads(recovery_run_path.read_text())
    validate_run_bindings(source_run,recovery_run)
    recovery_acquisition=json.loads(recovery_acquisition_path.read_text())
    if recovery_acquisition.get("status")!="COMPLETE_EXACT_8_FRESH_REPLACEMENT_CASE_ARTIFACT_UNIVERSE":
        raise CombinedRefusal("fresh recovery acquisition gate did not pass")
    if int(recovery_acquisition.get("runId") or 0)!=int(recovery_run.get("id") or 0):
        raise CombinedRefusal("recovery acquisition/run identity drift")
    if recovery_acquisition.get("workflowRunAttempt")!=1 or recovery_acquisition.get("caseArtifactCount")!=8:
        raise CombinedRefusal("recovery acquisition attempt/cardinality drift")
    if recovery_acquisition.get("retainedSourceCaseCountForFutureCombinedAnalysis")!=568 or recovery_acquisition.get("effectiveCombinedCaseCount")!=576:
        raise CombinedRefusal("recovery acquisition combined-universe drift")
    if recovery_acquisition.get("scientificChannelsInterpreted") is not False:
        raise CombinedRefusal("recovery acquisition opened channels before combined analysis")
    source_meta=rows_from_metadata(source_metadata_path); recovery_meta=rows_from_metadata(recovery_metadata_path)
    effective=build_effective_manifest(source_manifest,recovery_manifest)
    output_dir.mkdir(parents=True,exist_ok=True)
    effective_path=output_dir/"effective-manifest.json"
    effective_path.write_text(json.dumps(effective,indent=2,sort_keys=True)+"\n")
    stage=output_dir/"effective-artifacts"
    synthetic=stage_artifacts(source_manifest,recovery_manifest,source_meta,recovery_meta,source_downloads,recovery_downloads,stage)
    synthetic_meta_path=output_dir/"effective-artifact-metadata.json"
    synthetic_meta_path.write_text(json.dumps({"artifacts":synthetic},indent=2,sort_keys=True)+"\n")
    freeze={
      "manifestRawSha256":sha(effective_path),
      "analysisContractRawSha256":sha(repository_root/"experiments/aerosol-family-challenge-v2-r8/analysis-contract.v3.json"),
      "analysisImplementationRawSha256":sha(repository_root/"experiments/aerosol-family-challenge-v2-r8/analysis.py"),
      "derivedChannelsRawSha256":sha(repository_root/"experiments/aerosol-family-challenge-v2-r8/derived_channels.py"),
    }
    freeze_path=output_dir/"effective-freeze.json"; freeze_path.write_text(json.dumps(freeze,indent=2,sort_keys=True)+"\n")
    agg=load("afc2_r8_frozen_aggregate_for_combined",repository_root/"experiments/aerosol-family-challenge-v2-r8/execution-candidate/aggregate_results.py")
    acquisition, analysis_out, spectral=agg.aggregate(
      repository_root,stage,synthetic_meta_path,effective_path,
      repository_root/"experiments/aerosol-family-challenge-v2-r8/analysis-contract.v3.json",freeze_path,
    )
    if acquisition.get("caseArtifactCount")!=576 or analysis_out.get("caseCount")!=576:
        raise CombinedRefusal("frozen R8 aggregate did not produce exact 576-case result")
    if analysis_out.get("comparisonGroupCount")!=72 or analysis_out.get("analysisCellCount")!=24:
        raise CombinedRefusal("frozen R8 analysis cardinality drift")
    if analysis_out.get("status")!="COMPLETED_PREREGISTERED_ANALYSIS":
        raise CombinedRefusal("frozen R8 analysis did not complete")
    (output_dir/"acquisition.json").write_text(json.dumps(acquisition,indent=2,sort_keys=True)+"\n")
    (output_dir/"analysis.json").write_text(json.dumps(analysis_out,indent=2,sort_keys=True)+"\n")
    (output_dir/"spectral-analysis.json").write_text(json.dumps(spectral,indent=2,sort_keys=True)+"\n")
    index={
      "schemaVersion":1,"stageId":STAGE,"status":"COMPLETED_FROZEN_COMBINED_ANALYSIS",
      "sourceRunId":SOURCE_RUN_ID,"sourceRunAttempt":1,"sourceRetainedCaseCount":568,
      "recoveryRunId":int(recovery_run["id"]),"recoveryRunAttempt":1,"freshReplacementCaseCount":8,
      "effectiveCaseCount":576,"comparisonGroupCount":72,"analysisCellCount":24,
      "sourceAffectedGroupArtifactsReused":False,"scientificSolverExecuted":False,
      "effectiveManifestRawSha256":sha(effective_path),"acquisitionRawSha256":sha(output_dir/"acquisition.json"),
      "analysisRawSha256":sha(output_dir/"analysis.json"),"spectralAnalysisRawSha256":sha(output_dir/"spectral-analysis.json"),
    }
    (output_dir/"combined-index.json").write_text(json.dumps(index,indent=2,sort_keys=True)+"\n")


def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--repository-root",type=Path,required=True)
    p.add_argument("--source-run",type=Path,required=True); p.add_argument("--recovery-run",type=Path,required=True); p.add_argument("--recovery-acquisition",type=Path,required=True)
    p.add_argument("--source-metadata",type=Path,required=True); p.add_argument("--recovery-metadata",type=Path,required=True)
    p.add_argument("--source-downloads",type=Path,required=True); p.add_argument("--recovery-downloads",type=Path,required=True)
    p.add_argument("--output-dir",type=Path,required=True)
    a=p.parse_args(); combined(a.repository_root,a.source_run,a.recovery_run,a.recovery_acquisition,a.source_metadata,a.recovery_metadata,a.source_downloads,a.recovery_downloads,a.output_dir); return 0

if __name__=="__main__": raise SystemExit(main())
