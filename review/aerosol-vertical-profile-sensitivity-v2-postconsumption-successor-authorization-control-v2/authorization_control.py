from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
CORE_PATH = HERE / "authorization_control_core_v1.py"
EXPECTED_CORE_BLOB = "4cb6bca83c85b649d69f8daeb808fe8809f1e2c5"

WORKFLOW_PATH = ".github/workflows/avps-v2-postconsumption-successor-authorization-control-v2.yml"
SCRIPT_PATH = "review/aerosol-vertical-profile-sensitivity-v2-postconsumption-successor-authorization-control-v2/authorization_control.py"
CORE_VENDOR_PATH = "review/aerosol-vertical-profile-sensitivity-v2-postconsumption-successor-authorization-control-v2/authorization_control_core_v1.py"
CONTROL_BRANCH = "review/avps-v2-postconsumption-successor-authorization-control-replacement-v2-20260909"
CONTROL_STAGE = "AVPS_V2_POSTCONSUMPTION_SUCCESSOR_AUTHORIZATION_CONTROL_GLOBAL_SCAN_V2"
CONTROL_ARTIFACT_NAME = "vertical-profile-v2-postconsumption-successor-authorization-control-v2-proof"


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


if git_blob_sha1(CORE_PATH) != EXPECTED_CORE_BLOB:
    raise RuntimeError("frozen authorization-control core byte drift")
spec = importlib.util.spec_from_file_location("avps_successor_authorization_control_core_v1", CORE_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError("cannot load frozen authorization-control core")
core = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = core
spec.loader.exec_module(core)

# Fresh versioned identity only. All frozen scientific/source bindings remain in the core.
core.WORKFLOW_PATH = WORKFLOW_PATH
core.SCRIPT_PATH = SCRIPT_PATH
core.ALLOWED_PATHS = sorted([WORKFLOW_PATH, SCRIPT_PATH, CORE_VENDOR_PATH])
core.CONTROL_DIR = HERE
core.CONTROL_BRANCH = CONTROL_BRANCH
core.CONTROL_STAGE = CONTROL_STAGE
core.CONTROL_ARTIFACT_NAME = CONTROL_ARTIFACT_NAME


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _origin(url: str) -> tuple[str, str, int | None]:
    p = urllib.parse.urlsplit(url)
    return p.scheme.lower(), (p.hostname or "").lower(), p.port


def _github_request(url: str, token: str) -> urllib.request.Request:
    return urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "avps-successor-authorization-control-v2",
        },
    )


def _anonymous_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "avps-successor-authorization-control-v2"})
    try:
        with urllib.request.urlopen(req, timeout=90) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        raise core.Refusal(f"signed artifact storage request failed HTTP {exc.code}") from None
    except urllib.error.URLError as exc:
        raise core.Refusal(f"signed artifact storage request failed: {type(exc.reason).__name__}") from None


def safe_request_bytes(url: str, token: str, _hops: int = 0) -> bytes:
    """Authenticate GitHub API only; never forward credentials to another origin."""
    core.require(_hops <= 5, "too many HTTP redirects")
    opener = urllib.request.build_opener(_NoRedirect())
    req = _github_request(url, token)
    try:
        with opener.open(req, timeout=90) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        if exc.code not in (301, 302, 303, 307, 308):
            raise core.Refusal(f"GitHub API request failed HTTP {exc.code}") from None
        location = exc.headers.get("Location")
        core.require(bool(location), "GitHub API redirect missing Location")
        target = urllib.parse.urljoin(url, location)
        if _origin(target) == _origin(url):
            return safe_request_bytes(target, token, _hops + 1)
        return _anonymous_bytes(target)
    except urllib.error.URLError as exc:
        raise core.Refusal(f"GitHub API request failed: {type(exc.reason).__name__}") from None


def _require_digest(raw: bytes, expected: str) -> str:
    actual = "sha256:" + hashlib.sha256(raw).hexdigest()
    core.require(actual == expected, "downloaded source artifact byte digest drift")
    return actual


class _FixtureState:
    first_authorization: str | None = None
    second_authorization: str | None = None
    target_url: str | None = None


