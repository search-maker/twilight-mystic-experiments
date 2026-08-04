from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import math
import os
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Any
STAGE_ID = 'g01-fixed-precision-diagnosis-execution-v1'
SOURCE_STAGE_ID = 'g01-fixed-precision-diagnosis-proposal-v1'
SOURCE_WORKFLOW_NAME = 'G01 fixed precision diagnosis proposal'
SOURCE_WORKFLOW_PATH = '.github/workflows/g01-fixed-precision-diagnosis-proposal.yml'
SOURCE_ARTIFACT_NAME = 'g01-fixed-precision-diagnosis-proposal-v1'
AUTH_PATH = Path('experiments/mystic-batch-v1/authorization.g01-fixed-precision-diagnosis.json')
AUTH_TEMPLATE_PATH = Path('experiments/mystic-batch-v1/authorization.g01-fixed-precision-diagnosis-template.json')
EXECUTION_KEY = 'g01-fixed-precision-diagnosis-v1:final:1'
AUTHORIZATION_ORDINAL = 1
GROUP_ID = 'g01-reference-bridge'
NEW_CASE_IDS = [f'g01pd-alis-b{i}' for i in range(5, 9)]
NEW_SEEDS = [84601, 84602, 84603, 84604]
TARGET_RSEM = 0.08
VROOM_MAX_RSEM = 0.1
RATIO_INTERVAL = [0.5, 2.0]
MIN_NODE_AGREEMENT = 0.8
NODES = 15

class StageError(RuntimeError):
    pass

def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise StageError(f'expected JSON object: {path}')
    return value

def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n'

def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()

def git(root: Path, *args: str) -> str:
    return subprocess.check_output(['git', *args], cwd=root, text=True).strip()

def artifact_by_name(listing: dict[str, Any], name: str, run_id: int) -> dict[str, Any]:
    artifacts = listing.get('artifacts')
    if not isinstance(artifacts, list):
        raise StageError('artifact listing missing')
    matches = [item for item in artifacts if isinstance(item, dict) and item.get('name') == name]
    if len(matches) != 1:
        raise StageError(f'expected one {name} artifact, found {len(matches)}')
    artifact = matches[0]
    if artifact.get('expired') is not False:
        raise StageError(f'artifact expired: {name}')
    if not isinstance(artifact.get('id'), int) or artifact['id'] < 1:
        raise StageError(f'artifact ID invalid: {name}')
    digest = artifact.get('digest')
    if not isinstance(digest, str) or not digest.startswith('sha256:') or len(digest) != 71:
        raise StageError(f'artifact digest invalid: {name}')
    workflow_run = artifact.get('workflow_run')
    if isinstance(workflow_run, dict) and workflow_run.get('id') not in {None, run_id}:
        raise StageError(f'artifact belongs to another run: {name}')
    return artifact

