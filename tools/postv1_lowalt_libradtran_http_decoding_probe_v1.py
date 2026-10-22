#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import shutil
import urllib.request
from pathlib import Path
from typing import Any

STAGE_ID = "postv1-lowalt-libradtran-http-decoding-probe-v1"
LITERAL_SOURCE_URL = "http://www.libradtran.org/download/libRadtran-2.0.6.tar.gz"
EXPECTED_CONDA_SOURCE_SHA256 = "999e47f4af4b5df6f85a6887fc105fc8f6e1a7cee89a3124f69ac8d8912c8e85"
KNOWN_WIRE_SHA256 = "64930cc40b6e4a37aa220520974d330fc1563796f466a649b2238131f2d69840"
PINNED_PACKAGE_SHA256 = "9090033a39a7e963ecabb31d5cbd264330c64ec1c4cb5f44be2e70f10cbc54c2"
PINNED_UVSPEC_SHA256 = "2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3"
PINNED_PACKAGE_ARTIFACT_ID = 8907428859
PINNED_PACKAGE_ARTIFACT_DIGEST = "sha256:2428a148fbcac0e68fe9bec41ecf5f53b775373786f025da759297246e9b4467"
PINNED_PACKAGE_BUILD_HEAD = "85248fcf7d0c3f1e1a79df69f362353998ca3e81"
PINNED_CONDA_TAG = "26.1.1"
PINNED_CONDA_COMMIT = "a0b1779edb6df26600b9aa6f2bc9d466f512b0ed"
PINNED_REQUESTS_TAG = "v2.32.5"
PINNED_REQUESTS_COMMIT = "b25c87d7cb8d6a18a37fa12442b5f883f9e41741"
PINNED_URLLIB3_TAG = "2.6.3"
PINNED_URLLIB3_COMMIT = "0248277dd7ac0239204889ca991353ad3e3a1ddc"


class RedirectRecorder(urllib.request.HTTPRedirectHandler):
    def __init__(self) -> None:
        super().__init__()
        self.chain: list[dict[str, Any]] = []

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        self.chain.append(
            {
                "status": int(code),
                "fromUrl": req.full_url,
                "toUrl": newurl,
            }
        )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def gzip_decode_file(source: Path, destination: Path) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(source, "rb") as input_handle, destination.open("wb") as output_handle:
        shutil.copyfileobj(input_handle, output_handle, length=1024 * 1024)
    return {
        "sizeBytes": destination.stat().st_size,
        "sha256": sha256_file(destination),
    }


