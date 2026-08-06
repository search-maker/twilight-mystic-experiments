from __future__ import annotations

import hashlib
import io
import json
import re
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

SOURCE_HEAD_SHA = "f41f18af6c0c802cc4bad35186bd864f9680f81b"
SOURCE_RUN_ID = 31_078_099_534
SOURCE_ARTIFACT_ID = 8_958_327_171
SOURCE_ARTIFACT_ZIP_SHA256 = "b98b1275ac68cde7f162f27805e3bd5accfb47775df89e7e76a05376f44c21a6"
SOURCE_DATASET_RAW_SHA256 = "a6fd419ac79ae491896c22627a0d0605a5f688261ae8f03ef594517bb073c7ae"
SOURCE_DATASET_SHA256 = "f7fd12ac5921c039de3418960a5f3d94ea4820c549247390ff47c316b1111271"
SCIENTIFIC_RUN_ID = 31_070_968_611
SCIENTIFIC_HEAD_SHA = "6c22de3578b1b0dcbc640779baa66be8d1051fe1"
ANALYSIS_ARTIFACT_ID = 8_956_922_604
ANALYSIS_ARTIFACT_ZIP_SHA256 = "00fe0cecf2cef26d7438786fc9ddb249b4f804f02b8eade48dc1f2744b45dc07"
ANALYSIS_RAW_SHA256 = "f21548f0c6fe043ba5600ced1f0b19fbe569be6c2bca0de24ca5894dd6b01ad1"
TRAINING_IDS = {
    "train-0003", "train-0007", "train-0011", "train-0013", "train-0019",
    "train-0023", "train-0027", "train-0029", "train-0031", "train-0039",
    "train-0041", "train-0043", "train-0047",
}


class ArtifactRefusal(RuntimeError):
    pass


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, response_headers, newurl):
        redirected = super().redirect_request(req, fp, code, msg, response_headers, newurl)
        if (
            redirected is not None
            and urllib.parse.urlparse(req.full_url).netloc
            != urllib.parse.urlparse(newurl).netloc
        ):
            redirected.remove_header("Authorization")
        return redirected


def _client(repository: str, token: str):
    api_root = f"https://api.github.com/repos/{repository}"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "surrogate-training-v2-terminal-training-only-contract",
    }
    opener = urllib.request.build_opener(SafeRedirect())

    def request(url: str) -> bytes:
        with opener.open(urllib.request.Request(url, headers=headers), timeout=90) as response:
            return response.read()

    def api_json(url: str) -> dict[str, Any]:
        value = json.loads(request(url))
        if not isinstance(value, dict):
            raise ArtifactRefusal(f"expected GitHub object: {url}")
        return value

    return api_root, request, api_json


def _download_exact_artifact(api_root, request, api_json, artifact_id, run_id, head_sha, zip_sha):
    metadata = api_json(f"{api_root}/actions/artifacts/{artifact_id}")
    workflow = metadata.get("workflow_run", {})
    if workflow.get("id") != run_id or workflow.get("head_sha") != head_sha:
        raise ArtifactRefusal(f"artifact {artifact_id} run/head binding changed")
    data = request(metadata["archive_download_url"])
    digest = hashlib.sha256(data).hexdigest()
    if digest != zip_sha or metadata.get("digest", "").removeprefix("sha256:") != zip_sha:
        raise ArtifactRefusal(f"artifact {artifact_id} ZIP digest changed")
    return metadata, data