def source_audit(diagnosis_path: Path, proposal_path: Path, readiness_path: Path, source_run_path: Path, source_artifacts_path: Path) -> dict[str, Any]:
    diagnosis = load(diagnosis_path)
    proposal = load(proposal_path)
    readiness = load(readiness_path)
    source_run = load(source_run_path)
    source_artifacts = load(source_artifacts_path)
    required_run = {'status': 'completed', 'conclusion': 'success', 'run_attempt': 1, 'head_branch': 'main', 'name': SOURCE_WORKFLOW_NAME, 'path': SOURCE_WORKFLOW_PATH}
    stale = {key: (source_run.get(key), expected) for key, expected in required_run.items() if source_run.get(key) != expected}
    if stale:
        raise StageError(f'source diagnosis run mismatch: {stale}')
    if source_run.get('event') not in {'push', 'workflow_dispatch'}:
        raise StageError(f"source diagnosis event invalid: {source_run.get('event')}")
    run_id = source_run.get('id')
    head_sha = source_run.get('head_sha')
    if not isinstance(run_id, int) or run_id < 1 or not isinstance(head_sha, str) or len(head_sha) != 40:
        raise StageError('source diagnosis run identity invalid')
    artifact = artifact_by_name(source_artifacts, SOURCE_ARTIFACT_NAME, run_id)
    required_diagnosis = {'schemaVersion': 1, 'stageId': SOURCE_STAGE_ID, 'status': 'G01_MONTE_CARLO_PRECISION_DIAGNOSED', 'sourceRunId': 30875148389, 'groupId': GROUP_ID, 'failureMode': 'MONTE_CARLO_PRECISION_ONLY', 'structuralExecutionFailure': False, 'methodCompatibilityPassed': True, 'selectedAlisReferenceNm': 600.0, 'selectionDataExcludedFromAcceptanceDecision': True, 'singleBlockDeletionAuthorized': False, 'targetRelativeStandardErrorOfMean': TARGET_RSEM, 'recommendedFixedTotalBlocks': 8, 'recommendedAdditionalBlocks': 4, 'planningHeuristicIsNotAcceptanceEvidence': True}
    stale = {key: (diagnosis.get(key), expected) for key, expected in required_diagnosis.items() if diagnosis.get(key) != expected}
    if stale:
        raise StageError(f'diagnosis mismatch: {stale}')
    held = diagnosis.get('heldOutStatistics')
    vroom = diagnosis.get('frozenVroomStatistics')
    if not isinstance(held, dict) or held.get('blockCount') != 4 or not isinstance(vroom, dict) or vroom.get('blockCount') != 6:
        raise StageError('diagnosis method statistics invalid')
    if not TARGET_RSEM < float(held.get('relativeStandardErrorOfMean', math.inf)) < VROOM_MAX_RSEM:
        raise StageError('diagnosis held-out precision boundary changed')
    if float(vroom.get('relativeStandardErrorOfMean', math.inf)) > VROOM_MAX_RSEM:
        raise StageError('frozen VROOM precision changed')
    required_proposal = {'schemaVersion': 1, 'stageId': STAGE_ID, 'batchId': 'g01-fixed-precision-diagnosis-v1', 'status': 'PROPOSAL_ONLY_NOT_AUTHORIZATION', 'mode': 'scientific-proposal', 'proposalOnly': True, 'scientificExecution': False, 'scientificDiagnostic': True, 'successDoesNotAuthorizeProduction': True, 'sourceRunId': 30875148389, 'selectedGeometryIds': [GROUP_ID], 'selectedAlisReferenceNm': 600.0, 'existingHeldOutBlocks': [1, 2, 3, 4], 'newDiagnosticBlocks': [5, 6, 7, 8], 'executionAuthorizedByProposal': False, 'surrogateTrainingAutomaticallyAuthorized': False, 'productionModelReady': False, 'observationValidationRequired': True}
    stale = {key: (proposal.get(key), expected) for key, expected in required_proposal.items() if proposal.get(key) != expected}
    if stale:
        raise StageError(f'diagnostic proposal mismatch: {stale}')
    cases = proposal.get('cases')
    if not isinstance(cases, list) or len(cases) != 4:
        raise StageError('exactly four diagnostic cases required')
    if [case.get('ordinal') for case in cases] != [1, 2, 3, 4]:
        raise StageError('diagnostic case ordinals changed')
    if [case.get('caseId') for case in cases] != NEW_CASE_IDS:
        raise StageError('diagnostic case IDs changed')
    if [case.get('seed') for case in cases] != NEW_SEEDS:
        raise StageError('diagnostic seeds changed')
    if [case.get('block') for case in cases] != [5, 6, 7, 8]:
        raise StageError('diagnostic block sequence changed')
    if proposal.get('diagnosisRawSha256') != raw_sha256(diagnosis_path):
        raise StageError('diagnostic proposal no longer binds diagnosis')
    if any(case.get('groupId') != GROUP_ID or case.get('method') != 'alis' or case.get('block') not in {5, 6, 7, 8} or case.get('photonHistories') != 50000000 or float(case.get('alisSpectralImportanceSamplingNm', -1)) != 600.0 for case in cases):
        raise StageError('diagnostic case contract changed')
    limits = proposal.get('limits')
    if not isinstance(limits, dict) or limits != {'maximumCases': 4, 'maximumParallel': 4, 'perCaseTimeoutSeconds': 900, 'maximumPhotonHistoriesPerBlock': 50000000, 'maximumConfiguredMcPhotonsSum': 200000000}:
        raise StageError('diagnostic limits changed')
    analysis_plan = proposal.get('analysisPlan')
    if not isinstance(analysis_plan, dict) or analysis_plan.get('combinedAlisBlockCount') != 8 or analysis_plan.get('noAutomaticAdditionalBlocks') is not True:
        raise StageError('diagnostic analysis plan changed')
    required_readiness = {'schemaVersion': 1, 'stageId': SOURCE_STAGE_ID, 'status': 'G01_FIXED_PRECISION_DIAGNOSIS_PROPOSED_PENDING_SEPARATE_AUTHORIZATION', 'sourceRunId': 30875148389, 'diagnosisComplete': True, 'failureMode': 'MONTE_CARLO_PRECISION_ONLY', 'newCaseCount': 4, 'newConfiguredMcPhotonsSum': 200000000, 'scientificExecution': False, 'executionAuthorized': False, 'noAutomaticAdditionalBlocks': True, 'surrogateTrainingAuthorized': False, 'productionModelReady': False, 'observationValidationRequired': True}
    stale = {key: (readiness.get(key), expected) for key, expected in required_readiness.items() if readiness.get(key) != expected}
    if stale:
        raise StageError(f'diagnosis readiness mismatch: {stale}')
    return {'schemaVersion': 1, 'stageId': 'g01-fixed-precision-diagnosis-source-audit-v1', 'status': 'G01_DIAGNOSIS_SOURCE_AUDITED', 'sourceDiagnosisRunId': run_id, 'sourceDiagnosisHeadSha': head_sha, 'sourceDiagnosisEvent': source_run['event'], 'sourceDiagnosisArtifactId': artifact['id'], 'sourceDiagnosisArtifactDigest': artifact['digest'], 'diagnosisRawSha256': raw_sha256(diagnosis_path), 'proposalRawSha256': raw_sha256(proposal_path), 'readinessRawSha256': raw_sha256(readiness_path), 'caseCount': 4, 'configuredMcPhotonsSum': 200000000, 'scientificExecution': False, 'executionAuthorized': False, 'noAutomaticAdditionalBlocks': True, 'boundary': 'source diagnosis proposal audited; no syntax check, solver, or authorization'}