def artifact_redirect_fixture() -> dict[str, Any]:
    state = _FixtureState()
    payload = b"avps-cross-origin-artifact-fixture-v2\n"
    expected = "sha256:" + hashlib.sha256(payload).hexdigest()

    class StorageHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            state.second_authorization = self.headers.get("Authorization")
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, fmt, *args):
            return

    storage = ThreadingHTTPServer(("127.0.0.1", 0), StorageHandler)
    storage_thread = threading.Thread(target=storage.serve_forever, daemon=True)
    storage_thread.start()
    storage_port = storage.server_address[1]

    class ApiHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            state.first_authorization = self.headers.get("Authorization")
            # Dummy signed-query value is deliberately never returned/logged.
            state.target_url = f"http://127.0.0.1:{storage_port}/artifact.zip?sig=fixture-secret"
            self.send_response(302)
            self.send_header("Location", state.target_url)
            self.end_headers()

        def log_message(self, fmt, *args):
            return

    api = ThreadingHTTPServer(("127.0.0.1", 0), ApiHandler)
    api_thread = threading.Thread(target=api.serve_forever, daemon=True)
    api_thread.start()
    api_port = api.server_address[1]
    try:
        raw = safe_request_bytes(f"http://127.0.0.1:{api_port}/artifact", "fixture-token")
        core.require(state.first_authorization == "Bearer fixture-token", "GitHub-origin credential missing in redirect fixture")
        core.require(state.second_authorization is None, "credential leaked to cross-origin signed artifact storage")
        core.require(raw == payload, "cross-origin artifact fixture byte drift")
        _require_digest(raw, expected)
        mismatch_refused = False
        try:
            _require_digest(raw, "sha256:" + "0" * 64)
        except core.Refusal:
            mismatch_refused = True
        core.require(mismatch_refused, "artifact digest mismatch was not refused")
        return {
            "schemaVersion": 1,
            "githubOriginAuthorizationPresent": True,
            "crossOriginAuthorizationAbsent": True,
            "crossOriginRedirectFollowedWithFreshAnonymousRequest": True,
            "payloadSha256": expected,
            "matchingDigestAccepted": True,
            "mismatchingDigestRefused": True,
            "signedQueryLogged": False,
        }
    finally:
        api.shutdown()
        storage.shutdown()
        api.server_close()
        storage.server_close()


def _related_pr_number(row: dict[str, Any]) -> int | None:
    for key in ("issue_url", "pull_request_url"):
        value = str(row.get(key) or "")
        match = re.search(r"/(?:issues|pulls)/([1-9][0-9]*)$", value)
        if match:
            return int(match.group(1))
    return None