def _run_artifacts(api_root, api_json, run_id: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    page = 1
    while True:
        value = api_json(f"{api_root}/actions/runs/{run_id}/artifacts?per_page=100&page={page}")
        batch = value.get("artifacts", [])
        if not isinstance(batch, list):
            raise ArtifactRefusal("artifact page changed")
        rows.extend(batch)
        if len(batch) < 100:
            return rows
        page += 1


def download_inputs(repository: str, token: str, output_root: Path) -> dict[str, Any]:
    api_root, request, api_json = _client(repository, token)
    source_dir = output_root / "b1-b6"
    source_dir.mkdir(parents=True)
    _, data = _download_exact_artifact(
        api_root, request, api_json, SOURCE_ARTIFACT_ID, SOURCE_RUN_ID,
        SOURCE_HEAD_SHA, SOURCE_ARTIFACT_ZIP_SHA256,
    )
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        members = [name for name in archive.namelist() if name.endswith("wave2-training-only-dataset.json")]
        if len(members) != 1:
            raise ArtifactRefusal("b1-b6 source artifact member universe changed")
        source_bytes = archive.read(members[0])
    if hashlib.sha256(source_bytes).hexdigest() != SOURCE_DATASET_RAW_SHA256:
        raise ArtifactRefusal("b1-b6 source dataset raw hash changed")
    source_value = json.loads(source_bytes)
    if source_value.get("datasetSha256") != SOURCE_DATASET_SHA256:
        raise ArtifactRefusal("b1-b6 source dataset canonical hash changed")
    source_path = source_dir / "wave2-training-only-dataset.json"
    source_path.write_bytes(source_bytes)

    artifacts = _run_artifacts(api_root, api_json, SCIENTIFIC_RUN_ID)
    if len(artifacts) != 35 or len({row["name"] for row in artifacts}) != 35:
        raise ArtifactRefusal(f"ordinal-13 terminal artifact universe changed: {len(artifacts)}")
    pattern = re.compile(
        r"tier1-wave3-ordinal13-case-(?P<gid>train-\d{4})-precision-continuation-wave3-v1-b(?P<block>[78])"
    )
    selected = []
    for artifact in artifacts:
        match = pattern.fullmatch(artifact["name"])
        if match and match.group("gid") in TRAINING_IDS:
            selected.append(artifact)
    if len(selected) != 26:
        raise ArtifactRefusal(f"expected 26 ordinal-13 training case artifacts, found {len(selected)}")
    results_root = output_root / "wave3-results"
    results_root.mkdir()
    identities = set()
    case_zip_sha_by_name = {}
    for artifact in selected:
        if artifact.get("workflow_run", {}).get("head_sha") != SCIENTIFIC_HEAD_SHA:
            raise ArtifactRefusal(f"case artifact head changed: {artifact['name']}")
        data = request(artifact["archive_download_url"])
        digest = hashlib.sha256(data).hexdigest()
        if digest != artifact.get("digest", "").removeprefix("sha256:"):
            raise ArtifactRefusal(f"case artifact ZIP digest changed: {artifact['name']}")
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            members = [name for name in archive.namelist() if name.endswith("case-result.json")]
            if len(members) != 1:
                raise ArtifactRefusal(f"case artifact member universe changed: {artifact['name']}")
            result = json.loads(archive.read(members[0]))
        identity = (result.get("groupId"), result.get("block"))
        if identity in identities:
            raise ArtifactRefusal(f"duplicate ordinal-13 training case identity: {identity}")
        identities.add(identity)
        case_dir = results_root / artifact["name"]
        case_dir.mkdir()
        (case_dir / "case-result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        case_zip_sha_by_name[artifact["name"]] = digest
    expected_identities = {(gid, block) for gid in TRAINING_IDS for block in (7, 8)}
    if identities != expected_identities:
        raise ArtifactRefusal("ordinal-13 training case matrix changed")

    _, data = _download_exact_artifact(
        api_root, request, api_json, ANALYSIS_ARTIFACT_ID, SCIENTIFIC_RUN_ID,
        SCIENTIFIC_HEAD_SHA, ANALYSIS_ARTIFACT_ZIP_SHA256,
    )
    analysis_dir = output_root / "terminal-analysis"
    analysis_dir.mkdir()
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        members = [name for name in archive.namelist() if name.endswith("analysis.json")]
        if len(members) != 1:
            raise ArtifactRefusal("ordinal-13 analysis member universe changed")
        analysis_bytes = archive.read(members[0])
    if hashlib.sha256(analysis_bytes).hexdigest() != ANALYSIS_RAW_SHA256:
        raise ArtifactRefusal("ordinal-13 analysis raw hash changed")
    analysis_path = analysis_dir / "analysis.json"
    analysis_path.write_bytes(analysis_bytes)

    return {
        "sourceDatasetPath": str(source_path),
        "resultsRoot": str(results_root),
        "analysisPath": str(analysis_path),
        "sourceContractHeadSha": SOURCE_HEAD_SHA,
        "sourceContractRunId": SOURCE_RUN_ID,
        "sourceContractArtifactId": SOURCE_ARTIFACT_ID,
        "sourceContractArtifactZipSha256": SOURCE_ARTIFACT_ZIP_SHA256,
        "sourceTrainingDatasetRawSha256": SOURCE_DATASET_RAW_SHA256,
        "sourceTrainingDatasetSha256": SOURCE_DATASET_SHA256,
        "scientificRunId": SCIENTIFIC_RUN_ID,
        "scientificHeadSha": SCIENTIFIC_HEAD_SHA,
        "terminalArtifactCount": len(artifacts),
        "selectedTrainingCaseArtifactCount": len(selected),
        "trainingCaseArtifactZipSha256ByName": case_zip_sha_by_name,
        "terminalAnalysisArtifactId": ANALYSIS_ARTIFACT_ID,
        "terminalAnalysisArtifactZipSha256": ANALYSIS_ARTIFACT_ZIP_SHA256,
        "terminalAnalysisRawSha256": ANALYSIS_RAW_SHA256,
    }