def build_manifest(proposal_path: Path, pilot_path: Path, source_audit_path: Path) -> dict[str, Any]:
    proposal = load(proposal_path)
    pilot = load(pilot_path)
    audit = load(source_audit_path)
    if audit.get('status') != 'G01_DIAGNOSIS_SOURCE_AUDITED' or audit.get('proposalRawSha256') != raw_sha256(proposal_path):
        raise StageError('source audit does not bind proposal')
    if proposal.get('stageId') != STAGE_ID or len(proposal.get('cases', [])) != 4:
        raise StageError('proposal invalid')
    if pilot.get('stageId') != 'cross-geometry-pilot-v1' or pilot.get('adapterId') != 'mystic-cross-geometry-v1':
        raise StageError('pilot source invalid')
    geometries = [item for item in pilot.get('geometries', []) if isinstance(item, dict) and item.get('geometryId') == GROUP_ID]
    if len(geometries) != 1:
        raise StageError('g01 geometry missing from pilot')
    runtime = pilot.get('runtime')
    frozen = pilot.get('frozenInputs')
    if not isinstance(runtime, dict) or not isinstance(frozen, dict):
        raise StageError('pilot runtime or frozen inputs missing')
    frozen = json.loads(json.dumps(frozen))
    frozen['alisSpectralImportanceSamplingNm'] = 600.0
    return {'schemaVersion': 1, 'stageId': STAGE_ID, 'batchId': proposal['batchId'], 'mode': 'scientific-proposal', 'proposalOnly': True, 'scientificExecution': False, 'scientificDiagnostic': True, 'successDoesNotAuthorizeProduction': True, 'adapterId': 'mystic-g01-fixed-precision-diagnosis-v1', 'sourceDiagnosisRunId': audit['sourceDiagnosisRunId'], 'sourceDiagnosisArtifactId': audit['sourceDiagnosisArtifactId'], 'sourceDiagnosisArtifactDigest': audit['sourceDiagnosisArtifactDigest'], 'diagnosisRawSha256': audit['diagnosisRawSha256'], 'sourceProposalRawSha256': raw_sha256(proposal_path), 'sourcePilotManifestRawSha256': raw_sha256(pilot_path), 'runtime': runtime, 'frozenInputs': frozen, 'geometries': geometries, 'cases': proposal['cases'], 'analysisPlan': proposal['analysisPlan'], 'limits': proposal['limits'], 'noAutomaticAdditionalBlocks': True, 'surrogateTrainingAutomaticallyAuthorized': False, 'productionModelReady': False, 'observationValidationRequired': True, 'boundary': 'four-case fixed precision diagnosis execution package only; no execution authorized by package'}

def bound_paths() -> dict[str, Path]:
    base = Path('experiments/mystic-batch-v1')
    return {'executionCodeRawSha256': base / 'g01_fixed_diagnostic_execution.py', 'executionAdapterRawSha256': base / 'g01_fixed_diagnostic_adapter.py', 'duplicateRunAuditRawSha256': base / 'duplicate_run_audit.py', 'runtimeProbeRawSha256': base / 'runtime_probe.py', 'executionWorkflowRawSha256': Path('.github/workflows/g01-fixed-precision-diagnosis-execution.yml'), 'runtimeLockRawSha256': base / 'runtime-lock.micromamba.json', 'executorRawSha256': base / 'scientific_case_executor.py', 'aggregateRawSha256': base / 'scientific_aggregate.py', 'auditRawSha256': base / 'scientific_audit.py', 'convergenceModuleRawSha256': base / 'cross_geometry_convergence_v2.py', 'baseAdapterRawSha256': base / 'cross_geometry_adapter.py', 'sourcePilotManifestRawSha256': base / 'manifest.cross-geometry-pilot.proposal.json'}