def _row_text(row: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("name", "path", "head_branch", "display_title", "title", "body"):
        value = row.get(key)
        if isinstance(value, str):
            parts.append(value)
    head = row.get("head") or {}
    if isinstance(head, dict) and isinstance(head.get("ref"), str):
        parts.append(head["ref"])
    return "\n".join(parts)


def _row_identity(surface: str, row: dict[str, Any]) -> str:
    ident = row.get("id") or row.get("number") or row.get("name") or row.get("url") or "unknown"
    return f"{surface}:{ident}"


def _structural_key_use(surface: str, row: dict[str, Any], execution_key: str) -> bool:
    fields: list[str] = []
    if surface == "branch":
        fields.append(str(row.get("name") or ""))
    elif surface == "run":
        for key in ("name", "path", "head_branch", "display_title"):
            fields.append(str(row.get(key) or ""))
    elif surface == "artifact":
        fields.append(str(row.get("name") or ""))
    elif surface == "pull":
        head = row.get("head") or {}
        if isinstance(head, dict):
            fields.append(str(head.get("ref") or ""))
    return any(execution_key in value for value in fields)


def _explicitly_non_authoritative_text(text: str, execution_key: str) -> bool:
    lowered = text.lower()
    # Exact key shown only as inline-code narrative remains provenance, not use.
    without_backtick_key = text.replace(f"`{execution_key}`", "")
    if execution_key not in without_backtick_key and f"`{execution_key}`" in text:
        return True
    # Questions are non-authoritative by the already-reviewed claim grammar.
    if any(execution_key in line and line.strip().endswith("?") for line in text.splitlines()):
        return True
    # Allow only explicit proposal/negation language; ambiguous bare occurrences fail closed.
    non_authoritative = re.compile(
        r"\b(?:proposal|proposed|planned|plan|pending|requested|request|not\s+created|"
        r"not\s+allocated|not\s+reserved|not\s+dispatched|not\s+consumed|not\s+applied|"
        r"never\s+created|never\s+allocated|never\s+reserved|never\s+dispatched|"
        r"unauthorized|unallocated|unreserved|proposal-only)\b",
        re.I,
    )
    return bool(non_authoritative.search(lowered))


def proposal_aware_execution_key_scan(
    payload: dict[str, Any],
    execution_key: str,
    ordinal: int,
    positive_candidate_claims,
    *,
    current_pr: int | None,
    current_run_id: int | None,
) -> dict[str, Any]:
    authoritative: set[str] = set()
    proposal_only: set[str] = set()
    surfaces = (
        ("branch", payload.get("branches", [])),
        ("run", payload.get("runs", [])),
        ("artifact", payload.get("artifacts", [])),
        ("pull", payload.get("pulls", [])),
        ("issue", payload.get("issues", [])),
        ("issue-comment", payload.get("issueComments", [])),
        ("pull-review-comment", payload.get("pullReviewComments", [])),
        ("commit-comment", payload.get("commitComments", [])),
        ("issue60-comment", payload.get("issue60Comments", [])),
    )
    issue60_ids = {str(r.get("id") or "") for r in payload.get("issue60Comments", [])}
    seen: set[tuple[str, str]] = set()
    for surface, rows in surfaces:
        for row in rows:
            if surface == "run" and current_run_id is not None and int(row.get("id") or 0) == current_run_id:
                continue
            if surface == "pull" and current_pr is not None and int(row.get("number") or 0) == current_pr:
                continue
            if surface in ("issue-comment", "pull-review-comment") and current_pr is not None and _related_pr_number(row) == current_pr:
                continue
            # issue60 rows are duplicated in the repository-wide issueComments endpoint.
            if surface == "issue-comment" and str(row.get("id") or "") in issue60_ids:
                continue
            packed = json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            if execution_key not in packed:
                continue
            ident = _row_identity(surface, row)
            unique = (surface, ident)
            if unique in seen:
                continue
            seen.add(unique)
            if _structural_key_use(surface, row, execution_key):
                authoritative.add(ident)
                continue
            text = _row_text(row)
            claims = positive_candidate_claims(text, ordinal)
            if claims:
                authoritative.add(ident)
            elif _explicitly_non_authoritative_text(text, execution_key):
                proposal_only.add(ident)
            else:
                authoritative.add(ident)
    return {
        "schemaVersion": 1,
        "executionKeyOccurrencesInspected": len(authoritative) + len(proposal_only),
        "authoritativeExecutionKeyUseCount": len(authoritative),
        "authoritativeExecutionKeyUseRows": sorted(authoritative),
        "proposalOrNegatedExecutionKeyProvenanceCount": len(proposal_only),
        "proposalOrNegatedExecutionKeyProvenanceRows": sorted(proposal_only),
        "reviewedPositiveClaimGrammarUsed": True,
    }


def proposal_aware_fixture() -> dict[str, Any]:
    preauth = core.load("avps_auth_control_fixture_preauth", core.ROOT / core.PREAUTH_SURFACE_PATH)
    freshness, _, _ = preauth._modules()
    key = freshness.execution_key(46)

    allowed_payload = {
        "branches": [], "runs": [], "artifacts": [], "pulls": [], "issues": [],
        "issueComments": [], "pullReviewComments": [], "commitComments": [],
        "issue60Comments": [
            {"id": 1, "body": f"Ordinal46 remains PROPOSED-ONLY / NOT ALLOCATED / NOT RESERVED / NOT DISPATCHED. executionKey `{key}`."},
            {"id": 2, "body": f"Could ordinal 46 later use `{key}`?"},
        ],
    }
    allowed = proposal_aware_execution_key_scan(allowed_payload, key, 46, freshness.positive_candidate_claims, current_pr=None, current_run_id=None)
    core.require(allowed["authoritativeExecutionKeyUseCount"] == 0, "proposal-aware fixture rejected non-authoritative provenance")
    core.require(allowed["proposalOrNegatedExecutionKeyProvenanceCount"] == 2, "proposal-aware fixture did not inspect expected provenance")

    factual_payload = {**allowed_payload, "issue60Comments": [{"id": 3, "body": f"The system allocated ordinal 46. executionKey={key}"}]}
    factual = proposal_aware_execution_key_scan(factual_payload, key, 46, freshness.positive_candidate_claims, current_pr=None, current_run_id=None)
    core.require(factual["authoritativeExecutionKeyUseCount"] == 1, "positive allocation claim was not rejected")

    structural_payload = {**allowed_payload, "issue60Comments": [], "runs": [{"id": 4, "path": f".github/workflows/{key}.yml", "head_branch": "x"}]}
    structural = proposal_aware_execution_key_scan(structural_payload, key, 46, freshness.positive_candidate_claims, current_pr=None, current_run_id=None)
    core.require(structural["authoritativeExecutionKeyUseCount"] == 1, "structural execution-key use was not rejected")

    ambiguous_payload = {**allowed_payload, "issue60Comments": [{"id": 5, "body": f"executionKey={key}"}]}
    ambiguous = proposal_aware_execution_key_scan(ambiguous_payload, key, 46, freshness.positive_candidate_claims, current_pr=None, current_run_id=None)
    core.require(ambiguous["authoritativeExecutionKeyUseCount"] == 1, "ambiguous bare execution-key occurrence did not fail closed")
    return {
        "schemaVersion": 1,
        "proposalAndNegatedProvenanceAccepted": True,
        "questionAndBacktickNarrativeAccepted": True,
        "positiveAllocationClaimRejected": True,
        "structuralRunIdentityRejected": True,
        "ambiguousBareExecutionKeyRejected": True,
        "reviewedPositiveClaimGrammarUsed": True,
    }


def dynamic_ordinal(repository: str, token: str, run_id: int, source_receipt: dict[str, Any], evidence: Path):
    preauth = core.load("avps_auth_control_dynamic_ordinal_v2", core.ROOT / core.PREAUTH_SURFACE_PATH)
    payload = preauth.collect(repository, token)
    latest = preauth.latest_consumed_or_dispatched_ordinal(payload)
    candidate, observations = preauth.derive_next_global_ordinal(payload, latest, current_run_id=run_id)
    core.require(latest == source_receipt["latestPriorConsumedOrDispatchedScientificOrdinal"] == 45, f"latest global ordinal drift: {latest}")
    core.require(candidate == source_receipt["nextAvailableScientificOrdinal"] == 46, f"next global ordinal changed: {candidate}")
    auth_branch = source_receipt["authorizationBranch"]
    dispatch_branch = source_receipt["dispatchBranch"]
    execution_key = source_receipt["executionKey"]
    branch_names = {str(r.get("name") or "") for r in payload.get("branches", [])}
    core.require(auth_branch not in branch_names and dispatch_branch not in branch_names, "ordinal46 authorization/dispatch ref already exists")
    proposed_paths = {source_receipt["proposedPublisherWorkflowPath"], source_receipt["proposedScienceWorkflowPath"]}
    core.require(not any(str(r.get("path") or "") in proposed_paths for r in payload.get("runs", [])), "ordinal46 proposed workflow run identity already exists")

    freshness, _, _ = preauth._modules()
    key_scan = proposal_aware_execution_key_scan(
        payload,
        execution_key,
        candidate,
        freshness.positive_candidate_claims,
        current_pr=None,
        current_run_id=run_id,
    )
    core.require(key_scan["authoritativeExecutionKeyUseCount"] == 0, f"ordinal46 execution key has authoritative prior use: {key_scan['authoritativeExecutionKeyUseRows']}")
    core.require(core.run("git", "grep", "-F", execution_key, check=False).returncode == 1, "ordinal46 execution key already appears in tracked bytes")
    comments = [str(r.get("body") or "").strip() for r in payload.get("issue60Comments", [])]
    core.require(not any(body.upper().startswith(f"ORDINAL{candidate}_") for body in comments), "ordinal46 allocation/consumption marker already exists")
    core.write_json(evidence / "global-ordinal-observations.json", observations)
    core.write_json(evidence / "proposal-aware-execution-key-scan.json", key_scan)
    return payload, latest, candidate, observations


_original_stress = core.stress


def stress(args) -> None:
    transport = artifact_redirect_fixture()
    proposal_fixture = proposal_aware_fixture()
    _original_stress(args)
    source_api = core.verify_source_api(args.repository, args.token)
    _, latest, candidate, _ = dynamic_ordinal(args.repository, args.token, args.run_id, source_api["receipt"], args.evidence_dir)
    core.require(latest == 45 and candidate == 46, "stress live proposal-aware dynamic ordinal proof drift")
    core.write_json(args.evidence_dir / "artifact-redirect-transport-fixture.json", transport)
    core.write_json(args.evidence_dir / "proposal-aware-execution-key-fixture.json", proposal_fixture)
    result_path = args.evidence_dir / "stress-result.json"
    result = json.loads(result_path.read_text())
    result.update({
        "crossOriginArtifactAuthorizationStripped": True,
        "artifactDigestMismatchRefused": True,
        "proposalAwareExecutionKeyFixturePassed": True,
        "currentLiveProposalAwareExecutionKeyCasePassed": True,
        "dynamicLatestConsumedOrDispatchedScientificOrdinal": latest,
        "dynamicNextScientificOrdinal": candidate,
    })
    core.write_json(result_path, result)


core.request_bytes = safe_request_bytes
core.dynamic_ordinal = dynamic_ordinal
core.stress = stress


def main() -> int:
    return core.main()


if __name__ == "__main__":
    raise SystemExit(main())