def download_wire(destination: Path, timeout: int) -> dict[str, Any]:
    recorder = RedirectRecorder()
    opener = urllib.request.build_opener(recorder)
    request = urllib.request.Request(
        LITERAL_SOURCE_URL,
        headers={
            "User-Agent": "postv1-lowalt-libradtran-http-decoding-probe/1",
            "Accept": "*/*",
        },
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    with opener.open(request, timeout=timeout) as response, destination.open("wb") as output:
        shutil.copyfileobj(response, output, length=1024 * 1024)
        headers = {str(k).lower(): str(v) for k, v in response.headers.items()}
        final_url = response.geturl()
        status = int(getattr(response, "status", response.getcode()))
    return {
        "requestedUrl": LITERAL_SOURCE_URL,
        "finalUrl": final_url,
        "status": status,
        "redirectChain": recorder.chain,
        "responseHeaders": headers,
        "sizeBytes": destination.stat().st_size,
        "sha256": sha256_file(destination),
    }


def classify(wire: dict[str, Any], decoded: dict[str, Any] | None) -> dict[str, Any]:
    wire_match = wire["sha256"] == EXPECTED_CONDA_SOURCE_SHA256
    decoded_match = bool(decoded and decoded["sha256"] == EXPECTED_CONDA_SOURCE_SHA256)
    if wire_match:
        representation = "wire"
    elif decoded_match:
        representation = "http-content-decoded"
    else:
        representation = None
    return {
        "expectedSourceSha256": EXPECTED_CONDA_SOURCE_SHA256,
        "wireMatchesExpected": wire_match,
        "decodedMatchesExpected": decoded_match,
        "matchingRepresentation": representation,
        "sourceRepresentationRecovered": representation is not None,
    }


def run(output_dir: Path, timeout: int, preserve_match: bool) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    wire_path = output_dir / "wire-response.bin"
    decoded_path = output_dir / "content-decoded.bin"
    wire = download_wire(wire_path, timeout)

    content_encoding = wire["responseHeaders"].get("content-encoding", "").strip().lower()
    decoded: dict[str, Any] | None = None
    if content_encoding in {"gzip", "x-gzip"}:
        decoded = gzip_decode_file(wire_path, decoded_path)
        decoded["contentEncoding"] = content_encoding
    decision = classify(wire, decoded)

    preserved: list[str] = []
    if preserve_match:
        if decision["matchingRepresentation"] == "wire":
            preserved.append(wire_path.name)
        elif decision["matchingRepresentation"] == "http-content-decoded":
            preserved.append(decoded_path.name)
    if wire_path.name not in preserved:
        wire_path.unlink(missing_ok=True)
    if decoded_path.name not in preserved:
        decoded_path.unlink(missing_ok=True)

    report = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": (
            "EXACT_SOURCE_REPRESENTATION_RECOVERED"
            if decision["sourceRepresentationRecovered"]
            else "EXACT_SOURCE_REPRESENTATION_NOT_RECOVERED"
        ),
        "literalHttpRouteUsed": wire["requestedUrl"] == LITERAL_SOURCE_URL,
        "httpsSubstitutionPerformed": False,
        "wire": wire,
        "decoded": decoded,
        "decision": decision,
        "knownPriorWireSha256": KNOWN_WIRE_SHA256,
        "wireMatchesKnownPrior": wire["sha256"] == KNOWN_WIRE_SHA256,
        "pinnedRuntime": {
            "packageSha256": PINNED_PACKAGE_SHA256,
            "uvspecSha256": PINNED_UVSPEC_SHA256,
            "packageEvidenceArtifactId": PINNED_PACKAGE_ARTIFACT_ID,
            "packageEvidenceArtifactDigest": PINNED_PACKAGE_ARTIFACT_DIGEST,
            "packageBuildHead": PINNED_PACKAGE_BUILD_HEAD,
        },
        "pinnedDownloaderSemantics": {
            "conda": {"tag": PINNED_CONDA_TAG, "commit": PINNED_CONDA_COMMIT},
            "requests": {"tag": PINNED_REQUESTS_TAG, "commit": PINNED_REQUESTS_COMMIT},
            "urllib3": {"tag": PINNED_URLLIB3_TAG, "commit": PINNED_URLLIB3_COMMIT},
            "semanticContract": (
                "conda writes Requests iter_content() chunks to the checksum target; "
                "Requests asks urllib3 stream(..., decode_content=True); urllib3 treats x-gzip as gzip"
            ),
        },
        "preservedMatchingFiles": preserved,
        "scientificExecution": False,
        "solverExecutionCount": 0,
        "protectedResultsOpened": False,
        "identitySeedOrdinalAllocated": False,
        "v1SeamChanged": False,
        "v1FloorDegrees": 5.0,
        "postV1Only": True,
    }
    report_path = output_dir / "report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--preserve-match", action="store_true")
    args = parser.parse_args()
    try:
        report = run(args.output_dir, args.timeout, args.preserve_match)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        failure = {
            "schemaVersion": 1,
            "stageId": STAGE_ID,
            "status": "REFUSED",
            "reason": f"{type(exc).__name__}: {exc}",
            "scientificExecution": False,
            "solverExecutionCount": 0,
            "protectedResultsOpened": False,
            "identitySeedOrdinalAllocated": False,
            "v1SeamChanged": False,
            "v1FloorDegrees": 5.0,
            "postV1Only": True,
        }
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "report.json").write_text(
            json.dumps(failure, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(json.dumps(failure, indent=2, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