def guard(root: Path, authorization_path: Path, template_path: Path, manifest_path: Path, source_audit_path: Path, authorization_ref: str, execution_key: str, authorization_ordinal: int, require_context: bool=True, require_one_purpose: bool=True) -> dict[str, Any]:
    if execution_key != EXECUTION_KEY or authorization_ordinal != AUTHORIZATION_ORDINAL:
        raise StageError('execution key or authorization ordinal changed')
    if require_context:
        expected_context = {'GITHUB_ACTIONS': 'true', 'GITHUB_EVENT_NAME': 'workflow_dispatch', 'GITHUB_RUN_ATTEMPT': '1'}
        stale = {key: (os.getenv(key), value) for key, value in expected_context.items() if os.getenv(key) != value}
        if stale:
            raise StageError(f'wrong GitHub context: {stale}')
    authorization = load(root / authorization_path)
    template = load(root / template_path)
    manifest = load(manifest_path)
    source = load(source_audit_path)
    if authorization.keys() != template.keys() or template.get('authorized') is not False or template.get('authorizationOrdinal') != 0:
        raise StageError('authorization schema/template invalid')
    if manifest.get('stageId') != STAGE_ID or len(manifest.get('cases', [])) != 4:
        raise StageError('execution manifest invalid')
    if source.get('status') != 'G01_DIAGNOSIS_SOURCE_AUDITED':
        raise StageError('source audit invalid')
    expected = {'schemaVersion': 1, 'stageId': STAGE_ID, 'authorized': True, 'scientificExecution': True, 'scientificDiagnostic': True, 'successDoesNotAuthorizeProduction': True, 'executionKey': execution_key, 'sourceDiagnosisRunId': source['sourceDiagnosisRunId'], 'sourceDiagnosisArtifactId': source['sourceDiagnosisArtifactId'], 'sourceDiagnosisArtifactDigest': source['sourceDiagnosisArtifactDigest'], 'sourceDiagnosisAuditRawSha256': raw_sha256(source_audit_path), 'manifestRawSha256': raw_sha256(manifest_path), 'authorizationOrdinal': authorization_ordinal, 'exactAuthorizationCommit': None, 'consumed': False}
    for field, path in bound_paths().items():
        expected[field] = raw_sha256(root / path)
    stale = {key: (authorization.get(key), value) for key, value in expected.items() if authorization.get(key) != value}
    if stale:
        raise StageError(f'authorization stale: {stale}')
    head = git(root, 'rev-parse', 'HEAD')
    parent = git(root, 'rev-parse', 'HEAD^')
    if head != authorization_ref or authorization.get('exactAuthorizationParentCommit') != parent:
        raise StageError('authorization ref or parent mismatch')
    if require_one_purpose:
        changed = git(root, 'diff', '--name-only', parent, head).splitlines()
        if changed != [authorization_path.as_posix()]:
            raise StageError(f'authorization commit is not one-purpose: {changed}')
    return {'schemaVersion': 1, 'stageId': STAGE_ID, 'status': 'AUTHORIZED', 'executionKey': execution_key, 'authorizationRef': head, 'authorizationParentCommit': parent, 'authorizationOrdinal': authorization_ordinal, 'sourceDiagnosisRunId': source['sourceDiagnosisRunId'], 'sourceDiagnosisArtifactId': source['sourceDiagnosisArtifactId'], 'sourceDiagnosisArtifactDigest': source['sourceDiagnosisArtifactDigest'], 'caseCount': 4, 'configuredMcPhotonsSum': 200000000, 'maximumParallel': 4, 'perCaseTimeoutSeconds': 900, 'scientificExecution': True, 'scientificDiagnostic': True, 'noAutomaticAdditionalBlocks': True, 'successDoesNotAuthorizeProduction': True, 'surrogateTrainingAuthorized': False, 'productionModelReady': False, 'observationValidationRequired': True}

def plan(manifest_path: Path, guard_path: Path, adapter_path: Path, runtime_lock_path: Path, workflow_path: Path) -> dict[str, Any]:
    manifest = load(manifest_path)
    authorized = load(guard_path)
    if manifest.get('stageId') != STAGE_ID or authorized.get('status') != 'AUTHORIZED':
        raise StageError('manifest or guard invalid')
    cases = manifest.get('cases')
    if not isinstance(cases, list) or len(cases) != 4:
        raise StageError('four cases required')
    normalized = []
    matrix = []
    for case in cases:
        normalized.append({key: case[key] for key in ('ordinal', 'caseId', 'groupId', 'method', 'block', 'seed', 'photonHistories', 'alisSpectralImportanceSamplingNm', 'purpose')})
        matrix.append({'case_id': case['caseId'], 'ordinal': case['ordinal'], 'seed': case['seed'], 'photon_histories': case['photonHistories']})
    return {'schemaVersion': 1, 'stageId': 'mystic-batch-v1', 'batchId': manifest['batchId'], 'scientificExecution': True, 'scientificDiagnostic': True, 'successDoesNotAuthorizeProduction': True, 'authorizationRef': authorized['authorizationRef'], 'authorizationOrdinal': authorized['authorizationOrdinal'], 'executionKey': authorized['executionKey'], 'manifestRawSha256': raw_sha256(manifest_path), 'scientificAdapterRawSha256': raw_sha256(adapter_path), 'runtimeLockRawSha256': raw_sha256(runtime_lock_path), 'executionWorkflowRawSha256': raw_sha256(workflow_path), 'caseCount': 4, 'configuredMcPhotonsSum': 200000000, 'maximumParallel': 4, 'perCaseTimeoutSeconds': 900, 'cases': normalized, 'matrix': matrix, 'boundary': 'four fixed g01 diagnostic blocks only; no retry or automatic continuation'}

def module_from_path(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise StageError(f'cannot load module: {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def find_case_rows(root: Path) -> list[dict[str, Any]]:
    return [load(path) for path in sorted(root.rglob('case-result.json'))]

def validate_case(row: dict[str, Any], expected_id: str, expected_seed: int, expected_photons: int) -> None:
    required = {'caseId': expected_id, 'status': 'COMPLETED', 'seed': expected_seed, 'photonHistories': expected_photons, 'syntaxCheckCount': 1, 'solverExecutionCount': 1}
    stale = {key: (row.get(key), value) for key, value in required.items() if row.get(key) != value}
    if stale:
        raise StageError(f'case invariant failed: {expected_id}: {stale}')
    syntax = row.get('syntax')
    solver = row.get('solver')
    if not isinstance(syntax, dict) or syntax.get('exitCode') != 0 or syntax.get('timedOut') is not False:
        raise StageError(f'syntax failed: {expected_id}')
    if not isinstance(solver, dict) or solver.get('exitCode') != 0 or solver.get('timedOut') is not False:
        raise StageError(f'solver failed: {expected_id}')
    if not math.isfinite(float(row.get('selectedPhotopicContributionCdM2', math.nan))) or float(row['selectedPhotopicContributionCdM2']) <= 0:
        raise StageError(f'invalid luminance: {expected_id}')
    if len(row.get('selectedNodeRadiance', [])) != NODES:
        raise StageError(f'node vector invalid: {expected_id}')

def method_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    values = [float(row['selectedPhotopicContributionCdM2']) for row in rows]
    mean = statistics.fmean(values)
    sample_std = statistics.stdev(values)
    node_mean = [statistics.fmean(float(row['selectedNodeRadiance'][index]) for row in rows) for index in range(NODES)]
    return {'blockCount': len(rows), 'valuesCdM2': values, 'meanCdM2': mean, 'sampleStandardDeviationCdM2': sample_std, 'coefficientOfVariation': sample_std / mean, 'relativeStandardErrorOfMean': sample_std / mean / math.sqrt(len(rows)), 'nodeMeanRadiance': node_mean, 'reportedNodeStdAvailable': False, 'photopicWeightedReportedRelativeStd': None}

def analyze(diagnosis_path: Path, proposal_path: Path, manifest_path: Path, source_analysis_path: Path, source_readiness_path: Path, source_dataset_path: Path, old_cases_root: Path, new_cases_root: Path, batch_summary_path: Path, audit_path: Path, convergence_module_path: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    diagnosis = load(diagnosis_path)
    proposal = load(proposal_path)
    manifest = load(manifest_path)
    source_analysis = load(source_analysis_path)
    source_readiness = load(source_readiness_path)
    source_dataset = load(source_dataset_path)
    batch = load(batch_summary_path)
    independent_audit = load(audit_path)
    required_source_analysis = {'schemaVersion': 1, 'stageId': 'cross-geometry-held-out-confirmation-timeout-continuation-v1', 'status': 'TIMEOUT_CONTINUATION_ANALYZED', 'computationalReferenceScreeningComplete': False, 'noAutomaticAdditionalBlocks': True, 'screeningOnly': True, 'successDoesNotAuthorizeProduction': True}
    stale = {key: (source_analysis.get(key), expected) for key, expected in required_source_analysis.items() if source_analysis.get(key) != expected}
    if stale:
        raise StageError(f'source ordinal-6 analysis changed: {stale}')
    required_source_readiness = {'schemaVersion': 1, 'status': 'COMPUTATIONAL_REFERENCE_SCREENING_REQUIRES_DIAGNOSIS', 'computationalReferenceScreeningComplete': False, 'acceptedReferenceGeometryCount': 5, 'heldOutConfirmationFailureCount': 1, 'noAutomaticAdditionalBlocks': True, 'productionModelReady': False, 'observationValidationRequired': True, 'surrogateTrainingAutomaticallyAuthorized': False}
    stale = {key: (source_readiness.get(key), expected) for key, expected in required_source_readiness.items() if source_readiness.get(key) != expected}
    if stale or source_readiness.get('technicalDiagnosisRequiredGeometryIds') != [GROUP_ID]:
        raise StageError(f'source ordinal-6 readiness changed: {stale}')
    if diagnosis.get('sourceAnalysisRawSha256') != raw_sha256(source_analysis_path):
        raise StageError('diagnosis no longer binds source ordinal-6 analysis')
    if diagnosis.get('sourceReadinessRawSha256') != raw_sha256(source_readiness_path):
        raise StageError('diagnosis no longer binds source ordinal-6 readiness')
    if diagnosis.get('sourceDatasetRawSha256') != raw_sha256(source_dataset_path):
        raise StageError('diagnosis no longer binds source five-record dataset')
    if diagnosis.get('status') != 'G01_MONTE_CARLO_PRECISION_DIAGNOSED' or proposal.get('stageId') != STAGE_ID:
        raise StageError('diagnosis or proposal invalid')
    if manifest.get('stageId') != STAGE_ID or len(manifest.get('cases', [])) != 4:
        raise StageError('manifest invalid')
    if batch.get('classification') != 'BATCH_NUMERICALLY_COMPLETE' or batch.get('caseCountCompleted') != 4 or batch.get('configuredMcPhotonsSum') != 200000000:
        raise StageError('new batch incomplete')
    if independent_audit.get('status') != 'PASSED' or independent_audit.get('caseResultCount') != 4:
        raise StageError('new batch independent audit failed')
    old_rows = find_case_rows(old_cases_root)
    new_rows = find_case_rows(new_cases_root)
    if len(old_rows) != 4 or len(new_rows) != 4:
        raise StageError('expected four old and four new g01 rows')
    old_rows.sort(key=lambda row: row['caseId'])
    new_rows.sort(key=lambda row: row['caseId'])
    for index, row in enumerate(old_rows, start=1):
        validate_case(row, f'cgc-g01-alis-r{index}', 80600 + index, 50000000)
    for index, row in enumerate(new_rows, start=1):
        validate_case(row, NEW_CASE_IDS[index - 1], NEW_SEEDS[index - 1], 50000000)
    alis = method_summary(old_rows + new_rows)
    vroom = diagnosis.get('frozenVroomStatistics')
    if not isinstance(vroom, dict) or vroom.get('blockCount') != 6:
        raise StageError('frozen VROOM statistics invalid')
    convergence = module_from_path('g01_convergence', convergence_module_path)
    compatibility = convergence.classify({'reference-vroom': vroom, 'alis': alis}, {'integratedMeanRatioAlisToVroomClosedInterval': RATIO_INTERVAL, 'minimumVroomPhotopicWeightFractionNodeRatioInsideInterval': MIN_NODE_AGREEMENT, 'maximumRelativeStandardErrorOfMean': TARGET_RSEM})
    ratio = float(compatibility['meanRatioAlisToVroom'])
    node_agreement = float(compatibility['vroomPhotopicWeightFractionNodeRatioInsideInterval'])
    precision_ok = float(alis['relativeStandardErrorOfMean']) <= TARGET_RSEM and float(vroom['relativeStandardErrorOfMean']) <= VROOM_MAX_RSEM
    compatibility_ok = RATIO_INTERVAL[0] <= ratio <= RATIO_INTERVAL[1] and node_agreement >= MIN_NODE_AGREEMENT
    if precision_ok and compatibility_ok:
        classification = 'G01_FIXED_PRECISION_DIAGNOSIS_PASSED'
        next_action = 'COMPLETE_SIX_GEOMETRY_REFERENCE_DATASET'
    elif compatibility_ok:
        classification = 'G01_PERSISTENT_HIGH_VARIANCE'
        next_action = 'STOP_G01_BLOCKS_TECHNICAL_VARIANCE_REVIEW'
    else:
        classification = 'G01_METHOD_DISCREPANCY'
        next_action = 'STOP_G01_BLOCKS_METHOD_DIAGNOSIS'
    result = {'schemaVersion': 1, 'stageId': STAGE_ID, 'status': 'G01_FIXED_PRECISION_DIAGNOSIS_ANALYZED', 'classification': classification, 'nextAction': next_action, 'groupId': GROUP_ID, 'selectedAlisReferenceNm': 600.0, 'preservedHeldOutBlockCount': 4, 'newDiagnosticBlockCount': 4, 'combinedAlisBlockCount': 8, 'newConfiguredMcPhotonsSum': 200000000, 'methodStatistics': {'reference-vroom': vroom, 'alis': alis}, 'meanRatioAlisToVroom': ratio, 'nodeMeanRatiosAlisToVroom': compatibility['nodeMeanRatiosAlisToVroom'], 'vroomPhotopicWeightFractionNodeRatioInsideInterval': node_agreement, 'targetRelativeStandardErrorOfMean': TARGET_RSEM, 'frozenReferenceMaximumRelativeStandardErrorOfMean': VROOM_MAX_RSEM, 'integratedMeanRatioAlisToVroomClosedInterval': RATIO_INTERVAL, 'minimumVroomPhotopicWeightFractionNodeRatioInsideInterval': MIN_NODE_AGREEMENT, 'selectionDataExcludedFromAcceptanceDecision': True, 'noAutomaticAdditionalBlocks': True, 'successDoesNotAuthorizeProduction': True, 'surrogateTrainingAutomaticallyAuthorized': False, 'productionModelReady': False, 'observationValidationRequired': True, 'boundary': 'fixed final g01 precision diagnosis only; no additional blocks, model fitting, or production claim'}
    existing = source_dataset.get('records')
    expected_existing_ids = {'g02-early-near-low', 'g03-early-perpendicular-high', 'g04-mid-perpendicular', 'g05-mid-opposite-low', 'g06-late-opposite-high-aerosol'}
    actual_existing_ids = {item.get('groupId') for item in existing if isinstance(item, dict)} if isinstance(existing, list) else set()
    if not isinstance(existing, list) or len(existing) != 5 or actual_existing_ids != expected_existing_ids:
        raise StageError(f'source five-record dataset invalid: {sorted(actual_existing_ids)}')
    geometry = manifest['geometries'][0]
    g01_record = {'groupId': GROUP_ID, 'geometry': {key: geometry[key] for key in ('geometryId', 'sunDepressionDeg', 'targetAltitudeDeg', 'relativeAzimuthDeg', 'observerElevationM', 'aod550')}, 'classification': classification, 'methodOrigins': {'reference-vroom': 'frozen-six-block-final-convergence-reference', 'alis': 'eight-independent-held-out-and-fixed-diagnostic-blocks-at-600-nm'}, 'methodStatistics': {'reference-vroom': vroom, 'alis': alis}, 'meanRatioAlisToVroom': ratio, 'nodeMeanRatiosAlisToVroom': compatibility['nodeMeanRatiosAlisToVroom'], 'vroomPhotopicWeightFractionNodeRatioInsideInterval': node_agreement, 'screeningOnly': True, 'observationValidationRequired': True, 'successDoesNotAuthorizeProduction': True}
    if classification == 'G01_FIXED_PRECISION_DIAGNOSIS_PASSED':
        records = sorted(existing + [g01_record], key=lambda item: item['groupId'])
        dataset_status = 'AUDITED_COMPUTATIONAL_REFERENCE_DATASET'
        complete = True
        diagnosis_ids: list[str] = []
    else:
        records = existing
        dataset_status = 'INCOMPLETE_COMPUTATIONAL_REFERENCE_DATASET'
        complete = False
        diagnosis_ids = [GROUP_ID]
    dataset = {'schemaVersion': 1, 'stageId': STAGE_ID, 'status': dataset_status, 'screeningOnly': True, 'successDoesNotAuthorizeProduction': True, 'observationValidationRequired': True, 'computationalReferenceScreeningComplete': complete, 'records': records, 'technicalDiagnosisRequiredGeometryIds': diagnosis_ids}
    readiness = {'schemaVersion': 1, 'stageId': STAGE_ID, 'status': 'COMPUTATIONAL_REFERENCE_SCREENING_COMPLETE' if complete else 'COMPUTATIONAL_REFERENCE_SCREENING_REMAINS_INCOMPLETE_NO_MORE_BLOCKS', 'computationalReferenceScreeningComplete': complete, 'acceptedReferenceGeometryCount': len(records), 'g01Classification': classification, 'technicalDiagnosisRequiredGeometryIds': diagnosis_ids, 'noAutomaticAdditionalBlocks': True, 'surrogateTrainingAutomaticallyAuthorized': False, 'productionModelReady': False, 'observationValidationRequired': True}
    return result, dataset, readiness

def authorization_proposal(root: Path, source_audit_path: Path, manifest_path: Path) -> dict[str, Any]:
    source = load(source_audit_path)
    manifest = load(manifest_path)
    template = load(root / AUTH_TEMPLATE_PATH)
    active = load(root / AUTH_PATH)
    if active != template or template.get('authorized') is not False or template.get('authorizationOrdinal') != 0:
        raise StageError('active authorization is not exactly disabled')
    if source.get('status') != 'G01_DIAGNOSIS_SOURCE_AUDITED' or manifest.get('stageId') != STAGE_ID:
        raise StageError('source audit or manifest invalid')
    parent = git(root, 'rev-parse', 'HEAD')
    authorization = dict(template)
    authorization.update({'authorized': True, 'scientificExecution': True, 'scientificDiagnostic': True, 'executionKey': EXECUTION_KEY, 'sourceDiagnosisRunId': source['sourceDiagnosisRunId'], 'sourceDiagnosisArtifactId': source['sourceDiagnosisArtifactId'], 'sourceDiagnosisArtifactDigest': source['sourceDiagnosisArtifactDigest'], 'sourceDiagnosisAuditRawSha256': raw_sha256(source_audit_path), 'manifestRawSha256': raw_sha256(manifest_path), 'exactAuthorizationParentCommit': parent, 'exactAuthorizationCommit': None, 'authorizationOrdinal': AUTHORIZATION_ORDINAL, 'consumed': False, 'note': 'One-purpose fixed g01 precision diagnosis authorization proposal; copy unchanged into a single-file child commit before manual dispatch.'})
    for field, path in bound_paths().items():
        authorization[field] = raw_sha256(root / path)
    return {'schemaVersion': 1, 'stageId': 'g01-fixed-precision-diagnosis-authorization-proposal-v1', 'status': 'PROPOSAL_ONLY_NOT_AUTHORIZATION', 'executionAuthorizedByProposal': False, 'scientificExecution': False, 'sourceDiagnosisRunId': source['sourceDiagnosisRunId'], 'sourceDiagnosisArtifactId': source['sourceDiagnosisArtifactId'], 'sourceDiagnosisArtifactDigest': source['sourceDiagnosisArtifactDigest'], 'sourceDiagnosisAuditRawSha256': raw_sha256(source_audit_path), 'manifestRawSha256': raw_sha256(manifest_path), 'authorizationPath': AUTH_PATH.as_posix(), 'exactAuthorizationParentCommit': parent, 'executionKey': EXECUTION_KEY, 'authorizationOrdinal': AUTHORIZATION_ORDINAL, 'caseCount': 4, 'configuredMcPhotonsSum': 200000000, 'authorization': authorization, 'boundary': 'proposal only; no syntax check, solver, authorization commit, retry, or automatic continuation'}

def write_result(output: Path, value: dict[str, Any]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(dump(value))
    print(dump(value), end='')

def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('source-audit')
    for name in ('diagnosis', 'proposal', 'readiness', 'source-run', 'source-artifacts', 'output'):
        p.add_argument(f'--{name}', type=Path, required=True)
    p = sub.add_parser('build-manifest')
    p.add_argument('--proposal', type=Path, required=True)
    p.add_argument('--pilot-manifest', type=Path, required=True)
    p.add_argument('--source-audit', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p = sub.add_parser('guard')
    p.add_argument('--repository-root', type=Path, required=True)
    p.add_argument('--authorization', type=Path, required=True)
    p.add_argument('--authorization-template', type=Path, required=True)
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--source-audit', type=Path, required=True)
    p.add_argument('--authorization-ref', required=True)
    p.add_argument('--execution-key', required=True)
    p.add_argument('--authorization-ordinal', type=int, required=True)
    p.add_argument('--output', type=Path, required=True)
    p = sub.add_parser('plan')
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--guard-report', type=Path, required=True)
    p.add_argument('--adapter', type=Path, required=True)
    p.add_argument('--runtime-lock', type=Path, required=True)
    p.add_argument('--workflow', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--github-output', type=Path)
    p = sub.add_parser('analyze')
    for name in ('diagnosis', 'proposal', 'manifest', 'source-analysis', 'source-readiness', 'source-dataset', 'old-cases-root', 'new-cases-root', 'summary', 'audit', 'convergence-module', 'output-dir'):
        p.add_argument(f'--{name}', type=Path, required=True)
    p = sub.add_parser('authorization-proposal')
    p.add_argument('--repository-root', type=Path, required=True)
    p.add_argument('--source-audit', type=Path, required=True)
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == 'source-audit':
            write_result(args.output, source_audit(args.diagnosis, args.proposal, args.readiness, args.source_run, args.source_artifacts))
        elif args.command == 'build-manifest':
            write_result(args.output, build_manifest(args.proposal, args.pilot_manifest, args.source_audit))
        elif args.command == 'guard':
            write_result(args.output, guard(args.repository_root.resolve(), args.authorization, args.authorization_template, args.manifest, args.source_audit, args.authorization_ref, args.execution_key, args.authorization_ordinal))
        elif args.command == 'plan':
            result = plan(args.manifest, args.guard_report, args.adapter, args.runtime_lock, args.workflow)
            write_result(args.output, result)
            if args.github_output:
                with args.github_output.open('a') as handle:
                    handle.write('matrix=' + json.dumps({'include': result['matrix']}, separators=(',', ':')) + '\nmax_parallel=4\ntimeout_seconds=900\n')
        elif args.command == 'analyze':
            result, dataset, readiness = analyze(args.diagnosis, args.proposal, args.manifest, args.source_analysis, args.source_readiness, args.source_dataset, args.old_cases_root, args.new_cases_root, args.summary, args.audit, args.convergence_module)
            args.output_dir.mkdir(parents=True, exist_ok=True)
            (args.output_dir / 'g01-fixed-diagnostic-analysis.json').write_text(dump(result))
            (args.output_dir / 'audited-reference-dataset.json').write_text(dump(dataset))
            (args.output_dir / 'reference-readiness.json').write_text(dump(readiness))
            print(dump(result), end='')
        else:
            write_result(args.output, authorization_proposal(args.repository_root.resolve(), args.source_audit, args.manifest))
        return 0
    except Exception as exc:
        print(dump({'schemaVersion': 1, 'stageId': STAGE_ID, 'status': 'REFUSED', 'reason': str(exc)}), file=sys.stderr, end='')
        return 2
if __name__ == '__main__':
    raise SystemExit(main())
